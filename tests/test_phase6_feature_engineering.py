from __future__ import annotations

import json
import os
import unittest

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MPLBACKEND", "Agg")

import pandas as pd
from PIL import Image

from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.phase6_feature_engineering import (
    AGE_LABELS,
    DEFAULT_MODEL1_INPUT,
    DEFAULT_MODEL1_OUTPUT,
    DEFAULT_MODEL2_INPUT,
    DEFAULT_MODEL2_OUTPUT,
    MODEL1_FINAL_FEATURES,
    MODEL2_FINAL_FEATURES,
    engineer_model_frame,
    run,
)


OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_6"


class Phase6FeatureEngineeringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = run()
        cls.model1 = pd.read_csv(DEFAULT_MODEL1_OUTPUT)
        cls.model2 = pd.read_csv(DEFAULT_MODEL2_OUTPUT)

    def test_final_shapes_and_target_distributions(self) -> None:
        self.assertEqual(self.model1.shape, (1051, 16))
        self.assertEqual(self.model2.shape, (1051, 17))
        self.assertEqual(self.model1["account_fin"].value_counts().to_dict(), {1: 537, 0: 514})
        self.assertEqual(self.model2["account_mob"].value_counts().to_dict(), {1: 611, 0: 440})
        self.assertEqual(self.model1.columns.tolist(), ["account_fin", *MODEL1_FINAL_FEATURES])
        self.assertEqual(self.model2.columns.tolist(), ["account_mob", *MODEL2_FINAL_FEATURES])

    def test_outputs_are_complete_and_all_predictors_are_categorical(self) -> None:
        self.assertEqual(int(self.model1.isna().sum().sum()), 0)
        self.assertEqual(int(self.model2.isna().sum().sum()), 0)
        self.assertEqual(self.summary["models"]["model1"]["numeric_features"], [])
        self.assertEqual(self.summary["models"]["model2"]["numeric_features"], [])

    def test_fixed_age_bands_cover_every_respondent(self) -> None:
        self.assertEqual(set(self.model1["age_group"].unique()), set(AGE_LABELS))
        self.assertEqual(set(self.model2["age_group"].unique()), set(AGE_LABELS))
        self.assertTrue(self.model1["age_group"].equals(self.model2["age_group"]))

    def test_phone_access_routing_reconciles_to_source(self) -> None:
        expected = {
            "Smartphone": 582,
            "Basic text phone": 342,
            "No personal mobile phone": 117,
            "Phone type nonresponse": 9,
            "Phone ownership nonresponse": 1,
        }
        self.assertEqual(self.model1["phone_access_tier"].value_counts().to_dict(), expected)
        self.assertEqual(self.model2["phone_access_tier"].value_counts().to_dict(), expected)

    def test_model2_digital_routing_reconciles(self) -> None:
        internet = self.model2["internet_engagement_level"].value_counts().to_dict()
        self.assertEqual(internet["No recent internet use / no-DK-ref"], 423)
        self.assertEqual(internet["Daily internet use"], 429)
        self.assertEqual(sum(internet.values()), 1051)
        purchase = self.model2["data_purchase_pattern"].value_counts().to_dict()
        self.assertEqual(purchase["No recent internet use / skipped"], 423)
        self.assertEqual(purchase["Does not purchase data"], 76)
        self.assertEqual(sum(purchase.values()), 1051)

    def test_replaced_and_rejected_fields_are_absent(self) -> None:
        self.assertTrue({"age", "con1", "con9"}.isdisjoint(self.model1.columns))
        excluded_model2 = {
            "age",
            "con1",
            "con9",
            "internet_use",
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
        }
        self.assertTrue(excluded_model2.isdisjoint(self.model2.columns))
        self.assertNotIn("account_mob", self.model1.columns)
        self.assertNotIn("account_fin", self.model2.columns)

    def test_feature_derivation_is_target_independent(self) -> None:
        source1 = pd.read_csv(DEFAULT_MODEL1_INPUT)
        original1 = engineer_model_frame(source1, "model1")
        source1["account_fin"] = 1 - source1["account_fin"]
        changed1 = engineer_model_frame(source1, "model1")
        pd.testing.assert_frame_equal(
            original1.loc[:, list(MODEL1_FINAL_FEATURES)],
            changed1.loc[:, list(MODEL1_FINAL_FEATURES)],
        )

        source2 = pd.read_csv(DEFAULT_MODEL2_INPUT)
        original2 = engineer_model_frame(source2, "model2")
        source2["account_mob"] = 1 - source2["account_mob"]
        changed2 = engineer_model_frame(source2, "model2")
        pd.testing.assert_frame_equal(
            original2.loc[:, list(MODEL2_FINAL_FEATURES)],
            changed2.loc[:, list(MODEL2_FINAL_FEATURES)],
        )

    def test_review_records_key_exclusions_and_no_target_use(self) -> None:
        review = pd.read_csv(OUTPUT_DIR / "feature_engineering_review.csv")
        self.assertFalse(review["uses_target"].any())
        model2_online = review.loc[
            (review["model"] == "model2")
            & (review["engineered_feature"] == "online_activity_breadth")
        ].iloc[0]
        self.assertEqual(model2_online["decision"], "EXCLUDE")
        self.assertEqual(model2_online["leakage_risk"], "MODERATE")
        self.assertEqual(
            review.loc[
                review["engineered_feature"] == "digital_access_score", "decision"
            ].unique().tolist(),
            ["EXCLUDE"],
        )

    def test_phase_contains_no_model_or_split_outputs(self) -> None:
        self.assertFalse(self.summary["split_performed"])
        self.assertFalse(self.summary["models_trained"])
        self.assertNotIn("model_artifact", self.summary)
        self.assertNotIn("model_metrics", self.summary)

    def test_figure_and_report_artifacts_are_valid(self) -> None:
        png = OUTPUT_DIR / "figures" / "01_engineered_feature_distributions.png"
        svg = OUTPUT_DIR / "figures" / "01_engineered_feature_distributions.svg"
        self.assertTrue(png.is_file())
        self.assertTrue(svg.is_file())
        self.assertGreater(png.stat().st_size, 10_000)
        with Image.open(png) as image:
            self.assertGreaterEqual(image.width, 1800)
            self.assertGreaterEqual(image.height, 1200)
        summary = json.loads((OUTPUT_DIR / "phase6_summary.json").read_text(encoding="utf-8"))
        self.assertTrue(summary["deliverable_validation"]["passed"])
        self.assertTrue((OUTPUT_DIR / "feature_engineering_report.md").is_file())
        self.assertTrue((OUTPUT_DIR / "deliverable_checklist.md").is_file())


if __name__ == "__main__":
    unittest.main()
