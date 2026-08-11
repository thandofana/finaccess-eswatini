"""Unfitted scikit-learn preprocessing templates for each model."""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from finaccess_eswatini.feature_config import get_model_config


def build_preprocessor(model: str | int, *, scale_numeric: bool = True) -> ColumnTransformer:
    """Build, but deliberately do not fit, a model-specific transformer.

    The returned object must later be placed inside a full estimator pipeline
    and fitted only on training data (or within a cross-validation fold).
    """

    config = get_model_config(model)
    numeric_steps: list[tuple[str, object]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "one_hot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=True),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", Pipeline(numeric_steps), list(config.numeric_features)),
            ("categorical", categorical_pipeline, list(config.categorical_features)),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )
