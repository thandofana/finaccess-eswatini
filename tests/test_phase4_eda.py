from __future__ import annotations

import json
import os
import unittest

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MPLBACKEND", "Agg")

import pandas as pd
from PIL import Image

from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.phase4_eda import DIMENSIONS, run


OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_4"


class Phase4EdaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = run()
        cls.overall = pd.read_csv(OUTPUT_DIR / "overall_rates.csv")
        cls.subgroup = pd.read_csv(OUTPUT_DIR / "subgroup_rates.csv")

    def test_weight_contract_and_source_rows(self) -> None:
        validation = self.summary["source_validation"]
        self.assertEqual(validation["rows"], 1051)
        self.assertEqual(validation["weight_count"], 1051)
        self.assertEqual(validation["weight_missing"], 0)
        self.assertEqual(validation["weight_nonpositive"], 0)
        self.assertAlmostEqual(validation["weight_sum"], 1051.0, places=6)

    def test_overall_rates_reconcile_with_targets(self) -> None:
        by_target = self.overall.set_index("target")
        self.assertEqual(int(by_target.loc["account_fin", "positive_count"]), 537)
        self.assertEqual(int(by_target.loc["account_mob", "positive_count"]), 611)
        self.assertAlmostEqual(by_target.loc["account_fin", "weighted_rate"], 0.4313562215, places=8)
        self.assertAlmostEqual(by_target.loc["account_mob", "weighted_rate"], 0.5040691756, places=8)
        self.assertAlmostEqual(by_target.loc["account_fin", "unweighted_rate"], 537 / 1051, places=12)
        self.assertAlmostEqual(by_target.loc["account_mob", "unweighted_rate"], 611 / 1051, places=12)

    def test_every_dimension_reconciles_to_full_sample(self) -> None:
        self.assertEqual(len(self.subgroup), 56)
        for target in ("account_fin", "account_mob"):
            for dimension in DIMENSIONS:
                rows = self.subgroup.loc[
                    (self.subgroup["target"] == target)
                    & (self.subgroup["dimension"] == dimension.key)
                ]
                self.assertEqual(int(rows["n"].sum()), 1051, f"{target}/{dimension.key}")
                self.assertEqual(int(rows["positive_count"].sum()), 537 if target == "account_fin" else 611)

    def test_rates_are_bounded_and_counts_are_auditable(self) -> None:
        for rate_column in ("weighted_rate", "unweighted_rate"):
            self.assertTrue(self.subgroup[rate_column].between(0, 1).all())
        self.assertTrue((self.subgroup["positive_count"] <= self.subgroup["n"]).all())
        self.assertTrue((self.subgroup["weight_sum"] > 0).all())

    def test_phase_contains_no_inferential_or_model_outputs(self) -> None:
        estimation = self.summary["estimation"]
        self.assertFalse(estimation["hypothesis_tests_performed"])
        self.assertFalse(estimation["causal_claims_made"])
        self.assertFalse(any(column in self.subgroup.columns for column in ("p_value", "chi_square", "effect_size")))
        self.assertNotIn("model_artifact", self.summary)
        self.assertNotIn("model_metrics", self.summary)

    def test_all_charts_exist_and_are_renderable(self) -> None:
        manifest = pd.read_csv(OUTPUT_DIR / "chart_manifest.csv")
        self.assertEqual(len(manifest), 8)
        self.assertEqual(set(manifest["format"]), {"png", "svg"})
        for filename in manifest["figure"]:
            path = OUTPUT_DIR / "figures" / filename
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 5_000)
            if path.suffix == ".png":
                with Image.open(path) as image:
                    self.assertGreaterEqual(image.width, 1_000)
                    self.assertGreaterEqual(image.height, 600)

    def test_report_and_machine_readable_summary_exist(self) -> None:
        self.assertTrue((OUTPUT_DIR / "eda_report.md").is_file())
        self.assertTrue((OUTPUT_DIR / "eda_summary.json").is_file())
        self.assertTrue((OUTPUT_DIR / "deliverable_checklist.md").is_file())
        summary = json.loads((OUTPUT_DIR / "eda_summary.json").read_text(encoding="utf-8"))
        self.assertTrue(summary["deliverable_validation"]["passed"])
        self.assertIn("urbanicity is constant", " ".join(summary["limitations"]))


if __name__ == "__main__":
    unittest.main()
