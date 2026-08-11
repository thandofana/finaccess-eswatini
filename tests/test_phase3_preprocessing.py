from __future__ import annotations

import json
import os
import unittest

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import pandas as pd
from sklearn.exceptions import NotFittedError
from sklearn.utils.validation import check_is_fitted

from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.feature_config import MODEL_CONFIGS
from finaccess_eswatini.phase3_preprocessing import run
from finaccess_eswatini.preprocessing import (
    CORE_MISSING_LABEL,
    NONRESPONSE_LABEL,
    ROUTED_MISSING_LABEL,
    build_preprocessor,
    split_features_target,
)
from finaccess_eswatini.preprocessing.cleaning import COMBINED_NO_NONRESPONSE_LABEL


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "reports" / "phase_3"


class Phase3ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = run()
        cls.frames = {
            "model1": pd.read_csv(PROCESSED_DIR / "model1_financial_inclusion.csv"),
            "model2": pd.read_csv(PROCESSED_DIR / "model2_mobile_money.csv"),
        }

    def test_model_specific_shapes_and_column_contracts(self) -> None:
        expected = {
            "model1": (1051, 17),
            "model2": (1051, 27),
        }
        for key, frame in self.frames.items():
            config = MODEL_CONFIGS[key]
            self.assertEqual(frame.shape, expected[key])
            self.assertEqual(frame.columns.tolist(), [config.target, *config.features])
        self.assertNotEqual(
            set(MODEL_CONFIGS["model1"].features),
            set(MODEL_CONFIGS["model2"].features),
        )

    def test_targets_are_unchanged_complete_and_binary(self) -> None:
        expected = {
            "model1": {0: 514, 1: 537},
            "model2": {0: 440, 1: 611},
        }
        for key, frame in self.frames.items():
            target = MODEL_CONFIGS[key].target
            self.assertEqual(frame[target].value_counts().sort_index().to_dict(), expected[key])
            self.assertEqual(int(frame[target].isna().sum()), 0)

    def test_missing_and_special_responses_are_semantic_categories(self) -> None:
        model1 = self.frames["model1"]
        self.assertEqual(int((model1["educ"] == CORE_MISSING_LABEL).sum()), 10)
        self.assertEqual(int((model1["con9"] == ROUTED_MISSING_LABEL).sum()), 118)
        self.assertEqual(int((model1["con16"] == ROUTED_MISSING_LABEL).sum()), 235)
        self.assertEqual(int((model1["con1"] == NONRESPONSE_LABEL).sum()), 1)
        self.assertEqual(
            int((model1["internet_use"] == COMBINED_NO_NONRESPONSE_LABEL).sum()),
            423,
        )
        for frame in self.frames.values():
            self.assertEqual(int(frame.isna().sum().sum()), 0)
            self.assertFalse((frame.astype(str) == "").any().any())

    def test_numeric_age_contract(self) -> None:
        for frame in self.frames.values():
            self.assertEqual(int(frame["age"].min()), 15)
            self.assertEqual(int(frame["age"].max()), 100)
            self.assertTrue(((frame["age"] % 1) == 0).all())

    def test_leakage_and_identifier_fields_are_absent(self) -> None:
        forbidden = {
            "wpid_random",
            "wgt",
            "year",
            "economy",
            "economycode",
            "regionwb",
            "pop_adult",
            "account",
            "dig_account",
            "anydigpayment",
        }
        for key, frame in self.frames.items():
            parallel_target = "account_mob" if key == "model1" else "account_fin"
            self.assertTrue(forbidden.isdisjoint(frame.columns))
            self.assertNotIn(parallel_target, frame.columns)

    def test_preprocessors_are_unfitted_and_transform_unseen_rows(self) -> None:
        for key, frame in self.frames.items():
            preprocessor = build_preprocessor(key)
            with self.assertRaises(NotFittedError):
                check_is_fitted(preprocessor)
            features, _ = split_features_target(frame, key)
            transformed_train = preprocessor.fit_transform(features.iloc[:800])
            transformed_holdout = preprocessor.transform(features.iloc[800:])
            self.assertEqual(transformed_train.shape[0], 800)
            self.assertEqual(transformed_holdout.shape[0], 251)
            self.assertGreater(transformed_train.shape[1], len(features.columns))

    def test_reports_and_phase3_records_no_fitted_artifact(self) -> None:
        expected_reports = {
            "phase3_summary.json",
            "phase3_summary.md",
            "preprocessing_spec.json",
            "category_mappings.csv",
            "processed_schema_model1.csv",
            "processed_schema_model2.csv",
        }
        self.assertTrue(all((REPORT_DIR / name).is_file() for name in expected_reports))
        spec = json.loads((REPORT_DIR / "preprocessing_spec.json").read_text(encoding="utf-8"))
        self.assertFalse(spec["fitted_in_phase_3"])
        self.assertFalse(self.summary["preprocessor_fitted"])
        self.assertNotIn("model_artifact", self.summary)


if __name__ == "__main__":
    unittest.main()
