from __future__ import annotations

import json
import os
import unittest

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import pandas as pd

from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.phase5_statistics import (
    benjamini_hochberg,
    bias_corrected_cramers_v,
    run,
)


OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_5"


class Phase5StatisticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = run()
        cls.categorical = pd.read_csv(OUTPUT_DIR / "categorical_tests.csv")
        cls.numeric = pd.read_csv(OUTPUT_DIR / "numeric_tests.csv")
        cls.combined = pd.read_csv(OUTPUT_DIR / "association_results.csv")
        cls.contingency = pd.read_csv(OUTPUT_DIR / "contingency_tables.csv")

    def test_multiple_testing_reference_example(self) -> None:
        adjusted = benjamini_hochberg([0.01, 0.04, 0.03, 0.002])
        expected = [0.02, 0.04, 0.04, 0.008]
        for observed, reference in zip(adjusted, expected, strict=True):
            self.assertAlmostEqual(observed, reference, places=12)

    def test_cramers_v_is_bounded(self) -> None:
        self.assertEqual(bias_corrected_cramers_v(0.0, 100, 2, 2), 0.0)
        value = bias_corrected_cramers_v(25.0, 100, 2, 2)
        self.assertGreater(value, 0)
        self.assertLessEqual(value, 1)

    def test_expected_number_of_pre_specified_tests(self) -> None:
        self.assertEqual(len(self.categorical), 14)
        self.assertEqual(len(self.numeric), 2)
        self.assertEqual(len(self.combined), 16)
        for target in ("account_fin", "account_mob"):
            self.assertEqual(int((self.combined["target"] == target).sum()), 8)

    def test_fdr_results_and_gender_nonassociation(self) -> None:
        for target in ("account_fin", "account_mob"):
            rows = self.combined.loc[self.combined["target"] == target]
            self.assertEqual(int(rows["significant_fdr_0_05"].sum()), 7)
            gender = rows.loc[rows["variable_label"] == "Gender"].iloc[0]
            self.assertFalse(bool(gender["significant_fdr_0_05"]))
            self.assertGreater(float(gender["adjusted_p_value"]), 0.05)
        self.assertTrue((self.combined["adjusted_p_value"] >= self.combined["p_value"] - 1e-15).all())

    def test_effect_sizes_reconcile_to_reference_results(self) -> None:
        categorical = self.categorical.set_index(["target", "dimension"])
        numeric = self.numeric.set_index("target")
        self.assertAlmostEqual(
            categorical.loc[("account_fin", "income_quintile"), "effect_size"],
            0.2703711800,
            places=8,
        )
        self.assertAlmostEqual(
            categorical.loc[("account_mob", "phone_type"), "effect_size"],
            0.2364802817,
            places=8,
        )
        self.assertAlmostEqual(numeric.loc["account_fin", "effect_size"], 0.2029867617, places=8)
        self.assertAlmostEqual(numeric.loc["account_mob", "effect_size"], 0.1080122006, places=8)

    def test_chi_square_expected_count_assumptions_pass(self) -> None:
        self.assertTrue(self.categorical["assumption_passed"].all())
        self.assertEqual(int(self.categorical["expected_cells_below_5"].sum()), 0)
        self.assertGreater(float(self.categorical["minimum_expected_count"].min()), 5)
        observed_totals = self.contingency.groupby(["target", "dimension"])["observed_count"].sum()
        for total in observed_totals:
            self.assertIn(int(total), {1041, 1042, 1050, 1051})

    def test_inference_and_descriptive_weighting_are_separated(self) -> None:
        design = self.summary["design"]
        self.assertEqual(design["inference_weighting"], "unweighted respondent counts")
        self.assertEqual(design["weighted_rates_role"], "descriptive context only")
        self.assertFalse(self.summary["causal_claims_made"])
        self.assertFalse(self.summary["models_trained"])

    def test_reports_and_deliverable_validation(self) -> None:
        required = (
            "categorical_tests.csv",
            "numeric_tests.csv",
            "association_results.csv",
            "contingency_tables.csv",
            "age_distributions.csv",
            "phase5_summary.json",
            "statistical_analysis_report.md",
            "deliverable_checklist.md",
        )
        self.assertTrue(all((OUTPUT_DIR / filename).is_file() for filename in required))
        summary = json.loads((OUTPUT_DIR / "phase5_summary.json").read_text(encoding="utf-8"))
        self.assertTrue(summary["deliverable_validation"]["passed"])


if __name__ == "__main__":
    unittest.main()
