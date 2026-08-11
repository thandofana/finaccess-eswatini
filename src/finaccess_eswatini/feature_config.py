"""Approved model-specific feature contracts from Phase 2.

The ordered tuples define the only raw predictors that Phase 3 may place in
each modelling dataset. Keeping this policy in one module prevents the data
cleaner, preprocessing templates, reports, and later model code from drifting.
"""

from __future__ import annotations

from dataclasses import dataclass


MODEL1_CORE_FEATURES = (
    "female",
    "age",
    "educ",
    "inc_q",
    "emp_in",
    "internet_use",
    "con1",
    "fin46",
)

MODEL1_CONDITIONAL_FEATURES = (
    "fin24c",
    "con9",
    "con11",
    "con12",
    "con14",
    "con16",
    "con18",
    "con20",
)

MODEL2_CORE_FEATURES = MODEL1_CORE_FEATURES

MODEL2_CONDITIONAL_FEATURES = MODEL1_CONDITIONAL_FEATURES + (
    "con26",
    "con27",
    "con28",
    "con30a",
    "con30b",
    "con30c",
    "con30d",
    "con30e",
    "con30g",
    "con30h",
)

# Dataset order is retained to make generated files stable and easy to compare
# with the source data dictionary.
MODEL1_FEATURES = (
    "female",
    "age",
    "educ",
    "inc_q",
    "emp_in",
    "fin24c",
    "internet_use",
    "con1",
    "con9",
    "con11",
    "con12",
    "con14",
    "con16",
    "con18",
    "con20",
    "fin46",
)

MODEL2_FEATURES = (
    "female",
    "age",
    "educ",
    "inc_q",
    "emp_in",
    "fin24c",
    "internet_use",
    "con1",
    "con9",
    "con11",
    "con12",
    "con14",
    "con16",
    "con18",
    "con20",
    "con26",
    "con27",
    "con28",
    "con30a",
    "con30b",
    "con30c",
    "con30d",
    "con30e",
    "con30g",
    "con30h",
    "fin46",
)


@dataclass(frozen=True)
class ModelFeatureConfig:
    """Immutable feature contract for one prediction engine."""

    key: str
    target: str
    features: tuple[str, ...]
    core_features: tuple[str, ...]
    conditional_features: tuple[str, ...]
    numeric_features: tuple[str, ...] = ("age",)

    @property
    def categorical_features(self) -> tuple[str, ...]:
        return tuple(name for name in self.features if name not in self.numeric_features)


MODEL_CONFIGS = {
    "model1": ModelFeatureConfig(
        key="model1",
        target="account_fin",
        features=MODEL1_FEATURES,
        core_features=MODEL1_CORE_FEATURES,
        conditional_features=MODEL1_CONDITIONAL_FEATURES,
    ),
    "model2": ModelFeatureConfig(
        key="model2",
        target="account_mob",
        features=MODEL2_FEATURES,
        core_features=MODEL2_CORE_FEATURES,
        conditional_features=MODEL2_CONDITIONAL_FEATURES,
    ),
}


def get_model_config(model: str | int) -> ModelFeatureConfig:
    """Return a model contract from a friendly model identifier."""

    aliases = {1: "model1", 2: "model2", "1": "model1", "2": "model2"}
    key = aliases.get(model, model)
    if key not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model {model!r}; expected 'model1' or 'model2'.")
    return MODEL_CONFIGS[str(key)]
