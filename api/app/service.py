"""Immutable, process-cached inference service for both prediction engines."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from api.app.schemas import AssessmentRequest, AssessmentResponse, ExplanationFactor, PredictionResult
from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.phase3_preprocessing import file_hash
from finaccess_eswatini.phase9_explainability import (
    SPECS,
    ExplainabilitySpec,
    explain_profile_with_loaded_artifacts,
)


PHASE9_SUMMARY_PATH = PROJECT_ROOT / "reports" / "phase_9" / "phase9_summary.json"
SERVICE_VERSION = "1.0.0"
PURPOSE = (
    "Estimate whether an individual profile is likely to be financially included "
    "and likely to use mobile money."
)
DISCLAIMER = (
    "This proof-of-concept explains model predictions, not causation, eligibility, "
    "creditworthiness, or an official World Bank classification."
)


class ArtifactIntegrityError(RuntimeError):
    """Raised when a saved model or explainer fails its immutable contract."""


class InferenceError(RuntimeError):
    """Raised when a validated request cannot be evaluated safely."""


@dataclass(frozen=True)
class ModelRuntime:
    spec: ExplainabilitySpec
    pipeline: object
    bundle: dict[str, object]
    explainer_sha256: str
    learned_categories: dict[str, frozenset[str]]


def _learned_categories(pipeline: object, features: tuple[str, ...]) -> dict[str, frozenset[str]]:
    encoder = pipeline.named_steps["preprocess"].named_transformers_["categorical"].named_steps["onehot"]
    return {
        feature: frozenset(str(value) for value in categories)
        for feature, categories in zip(features, encoder.categories_, strict=True)
    }


class PredictionService:
    """Load artifacts once and produce two predictions from one validated profile."""

    def __init__(self) -> None:
        if not PHASE9_SUMMARY_PATH.is_file():
            raise ArtifactIntegrityError("Phase 9 explainability summary is missing.")
        summary = json.loads(PHASE9_SUMMARY_PATH.read_text(encoding="utf-8"))
        self._runtimes: dict[str, ModelRuntime] = {}
        self._lock = threading.RLock()
        for spec in SPECS:
            if file_hash(spec.pipeline_path) != spec.expected_sha256:
                raise ArtifactIntegrityError(f"{spec.model_key} pipeline hash does not match validation metadata.")
            if not spec.bundle_path.is_file():
                raise ArtifactIntegrityError(f"{spec.model_key} explainer artifact is missing.")
            expected_explainer_hash = summary["models"][spec.model_key]["explainer_sha256"]
            observed_explainer_hash = file_hash(spec.bundle_path)
            if observed_explainer_hash != expected_explainer_hash:
                raise ArtifactIntegrityError(f"{spec.model_key} explainer hash does not match Phase 9 metadata.")
            pipeline = joblib.load(spec.pipeline_path)
            bundle = joblib.load(spec.bundle_path)
            if bundle.get("pipeline_sha256") != spec.expected_sha256 or bundle.get("model") != spec.model_key:
                raise ArtifactIntegrityError(f"{spec.model_key} explainer is not paired with its validated pipeline.")
            self._runtimes[spec.model_key] = ModelRuntime(
                spec=spec,
                pipeline=pipeline,
                bundle=bundle,
                explainer_sha256=observed_explainer_hash,
                learned_categories=_learned_categories(pipeline, spec.features),
            )

    @property
    def health_models(self) -> list[dict[str, str]]:
        return [
            {
                "model": runtime.spec.model_key,
                "target": runtime.spec.target,
                "status": "ready",
                "pipeline_sha256": runtime.spec.expected_sha256,
                "explainer_sha256": runtime.explainer_sha256,
            }
            for runtime in self._runtimes.values()
        ]

    def _warnings(self, runtime: ModelRuntime, profile: pd.DataFrame) -> list[str]:
        warnings: list[str] = []
        for feature in runtime.spec.features:
            value = str(profile.iloc[0][feature])
            if value not in runtime.learned_categories[feature]:
                warnings.append(
                    f"{runtime.spec.model_label} did not observe {feature}={value!r} in its training partition; "
                    "the fitted encoder safely treats it as an unseen category."
                )
        return warnings

    @staticmethod
    def _result(model_key: str, explanation: dict[str, object], warnings: list[str]) -> PredictionResult:
        direction_map = {
            "increased": "increased_likelihood",
            "reduced": "reduced_likelihood",
            "did not change": "neutral",
        }
        factors = [
            ExplanationFactor(
                feature=str(factor["source_feature"]),
                label=str(factor["feature_label"]),
                value=str(factor["profile_value"]),
                direction=direction_map[str(factor["direction"])],
                explanation=str(factor["explanation_text"]),
                contribution_log_odds=float(factor["shap_log_odds"]),
            )
            for factor in explanation["factors"]
        ]
        probability = float(explanation["probability"])
        return PredictionResult(
            model="financial_inclusion" if model_key == "model1" else "mobile_money_adoption",
            question=str(explanation["question"]),
            answer=str(explanation["prediction_statement"]),
            probability=probability,
            probability_percent=round(probability * 100, 1),
            threshold=float(explanation["threshold"]),
            threshold_status="provisional",
            baseline_probability=float(explanation["baseline_probability"]),
            main_factors=factors,
            warnings=warnings,
        )

    def assess(self, request: AssessmentRequest, assessment_id: str | None = None) -> AssessmentResponse:
        values = request.model_dump()
        outputs: dict[str, PredictionResult] = {}
        try:
            with self._lock:
                for model_key, runtime in self._runtimes.items():
                    profile = pd.DataFrame(
                        [[values[feature] for feature in runtime.spec.features]],
                        columns=list(runtime.spec.features),
                    )
                    explanation = explain_profile_with_loaded_artifacts(
                        runtime.spec,
                        runtime.pipeline,
                        runtime.bundle,
                        profile,
                        top_n=5,
                    )
                    outputs[model_key] = self._result(
                        model_key,
                        explanation,
                        self._warnings(runtime, profile),
                    )
        except (ValueError, RuntimeError, KeyError) as exc:
            raise InferenceError("The validated profile could not be evaluated safely.") from exc
        return AssessmentResponse(
            assessment_id=assessment_id or str(uuid.uuid4()),
            purpose=PURPOSE,
            financial_inclusion=outputs["model1"],
            mobile_money_adoption=outputs["model2"],
            disclaimer=DISCLAIMER,
        )


@lru_cache(maxsize=1)
def get_prediction_service() -> PredictionService:
    return PredictionService()
