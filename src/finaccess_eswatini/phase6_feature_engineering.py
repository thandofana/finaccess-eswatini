"""Phase 6 deterministic, leakage-reviewed feature engineering.

The transformations in this module use only Phase 3 predictor values. They do
not inspect either target, learn parameters, split data, or fit a model.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import pandas as pd

from finaccess_eswatini.data_audit import DEFAULT_INPUT, PROJECT_ROOT
from finaccess_eswatini.deliverables import (
    render_delivery_checklist,
    validate_completed_phase_files,
)
from finaccess_eswatini.phase3_preprocessing import RAW_DATA_SHA256, file_hash


DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_6"
DEFAULT_MODEL1_INPUT = DEFAULT_PROCESSED_DIR / "model1_financial_inclusion.csv"
DEFAULT_MODEL2_INPUT = DEFAULT_PROCESSED_DIR / "model2_mobile_money.csv"
DEFAULT_MODEL1_OUTPUT = DEFAULT_PROCESSED_DIR / "model1_financial_inclusion_final.csv"
DEFAULT_MODEL2_OUTPUT = DEFAULT_PROCESSED_DIR / "model2_mobile_money_final.csv"

PHASE3_INPUT_HASHES = {
    "model1": "dcfb2e615179b832f9dd7746667a1b9b0a35142c5b90575fe4db4c9c71429e4e",
    "model2": "8aebdf141e73c96c8a0c520dc2cb7bc245e29e4cd1e7d6aa097b890dd97020ed",
}

AGE_BINS = (15, 25, 35, 45, 55, 65, 111)
AGE_LABELS = ("15–24", "25–34", "35–44", "45–54", "55–64", "65+")


@dataclass(frozen=True)
class FinalFeatureConfig:
    key: str
    target: str
    features: tuple[str, ...]

    @property
    def categorical_features(self) -> tuple[str, ...]:
        return self.features

    @property
    def numeric_features(self) -> tuple[str, ...]:
        return ()


COMMON_FINAL_FEATURES = (
    "female",
    "age_group",
    "educ",
    "inc_q",
    "emp_in",
    "fin24c",
)

MODEL1_FINAL_FEATURES = COMMON_FINAL_FEATURES + (
    "internet_use",
    "phone_access_tier",
    "con11",
    "con12",
    "con14",
    "con16",
    "con18",
    "con20",
    "fin46",
)

MODEL2_FINAL_FEATURES = COMMON_FINAL_FEATURES + (
    "internet_engagement_level",
    "phone_access_tier",
    "con11",
    "con12",
    "con14",
    "con16",
    "con18",
    "con20",
    "data_purchase_pattern",
    "fin46",
)

FINAL_MODEL_CONFIGS = {
    "model1": FinalFeatureConfig("model1", "account_fin", MODEL1_FINAL_FEATURES),
    "model2": FinalFeatureConfig("model2", "account_mob", MODEL2_FINAL_FEATURES),
}

PROHIBITED_OUTPUT_COLUMNS = {
    "account",
    "account_fin",
    "account_mob",
    "dig_account",
    "economy",
    "economycode",
    "wpid_random",
    "wgt",
}


def get_final_model_config(model: str | int) -> FinalFeatureConfig:
    aliases = {1: "model1", 2: "model2", "1": "model1", "2": "model2"}
    key = aliases.get(model, model)
    if key not in FINAL_MODEL_CONFIGS:
        raise ValueError(f"Unknown model {model!r}; expected 'model1' or 'model2'.")
    return FINAL_MODEL_CONFIGS[str(key)]


def derive_age_group(age: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(age, errors="raise")
    if numeric.isna().any() or ((numeric % 1) != 0).any() or not numeric.between(15, 110).all():
        raise ValueError("age must contain complete whole years between 15 and 110.")
    grouped = pd.cut(
        numeric,
        bins=AGE_BINS,
        labels=AGE_LABELS,
        right=False,
        include_lowest=True,
        ordered=True,
    )
    if grouped.isna().any():
        raise ValueError("Fixed age bands did not cover every respondent.")
    return grouped.astype("string")


def derive_phone_access_tier(frame: pd.DataFrame) -> pd.Series:
    required = {"con1", "con9"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Phone access derivation requires {sorted(required)}.")
    ownership = frame["con1"].astype("string")
    phone_type = frame["con9"].astype("string")
    output = pd.Series(pd.NA, index=frame.index, dtype="string")
    output.loc[ownership == "No"] = "No personal mobile phone"
    output.loc[ownership == "Nonresponse"] = "Phone ownership nonresponse"
    type_map = {
        "A smartphone": "Smartphone",
        "A basic text phone": "Basic text phone",
        "Nonresponse": "Phone type nonresponse",
    }
    for source, label in type_map.items():
        output.loc[(ownership == "Yes") & (phone_type == source)] = label
    if output.isna().any():
        combinations = (
            frame.loc[output.isna(), ["con1", "con9"]]
            .value_counts(dropna=False)
            .to_dict()
        )
        raise ValueError(f"Unresolved phone access combinations: {combinations}")
    return output


def derive_internet_engagement_level(frame: pd.DataFrame) -> pd.Series:
    required = {"internet_use", "con26"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Internet engagement derivation requires {sorted(required)}.")
    recent = frame["internet_use"].astype("string")
    frequency = frame["con26"].astype("string")
    output = pd.Series(pd.NA, index=frame.index, dtype="string")
    output.loc[recent == "No / don't know / refused"] = (
        "No recent internet use / no-DK-ref"
    )
    frequency_map = {
        "Daily": "Daily internet use",
        "Weekly": "Weekly internet use",
        "Monthly": "Monthly internet use",
        "Less than once a month": "Less than monthly internet use",
        "Never": "Recent-use indicator; frequency reported never",
        "Nonresponse": "Recent internet use; frequency nonresponse",
    }
    for source, label in frequency_map.items():
        output.loc[(recent == "Yes") & (frequency == source)] = label
    if output.isna().any():
        combinations = (
            frame.loc[output.isna(), ["internet_use", "con26"]]
            .value_counts(dropna=False)
            .to_dict()
        )
        raise ValueError(f"Unresolved internet engagement combinations: {combinations}")
    return output


def derive_data_purchase_pattern(frame: pd.DataFrame) -> pd.Series:
    required = {"internet_use", "con27", "con28"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Data purchase derivation requires {sorted(required)}.")
    recent = frame["internet_use"].astype("string")
    purchase = frame["con27"].astype("string")
    frequency = frame["con28"].astype("string")
    output = pd.Series(pd.NA, index=frame.index, dtype="string")
    output.loc[recent == "No / don't know / refused"] = (
        "No recent internet use / skipped"
    )
    output.loc[(recent == "Yes") & (purchase == "No")] = "Does not purchase data"
    output.loc[(recent == "Yes") & (purchase == "Nonresponse")] = (
        "Data-purchase status nonresponse"
    )
    frequency_map = {
        "Daily": "Purchases data daily",
        "Weekly": "Purchases data weekly",
        "Monthly": "Purchases data monthly",
        "Less than once a month": "Purchases data less than monthly",
        "Never": "Reports purchasing data but frequency never",
        "Nonresponse": "Data-purchase frequency nonresponse",
    }
    for source, label in frequency_map.items():
        output.loc[
            (recent == "Yes") & (purchase == "Yes") & (frequency == source)
        ] = label
    if output.isna().any():
        combinations = (
            frame.loc[output.isna(), ["internet_use", "con27", "con28"]]
            .value_counts(dropna=False)
            .to_dict()
        )
        raise ValueError(f"Unresolved data-purchase combinations: {combinations}")
    return output


def engineer_model_frame(frame: pd.DataFrame, model: str | int) -> pd.DataFrame:
    """Return a target-plus-final-features frame without consulting the target."""

    config = get_final_model_config(model)
    if config.target not in frame.columns:
        raise ValueError(f"Input frame is missing target {config.target!r}.")
    target = pd.to_numeric(frame[config.target], errors="raise")
    if target.isna().any() or not set(target.astype(int).unique()).issubset({0, 1}):
        raise ValueError(f"{config.target} must remain complete and binary.")

    output = pd.DataFrame(index=frame.index)
    output[config.target] = target.astype("int8")
    output["female"] = frame["female"].astype("string")
    output["age_group"] = derive_age_group(frame["age"])
    for feature in ("educ", "inc_q", "emp_in", "fin24c"):
        output[feature] = frame[feature].astype("string")

    if config.key == "model1":
        output["internet_use"] = frame["internet_use"].astype("string")
    else:
        output["internet_engagement_level"] = derive_internet_engagement_level(frame)
    output["phone_access_tier"] = derive_phone_access_tier(frame)

    for feature in ("con11", "con12", "con14", "con16", "con18", "con20"):
        output[feature] = frame[feature].astype("string")
    if config.key == "model2":
        output["data_purchase_pattern"] = derive_data_purchase_pattern(frame)
    output["fin46"] = frame["fin46"].astype("string")

    validate_final_frame(output, config.key)
    return output.loc[:, [config.target, *config.features]]


def validate_final_frame(frame: pd.DataFrame, model: str | int) -> None:
    config = get_final_model_config(model)
    expected = [config.target, *config.features]
    if frame.columns.tolist() != expected:
        raise ValueError(f"Unexpected {config.key} final columns or ordering.")
    if len(frame) != 1051:
        raise ValueError(f"{config.key} must preserve all 1,051 respondents.")
    if frame.isna().any().any():
        raise ValueError(f"{config.key} contains unresolved nulls after engineering.")
    leaked = (set(frame.columns) & PROHIBITED_OUTPUT_COLUMNS) - {config.target}
    if leaked:
        raise ValueError(f"Prohibited columns entered {config.key}: {sorted(leaked)}")
    if not set(frame[config.target].unique()).issubset({0, 1}):
        raise ValueError(f"{config.target} is not binary after engineering.")


def _review_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    proposals = (
        (
            "age_group",
            "age",
            "RETAIN",
            "LOW",
            "Fixed domain bands capture interpretable non-linearity; raw age is removed to avoid redundant explanations.",
        ),
        (
            "phone_access_tier",
            "con1;con9",
            "RETAIN",
            "LOW",
            "Combines phone ownership and routed phone type into one truthful, assessment-ready access state.",
        ),
        (
            "internet_engagement_level",
            "internet_use;con26",
            "MODEL_SPECIFIC",
            "LOW_WITH_TEMPORAL_NOTE",
            "Retained only for Model 2; recent internet engagement is relevant digital context but overlaps the target observation period.",
        ),
        (
            "data_purchase_pattern",
            "internet_use;con27;con28",
            "MODEL_SPECIFIC",
            "LOW_WITH_TEMPORAL_NOTE",
            "Retained only for Model 2 as non-financial digital-access context with routing consolidated explicitly.",
        ),
        (
            "online_activity_breadth",
            "con30a;con30b;con30c;con30d;con30e;con30g;con30h",
            "EXCLUDE",
            "MODERATE",
            "Recent mobile activities overlap the mobile-money target period, add seven-question burden, and may encode unstable behavioural intensity.",
        ),
        (
            "digital_access_score",
            "internet_use;con1;con9;con11;con12;con14;con16;con18",
            "EXCLUDE",
            "LOW_BUT_REDUNDANT",
            "An additive score would impose arbitrary equal weights, hide routing, double-count inputs, and weaken SHAP interpretability.",
        ),
    )
    for model in ("model1", "model2"):
        for feature, sources, base_decision, risk, rationale in proposals:
            decision = base_decision
            if feature in {"internet_engagement_level", "data_purchase_pattern"}:
                decision = "RETAIN" if model == "model2" else "EXCLUDE_MODEL_SCOPE"
            elif base_decision == "MODEL_SPECIFIC":
                decision = "EXCLUDE_MODEL_SCOPE"
            rows.append(
                {
                    "model": model,
                    "engineered_feature": feature,
                    "source_variables": sources,
                    "decision": decision,
                    "leakage_risk": risk,
                    "uses_target": False,
                    "learns_from_full_sample": False,
                    "rationale": rationale,
                }
            )
    return rows


FEATURE_LABELS = {
    "female": "Gender",
    "age_group": "Age group",
    "educ": "Education level",
    "inc_q": "Income quintile",
    "emp_in": "Workforce status",
    "fin24c": "Natural-disaster or severe-weather exposure",
    "internet_use": "Recent internet use",
    "internet_engagement_level": "Internet engagement level",
    "phone_access_tier": "Phone access tier",
    "con11": "SIM registered in respondent's name",
    "con12": "Mobile-phone use frequency",
    "con14": "Read a text message",
    "con16": "Sent a text message",
    "con18": "Phone protected by PIN or password",
    "con20": "Rules about using own phone",
    "data_purchase_pattern": "Mobile-data purchase pattern",
    "fin46": "Identity-document ownership",
}

FEATURE_SOURCES = {
    "female": "female",
    "age_group": "age",
    "educ": "educ",
    "inc_q": "inc_q",
    "emp_in": "emp_in",
    "fin24c": "fin24c",
    "internet_use": "internet_use",
    "internet_engagement_level": "internet_use;con26",
    "phone_access_tier": "con1;con9",
    "con11": "con11",
    "con12": "con12",
    "con14": "con14",
    "con16": "con16",
    "con18": "con18",
    "con20": "con20",
    "data_purchase_pattern": "internet_use;con27;con28",
    "fin46": "fin46",
}


def _manifest_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    engineered = {
        "age_group",
        "internet_engagement_level",
        "phone_access_tier",
        "data_purchase_pattern",
    }
    temporal_note = {"fin24c", "internet_engagement_level", "data_purchase_pattern"}
    for config in FINAL_MODEL_CONFIGS.values():
        for position, feature in enumerate(config.features, start=1):
            rows.append(
                {
                    "model": config.key,
                    "target": config.target,
                    "position": position,
                    "feature": feature,
                    "label": FEATURE_LABELS[feature],
                    "feature_type": "engineered_categorical" if feature in engineered else "direct_categorical",
                    "source_variables": FEATURE_SOURCES[feature],
                    "target_used": False,
                    "leakage_risk": "LOW_WITH_TEMPORAL_NOTE" if feature in temporal_note else "LOW",
                    "final_status": "INCLUDE",
                }
            )
    return rows


def _distribution_rows(frames: dict[str, pd.DataFrame]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    engineered_by_model = {
        "model1": ("age_group", "phone_access_tier"),
        "model2": (
            "age_group",
            "phone_access_tier",
            "internet_engagement_level",
            "data_purchase_pattern",
        ),
    }
    for model, features in engineered_by_model.items():
        frame = frames[model]
        for feature in features:
            counts = frame[feature].value_counts(dropna=False)
            for category, count in counts.items():
                rows.append(
                    {
                        "model": model,
                        "feature": feature,
                        "category": str(category),
                        "count": int(count),
                        "proportion": float(count / len(frame)),
                    }
                )
    return rows


def _transformation_spec() -> dict[str, object]:
    return {
        "target_used_in_derivation": False,
        "learned_parameters": False,
        "age_group": {
            "source": ["age"],
            "rule": "fixed left-closed bands",
            "bins": list(AGE_BINS),
            "labels": list(AGE_LABELS),
            "raw_age_retained": False,
        },
        "phone_access_tier": {
            "source": ["con1", "con9"],
            "routing_policy": "ownership determines no-phone and nonresponse states; type is used only for owners",
        },
        "internet_engagement_level": {
            "models": ["model2"],
            "source": ["internet_use", "con26"],
            "routing_policy": "non-users receive an explicit no-recent-use state; owner frequency is preserved",
        },
        "data_purchase_pattern": {
            "models": ["model2"],
            "source": ["internet_use", "con27", "con28"],
            "routing_policy": "non-users, non-purchasers, and purchase frequency are distinct states",
        },
        "excluded_engineering": {
            "online_activity_breadth": "moderate temporal/conceptual overlap and response burden",
            "digital_access_score": "arbitrary weighting, redundancy, and reduced explainability",
        },
    }


def _create_distribution_figure(distributions: pd.DataFrame, figure_dir: Path) -> list[dict[str, object]]:
    figure_dir.mkdir(parents=True, exist_ok=True)
    panels = (
        ("model1", "age_group", "Age profile retained as fixed bands"),
        ("model1", "phone_access_tier", "Phone ownership and type consolidated"),
        ("model2", "internet_engagement_level", "Model 2 internet engagement states"),
        ("model2", "data_purchase_pattern", "Model 2 data-purchase states"),
    )
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    for ax, (model, feature, title) in zip(axes.flat, panels):
        subset = distributions.loc[
            (distributions["model"] == model) & (distributions["feature"] == feature)
        ].copy()
        if feature == "age_group":
            order = list(AGE_LABELS)
            subset["category"] = pd.Categorical(subset["category"], categories=order, ordered=True)
            subset = subset.sort_values("category")
        else:
            subset = subset.sort_values("count", ascending=True)
        ax.barh(subset["category"].astype("string"), subset["count"], color="#0F766E")
        ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
        ax.set_xlabel("Respondents")
        ax.grid(axis="x", alpha=0.18)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", labelsize=9)
        for position, value in enumerate(subset["count"]):
            ax.text(value + 8, position, f"{int(value):,}", va="center", fontsize=9)
    fig.suptitle(
        "Phase 6 engineered-feature coverage (unweighted counts)",
        x=0.04,
        ha="left",
        fontsize=17,
        fontweight="bold",
    )
    fig.text(
        0.04,
        0.015,
        "Counts describe feature coverage only; targets were not used to define the transformations.",
        fontsize=10,
        color="#475569",
    )
    fig.tight_layout(rect=(0.03, 0.04, 0.99, 0.94))
    paths: list[dict[str, object]] = []
    for suffix in ("png", "svg"):
        path = figure_dir / f"01_engineered_feature_distributions.{suffix}"
        fig.savefig(path, dpi=180 if suffix == "png" else None, bbox_inches="tight")
        paths.append(
            {
                "figure": path.name,
                "format": suffix,
                "purpose": "Validate coverage of retained deterministic engineered features",
            }
        )
    plt.close(fig)
    return paths


def _render_report(summary: dict[str, object]) -> str:
    model1 = summary["models"]["model1"]
    model2 = summary["models"]["model2"]
    return "\n".join(
        [
            "# Phase 6 — Feature Engineering",
            "",
            "## Scope",
            "",
            "Phase 6 applies deterministic, interpretable transformations to Phase 3 predictors and freezes one model-specific matrix per outcome. No train/test split, model fitting, tuning, evaluation, or SHAP analysis is performed.",
            "",
            "## Final matrices",
            "",
            "| Model | Target | Rows | Final predictors | Total columns | Null cells |",
            "|---|---|---:|---:|---:|---:|",
            f"| Financial inclusion | `{model1['target']}` | {model1['rows']} | {model1['feature_count']} | {model1['columns']} | {model1['null_cells']} |",
            f"| Mobile money | `{model2['target']}` | {model2['rows']} | {model2['feature_count']} | {model2['columns']} | {model2['null_cells']} |",
            "",
            "Respondent-level outputs remain Git-ignored. All 1,051 rows and both target distributions are preserved.",
            "",
            "## Retained transformations",
            "",
            "- `age_group`: fixed 15–24, 25–34, 35–44, 45–54, 55–64, and 65+ bands replace raw age. Fixed rules avoid learning cut points from either outcome, provide non-linearity, and keep explanations readable.",
            "- `phone_access_tier`: phone ownership and routed phone type become one consistent state: smartphone, basic phone, no personal phone, or explicit nonresponse.",
            "- `internet_engagement_level` (Model 2 only): recent internet use and use frequency are consolidated without treating routed non-use as random missingness.",
            "- `data_purchase_pattern` (Model 2 only): internet eligibility, data purchasing, and purchase frequency are combined into explicit routed states.",
            "",
            "## Excluded proposals",
            "",
            "- `online_activity_breadth` was rejected. Its seven recent mobile activities overlap the mobile-money outcome period, increase assessment burden, and risk encoding unstable behavior rather than durable access characteristics.",
            "- A generic `digital_access_score` was rejected because arbitrary equal weighting would double-count related inputs and obscure truthful SHAP explanations.",
            "- Raw age, `con1`, and `con9` are removed after their approved replacements are created. Model 2 also removes component fields `internet_use`, `con26`, `con27`, and `con28` after consolidation.",
            "",
            "## Leakage safeguards",
            "",
            "- No feature function reads, aggregates, or conditions on either target.",
            "- Transformations learn no sample statistics and therefore can be reproduced identically at inference time.",
            "- Parallel targets, identifiers, metadata, weights, account behaviors, and constructed payment outcomes remain absent.",
            "- Automated tests verify that changing the target leaves every engineered predictor unchanged.",
            "",
            "## Final preprocessing contract",
            "",
            "All final predictors are categorical. Later model phases must one-hot encode them inside a complete training-fold pipeline with unknown-category tolerance. No encoder is fitted in Phase 6.",
            "",
            "## Notes carried forward",
            "",
            "- Fixed age bands trade some within-band detail for interpretability and non-linearity; Phase 7/8 evaluation must reveal whether that tradeoff generalizes.",
            "- Model 2 internet and data-purchase fields are non-financial digital behaviors, but they overlap the mobile-money target observation window; this limitation remains explicit.",
            "- `internet_use=0` combines no, don't know, and refused, so the derived no-recent-use state preserves that ambiguity in its label.",
            "- Feature decisions are semantic and data-quality based; no full-sample target association or model score was used to select them.",
            "",
        ]
    )


def run(
    model1_input: Path = DEFAULT_MODEL1_INPUT,
    model2_input: Path = DEFAULT_MODEL2_INPUT,
    model1_output: Path = DEFAULT_MODEL1_OUTPUT,
    model2_output: Path = DEFAULT_MODEL2_OUTPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    inputs = {"model1": model1_input, "model2": model2_input}
    for model, path in inputs.items():
        if not path.is_file():
            raise FileNotFoundError(f"Phase 3 input not found: {path}")
        observed_hash = file_hash(path)
        if observed_hash != PHASE3_INPUT_HASHES[model]:
            raise ValueError(
                f"{model} Phase 3 input hash changed: expected {PHASE3_INPUT_HASHES[model]}, found {observed_hash}"
            )
    raw_hash = file_hash(DEFAULT_INPUT)
    if raw_hash != RAW_DATA_SHA256:
        raise ValueError(f"Raw data hash changed: expected {RAW_DATA_SHA256}, found {raw_hash}")

    source_frames = {
        "model1": pd.read_csv(model1_input),
        "model2": pd.read_csv(model2_input),
    }
    final_frames = {
        model: engineer_model_frame(frame, model)
        for model, frame in source_frames.items()
    }
    outputs = {"model1": model1_output, "model2": model2_output}
    for model, path in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        final_frames[model].to_csv(path, index=False, encoding="utf-8", lineterminator="\n")

    output_dir.mkdir(parents=True, exist_ok=True)
    review = pd.DataFrame(_review_rows())
    manifest = pd.DataFrame(_manifest_rows())
    distributions = pd.DataFrame(_distribution_rows(final_frames))
    review.to_csv(output_dir / "feature_engineering_review.csv", index=False, encoding="utf-8", lineterminator="\n")
    manifest.to_csv(output_dir / "final_feature_manifest.csv", index=False, encoding="utf-8", lineterminator="\n")
    distributions.to_csv(output_dir / "engineered_feature_distributions.csv", index=False, encoding="utf-8", lineterminator="\n")
    (output_dir / "transformation_spec.json").write_text(
        json.dumps(_transformation_spec(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    figures = _create_distribution_figure(distributions, output_dir / "figures")

    summary: dict[str, object] = {
        "phase": 6,
        "status": "PASS_WITH_NOTES",
        "scope": "deterministic feature engineering and final matrices only",
        "source_validation": {
            "raw_sha256": raw_hash,
            "model1_phase3_sha256": file_hash(model1_input),
            "model2_phase3_sha256": file_hash(model2_input),
        },
        "models": {},
        "engineering": {
            "retained_features": [
                "age_group",
                "phone_access_tier",
                "internet_engagement_level (model2 only)",
                "data_purchase_pattern (model2 only)",
            ],
            "excluded_proposals": ["online_activity_breadth", "digital_access_score"],
            "target_used_in_derivation": False,
            "learned_parameters": False,
        },
        "split_performed": False,
        "models_trained": False,
        "figures": figures,
        "limitations": [
            "fixed age bands discard within-band age detail",
            "recent Model 2 digital behaviors overlap the mobile-money target observation period",
            "internet_use=0 combines no, don't know, and refused",
            "model usefulness and generalisation remain untested until the dedicated modelling phases",
        ],
    }
    for model, frame in final_frames.items():
        config = get_final_model_config(model)
        summary["models"][model] = {
            "target": config.target,
            "rows": int(len(frame)),
            "columns": int(frame.shape[1]),
            "feature_count": len(config.features),
            "features": list(config.features),
            "numeric_features": [],
            "categorical_features": list(config.features),
            "null_cells": int(frame.isna().sum().sum()),
            "target_distribution": {
                str(int(value)): int(count)
                for value, count in frame[config.target].value_counts().sort_index().items()
            },
            "output_file": str(outputs[model].relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "output_sha256": file_hash(outputs[model]),
        }
    (output_dir / "phase6_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "feature_engineering_report.md").write_text(
        _render_report(summary), encoding="utf-8"
    )
    (output_dir / "deliverable_checklist.md").write_text(
        render_delivery_checklist(PROJECT_ROOT, through_phase=6), encoding="utf-8"
    )
    missing = validate_completed_phase_files(PROJECT_ROOT, through_phase=6)
    if missing:
        raise RuntimeError(f"Completed-phase deliverable validation failed: {missing}")
    summary["deliverable_validation"] = {
        "passed": True,
        "phases_checked": [1, 2, 3, 4, 5, 6],
        "missing_files": {},
        "checklist": "reports/phase_6/deliverable_checklist.md",
    }
    (output_dir / "phase6_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model1-input", type=Path, default=DEFAULT_MODEL1_INPUT)
    parser.add_argument("--model2-input", type=Path, default=DEFAULT_MODEL2_INPUT)
    parser.add_argument("--model1-output", type=Path, default=DEFAULT_MODEL1_OUTPUT)
    parser.add_argument("--model2-output", type=Path, default=DEFAULT_MODEL2_OUTPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run(
        args.model1_input.resolve(),
        args.model2_input.resolve(),
        args.model1_output.resolve(),
        args.model2_output.resolve(),
        args.output_dir.resolve(),
    )
    print(
        json.dumps(
            {
                "status": summary["status"],
                "model1_shape": [summary["models"]["model1"]["rows"], summary["models"]["model1"]["columns"]],
                "model2_shape": [summary["models"]["model2"]["rows"], summary["models"]["model2"]["columns"]],
                "models_trained": summary["models_trained"],
                "output_dir": str(args.output_dir.resolve()),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
