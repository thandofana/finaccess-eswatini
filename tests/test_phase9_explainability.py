from __future__ import annotations

import hashlib
import json
import unittest

import joblib
import numpy as np
import pandas as pd
from PIL import Image

from finaccess_eswatini.phase7_model1 import DEFAULT_MODEL_PATH as MODEL1_PATH
from finaccess_eswatini.phase8_model2 import DEFAULT_MODEL_PATH as MODEL2_PATH
from finaccess_eswatini.phase9_explainability import (
    ADDITIVITY_TOLERANCE,
    DEFAULT_OUTPUT_DIR,
    MODEL1_EXPECTED_SHA256,
    MODEL2_EXPECTED_SHA256,
    SPECS,
    _load_inputs,
    explain_profile,
)


class Phase9ExplainabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = json.loads((DEFAULT_OUTPUT_DIR / "phase9_summary.json").read_text(encoding="utf-8"))
        cls.global_table = pd.read_csv(DEFAULT_OUTPUT_DIR / "global_shap_importance.csv")
        cls.individual = pd.read_csv(DEFAULT_OUTPUT_DIR / "individual_explanations.csv")
        cls.validation = pd.read_csv(DEFAULT_OUTPUT_DIR / "additivity_validation.csv")

    def test_both_models_have_separate_explainers(self) -> None:
        self.assertEqual(set(self.summary["models"]), {"model1", "model2"})
        self.assertEqual(self.summary["models"]["model1"]["explainer_type"], "TreeExplainer")
        self.assertEqual(self.summary["models"]["model2"]["explainer_type"], "LinearExplainer")
        for spec in SPECS:
            self.assertTrue(spec.bundle_path.is_file())
            bundle = joblib.load(spec.bundle_path)
            self.assertEqual(bundle["pipeline_sha256"], spec.expected_sha256)
            self.assertEqual(bundle["model"], spec.model_key)

    def test_validated_pipelines_are_unchanged(self) -> None:
        self.assertEqual(hashlib.sha256(MODEL1_PATH.read_bytes()).hexdigest(), MODEL1_EXPECTED_SHA256)
        self.assertEqual(hashlib.sha256(MODEL2_PATH.read_bytes()).hexdigest(), MODEL2_EXPECTED_SHA256)

    def test_global_tables_cover_original_and_encoded_features(self) -> None:
        expected_counts = {"model1": 15, "model2": 16}
        self.assertEqual(self.global_table.groupby("model").size().to_dict(), expected_counts)
        shares = self.global_table.groupby("model")["importance_share"].sum()
        np.testing.assert_allclose(shares.to_numpy(), 1.0)
        encoded = pd.read_csv(DEFAULT_OUTPUT_DIR / "encoded_shap_importance.csv")
        self.assertEqual(encoded.groupby("model").size().to_dict(), {"model1": 58, "model2": 72})
        native = pd.read_csv(DEFAULT_OUTPUT_DIR / "native_feature_importance.csv")
        self.assertEqual(native.groupby("model").size().to_dict(), expected_counts)

    def test_shap_reconstructs_raw_scores_and_probabilities(self) -> None:
        self.assertTrue((self.validation["max_raw_score_error"] <= ADDITIVITY_TOLERANCE).all())
        self.assertTrue((self.validation["max_probability_error"] <= ADDITIVITY_TOLERANCE).all())
        self.assertTrue((self.validation["max_source_aggregation_error"] <= ADDITIVITY_TOLERANCE).all())
        self.assertTrue(self.validation["explainer_reload_match"].all())

    def test_individual_explanations_are_model_derived_and_ranked(self) -> None:
        self.assertEqual(len(self.individual), 30)
        self.assertEqual(set(self.individual["example_type"]), {"lowest_probability", "boundary", "highest_probability"})
        for _, group in self.individual.groupby(["model", "example_type"]):
            self.assertEqual(group["factor_rank"].tolist(), [1, 2, 3, 4, 5])
            magnitudes = group["shap_log_odds"].abs().to_numpy()
            self.assertTrue(np.all(magnitudes[:-1] >= magnitudes[1:]))
        positive = self.individual["shap_log_odds"] > 0
        negative = self.individual["shap_log_odds"] < 0
        self.assertTrue((self.individual.loc[positive, "direction"] == "increased").all())
        self.assertTrue((self.individual.loc[negative, "direction"] == "reduced").all())

    def test_reusable_inference_explanation_matches_pipeline(self) -> None:
        for spec in SPECS:
            pipeline, split = _load_inputs(spec)
            profile = split["X_test"].iloc[[0]].copy()
            result = explain_profile(spec.model_key, profile)
            expected_probability = float(pipeline.predict_proba(profile)[0, 1])
            self.assertAlmostEqual(result["probability"], expected_probability, places=12)
            self.assertLessEqual(result["additivity_error"], ADDITIVITY_TOLERANCE)
            self.assertEqual(len(result["factors"]), 5)

    def test_reports_figures_and_phase_scope(self) -> None:
        for name in ("01_global_shap_importance.png", "02_individual_explanations.png"):
            path = DEFAULT_OUTPUT_DIR / "figures" / name
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 20_000)
            with Image.open(path) as image:
                self.assertGreaterEqual(image.width, 1800)
                self.assertGreaterEqual(image.height, 700)
        self.assertTrue((DEFAULT_OUTPUT_DIR / "explainability_report.md").is_file())
        self.assertTrue(self.summary["deliverable_validation"]["passed"])
        self.assertFalse(self.summary["next_phase_started"])


if __name__ == "__main__":
    unittest.main()
