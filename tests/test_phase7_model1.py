from __future__ import annotations

import hashlib
import json
import os
import unittest
import warnings

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MPLBACKEND", "Agg")

import joblib
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.pipeline import Pipeline

from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.phase7_model1 import (
    DEFAULT_METADATA_PATH,
    DEFAULT_MODEL_PATH,
    DEFAULT_OUTPUT_DIR,
    MODEL1_FINAL_FEATURES,
    build_cv_splits,
    create_holdout_split,
    load_model_frame,
)


class Phase7Model1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = load_model_frame()
        cls.split = create_holdout_split(cls.frame)
        cls.summary = json.loads(
            (DEFAULT_OUTPUT_DIR / "phase7_summary.json").read_text(encoding="utf-8")
        )
        cls.comparison = pd.read_csv(DEFAULT_OUTPUT_DIR / "model_comparison.csv")
        cls.metrics = pd.read_csv(DEFAULT_OUTPUT_DIR / "holdout_metrics.csv")

    def test_group_aware_holdout_is_deterministic_and_disjoint(self) -> None:
        metadata = self.split["metadata"]
        self.assertEqual(metadata["train_rows"], 840)
        self.assertEqual(metadata["test_rows"], 211)
        self.assertEqual(metadata["profile_overlap_count"], 0)
        self.assertEqual(metadata["unique_profiles_total"], 877)
        self.assertEqual(metadata["duplicate_rows_after_first"], 174)
        self.assertEqual(metadata["conflicting_label_profile_groups"], 44)
        self.assertEqual(metadata["respondents_in_conflicting_groups"], 134)
        repeated = create_holdout_split(self.frame)
        np.testing.assert_array_equal(self.split["train_index"], repeated["train_index"])
        np.testing.assert_array_equal(self.split["test_index"], repeated["test_index"])

    def test_cross_validation_folds_have_no_profile_overlap(self) -> None:
        _, rows = build_cv_splits(
            self.split["X_train"],
            self.split["y_train"],
            self.split["groups_train"],
        )
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row["profile_overlap_count"] == 0 for row in rows))
        self.assertEqual(sum(row["validation_rows"] for row in rows), 840)

    def test_candidate_set_and_selection_rule_are_auditable(self) -> None:
        self.assertEqual(
            set(self.comparison["model_key"]),
            {
                "dummy",
                "logistic_regression",
                "decision_tree",
                "random_forest",
                "gradient_boosting",
            },
        )
        self.assertEqual(int(self.comparison["selected"].sum()), 1)
        selected = self.comparison.loc[self.comparison["selected"]].iloc[0]
        eligible = self.comparison.loc[self.comparison["within_one_se_of_best_auc"]]
        self.assertTrue(bool(selected["within_one_se_of_best_auc"]))
        self.assertEqual(int(selected["complexity_rank"]), int(eligible["complexity_rank"].min()))
        self.assertNotIn("holdout_roc_auc", self.comparison.columns)

    def test_holdout_metrics_and_confusion_reconcile(self) -> None:
        required = {
            "accuracy",
            "balanced_accuracy",
            "precision",
            "recall",
            "f1",
            "roc_auc",
            "brier_score",
            "log_loss",
        }
        self.assertEqual(set(self.metrics["metric"]), required)
        self.assertTrue(self.metrics["value"].between(0, 1).all())
        matrix = pd.read_csv(DEFAULT_OUTPUT_DIR / "confusion_matrix.csv")
        self.assertEqual(int(matrix["count"].sum()), 211)
        intervals = pd.read_csv(DEFAULT_OUTPUT_DIR / "bootstrap_intervals.csv")
        self.assertEqual(set(intervals["metric"]), {"accuracy", "precision", "recall", "f1", "roc_auc", "brier_score"})
        self.assertTrue((intervals["lower_95"] <= intervals["median"]).all())
        self.assertTrue((intervals["median"] <= intervals["upper_95"]).all())
        self.assertTrue((intervals["iterations"] == 1000).all())

    def test_saved_complete_pipeline_reloads_and_predicts(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            pipeline = joblib.load(DEFAULT_MODEL_PATH)
        self.assertIsInstance(pipeline, Pipeline)
        self.assertEqual(list(pipeline.named_steps), ["preprocess", "model"])
        probability = pipeline.predict_proba(self.split["X_test"])
        self.assertEqual(probability.shape, (211, 2))
        self.assertTrue(np.allclose(probability.sum(axis=1), 1.0))
        unseen_profile = self.split["X_test"].iloc[[0]].copy()
        unseen_profile["female"] = "Unseen inference category"
        unseen_probability = pipeline.predict_proba(unseen_profile)
        self.assertEqual(unseen_probability.shape, (1, 2))
        self.assertTrue(np.allclose(unseen_probability.sum(axis=1), 1.0))
        metadata = json.loads(DEFAULT_METADATA_PATH.read_text(encoding="utf-8"))
        digest = hashlib.sha256(DEFAULT_MODEL_PATH.read_bytes()).hexdigest()
        self.assertEqual(metadata["model_sha256"], digest)
        self.assertEqual(metadata["input_features"], list(MODEL1_FINAL_FEATURES))
        self.assertEqual(metadata["decision_threshold"], 0.5)

    def test_holdout_category_coverage_and_calibration_are_reported(self) -> None:
        coverage = pd.read_csv(DEFAULT_OUTPUT_DIR / "test_category_coverage.csv")
        self.assertEqual(coverage["feature"].tolist(), list(MODEL1_FINAL_FEATURES))
        self.assertEqual(int(coverage["unseen_test_category_count"].sum()), 1)
        unseen = coverage.loc[coverage["unseen_test_category_count"] == 1].iloc[0]
        self.assertEqual(unseen["feature"], "con12")
        self.assertIn("Never", unseen["unseen_test_categories"])
        calibration = pd.read_csv(DEFAULT_OUTPUT_DIR / "calibration_curve.csv")
        self.assertEqual(int(calibration["n"].sum()), 211)
        self.assertTrue(calibration["mean_predicted_probability"].between(0, 1).all())
        self.assertTrue(calibration["observed_positive_rate"].between(0, 1).all())

    def test_phase_scope_excludes_model2_and_explainability(self) -> None:
        self.assertFalse(self.summary["model2_trained"])
        self.assertFalse(self.summary["feature_importance_generated"])
        self.assertFalse(self.summary["shap_generated"])
        self.assertNotIn("model2_artifact", self.summary)
        self.assertNotIn("model2_metrics", self.summary)

    def test_figures_reports_and_deliverables_are_valid(self) -> None:
        for name in ("01_model_comparison.png", "02_holdout_evaluation.png"):
            path = DEFAULT_OUTPUT_DIR / "figures" / name
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 20_000)
            with Image.open(path) as image:
                self.assertGreaterEqual(image.width, 1800)
                self.assertGreaterEqual(image.height, 700)
        self.assertTrue((DEFAULT_OUTPUT_DIR / "model1_report.md").is_file())
        self.assertTrue(self.summary["artifact"]["reload_prediction_match"])
        self.assertTrue(self.summary["deliverable_validation"]["passed"])


if __name__ == "__main__":
    unittest.main()
