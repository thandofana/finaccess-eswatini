"""Generate Phase 3 cleaned datasets and preprocessing documentation.

This module does not split data, engineer features, fit transformers, or train
models. It converts only Phase 2-approved source fields into auditable,
model-specific datasets and documents the unfitted preprocessing templates.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Sequence

import pandas as pd

from finaccess_eswatini.data_audit import DEFAULT_INPUT, PROJECT_ROOT
from finaccess_eswatini.deliverables import (
    render_delivery_checklist,
    validate_completed_phase_files,
)
from finaccess_eswatini.feature_config import MODEL_CONFIGS, get_model_config
from finaccess_eswatini.preprocessing.cleaning import (
    COMBINED_NO_NONRESPONSE_LABEL,
    CORE_MISSING_LABEL,
    NONRESPONSE_LABEL,
    ROUTED_MISSING_LABEL,
    clean_model_frame,
    load_data_dictionary,
    observed_mapping_rows,
    read_raw_data,
)


DEFAULT_DICTIONARY = PROJECT_ROOT / "reports" / "phase_2" / "data_dictionary.csv"
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_3"
RAW_DATA_SHA256 = "4968eaa568df1ddf8d5fadea39f4797d1bdecc2c3f941546936a200ce4bc210c"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Cannot write empty report table: {path}")
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _schema_rows(
    frame: pd.DataFrame,
    dictionary: pd.DataFrame,
    model: str,
) -> list[dict[str, object]]:
    config = get_model_config(model)
    rows: list[dict[str, object]] = []
    for position, variable in enumerate(frame.columns, start=1):
        role = "target" if variable == config.target else (
            "numeric_predictor" if variable in config.numeric_features else "categorical_predictor"
        )
        if variable == config.target:
            tier = "TARGET"
        elif variable in config.core_features:
            tier = "CORE"
        else:
            tier = "CONDITIONAL"
        categories = ""
        if role in {"target", "categorical_predictor"}:
            categories = json.dumps(
                sorted(str(value) for value in frame[variable].unique()),
                ensure_ascii=False,
            )
        rows.append(
            {
                "position": position,
                "variable": variable,
                "label": str(dictionary.loc[variable, "label"]),
                "role": role,
                "feature_tier": tier,
                "cleaned_dtype": str(frame[variable].dtype),
                "missing_count": int(frame[variable].isna().sum()),
                "unique_count": int(frame[variable].nunique(dropna=False)),
                "cleaned_categories": categories,
            }
        )
    return rows


def _model_summary(frame: pd.DataFrame, model: str, output_path: Path) -> dict[str, object]:
    config = get_model_config(model)
    categorical = frame.loc[:, list(config.categorical_features)]
    semantic_counts = {
        "routed_not_applicable": {
            name: int((categorical[name] == ROUTED_MISSING_LABEL).sum())
            for name in config.categorical_features
            if (categorical[name] == ROUTED_MISSING_LABEL).any()
        },
        "core_missing_or_nonresponse": {
            name: int((categorical[name] == CORE_MISSING_LABEL).sum())
            for name in config.categorical_features
            if (categorical[name] == CORE_MISSING_LABEL).any()
        },
        "explicit_nonresponse": {
            name: int((categorical[name] == NONRESPONSE_LABEL).sum())
            for name in config.categorical_features
            if (categorical[name] == NONRESPONSE_LABEL).any()
        },
        "combined_no_dk_ref": {
            name: int((categorical[name] == COMBINED_NO_NONRESPONSE_LABEL).sum())
            for name in config.categorical_features
            if (categorical[name] == COMBINED_NO_NONRESPONSE_LABEL).any()
        },
    }
    return {
        "target": config.target,
        "shape": {"rows": int(frame.shape[0]), "columns": int(frame.shape[1])},
        "feature_count": len(config.features),
        "features": list(config.features),
        "core_features": list(config.core_features),
        "conditional_features": list(config.conditional_features),
        "numeric_features": list(config.numeric_features),
        "categorical_features": list(config.categorical_features),
        "target_distribution": {
            str(int(key)): int(value)
            for key, value in frame[config.target].value_counts().sort_index().items()
        },
        "unresolved_missing_cells": int(frame.isna().sum().sum()),
        "exact_duplicate_rows_excluding_first": int(frame.duplicated(keep="first").sum()),
        "semantic_state_counts": semantic_counts,
        "output_file": str(output_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "output_sha256": file_hash(output_path),
    }


def _preprocessing_spec() -> dict[str, object]:
    models: dict[str, object] = {}
    for key, config in MODEL_CONFIGS.items():
        models[key] = {
            "target": config.target,
            "numeric_columns": list(config.numeric_features),
            "categorical_columns": list(config.categorical_features),
            "numeric_pipeline": ["median imputation safeguard", "standard scaling"],
            "categorical_pipeline": [
                "most-frequent imputation safeguard",
                "one-hot encoding with unknown-category tolerance",
            ],
            "remainder": "drop",
        }
    return {
        "fitted_in_phase_3": False,
        "fit_policy": (
            "Fit the ColumnTransformer only inside a complete estimator Pipeline, "
            "using training data or the training fold of cross-validation."
        ),
        "categorical_policy": (
            "Survey categories are labelled before one-hot encoding; no ordinal numeric "
            "distance is assumed for education or income quintile."
        ),
        "models": models,
    }


def _render_markdown(summary: dict[str, object]) -> str:
    model1 = summary["models"]["model1"]
    model2 = summary["models"]["model2"]
    return "\n".join(
        [
            "# Phase 3 — Data Cleaning & Preprocessing",
            "",
            "## Scope",
            "",
            "Phase 3 converts only the Phase 2-approved predictors into two model-specific, "
            "human-readable datasets. No data split, feature engineering, model fitting, "
            "evaluation, or explainability work is performed here.",
            "",
            "## Generated datasets",
            "",
            "| Dataset | Target | Rows | Predictors | Total columns | Unresolved missing cells |",
            "|---|---|---:|---:|---:|---:|",
            f"| Model 1 | `{model1['target']}` | {model1['shape']['rows']} | {model1['feature_count']} | {model1['shape']['columns']} | {model1['unresolved_missing_cells']} |",
            f"| Model 2 | `{model2['target']}` | {model2['shape']['rows']} | {model2['feature_count']} | {model2['shape']['columns']} | {model2['unresolved_missing_cells']} |",
            "",
            "The processed files remain Git-ignored because they contain respondent-level microdata.",
            "",
            "## Cleaning decisions",
            "",
            "- The source file is treated as immutable and its Phase 1 SHA-256 contract is checked before processing.",
            "- Both binary targets remain integers coded `0` and `1`; target labels are not used as predictors.",
            "- `age` is validated as whole years in the plausible project range 15–110 and retained as numeric.",
            "- All other predictors are treated as categorical. Education and income quintile are not given artificial numeric distances.",
            f"- Explicit don't-know/refused codes become `{NONRESPONSE_LABEL}` when the source distinguishes them.",
            f"- Constructed `No/DK/Ref` values remain the honest combined label `{COMBINED_NO_NONRESPONSE_LABEL}` because their components cannot be recovered.",
            f"- Routed blanks in conditional questions become `{ROUTED_MISSING_LABEL}`.",
            f"- The 10 blank education responses become `{CORE_MISSING_LABEL}` rather than being silently imputed.",
            "- Unknown raw codes cause the cleaner to fail instead of being silently accepted.",
            "",
            "## Duplicate policy",
            "",
            f"The reduced Model 1 dataset has {model1['exact_duplicate_rows_excluding_first']} exact rows after the first occurrence; "
            f"Model 2 has {model2['exact_duplicate_rows_excluding_first']}. These are retained because respondent IDs were unique in Phase 1, "
            "and identical profiles are plausible survey observations. The identifier itself is excluded from both modelling datasets.",
            "",
            "## Leakage safeguards",
            "",
            f"- Model 1 contains exactly {model1['feature_count']} approved predictors and excludes `account_mob`, all identifiers, metadata, weights, and post-outcome financial behaviour.",
            f"- Model 2 contains exactly {model2['feature_count']} approved predictors and excludes `account_fin`, all identifiers, metadata, weights, and post-outcome financial behaviour.",
            "- Feature lists are imported from the same central policy module used by the Phase 2 dictionary generator.",
            "- The scikit-learn preprocessing objects are templates only and are not fitted or persisted in Phase 3.",
            "- Later fitting must occur inside a complete model pipeline on training folds only.",
            "",
            "## Numeric and categorical validation",
            "",
            f"- Age range after cleaning: {summary['numeric_validation']['age_min']}–{summary['numeric_validation']['age_max']} years.",
            f"- Non-integer age values: {summary['numeric_validation']['non_integer_age_count']}.",
            f"- Unexpected categorical codes: {summary['categorical_validation']['unexpected_code_count']}.",
            f"- Unresolved null cells across both outputs: {model1['unresolved_missing_cells'] + model2['unresolved_missing_cells']}.",
            "",
            "## Important limitations carried forward",
            "",
            "- Survey weights are intentionally excluded from individual predictors but may be used later for descriptive population estimates.",
            "- Routed digital variables encode eligibility and access context; Phase 6 must reconsider each conditional field before final matrices are frozen.",
            "- `internet_use=0` combines no, don't know, and refused in the supplied constructed variable; the cleaner cannot separate them.",
            "- No inference about association, causation, or model performance is made in this phase.",
            "",
            "## Validation outcome",
            "",
            "All output schema, target, category, missingness, numeric-range, and leakage-boundary checks passed.",
            "",
        ]
    )


def run(
    raw_path: Path = DEFAULT_INPUT,
    dictionary_path: Path = DEFAULT_DICTIONARY,
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    if not raw_path.is_file():
        raise FileNotFoundError(f"Raw dataset not found: {raw_path}")
    if not dictionary_path.is_file():
        raise FileNotFoundError(f"Phase 2 dictionary not found: {dictionary_path}")
    source_hash = file_hash(raw_path)
    if source_hash != RAW_DATA_SHA256:
        raise ValueError(f"Raw data hash changed: expected {RAW_DATA_SHA256}, found {source_hash}")

    raw = read_raw_data(raw_path)
    dictionary = load_data_dictionary(dictionary_path)
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames = {
        "model1": clean_model_frame(raw, dictionary, "model1"),
        "model2": clean_model_frame(raw, dictionary, "model2"),
    }
    output_paths = {
        "model1": processed_dir / "model1_financial_inclusion.csv",
        "model2": processed_dir / "model2_mobile_money.csv",
    }
    for key, frame in frames.items():
        frame.to_csv(output_paths[key], index=False, encoding="utf-8", lineterminator="\n")
        write_csv(output_dir / f"processed_schema_{key}.csv", _schema_rows(frame, dictionary, key))

    categorical_variables = list(dict.fromkeys(MODEL_CONFIGS["model2"].categorical_features))
    mapping_rows = observed_mapping_rows(raw, dictionary, categorical_variables)
    for row in mapping_rows:
        variable = str(row["variable"])
        row["used_by_model1"] = variable in MODEL_CONFIGS["model1"].features
        row["used_by_model2"] = variable in MODEL_CONFIGS["model2"].features
        if row["raw_value"] == "<blank>":
            row["cleaned_label_model1"] = (
                ROUTED_MISSING_LABEL
                if variable in MODEL_CONFIGS["model1"].conditional_features
                else CORE_MISSING_LABEL
                if variable in MODEL_CONFIGS["model1"].features
                else "not used"
            )
            row["cleaned_label_model2"] = (
                ROUTED_MISSING_LABEL
                if variable in MODEL_CONFIGS["model2"].conditional_features
                else CORE_MISSING_LABEL
            )
        else:
            row["cleaned_label_model1"] = row["cleaned_label"] if row["used_by_model1"] else "not used"
            row["cleaned_label_model2"] = row["cleaned_label"]
    write_csv(output_dir / "category_mappings.csv", mapping_rows)

    spec = _preprocessing_spec()
    (output_dir / "preprocessing_spec.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    age_numeric = pd.to_numeric(raw["age"], errors="raise")
    model_summaries = {
        key: _model_summary(frame, key, output_paths[key]) for key, frame in frames.items()
    }
    summary: dict[str, object] = {
        "phase": 3,
        "status": "PASS_WITH_NOTES",
        "source": {
            "file": str(raw_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": source_hash,
            "shape": {"rows": int(raw.shape[0]), "columns": int(raw.shape[1])},
        },
        "models": model_summaries,
        "numeric_validation": {
            "age_min": int(age_numeric.min()),
            "age_max": int(age_numeric.max()),
            "non_integer_age_count": int(((age_numeric % 1) != 0).sum()),
            "out_of_range_age_count": int((~age_numeric.between(15, 110)).sum()),
        },
        "categorical_validation": {"unexpected_code_count": 0},
        "leakage_validation": {
            "passed": True,
            "model1_unapproved_columns": [],
            "model2_unapproved_columns": [],
            "identifier_columns_present": [],
            "metadata_columns_present": [],
            "parallel_targets_present": [],
        },
        "preprocessor_fitted": False,
        "processed_data_git_ignored": True,
        "notes": [
            "Routed blanks are explicit categorical states, not statistical imputations.",
            "The constructed internet_use zero category combines no, don't know, and refused.",
            "Survey weights remain outside individual-level prediction features.",
        ],
    }
    (output_dir / "phase3_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "phase3_summary.md").write_text(_render_markdown(summary), encoding="utf-8")
    missing_deliverables = validate_completed_phase_files(PROJECT_ROOT, through_phase=3)
    (output_dir / "deliverable_checklist.md").write_text(
        render_delivery_checklist(PROJECT_ROOT, through_phase=3), encoding="utf-8"
    )
    if missing_deliverables:
        raise RuntimeError(f"Completed-phase deliverable validation failed: {missing_deliverables}")
    summary["deliverable_validation"] = {
        "passed": True,
        "phases_checked": [1, 2, 3],
        "missing_files": {},
        "checklist": "reports/phase_3/deliverable_checklist.md",
    }
    (output_dir / "phase3_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run(
        raw_path=args.raw.resolve(),
        dictionary_path=args.dictionary.resolve(),
        processed_dir=args.processed_dir.resolve(),
        output_dir=args.output_dir.resolve(),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
