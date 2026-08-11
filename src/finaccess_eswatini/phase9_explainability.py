"""Phase 9 SHAP explainability for both validated prediction pipelines.

Global explanations use each model's protected holdout. Local explanations are
additive in model log-odds and are aggregated from one-hot columns back to the
human-readable source fields without losing additivity.
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
import shap
from scipy.special import expit

from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.deliverables import render_delivery_checklist, validate_completed_phase_files
from finaccess_eswatini.phase3_preprocessing import file_hash
from finaccess_eswatini.phase6_feature_engineering import MODEL1_FINAL_FEATURES, MODEL2_FINAL_FEATURES
from finaccess_eswatini.phase7_model1 import (
    DEFAULT_MODEL_PATH as MODEL1_PATH,
    create_holdout_split as create_model1_split,
    load_model_frame as load_model1_frame,
)
from finaccess_eswatini.phase8_model2 import (
    DEFAULT_MODEL_PATH as MODEL2_PATH,
    create_holdout_split as create_model2_split,
    load_model_frame as load_model2_frame,
)


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_9"
DEFAULT_BUNDLE_DIR = PROJECT_ROOT / "models"
MODEL1_EXPECTED_SHA256 = "467e5519c022a0c716e38bae3f7b44752b4a50da6553720541d75efcb5d2b7b3"
MODEL2_EXPECTED_SHA256 = "3df51a31fc420043b8e386c73d2a46771cafe64a619d69faf6fd5a2db12d7606"
ADDITIVITY_TOLERANCE = 1e-8

FEATURE_LABELS = {
    "female": "gender",
    "age_group": "age group",
    "educ": "education level",
    "inc_q": "income quintile",
    "emp_in": "workforce status",
    "fin24c": "natural-disaster or severe-weather experience",
    "internet_use": "recent internet use",
    "internet_engagement_level": "internet engagement",
    "phone_access_tier": "phone access tier",
    "data_purchase_pattern": "data-purchase pattern",
    "con11": "SIM registration in own name",
    "con12": "mobile-phone use frequency",
    "con14": "ability to read a text message",
    "con16": "ability to send a text message",
    "con18": "phone PIN or password",
    "con20": "rules imposed on own-phone use",
    "fin46": "ID ownership",
}


@dataclass(frozen=True)
class ExplainabilitySpec:
    model_key: str
    model_label: str
    target: str
    outcome_label: str
    question: str
    features: tuple[str, ...]
    pipeline_path: Path
    expected_sha256: str
    bundle_path: Path


SPECS = (
    ExplainabilitySpec(
        "model1",
        "Financial Inclusion",
        "account_fin",
        "financially included",
        "Based on the characteristics provided, is this person likely to be financially included?",
        MODEL1_FINAL_FEATURES,
        MODEL1_PATH,
        MODEL1_EXPECTED_SHA256,
        DEFAULT_BUNDLE_DIR / "model1_shap_explainer.joblib",
    ),
    ExplainabilitySpec(
        "model2",
        "Mobile Money Adoption",
        "account_mob",
        "use mobile money",
        "Based on the characteristics provided, is this person likely to use mobile money?",
        MODEL2_FINAL_FEATURES,
        MODEL2_PATH,
        MODEL2_EXPECTED_SHA256,
        DEFAULT_BUNDLE_DIR / "model2_shap_explainer.joblib",
    ),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_inputs(spec: ExplainabilitySpec) -> tuple[object, dict[str, object]]:
    observed = file_hash(spec.pipeline_path)
    if observed != spec.expected_sha256:
        raise ValueError(
            f"{spec.model_label} pipeline hash changed: expected {spec.expected_sha256}, found {observed}"
        )
    pipeline = joblib.load(spec.pipeline_path)
    if spec.model_key == "model1":
        split = create_model1_split(load_model1_frame())
    else:
        split = create_model2_split(load_model2_frame())
    if list(split["X_test"].columns) != list(spec.features):
        raise ValueError(f"{spec.model_label} explanation schema does not match its frozen model schema.")
    return pipeline, split


def encoded_feature_map(pipeline: object, features: Sequence[str]) -> pd.DataFrame:
    """Map fitted one-hot output positions to their original input fields."""

    preprocessor = pipeline.named_steps["preprocess"]
    names = list(preprocessor.get_feature_names_out())
    encoder = preprocessor.named_transformers_["categorical"].named_steps["onehot"]
    rows: list[dict[str, object]] = []
    position = 0
    for source_feature, categories in zip(features, encoder.categories_, strict=True):
        for category in categories:
            rows.append(
                {
                    "encoded_index": position,
                    "encoded_feature": names[position],
                    "source_feature": source_feature,
                    "feature_label": FEATURE_LABELS.get(source_feature, source_feature.replace("_", " ")),
                    "encoded_category": str(category),
                }
            )
            position += 1
    mapping = pd.DataFrame(rows)
    if position != len(names):
        raise RuntimeError("The one-hot feature mapping did not cover every transformed column.")
    return mapping


def _build_explainer(pipeline: object, X_train: pd.DataFrame) -> tuple[object, str]:
    transformed_train = pipeline.named_steps["preprocess"].transform(X_train)
    estimator = pipeline.named_steps["model"]
    if estimator.__class__.__name__ == "GradientBoostingClassifier":
        return shap.TreeExplainer(estimator, model_output="raw"), "TreeExplainer"
    if estimator.__class__.__name__ == "LogisticRegression":
        masker = shap.maskers.Independent(transformed_train, max_samples=len(transformed_train))
        return shap.LinearExplainer(estimator, masker), "LinearExplainer"
    raise TypeError(f"No validated Phase 9 explainer for {estimator.__class__.__name__}.")


def _explanation_arrays(explainer: object, transformed: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    explanation = explainer(transformed)
    values = np.asarray(explanation.values, dtype=float)
    base = np.asarray(explanation.base_values, dtype=float)
    if values.ndim == 3:
        values = values[:, :, 1]
    if base.ndim > 1:
        base = base[:, 1]
    if base.ndim == 0:
        base = np.repeat(float(base), len(transformed))
    return values, base.reshape(-1)


def _global_tables(
    spec: ExplainabilitySpec,
    pipeline: object,
    X_test: pd.DataFrame,
    values: np.ndarray,
    mapping: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    encoded = mapping.copy()
    encoded["model"] = spec.model_key
    encoded["model_label"] = spec.model_label
    encoded["mean_abs_shap_log_odds"] = np.abs(values).mean(axis=0)
    encoded["mean_signed_shap_log_odds"] = values.mean(axis=0)
    encoded["rank"] = encoded["mean_abs_shap_log_odds"].rank(method="first", ascending=False).astype(int)

    source_rows: list[dict[str, object]] = []
    for feature in spec.features:
        positions = mapping.loc[mapping["source_feature"] == feature, "encoded_index"].to_numpy()
        aggregated = values[:, positions].sum(axis=1)
        source_rows.append(
            {
                "model": spec.model_key,
                "model_label": spec.model_label,
                "source_feature": feature,
                "feature_label": FEATURE_LABELS.get(feature, feature.replace("_", " ")),
                "mean_abs_shap_log_odds": float(np.abs(aggregated).mean()),
                "mean_signed_shap_log_odds": float(aggregated.mean()),
            }
        )
    global_table = pd.DataFrame(source_rows).sort_values("mean_abs_shap_log_odds", ascending=False)
    global_table["importance_share"] = global_table["mean_abs_shap_log_odds"] / global_table[
        "mean_abs_shap_log_odds"
    ].sum()
    global_table["rank"] = np.arange(1, len(global_table) + 1)

    estimator = pipeline.named_steps["model"]
    if hasattr(estimator, "feature_importances_"):
        native_values = np.asarray(estimator.feature_importances_, dtype=float)
        native_measure = "summed impurity importance"
    else:
        native_values = np.abs(np.asarray(estimator.coef_[0], dtype=float))
        native_measure = "summed absolute logistic coefficient"
    native_rows: list[dict[str, object]] = []
    for feature in spec.features:
        positions = mapping.loc[mapping["source_feature"] == feature, "encoded_index"].to_numpy()
        native_rows.append(
            {
                "model": spec.model_key,
                "model_label": spec.model_label,
                "source_feature": feature,
                "feature_label": FEATURE_LABELS.get(feature, feature.replace("_", " ")),
                "native_measure": native_measure,
                "native_importance": float(native_values[positions].sum()),
            }
        )
    native = pd.DataFrame(native_rows).sort_values("native_importance", ascending=False)
    native["importance_share"] = native["native_importance"] / native["native_importance"].sum()
    native["rank"] = np.arange(1, len(native) + 1)
    return global_table, encoded, native


def _statement(spec: ExplainabilitySpec, probability: float) -> str:
    if spec.model_key == "model1":
        return (
            "This person is likely to be financially included."
            if probability >= 0.5
            else "This person is unlikely to be financially included."
        )
    return (
        "This person is likely to use mobile money."
        if probability >= 0.5
        else "This person is unlikely to use mobile money."
    )


def _local_rows(
    spec: ExplainabilitySpec,
    profile: pd.Series,
    shap_row: np.ndarray,
    mapping: pd.DataFrame,
    probability: float,
    example_type: str,
    holdout_row: int,
    top_n: int = 5,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for feature in spec.features:
        positions = mapping.loc[mapping["source_feature"] == feature, "encoded_index"].to_numpy()
        contribution = float(shap_row[positions].sum())
        rows.append(
            {
                "model": spec.model_key,
                "model_label": spec.model_label,
                "example_type": example_type,
                "holdout_row": holdout_row,
                "question": spec.question,
                "prediction_statement": _statement(spec, probability),
                "probability": probability,
                "source_feature": feature,
                "feature_label": FEATURE_LABELS.get(feature, feature.replace("_", " ")),
                "profile_value": str(profile[feature]),
                "shap_log_odds": contribution,
                "direction": "increased" if contribution > 0 else "reduced" if contribution < 0 else "did not change",
                "explanation_text": (
                    f"{FEATURE_LABELS.get(feature, feature.replace('_', ' ')).capitalize()} "
                    f"({profile[feature]}) {'increased' if contribution > 0 else 'reduced' if contribution < 0 else 'did not change'} "
                    "the prediction relative to the model baseline."
                ),
            }
        )
    rows.sort(key=lambda item: abs(float(item["shap_log_odds"])), reverse=True)
    for rank, row in enumerate(rows[:top_n], start=1):
        row["factor_rank"] = rank
    return rows[:top_n]


def explain_profile(model_key: str, profile: pd.DataFrame, top_n: int = 5) -> dict[str, object]:
    """Explain one profile with a persisted, model-matched SHAP explainer."""

    spec = next((candidate for candidate in SPECS if candidate.model_key == model_key), None)
    if spec is None:
        raise ValueError("model_key must be 'model1' or 'model2'.")
    if profile.shape[0] != 1 or profile.columns.tolist() != list(spec.features):
        raise ValueError(f"Profile must have one row and exact {spec.model_key} feature order.")
    if file_hash(spec.pipeline_path) != spec.expected_sha256:
        raise ValueError("Validated model artifact has changed.")
    pipeline = joblib.load(spec.pipeline_path)
    bundle = joblib.load(spec.bundle_path)
    return explain_profile_with_loaded_artifacts(spec, pipeline, bundle, profile, top_n)


def explain_profile_with_loaded_artifacts(
    spec: ExplainabilitySpec,
    pipeline: object,
    bundle: dict[str, object],
    profile: pd.DataFrame,
    top_n: int = 5,
) -> dict[str, object]:
    """Explain one profile using already loaded, hash-matched artifacts.

    This entry point lets an inference service load immutable artifacts once at
    process start while retaining the same Phase 9 faithfulness checks.
    """

    if profile.shape[0] != 1 or profile.columns.tolist() != list(spec.features):
        raise ValueError(f"Profile must have one row and exact {spec.model_key} feature order.")
    if bundle["pipeline_sha256"] != spec.expected_sha256:
        raise ValueError("Explainer bundle is not matched to the validated model.")
    transformed = pipeline.named_steps["preprocess"].transform(profile)
    values, base = _explanation_arrays(bundle["explainer"], transformed)
    raw = float(pipeline.named_steps["model"].decision_function(transformed)[0])
    reconstructed_raw = float(base[0] + values[0].sum())
    if abs(raw - reconstructed_raw) > ADDITIVITY_TOLERANCE:
        raise RuntimeError("SHAP contributions do not reconstruct the model raw score.")
    probability = float(pipeline.predict_proba(profile)[0, 1])
    mapping = pd.DataFrame(bundle["feature_mapping"])
    factors = _local_rows(spec, profile.iloc[0], values[0], mapping, probability, "inference", 0, top_n)
    return {
        "model": spec.model_key,
        "question": spec.question,
        "prediction_statement": _statement(spec, probability),
        "probability": probability,
        "threshold": 0.5,
        "baseline_probability": float(expit(base[0])),
        "explanation_scale": "additive log-odds relative to the SHAP baseline",
        "factors": factors,
        "additivity_error": abs(raw - reconstructed_raw),
    }


def _plot_global(global_table: pd.DataFrame, figures_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(16, 8), constrained_layout=True)
    colors = {"model1": "#0F766E", "model2": "#2563EB"}
    for axis, (model, group) in zip(axes, global_table.groupby("model", sort=False), strict=True):
        shown = group.nsmallest(10, "rank").sort_values("mean_abs_shap_log_odds")
        axis.barh(shown["feature_label"], shown["mean_abs_shap_log_odds"], color=colors[model])
        axis.set_title(shown["model_label"].iloc[0])
        axis.set_xlabel("Mean absolute SHAP value (log-odds)")
        axis.grid(axis="x", alpha=0.2)
    fig.suptitle("Global SHAP importance on protected holdouts", fontsize=16, fontweight="bold")
    for suffix in ("png", "svg"):
        fig.savefig(figures_dir / f"01_global_shap_importance.{suffix}", dpi=180, bbox_inches="tight")
    plt.close(fig)


def _plot_individual(individual: pd.DataFrame, figures_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(16, 8), constrained_layout=True)
    representative = individual[individual["example_type"] == "boundary"]
    for axis, (_, group) in zip(axes, representative.groupby("model", sort=False), strict=True):
        shown = group.sort_values("shap_log_odds")
        colors = np.where(shown["shap_log_odds"] >= 0, "#0F766E", "#DC2626")
        labels = shown["feature_label"] + " = " + shown["profile_value"]
        axis.barh(labels, shown["shap_log_odds"], color=colors)
        axis.axvline(0, color="#111827", linewidth=0.8)
        probability = float(shown["probability"].iloc[0])
        axis.set_title(f"{shown['model_label'].iloc[0]} (p={probability:.1%})")
        axis.set_xlabel("Signed SHAP contribution (log-odds)")
        axis.grid(axis="x", alpha=0.2)
    fig.suptitle("Individual explanations near the decision boundary", fontsize=16, fontweight="bold")
    for suffix in ("png", "svg"):
        fig.savefig(figures_dir / f"02_individual_explanations.{suffix}", dpi=180, bbox_inches="tight")
    plt.close(fig)


def _report(summary: dict[str, object], global_table: pd.DataFrame, validation: pd.DataFrame) -> str:
    lines = [
        "# Phase 9 Explainability Report",
        "",
        "SHAP explanations were generated separately for both validated pipelines on their protected holdouts. Contributions are additive in log-odds and are summed from one-hot columns back to original input fields.",
        "",
        "## Leading global factors",
        "",
    ]
    for model, group in global_table.groupby("model", sort=False):
        lines.append(f"### {group['model_label'].iloc[0]}")
        lines.append("")
        for row in group.nsmallest(5, "rank").itertuples():
            lines.append(f"- {row.feature_label}: mean absolute SHAP {row.mean_abs_shap_log_odds:.4f} log-odds")
        lines.append("")
    lines.extend(
        [
            "## Faithfulness checks",
            "",
            f"- Maximum raw-score reconstruction error: {validation['max_raw_score_error'].max():.3e}",
            f"- Maximum probability reconstruction error: {validation['max_probability_error'].max():.3e}",
            "- Persisted explainers were reloaded and matched to immutable pipeline hashes.",
            "- Aggregation to source features preserves the exact sum of encoded SHAP values.",
            "",
            "## Interpretation boundaries",
            "",
            "- A positive SHAP value supports a higher model prediction relative to its explainer baseline; a negative value supports a lower prediction.",
            "- SHAP explains model behaviour, not causation or an official World Bank classification.",
            "- Correlated or conceptually overlapping inputs can share or redistribute attribution.",
            "- The 0.50 classification threshold remains provisional from the modelling phases.",
            "- Global rankings describe the protected holdout samples and should not be treated as population causal effects.",
            "",
        ]
    )
    return "\n".join(lines)


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    DEFAULT_BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    all_global: list[pd.DataFrame] = []
    all_encoded: list[pd.DataFrame] = []
    all_native: list[pd.DataFrame] = []
    all_individual: list[dict[str, object]] = []
    validation_rows: list[dict[str, object]] = []
    model_summaries: dict[str, object] = {}

    for spec in SPECS:
        pipeline, split = _load_inputs(spec)
        X_train = split["X_train"]
        X_test = split["X_test"]
        transformed_test = pipeline.named_steps["preprocess"].transform(X_test)
        explainer, explainer_type = _build_explainer(pipeline, X_train)
        values, base = _explanation_arrays(explainer, transformed_test)
        mapping = encoded_feature_map(pipeline, spec.features)
        estimator = pipeline.named_steps["model"]
        raw = np.asarray(estimator.decision_function(transformed_test), dtype=float)
        reconstructed_raw = base + values.sum(axis=1)
        probabilities = np.asarray(pipeline.predict_proba(X_test)[:, 1], dtype=float)
        reconstructed_probabilities = expit(reconstructed_raw)
        max_raw_error = float(np.max(np.abs(raw - reconstructed_raw)))
        max_probability_error = float(np.max(np.abs(probabilities - reconstructed_probabilities)))
        if max_raw_error > ADDITIVITY_TOLERANCE or max_probability_error > ADDITIVITY_TOLERANCE:
            raise RuntimeError(f"{spec.model_label} SHAP additivity validation failed.")

        global_table, encoded, native = _global_tables(spec, pipeline, X_test, values, mapping)
        all_global.append(global_table)
        all_encoded.append(encoded)
        all_native.append(native)

        examples = {
            "lowest_probability": int(np.argmin(probabilities)),
            "boundary": int(np.argmin(np.abs(probabilities - 0.5))),
            "highest_probability": int(np.argmax(probabilities)),
        }
        for example_type, row_index in examples.items():
            all_individual.extend(
                _local_rows(
                    spec,
                    X_test.iloc[row_index],
                    values[row_index],
                    mapping,
                    float(probabilities[row_index]),
                    example_type,
                    row_index,
                )
            )

        bundle = {
            "model": spec.model_key,
            "target": spec.target,
            "pipeline_sha256": spec.expected_sha256,
            "explainer_type": explainer_type,
            "explainer": explainer,
            "feature_mapping": mapping.to_dict(orient="records"),
            "explanation_scale": "raw model log-odds",
        }
        joblib.dump(bundle, spec.bundle_path)
        reloaded = joblib.load(spec.bundle_path)
        reload_values, reload_base = _explanation_arrays(reloaded["explainer"], transformed_test[:5])
        reload_match = bool(np.allclose(reload_values, values[:5]) and np.allclose(reload_base, base[:5]))
        if not reload_match:
            raise RuntimeError(f"{spec.model_label} explainer reload check failed.")
        source_sum_error = 0.0
        for row_index in range(len(values)):
            aggregated_sum = sum(
                values[row_index, mapping.loc[mapping["source_feature"] == feature, "encoded_index"].to_numpy()].sum()
                for feature in spec.features
            )
            source_sum_error = max(source_sum_error, abs(float(aggregated_sum - values[row_index].sum())))
        validation_rows.append(
            {
                "model": spec.model_key,
                "explainer_type": explainer_type,
                "holdout_rows": len(X_test),
                "encoded_features": values.shape[1],
                "source_features": len(spec.features),
                "max_raw_score_error": max_raw_error,
                "max_probability_error": max_probability_error,
                "max_source_aggregation_error": source_sum_error,
                "explainer_reload_match": reload_match,
                "pipeline_sha256": spec.expected_sha256,
                "explainer_sha256": _sha256(spec.bundle_path),
            }
        )
        model_summaries[spec.model_key] = {
            "model_label": spec.model_label,
            "target": spec.target,
            "explainer_type": explainer_type,
            "holdout_rows_explained": len(X_test),
            "encoded_features": values.shape[1],
            "source_features": len(spec.features),
            "baseline_probability": float(expit(base[0])),
            "top_global_features": global_table.nsmallest(5, "rank")["source_feature"].tolist(),
            "pipeline_sha256": spec.expected_sha256,
            "explainer_file": str(spec.bundle_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "explainer_sha256": _sha256(spec.bundle_path),
        }

    global_table = pd.concat(all_global, ignore_index=True)
    encoded_table = pd.concat(all_encoded, ignore_index=True)
    native_table = pd.concat(all_native, ignore_index=True)
    individual_table = pd.DataFrame(all_individual)
    validation = pd.DataFrame(validation_rows)
    global_table.to_csv(output_dir / "global_shap_importance.csv", index=False)
    encoded_table.to_csv(output_dir / "encoded_shap_importance.csv", index=False)
    native_table.to_csv(output_dir / "native_feature_importance.csv", index=False)
    individual_table.to_csv(output_dir / "individual_explanations.csv", index=False)
    validation.to_csv(output_dir / "additivity_validation.csv", index=False)
    _plot_global(global_table, figures_dir)
    _plot_individual(individual_table, figures_dir)

    summary: dict[str, object] = {
        "phase": 9,
        "status": "PASS_WITH_NOTES",
        "scope": "SHAP explainability for both validated model pipelines",
        "shap_version": shap.__version__,
        "models": model_summaries,
        "validation": {
            "tolerance": ADDITIVITY_TOLERANCE,
            "max_raw_score_error": float(validation["max_raw_score_error"].max()),
            "max_probability_error": float(validation["max_probability_error"].max()),
            "max_source_aggregation_error": float(validation["max_source_aggregation_error"].max()),
            "all_explainers_reload": bool(validation["explainer_reload_match"].all()),
            "model_pipeline_hashes_unchanged": True,
        },
        "individual_examples": {
            "per_model": 3,
            "selection": ["lowest probability", "closest to 0.50", "highest probability"],
            "factors_per_example": 5,
            "wording_basis": "signed aggregated SHAP values, not manually invented drivers",
        },
        "limitations": [
            "SHAP explains model behaviour rather than causation",
            "attributions are relative to each explainer baseline",
            "conceptually overlapping features can share attribution",
            "global importance is evaluated on finite protected holdouts",
            "the 0.50 classification threshold remains provisional",
        ],
        "next_phase_started": False,
    }
    (output_dir / "phase9_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "explainability_report.md").write_text(
        _report(summary, global_table, validation), encoding="utf-8"
    )
    missing = validate_completed_phase_files(PROJECT_ROOT, through_phase=9)
    (output_dir / "deliverable_checklist.md").write_text(
        render_delivery_checklist(PROJECT_ROOT, through_phase=9), encoding="utf-8"
    )
    if missing:
        raise RuntimeError(f"Completed-phase deliverables are missing: {missing}")
    summary["deliverable_validation"] = {
        "passed": True,
        "phases_checked": list(range(1, 10)),
        "missing_files": {},
        "checklist": "reports/phase_9/deliverable_checklist.md",
    }
    (output_dir / "phase9_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run(args.output_dir)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
