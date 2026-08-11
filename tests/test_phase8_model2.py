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
from finaccess_eswatini.phase8_model2 import (
    DEFAULT_METADATA_PATH,
    DEFAULT_MODEL_PATH,
    DEFAULT_OUTPUT_DIR,
    MODEL1_MODEL_PATH,
    MODEL2_FINAL_FEATURES,
    build_cv_splits,
    create_holdout_split,
    load_model_frame,
)


class Phase8Model2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = load_model_frame()
        cls.split = create_holdout_split(cls.frame)
        cls.summary = json.loads(
            (DEFAULT_OUTPUT_DIR / "phase8_summary.json").read_text(encoding="utf-8")
        )
        cls.comparison = pd.read_csv(DEFAULT_OUTPUT_DIR / "model_comparison.csv")
        cls.metrics = pd.read_csv(DEFAULT_OUTPUT_DIR / "holdout_metrics.csv")

    def test_group_aware_holdout_is_independent_and_disjoint(self) -> None:
        metadata = self.split["metadata"]
        self.assertEqual(metadata["train_rows"], 841)
        self.assertEqual(metadata["test_rows"], 210)
        self.assertEqual(metadata["profile_overlap_count"], 0)
        self.assertEqual(metadata["unique_profiles_total"], 958)
        self.assertEqual(metadata["duplicate_rows_after_first"], 93)
        self.assertEqual(metadata["conflicting_label_profile_groups"], 32)
        self.assertEqual(metadata["respondents_in_conflicting_groups"], 77)
        repeated = create_holdout_split(self.frame)
        np.testing.assert_array_equal(self.split["train_index"], repeated["train_index"])
        np.testing.assert_array_equal(self.split["test_index"], repeated["test_index"])

    def test_model2_cross_validation_folds_have_no_profile_overlap(self) -> None:
        _, rows = build_cv_splits(
            self.split["X_train"],
            self.split["y_train"],
            self.split["groups_train"],
        )
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row["profile_overlap_count"] == 0 for row in rows))
        self.assertEqual(sum(row["validation_rows"] for row in rows), 841)

    def test_model2_candidate_search_and_selection_are_separate(self) -> None:
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
        self.assertEqual(int(selected["complexity_rank"]), int(eligible["complexity_rank"].min()))
        self.assertEqual(
            float(selected["cv_mean_roc_auc"]),
            float(
                eligible.loc[
                    eligible["complexity_rank"] == selected["complexity_rank"],
                    "cv_mean_roc_auc",
                ].max()
            ),
        )
        self.assertNotIn("holdout_roc_auc", self.comparison.columns)

    def test_model2_holdout_metrics_and_confusion_reconcile(self) -> None:
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
        self.assertEqual(int(matrix["count"].sum()), 210)
        intervals = pd.read_csv(DEFAULT_OUTPUT_DIR / "bootstrap_intervals.csv")
        self.assertTrue((intervals["lower_95"] <= intervals["median"]).all())
        self.assertTrue((intervals["median"] <= intervals["upper_95"]).all())
        self.assertTrue((intervals["iterations"] == 1000).all())

    def test_saved_model2_pipeline_reloads_and_handles_unknowns(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            pipeline = joblib.load(DEFAULT_MODEL_PATH)
        self.assertIsInstance(pipeline, Pipeline)
        self.assertEqual(list(pipeline.named_steps), ["preprocess", "model"])
        probability = pipeline.predict_proba(self.split["X_test"])
        self.assertEqual(probability.shape, (210, 2))
        self.assertTrue(np.allclose(probability.sum(axis=1), 1.0))
        unseen = self.split["X_test"].iloc[[0]].copy()
        unseen["internet_engagement_level"] = "Unseen inference category"
        self.assertEqual(pipeline.predict_proba(unseen).shape, (1, 2))
        metadata = json.loads(DEFAULT_METADATA_PATH.read_text(encoding="utf-8"))
        digest = hashlib.sha256(DEFAULT_MODEL_PATH.read_bytes()).hexdigest()
        self.assertEqual(metadata["model_sha256"], digest)
        self.assertEqual(metadata["input_features"], list(MODEL2_FINAL_FEATURES))
        self.assertEqual(metadata["target"], "account_mob")

    def test_model1_pipeline_remained_unchanged(self) -> None:
        safeguard = self.summary["model1_safeguard"]
        self.assertTrue(safeguard["unchanged"])
        self.assertEqual(
            safeguard["pipeline_sha256_before"], safeguard["pipeline_sha256_after"]
        )
        self.assertEqual(file_hash_for_test(MODEL1_MODEL_PATH), safeguard["pipeline_sha256_after"])

    def test_model2_category_coverage_and_calibration_are_reported(self) -> None:
        coverage = pd.read_csv(DEFAULT_OUTPUT_DIR / "test_category_coverage.csv")
        self.assertEqual(coverage["feature"].tolist(), list(MODEL2_FINAL_FEATURES))
        self.assertEqual(
            int(coverage["unseen_test_category_count"].sum()),
            self.summary["diagnostics"]["unseen_holdout_category_count"],
        )
        calibration = pd.read_csv(DEFAULT_OUTPUT_DIR / "calibration_curve.csv")
        self.assertEqual(int(calibration["n"].sum()), 210)
        self.assertTrue(calibration["mean_predicted_probability"].between(0, 1).all())

    def test_phase_scope_stops_before_explainability(self) -> None:
        self.assertFalse(self.summary["feature_importance_generated"])
        self.assertFalse(self.summary["shap_generated"])
        self.assertTrue(self.summary["artifact"]["reload_prediction_match"])

    def test_phase8_figures_reports_and_deliverables_are_valid(self) -> None:
        for name in ("01_model_comparison.png", "02_holdout_evaluation.png"):
            path = DEFAULT_OUTPUT_DIR / "figures" / name
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 20_000)
            with Image.open(path) as image:
                self.assertGreaterEqual(image.width, 1800)
                self.assertGreaterEqual(image.height, 700)
        self.assertTrue((DEFAULT_OUTPUT_DIR / "model2_report.md").is_file())
        self.assertTrue(self.summary["deliverable_validation"]["passed"])


def file_hash_for_test(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
