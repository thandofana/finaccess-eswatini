"""Phase 3 cleaning logic for the two approved modelling datasets."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import pandas as pd

from finaccess_eswatini.feature_config import ModelFeatureConfig, get_model_config


ROUTED_MISSING_LABEL = "Not applicable / skipped"
CORE_MISSING_LABEL = "Missing or nonresponse"
NONRESPONSE_LABEL = "Nonresponse"
COMBINED_NO_NONRESPONSE_LABEL = "No / don't know / refused"

# inc_q has a documented range of 1-5 in the DDI but no value labels. Neutral
# labels preserve the source ordering without claiming unprovided boundaries.
FALLBACK_CODE_MAPS = {
    "inc_q": {str(value): f"Income quintile {value}" for value in range(1, 6)},
}

NONRESPONSE_TERMS = ("don't know", "dont know", "refused")


def read_raw_data(path: Path) -> pd.DataFrame:
    """Read source microdata without coercing survey codes or blank routes."""

    return pd.read_csv(path, dtype="string", keep_default_na=False, na_filter=False)


def load_data_dictionary(path: Path) -> pd.DataFrame:
    """Load the Phase 2 dictionary and require one row per variable."""

    dictionary = pd.read_csv(path, dtype="string", keep_default_na=False, na_filter=False)
    if "variable" not in dictionary.columns or dictionary["variable"].duplicated().any():
        raise ValueError("Phase 2 data dictionary must contain one unique row per variable.")
    return dictionary.set_index("variable", drop=False)


def _is_nonresponse(label: str) -> bool:
    lowered = label.casefold().strip()
    return any(term in lowered for term in NONRESPONSE_TERMS)


def _documented_code_map(dictionary_row: pd.Series) -> dict[str, str]:
    value = str(dictionary_row["documented_codes"]).strip()
    entries = json.loads(value or "[]")
    mapping: dict[str, str] = {}
    for entry in entries:
        raw_value = str(entry.get("value", "")).strip()
        label = str(entry.get("label", "")).strip()
        if not raw_value or raw_value.casefold() == "sysmiss":
            continue
        if label.casefold() == "no/dk/ref":
            mapping[raw_value] = COMBINED_NO_NONRESPONSE_LABEL
        elif _is_nonresponse(label):
            mapping[raw_value] = NONRESPONSE_LABEL
        else:
            mapping[raw_value] = label or f"Code {raw_value}"
    return mapping


def category_code_map(variable: str, dictionary: pd.DataFrame) -> dict[str, str]:
    """Return the approved raw-code-to-label mapping for one predictor."""

    if variable in FALLBACK_CODE_MAPS:
        return FALLBACK_CODE_MAPS[variable].copy()
    if variable not in dictionary.index:
        raise KeyError(f"{variable!r} is absent from the Phase 2 data dictionary.")
    mapping = _documented_code_map(dictionary.loc[variable])
    if not mapping:
        raise ValueError(f"No categorical code mapping is available for {variable!r}.")
    return mapping


def _clean_categorical(
    series: pd.Series,
    variable: str,
    mapping: dict[str, str],
    missing_label: str,
) -> pd.Series:
    stripped = series.astype("string").str.strip()
    nonblank = set(stripped[stripped.ne("")].unique().tolist())
    unknown = sorted(nonblank - set(mapping))
    if unknown:
        raise ValueError(f"Unexpected raw codes for {variable}: {unknown}")
    cleaned = stripped.map(mapping)
    cleaned = cleaned.where(stripped.ne(""), missing_label)
    if cleaned.isna().any():
        raise ValueError(f"Cleaning {variable!r} created unmapped values.")
    return cleaned.astype("string")


def _validate_phase2_contract(dictionary: pd.DataFrame, config: ModelFeatureConfig) -> None:
    status_field = f"{config.key}_status"
    if status_field not in dictionary.columns:
        raise ValueError(f"Phase 2 dictionary is missing {status_field!r}.")
    approved = {
        name
        for name, status in dictionary[status_field].items()
        if str(status).startswith("CANDIDATE")
    }
    if approved != set(config.features):
        missing = sorted(approved - set(config.features))
        extra = sorted(set(config.features) - approved)
        raise ValueError(
            f"Feature contract drift for {config.key}; unconfigured={missing}, unapproved={extra}."
        )


def clean_model_frame(
    raw: pd.DataFrame,
    dictionary: pd.DataFrame,
    model: str | int,
) -> pd.DataFrame:
    """Create a target-plus-features frame using only Phase 2-approved fields."""

    config = get_model_config(model)
    _validate_phase2_contract(dictionary, config)
    required = (config.target, *config.features)
    absent = [name for name in required if name not in raw.columns]
    if absent:
        raise ValueError(f"Raw dataset is missing required fields: {absent}")

    output = pd.DataFrame(index=raw.index)
    target = pd.to_numeric(raw[config.target], errors="raise")
    if target.isna().any() or not set(target.astype(int).unique()).issubset({0, 1}):
        raise ValueError(f"{config.target} must be complete and binary (0/1).")
    output[config.target] = target.astype("int8")

    age = pd.to_numeric(raw["age"].replace("", pd.NA), errors="raise")
    if age.isna().any():
        raise ValueError("age is a required numeric field and cannot be blank in the raw dataset.")
    if ((age % 1) != 0).any() or not age.between(15, 110).all():
        raise ValueError("age must contain whole years between 15 and 110.")

    for variable in config.features:
        if variable in config.numeric_features:
            output[variable] = age.astype("int16")
            continue
        missing_label = (
            ROUTED_MISSING_LABEL
            if variable in config.conditional_features
            else CORE_MISSING_LABEL
        )
        output[variable] = _clean_categorical(
            raw[variable],
            variable,
            category_code_map(variable, dictionary),
            missing_label,
        )

    validate_clean_frame(output, model)
    return output.loc[:, list(required)]


def validate_clean_frame(frame: pd.DataFrame, model: str | int) -> None:
    """Validate shape, types, ordering, and leakage boundaries."""

    config = get_model_config(model)
    expected = [config.target, *config.features]
    if frame.columns.tolist() != expected:
        raise ValueError(f"Unexpected {config.key} columns or order.")
    if frame.empty:
        raise ValueError(f"{config.key} modelling frame cannot be empty.")
    if frame.isna().any().any():
        raise ValueError(f"{config.key} modelling frame contains unresolved missing values.")
    if not set(frame[config.target].unique()).issubset({0, 1}):
        raise ValueError(f"{config.target} is not binary after cleaning.")
    age = frame["age"]
    if not age.between(15, 110).all():
        raise ValueError("Cleaned age values fall outside the approved range.")


def split_features_target(
    frame: pd.DataFrame, model: str | int
) -> tuple[pd.DataFrame, pd.Series]:
    """Return ordered X and y without fitting or transforming either one."""

    config = get_model_config(model)
    validate_clean_frame(frame, model)
    return frame.loc[:, config.features].copy(), frame[config.target].copy()


def observed_mapping_rows(
    raw: pd.DataFrame,
    dictionary: pd.DataFrame,
    variables: Iterable[str],
) -> list[dict[str, object]]:
    """Describe every observed mapping used by the generated datasets."""

    rows: list[dict[str, object]] = []
    for variable in variables:
        mapping = category_code_map(variable, dictionary)
        documented = _documented_code_map(dictionary.loc[variable]) if variable in dictionary.index else {}
        observed = raw[variable].astype("string").str.strip()
        counts = observed.value_counts(dropna=False).to_dict()
        for raw_value, cleaned_label in mapping.items():
            rows.append(
                {
                    "variable": variable,
                    "raw_value": raw_value,
                    "source_label": documented.get(raw_value, "DDI range 1-5; neutral project label"),
                    "cleaned_label": cleaned_label,
                    "mapping_basis": "documented code" if raw_value in documented else "documented range",
                    "observed_count": int(counts.get(raw_value, 0)),
                }
            )
        rows.append(
            {
                "variable": variable,
                "raw_value": "<blank>",
                "source_label": "System missing / routed blank",
                "cleaned_label": "model-specific; see feature tier",
                "mapping_basis": "routing-aware missingness policy",
                "observed_count": int(counts.get("", 0)),
            }
        )
    return rows
