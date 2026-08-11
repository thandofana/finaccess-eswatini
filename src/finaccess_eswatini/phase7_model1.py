"""Phase 7 training and protected-holdout evaluation for financial inclusion.

Only Model 1 (``account_fin``) is handled here. Candidate pipelines are tuned
with group-aware training-fold cross-validation so identical predictor profiles
never cross folds. The protected holdout is evaluated only after selection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MPLBACKEND", "Agg")

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.deliverables import (
    render_delivery_checklist,
    validate_completed_phase_files,
)
from finaccess_eswatini.phase3_preprocessing import file_hash
from finaccess_eswatini.phase6_feature_engineering import (
    DEFAULT_MODEL1_OUTPUT,
    MODEL1_FINAL_FEATURES,
)


RANDOM_STATE = 42
CV_RANDOM_STATE = 43
HOLDOUT_SPLITS = 5
CV_SPLITS = 5
DECISION_THRESHOLD = 0.5
BOOTSTRAP_ITERATIONS = 1_000
MODEL1_INPUT_SHA256 = "37785e0819f1d050f94d395476aacd5440e9daf6a642174f813b7c2f70ab2ccc"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_7"
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "model1_financial_inclusion_pipeline.joblib"
DEFAULT_METADATA_PATH = PROJECT_ROOT / "models" / "model1_financial_inclusion_metadata.json"

SCORING = {
    "roc_auc": "roc_auc",
    "accuracy": "accuracy",
    "precision": "precision",
    "recall": "recall",
    "f1": "f1",
    "neg_brier": "neg_brier_score",
}


@dataclass(frozen=True)
class CandidateSpec:
    key: str
    label: str
    estimator: BaseEstimator
    param_grid: dict[str, list[object]]
    complexity_rank: int


def profile_groups(features: pd.DataFrame) -> pd.Series:
    """Create deterministic groups for identical predictor profiles."""

    return pd.util.hash_pandas_object(features, index=False).astype("string")


def _index_signature(index: pd.Index | np.ndarray) -> str:
    values = ",".join(str(int(value)) for value in np.asarray(index))
    return hashlib.sha256(values.encode("utf-8")).hexdigest()


def load_model_frame(path: Path = DEFAULT_MODEL1_OUTPUT) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Phase 6 Model 1 matrix not found: {path}")
    observed_hash = file_hash(path)
    if observed_hash != MODEL1_INPUT_SHA256:
        raise ValueError(
            f"Phase 6 Model 1 matrix hash changed: expected {MODEL1_INPUT_SHA256}, found {observed_hash}"
        )
    frame = pd.read_csv(path)
    expected = ["account_fin", *MODEL1_FINAL_FEATURES]
    if frame.columns.tolist() != expected or frame.shape != (1051, 16):
        raise ValueError("Phase 6 Model 1 matrix does not match the frozen schema.")
    if frame.isna().any().any() or set(frame["account_fin"].unique()) != {0, 1}:
        raise ValueError("Model 1 matrix must be complete with a binary target.")
    return frame


def create_holdout_split(frame: pd.DataFrame) -> dict[str, object]:
    features = frame.loc[:, list(MODEL1_FINAL_FEATURES)].copy()
    target = frame["account_fin"].astype("int8").copy()
    groups = profile_groups(features)
    splitter = StratifiedGroupKFold(
        n_splits=HOLDOUT_SPLITS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )
    train_index, test_index = next(splitter.split(features, target, groups))
    train_groups = groups.iloc[train_index]
    test_groups = groups.iloc[test_index]
    overlap = set(train_groups) & set(test_groups)
    if overlap:
        raise RuntimeError("Identical profiles crossed the protected holdout boundary.")

    profile_summary = (
        pd.DataFrame({"group": groups, "target": target})
        .groupby("group", observed=True)
        .agg(n=("target", "size"), target_values=("target", "nunique"))
    )
    return {
        "X_train": features.iloc[train_index].reset_index(drop=True),
        "X_test": features.iloc[test_index].reset_index(drop=True),
        "y_train": target.iloc[train_index].reset_index(drop=True),
        "y_test": target.iloc[test_index].reset_index(drop=True),
        "groups_train": train_groups.reset_index(drop=True),
        "groups_test": test_groups.reset_index(drop=True),
        "train_index": train_index,
        "test_index": test_index,
        "metadata": {
            "method": "first fold of shuffled StratifiedGroupKFold",
            "random_state": RANDOM_STATE,
            "requested_test_fraction": 1 / HOLDOUT_SPLITS,
            "train_rows": int(len(train_index)),
            "test_rows": int(len(test_index)),
            "train_positive_rate": float(target.iloc[train_index].mean()),
            "test_positive_rate": float(target.iloc[test_index].mean()),
            "unique_profiles_total": int(groups.nunique()),
            "duplicate_rows_after_first": int(groups.duplicated().sum()),
            "duplicate_profile_groups": int((profile_summary["n"] > 1).sum()),
            "conflicting_label_profile_groups": int(
                (profile_summary["target_values"] > 1).sum()
            ),
            "respondents_in_conflicting_groups": int(
                profile_summary.loc[profile_summary["target_values"] > 1, "n"].sum()
            ),
            "profile_overlap_count": len(overlap),
            "train_index_sha256": _index_signature(train_index),
            "test_index_sha256": _index_signature(test_index),
        },
    }


def build_preprocessor() -> ColumnTransformer:
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    return ColumnTransformer(
        transformers=[("categorical", categorical, list(MODEL1_FINAL_FEATURES))],
        remainder="drop",
        verbose_feature_names_out=True,
    )


def _pipeline(estimator: BaseEstimator) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", build_preprocessor()),
            ("model", estimator),
        ]
    )


def candidate_specs(random_state: int = RANDOM_STATE) -> tuple[CandidateSpec, ...]:
    return (
        CandidateSpec(
            "dummy",
            "Dummy majority baseline",
            DummyClassifier(strategy="prior"),
            {},
            0,
        ),
        CandidateSpec(
            "logistic_regression",
            "Logistic Regression",
            LogisticRegression(
                solver="liblinear",
                max_iter=2_000,
                random_state=random_state,
            ),
            {
                "model__C": [0.05, 0.2, 1.0],
                "model__class_weight": [None, "balanced"],
            },
            1,
        ),
        CandidateSpec(
            "decision_tree",
            "Decision Tree",
            DecisionTreeClassifier(random_state=random_state),
            {
                "model__max_depth": [3, 5, 8],
                "model__min_samples_leaf": [5, 15, 30],
                "model__class_weight": [None, "balanced"],
            },
            2,
        ),
        CandidateSpec(
            "random_forest",
            "Random Forest",
            RandomForestClassifier(
                n_estimators=300,
                random_state=random_state,
                n_jobs=1,
            ),
            {
                "model__max_depth": [None, 8],
                "model__min_samples_leaf": [1, 5, 15],
                "model__max_features": ["sqrt", 0.5],
            },
            3,
        ),
        CandidateSpec(
            "gradient_boosting",
            "Gradient Boosting",
            GradientBoostingClassifier(random_state=random_state),
            {
                "model__n_estimators": [100, 200],
                "model__learning_rate": [0.03, 0.1],
                "model__max_depth": [1, 2],
                "model__min_samples_leaf": [5, 15],
            },
            3,
        ),
    )


def build_cv_splits(
    features: pd.DataFrame, target: pd.Series, groups: pd.Series
) -> tuple[list[tuple[np.ndarray, np.ndarray]], list[dict[str, object]]]:
    splitter = StratifiedGroupKFold(
        n_splits=CV_SPLITS,
        shuffle=True,
        random_state=CV_RANDOM_STATE,
    )
    splits = list(splitter.split(features, target, groups))
    rows: list[dict[str, object]] = []
    for fold, (train_index, validation_index) in enumerate(splits, start=1):
        overlap = set(groups.iloc[train_index]) & set(groups.iloc[validation_index])
        if overlap:
            raise RuntimeError(f"Identical profiles crossed CV fold {fold}.")
        rows.append(
            {
                "fold": fold,
                "train_rows": int(len(train_index)),
                "validation_rows": int(len(validation_index)),
                "train_positive_rate": float(target.iloc[train_index].mean()),
                "validation_positive_rate": float(target.iloc[validation_index].mean()),
                "profile_overlap_count": len(overlap),
            }
        )
    return splits, rows


def tune_candidates(
    features: pd.DataFrame,
    target: pd.Series,
    groups: pd.Series,
) -> tuple[dict[str, GridSearchCV], pd.DataFrame, pd.DataFrame, list[dict[str, object]]]:
    cv_splits, fold_rows = build_cv_splits(features, target, groups)
    searches: dict[str, GridSearchCV] = {}
    comparison_rows: list[dict[str, object]] = []
    search_rows: list[dict[str, object]] = []

    for spec in candidate_specs():
        search = GridSearchCV(
            estimator=_pipeline(spec.estimator),
            param_grid=spec.param_grid,
            scoring=SCORING,
            refit="roc_auc",
            cv=cv_splits,
            n_jobs=1,
            return_train_score=True,
            error_score="raise",
        )
        search.fit(features, target)
        searches[spec.key] = search
        best_index = int(search.best_index_)
        results = search.cv_results_
        comparison_rows.append(
            {
                "model_key": spec.key,
                "model": spec.label,
                "complexity_rank": spec.complexity_rank,
                "parameter_combinations": int(len(results["params"])),
                "best_parameters": json.dumps(search.best_params_, sort_keys=True),
                "cv_mean_roc_auc": float(results["mean_test_roc_auc"][best_index]),
                "cv_std_roc_auc": float(results["std_test_roc_auc"][best_index]),
                "cv_mean_accuracy": float(results["mean_test_accuracy"][best_index]),
                "cv_mean_precision": float(results["mean_test_precision"][best_index]),
                "cv_mean_recall": float(results["mean_test_recall"][best_index]),
                "cv_mean_f1": float(results["mean_test_f1"][best_index]),
                "cv_mean_brier": float(-results["mean_test_neg_brier"][best_index]),
                "train_mean_roc_auc": float(results["mean_train_roc_auc"][best_index]),
                "train_cv_roc_auc_gap": float(
                    results["mean_train_roc_auc"][best_index]
                    - results["mean_test_roc_auc"][best_index]
                ),
            }
        )
        for row_index, params in enumerate(results["params"]):
            search_rows.append(
                {
                    "model_key": spec.key,
                    "model": spec.label,
                    "parameters": json.dumps(params, sort_keys=True),
                    "rank_roc_auc": int(results["rank_test_roc_auc"][row_index]),
                    "cv_mean_roc_auc": float(results["mean_test_roc_auc"][row_index]),
                    "cv_std_roc_auc": float(results["std_test_roc_auc"][row_index]),
                    "cv_mean_f1": float(results["mean_test_f1"][row_index]),
                    "cv_mean_brier": float(-results["mean_test_neg_brier"][row_index]),
                    "train_mean_roc_auc": float(results["mean_train_roc_auc"][row_index]),
                    "train_cv_roc_auc_gap": float(
                        results["mean_train_roc_auc"][row_index]
                        - results["mean_test_roc_auc"][row_index]
                    ),
                }
            )

    comparison = pd.DataFrame(comparison_rows)
    search_results = pd.DataFrame(search_rows)
    return searches, comparison, search_results, fold_rows


def select_model(comparison: pd.DataFrame) -> tuple[str, dict[str, object]]:
    eligible = comparison.loc[comparison["model_key"] != "dummy"].copy()
    top_index = eligible["cv_mean_roc_auc"].idxmax()
    top = eligible.loc[top_index]
    standard_error = float(top["cv_std_roc_auc"] / np.sqrt(CV_SPLITS))
    cutoff = float(top["cv_mean_roc_auc"] - standard_error)
    one_se_candidates = eligible.loc[eligible["cv_mean_roc_auc"] >= cutoff].copy()
    selected = one_se_candidates.sort_values(
        ["complexity_rank", "cv_mean_roc_auc"], ascending=[True, False]
    ).iloc[0]
    comparison["within_one_se_of_best_auc"] = (
        (comparison["model_key"] != "dummy")
        & (comparison["cv_mean_roc_auc"] >= cutoff)
    )
    comparison["selected"] = comparison["model_key"] == selected["model_key"]
    details = {
        "primary_metric": "mean group-aware CV ROC-AUC",
        "rule": "one-standard-error rule, then lowest predefined complexity tier and highest mean CV ROC-AUC",
        "best_mean_cv_roc_auc": float(top["cv_mean_roc_auc"]),
        "best_model_by_mean_auc": str(top["model_key"]),
        "best_model_standard_error": standard_error,
        "eligibility_cutoff": cutoff,
        "selected_model": str(selected["model_key"]),
        "selected_model_label": str(selected["model"]),
    }
    return str(selected["model_key"]), details


def _calibration_table(target: pd.Series, probability: np.ndarray) -> pd.DataFrame:
    table = pd.DataFrame({"target": target.to_numpy(), "probability": probability})
    table["bin"] = pd.qcut(table["probability"], q=8, duplicates="drop")
    calibration = (
        table.groupby("bin", observed=True)
        .agg(
            n=("target", "size"),
            mean_predicted_probability=("probability", "mean"),
            observed_positive_rate=("target", "mean"),
            minimum_probability=("probability", "min"),
            maximum_probability=("probability", "max"),
        )
        .reset_index(drop=True)
    )
    calibration["absolute_calibration_error"] = (
        calibration["observed_positive_rate"]
        - calibration["mean_predicted_probability"]
    ).abs()
    calibration["weighted_error"] = (
        calibration["n"] / calibration["n"].sum()
    ) * calibration["absolute_calibration_error"]
    return calibration


def evaluate_holdout(
    estimator: Pipeline,
    features: pd.DataFrame,
    target: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    probability = estimator.predict_proba(features)[:, 1]
    prediction = (probability >= DECISION_THRESHOLD).astype("int8")
    tn, fp, fn, tp = confusion_matrix(target, prediction, labels=[0, 1]).ravel()
    metric_rows = [
        {"metric": "accuracy", "value": accuracy_score(target, prediction)},
        {"metric": "balanced_accuracy", "value": balanced_accuracy_score(target, prediction)},
        {"metric": "precision", "value": precision_score(target, prediction, zero_division=0)},
        {"metric": "recall", "value": recall_score(target, prediction, zero_division=0)},
        {"metric": "f1", "value": f1_score(target, prediction, zero_division=0)},
        {"metric": "roc_auc", "value": roc_auc_score(target, probability)},
        {"metric": "brier_score", "value": brier_score_loss(target, probability)},
        {"metric": "log_loss", "value": log_loss(target, probability, labels=[0, 1])},
    ]
    metrics = pd.DataFrame(metric_rows)
    matrix = pd.DataFrame(
        [
            {"actual": 0, "predicted": 0, "count": int(tn)},
            {"actual": 0, "predicted": 1, "count": int(fp)},
            {"actual": 1, "predicted": 0, "count": int(fn)},
            {"actual": 1, "predicted": 1, "count": int(tp)},
        ]
    )
    calibration = _calibration_table(target, probability)
    return metrics, matrix, calibration, probability, prediction


def bootstrap_intervals(
    target: pd.Series,
    probability: np.ndarray,
    prediction: np.ndarray,
    iterations: int = BOOTSTRAP_ITERATIONS,
    random_state: int = RANDOM_STATE,
) -> pd.DataFrame:
    target_array = target.to_numpy()
    negative = np.flatnonzero(target_array == 0)
    positive = np.flatnonzero(target_array == 1)
    rng = np.random.default_rng(random_state)
    values: dict[str, list[float]] = {
        "accuracy": [],
        "precision": [],
        "recall": [],
        "f1": [],
        "roc_auc": [],
        "brier_score": [],
    }
    for _ in range(iterations):
        sample = np.concatenate(
            [
                rng.choice(negative, size=len(negative), replace=True),
                rng.choice(positive, size=len(positive), replace=True),
            ]
        )
        sample_target = target_array[sample]
        sample_probability = probability[sample]
        sample_prediction = prediction[sample]
        values["accuracy"].append(accuracy_score(sample_target, sample_prediction))
        values["precision"].append(
            precision_score(sample_target, sample_prediction, zero_division=0)
        )
        values["recall"].append(recall_score(sample_target, sample_prediction, zero_division=0))
        values["f1"].append(f1_score(sample_target, sample_prediction, zero_division=0))
        values["roc_auc"].append(roc_auc_score(sample_target, sample_probability))
        values["brier_score"].append(brier_score_loss(sample_target, sample_probability))
    return pd.DataFrame(
        [
            {
                "metric": metric,
                "lower_95": float(np.quantile(metric_values, 0.025)),
                "median": float(np.quantile(metric_values, 0.5)),
                "upper_95": float(np.quantile(metric_values, 0.975)),
                "iterations": iterations,
                "method": "stratified nonparametric bootstrap",
            }
            for metric, metric_values in values.items()
        ]
    )


def category_coverage(
    train: pd.DataFrame, test: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for feature in MODEL1_FINAL_FEATURES:
        train_categories = set(train[feature].astype("string"))
        test_categories = set(test[feature].astype("string"))
        unseen = sorted(test_categories - train_categories)
        rows.append(
            {
                "feature": feature,
                "train_category_count": len(train_categories),
                "test_category_count": len(test_categories),
                "unseen_test_category_count": len(unseen),
                "unseen_test_categories": json.dumps(unseen, ensure_ascii=False),
            }
        )
    return pd.DataFrame(rows)


def _create_figures(
    comparison: pd.DataFrame,
    metrics: pd.DataFrame,
    matrix: pd.DataFrame,
    calibration: pd.DataFrame,
    target: pd.Series,
    probability: np.ndarray,
    selected_label: str,
    figure_dir: Path,
) -> list[dict[str, object]]:
    figure_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []

    ordered = comparison.sort_values("cv_mean_roc_auc", ascending=True)
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    colors = ["#0F766E" if selected else "#94A3B8" for selected in ordered["selected"]]
    axes[0].barh(ordered["model"], ordered["cv_mean_roc_auc"], color=colors)
    axes[0].errorbar(
        ordered["cv_mean_roc_auc"],
        np.arange(len(ordered)),
        xerr=ordered["cv_std_roc_auc"],
        fmt="none",
        ecolor="#334155",
        capsize=3,
    )
    axes[0].axvline(0.5, color="#64748B", linestyle="--", linewidth=1)
    axes[0].set_xlim(0.45, 1.0)
    axes[0].set_title("Group-aware CV ROC-AUC", loc="left", fontweight="bold")
    axes[0].set_xlabel("Mean ROC-AUC ± one fold SD")
    axes[1].barh(ordered["model"], ordered["cv_mean_f1"], color=colors)
    axes[1].set_xlim(0, 1)
    axes[1].set_title("Group-aware CV F1", loc="left", fontweight="bold")
    axes[1].set_xlabel("Mean F1 at threshold 0.50")
    for ax in axes:
        ax.grid(axis="x", alpha=0.18)
        ax.spines[["top", "right", "left"]].set_visible(False)
    fig.suptitle(
        "Model 1 candidate comparison — training data only",
        x=0.04,
        ha="left",
        fontsize=17,
        fontweight="bold",
    )
    fig.text(
        0.04,
        0.02,
        "Teal marks the model selected by the pre-specified one-standard-error rule.",
        color="#475569",
    )
    fig.tight_layout(rect=(0.03, 0.06, 0.99, 0.92))
    for suffix in ("png", "svg"):
        path = figure_dir / f"01_model_comparison.{suffix}"
        fig.savefig(path, dpi=180 if suffix == "png" else None, bbox_inches="tight")
        manifest.append(
            {
                "figure": path.name,
                "format": suffix,
                "purpose": "Compare candidate models using training-fold metrics only",
            }
        )
    plt.close(fig)

    metric_lookup = metrics.set_index("metric")["value"]
    fpr, tpr, _ = roc_curve(target, probability)
    matrix_values = (
        matrix.pivot(index="actual", columns="predicted", values="count")
        .reindex(index=[0, 1], columns=[0, 1])
        .to_numpy()
    )
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    axes[0].plot(fpr, tpr, color="#0F766E", linewidth=2.5)
    axes[0].plot([0, 1], [0, 1], color="#94A3B8", linestyle="--")
    axes[0].set_title(f"ROC curve (AUC {metric_lookup['roc_auc']:.3f})", loc="left", fontweight="bold")
    axes[0].set_xlabel("False-positive rate")
    axes[0].set_ylabel("True-positive rate")
    axes[0].set_xlim(0, 1)
    axes[0].set_ylim(0, 1)

    image = axes[1].imshow(matrix_values, cmap="BuGn")
    for row in range(2):
        for column in range(2):
            axes[1].text(column, row, int(matrix_values[row, column]), ha="center", va="center", fontsize=15)
    axes[1].set_xticks([0, 1], ["Predicted no", "Predicted yes"])
    axes[1].set_yticks([0, 1], ["Actual no", "Actual yes"])
    axes[1].set_title("Confusion matrix (threshold 0.50)", loc="left", fontweight="bold")
    fig.colorbar(image, ax=axes[1], fraction=0.046, pad=0.04)

    axes[2].plot([0, 1], [0, 1], color="#94A3B8", linestyle="--", label="Perfect calibration")
    axes[2].plot(
        calibration["mean_predicted_probability"],
        calibration["observed_positive_rate"],
        marker="o",
        color="#0F766E",
        linewidth=2,
        label=selected_label,
    )
    axes[2].set_xlim(0, 1)
    axes[2].set_ylim(0, 1)
    axes[2].set_xlabel("Mean predicted probability")
    axes[2].set_ylabel("Observed positive rate")
    axes[2].set_title(
        f"Calibration (Brier {metric_lookup['brier_score']:.3f})",
        loc="left",
        fontweight="bold",
    )
    axes[2].legend(frameon=False, fontsize=9)
    for ax in (axes[0], axes[2]):
        ax.grid(alpha=0.18)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(
        "Selected Model 1 — protected holdout evaluation",
        x=0.04,
        ha="left",
        fontsize=17,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0.03, 0.02, 0.99, 0.91))
    for suffix in ("png", "svg"):
        path = figure_dir / f"02_holdout_evaluation.{suffix}"
        fig.savefig(path, dpi=180 if suffix == "png" else None, bbox_inches="tight")
        manifest.append(
            {
                "figure": path.name,
                "format": suffix,
                "purpose": "Evaluate discrimination, classification errors, and calibration on the protected holdout",
            }
        )
    plt.close(fig)
    return manifest


def _render_report(summary: dict[str, object], comparison: pd.DataFrame) -> str:
    test = summary["holdout_evaluation"]["metrics"]
    selected = summary["selection"]
    lines = [
        "# Phase 7 — Model 1: Financial Inclusion",
        "",
        "## Scope",
        "",
        "This phase develops only the financial-inclusion classifier (`account_fin`). Mobile-money modelling, SHAP explainability, API work, and frontend work are outside this phase.",
        "",
        "## Validation design",
        "",
        f"- Protected holdout: {summary['split']['test_rows']} respondents ({summary['split']['requested_test_fraction']:.0%} target), never used for tuning or selection.",
        f"- Training set: {summary['split']['train_rows']} respondents.",
        "- Identical predictor profiles are grouped in both the holdout split and five-fold cross-validation.",
        f"- Profile overlap across holdout partitions: {summary['split']['profile_overlap_count']}.",
        "- Selection metric: training-fold ROC-AUC. The one-standard-error rule chooses the simplest competitive model.",
        "- Classification metrics use a provisional 0.50 threshold; it was not tuned on the holdout.",
        "- Survey weights are not predictors or loss weights; evaluation describes respondent-level generalisation in this file.",
        "",
        "## Candidate comparison",
        "",
        "| Candidate | CV ROC-AUC | CV F1 | CV accuracy | Train–CV AUC gap | Selected |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for _, row in comparison.sort_values("cv_mean_roc_auc", ascending=False).iterrows():
        lines.append(
            f"| {row['model']} | {row['cv_mean_roc_auc']:.3f} ± {row['cv_std_roc_auc']:.3f} | {row['cv_mean_f1']:.3f} | {row['cv_mean_accuracy']:.3f} | {row['train_cv_roc_auc_gap']:.3f} | {'Yes' if row['selected'] else 'No'} |"
        )
    lines.extend(
        [
            "",
            "## Selected model",
            "",
        f"**{selected['selected_model_label']}** was selected using the pre-specified one-standard-error and complexity-tier rule.",
            "",
            f"Best parameters: `{json.dumps(selected['best_parameters'], sort_keys=True)}`",
            "",
            "## Protected-holdout results",
            "",
            "| Metric | Value | 95% bootstrap interval where available |",
            "|---|---:|---|",
        ]
    )
    intervals = {
        row["metric"]: row for row in summary["holdout_evaluation"]["bootstrap_intervals"]
    }
    for metric, value in test.items():
        interval = intervals.get(metric)
        interval_text = (
            f"{interval['lower_95']:.3f}–{interval['upper_95']:.3f}"
            if interval
            else "—"
        )
        lines.append(f"| {metric.replace('_', ' ').title()} | {value:.3f} | {interval_text} |")
    confusion = summary["holdout_evaluation"]["confusion"]
    lines.extend(
        [
            "",
            f"Confusion counts at 0.50: TN={confusion['tn']}, FP={confusion['fp']}, FN={confusion['fn']}, TP={confusion['tp']}.",
            "",
            "## Generalisation and calibration",
            "",
            f"- Selected-model train–CV ROC-AUC gap: {summary['diagnostics']['train_cv_auc_gap']:.3f} ({summary['diagnostics']['overfitting_flag']}).",
            f"- Holdout versus mean CV ROC-AUC difference: {summary['diagnostics']['holdout_minus_cv_auc']:.3f}.",
            f"- Expected calibration error across quantile bins: {summary['diagnostics']['expected_calibration_error']:.3f}.",
            f"- Transformed one-hot feature count: {summary['diagnostics']['transformed_feature_count']}.",
            "",
            "## Limitations",
            "",
            "- The holdout contains about one fifth of a 1,051-row dataset, so uncertainty intervals remain important.",
            "- Forty-four identical-profile groups contain both outcomes (134 respondents), indicating that the available profile cannot perfectly separate inclusion.",
            "- Fixed age bands lose within-band detail.",
            "- Recent digital indicators are observational characteristics and do not establish causation.",
            "- The 0.50 threshold is provisional; any later wording or threshold policy must be justified without using the protected holdout for repeated tuning.",
            "- Model performance applies to this supplied survey file and is not evidence of nationwide production readiness.",
            "",
        ]
    )
    return "\n".join(lines)


def run(
    input_path: Path = DEFAULT_MODEL1_OUTPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    model_path: Path = DEFAULT_MODEL_PATH,
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> dict[str, object]:
    frame = load_model_frame(input_path)
    split = create_holdout_split(frame)
    searches, comparison, search_results, fold_rows = tune_candidates(
        split["X_train"], split["y_train"], split["groups_train"]
    )
    selected_key, selection = select_model(comparison)
    selected_search = searches[selected_key]
    selected_pipeline: Pipeline = selected_search.best_estimator_

    metrics, matrix, calibration, probability, prediction = evaluate_holdout(
        selected_pipeline, split["X_test"], split["y_test"]
    )
    intervals = bootstrap_intervals(split["y_test"], probability, prediction)
    coverage = category_coverage(split["X_train"], split["X_test"])
    if int(coverage["unseen_test_category_count"].sum()) > 0:
        # This is supported by the encoder, but must remain visible in reports.
        category_note = "One or more holdout categories were unseen in training and ignored by the encoder."
    else:
        category_note = "Every holdout category was represented in training."

    selected_row = comparison.loc[comparison["model_key"] == selected_key].iloc[0]
    selection["best_parameters"] = selected_search.best_params_
    selection["selected_cv_mean_roc_auc"] = float(selected_row["cv_mean_roc_auc"])
    selection["selected_cv_std_roc_auc"] = float(selected_row["cv_std_roc_auc"])
    selection["selected_cv_mean_f1"] = float(selected_row["cv_mean_f1"])

    output_dir.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(output_dir / "model_comparison.csv", index=False, encoding="utf-8", lineterminator="\n")
    search_results.to_csv(output_dir / "cv_search_results.csv", index=False, encoding="utf-8", lineterminator="\n")
    pd.DataFrame(fold_rows).to_csv(output_dir / "cv_fold_audit.csv", index=False, encoding="utf-8", lineterminator="\n")
    metrics.to_csv(output_dir / "holdout_metrics.csv", index=False, encoding="utf-8", lineterminator="\n")
    matrix.to_csv(output_dir / "confusion_matrix.csv", index=False, encoding="utf-8", lineterminator="\n")
    calibration.to_csv(output_dir / "calibration_curve.csv", index=False, encoding="utf-8", lineterminator="\n")
    intervals.to_csv(output_dir / "bootstrap_intervals.csv", index=False, encoding="utf-8", lineterminator="\n")
    coverage.to_csv(output_dir / "test_category_coverage.csv", index=False, encoding="utf-8", lineterminator="\n")

    metric_lookup = metrics.set_index("metric")["value"].to_dict()
    confusion_lookup = matrix.set_index(["actual", "predicted"])["count"]
    expected_calibration_error = float(calibration["weighted_error"].sum())
    transformed_feature_count = int(
        len(selected_pipeline.named_steps["preprocess"].get_feature_names_out())
    )
    train_cv_gap = float(selected_row["train_cv_roc_auc_gap"])
    if train_cv_gap < 0.05:
        overfitting_flag = "low observed train–CV gap"
    elif train_cv_gap < 0.10:
        overfitting_flag = "moderate observed train–CV gap"
    else:
        overfitting_flag = "high observed train–CV gap"

    figures = _create_figures(
        comparison,
        metrics,
        matrix,
        calibration,
        split["y_test"],
        probability,
        selection["selected_model_label"],
        output_dir / "figures",
    )

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(selected_pipeline, model_path)
    reloaded: Pipeline = joblib.load(model_path)
    if not np.allclose(reloaded.predict_proba(split["X_test"]), selected_pipeline.predict_proba(split["X_test"])):
        raise RuntimeError("Reloaded model probabilities do not match the saved pipeline.")

    metadata = {
        "artifact": "FinAccess Eswatini Model 1 complete preprocessing and estimator pipeline",
        "target": "account_fin",
        "positive_class_meaning": "Has an account at a financial institution",
        "input_features": list(MODEL1_FINAL_FEATURES),
        "input_matrix_sha256": file_hash(input_path),
        "random_state": RANDOM_STATE,
        "decision_threshold": DECISION_THRESHOLD,
        "selected_model": selection,
        "training_rows": int(len(split["X_train"])),
        "protected_test_rows": int(len(split["X_test"])),
        "transformed_feature_count": transformed_feature_count,
        "holdout_metrics": {key: float(value) for key, value in metric_lookup.items()},
        "model_sha256": file_hash(model_path),
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    summary: dict[str, object] = {
        "phase": 7,
        "status": "PASS_WITH_NOTES",
        "scope": "Model 1 financial-inclusion development only",
        "source": {
            "file": str(input_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": file_hash(input_path),
            "rows": int(len(frame)),
            "predictors": len(MODEL1_FINAL_FEATURES),
            "target_distribution": {
                str(int(value)): int(count)
                for value, count in frame["account_fin"].value_counts().sort_index().items()
            },
        },
        "split": split["metadata"],
        "cross_validation": {
            "method": "shuffled StratifiedGroupKFold on training partition",
            "folds": CV_SPLITS,
            "random_state": CV_RANDOM_STATE,
            "profile_overlap_count_every_fold": 0,
            "selection_data": "training partition only",
        },
        "selection": selection,
        "holdout_evaluation": {
            "evaluated_once_after_selection": True,
            "decision_threshold": DECISION_THRESHOLD,
            "metrics": {key: float(value) for key, value in metric_lookup.items()},
            "bootstrap_intervals": intervals.to_dict(orient="records"),
            "confusion": {
                "tn": int(confusion_lookup.loc[(0, 0)]),
                "fp": int(confusion_lookup.loc[(0, 1)]),
                "fn": int(confusion_lookup.loc[(1, 0)]),
                "tp": int(confusion_lookup.loc[(1, 1)]),
            },
        },
        "diagnostics": {
            "train_cv_auc_gap": train_cv_gap,
            "overfitting_flag": overfitting_flag,
            "holdout_minus_cv_auc": float(
                metric_lookup["roc_auc"] - selected_row["cv_mean_roc_auc"]
            ),
            "expected_calibration_error": expected_calibration_error,
            "transformed_feature_count": transformed_feature_count,
            "unseen_holdout_category_count": int(
                coverage["unseen_test_category_count"].sum()
            ),
            "category_coverage_note": category_note,
        },
        "artifact": {
            "pipeline_file": str(model_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "pipeline_sha256": file_hash(model_path),
            "metadata_file": str(metadata_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "reload_prediction_match": True,
            "contains_preprocessing_and_estimator": True,
        },
        "figures": figures,
        "model2_trained": False,
        "feature_importance_generated": False,
        "shap_generated": False,
        "limitations": [
            "small protected holdout produces material metric uncertainty",
            "134 respondents belong to identical predictor profiles with conflicting outcomes",
            "fixed age bands lose within-band information",
            "observational predictors do not support causal claims",
            "0.50 threshold remains provisional",
            "survey weights were not used as predictors or loss weights",
        ],
    }
    (output_dir / "phase7_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "model1_report.md").write_text(
        _render_report(summary, comparison), encoding="utf-8"
    )
    (output_dir / "deliverable_checklist.md").write_text(
        render_delivery_checklist(PROJECT_ROOT, through_phase=7), encoding="utf-8"
    )
    missing = validate_completed_phase_files(PROJECT_ROOT, through_phase=7)
    if missing:
        raise RuntimeError(f"Completed-phase deliverable validation failed: {missing}")
    summary["deliverable_validation"] = {
        "passed": True,
        "phases_checked": [1, 2, 3, 4, 5, 6, 7],
        "missing_files": {},
        "checklist": "reports/phase_7/deliverable_checklist.md",
    }
    (output_dir / "phase7_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_MODEL1_OUTPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--metadata-path", type=Path, default=DEFAULT_METADATA_PATH)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run(
        args.input.resolve(),
        args.output_dir.resolve(),
        args.model_path.resolve(),
        args.metadata_path.resolve(),
    )
    print(
        json.dumps(
            {
                "status": summary["status"],
                "selected_model": summary["selection"]["selected_model_label"],
                "cv_roc_auc": summary["selection"]["selected_cv_mean_roc_auc"],
                "holdout_metrics": summary["holdout_evaluation"]["metrics"],
                "model2_trained": summary["model2_trained"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
