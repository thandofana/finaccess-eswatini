from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from finaccess_eswatini.data_audit import DEFAULT_INPUT, PROJECT_ROOT


OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_2"


def read_rows(filename: str) -> list[dict[str, str]]:
    with (OUTPUT_DIR / filename).open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


class Phase2ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dictionary = read_rows("data_dictionary.csv")
        cls.by_name = {row["variable"]: row for row in cls.dictionary}

    def test_dictionary_matches_all_raw_columns_in_order(self) -> None:
        with DEFAULT_INPUT.open("r", encoding="utf-8-sig", newline="") as source:
            raw_headers = next(csv.reader(source))
        self.assertEqual(len(self.dictionary), 199)
        self.assertEqual([row["variable"] for row in self.dictionary], raw_headers)
        self.assertEqual(len(self.by_name), 199)

    def test_every_variable_has_complete_review(self) -> None:
        required = (
            "label",
            "primary_category",
            "tags",
            "model1_status",
            "model1_leakage_risk",
            "model1_reason",
            "model2_status",
            "model2_leakage_risk",
            "model2_reason",
            "source_url",
        )
        for row in self.dictionary:
            for field in required:
                self.assertTrue(row[field], f"{row['variable']} missing {field}")

    def test_targets_and_parallel_outcomes_are_protected(self) -> None:
        self.assertEqual(self.by_name["account_fin"]["model1_status"], "TARGET")
        self.assertEqual(self.by_name["account_mob"]["model2_status"], "TARGET")
        self.assertEqual(
            self.by_name["account_mob"]["model1_status"], "EXCLUDE_PARALLEL_OUTCOME"
        )
        self.assertEqual(
            self.by_name["account_fin"]["model2_status"], "EXCLUDE_PARALLEL_OUTCOME"
        )
        self.assertEqual(self.by_name["account"]["model1_leakage_risk"], "DIRECT")
        self.assertEqual(self.by_name["account"]["model2_leakage_risk"], "DIRECT")

    def test_candidates_are_covered_and_model_specific(self) -> None:
        model1 = {
            row["variable"]
            for row in self.dictionary
            if row["model1_status"].startswith("CANDIDATE")
        }
        model2 = {
            row["variable"]
            for row in self.dictionary
            if row["model2_status"].startswith("CANDIDATE")
        }
        self.assertEqual(model1, MODEL1_EXPECTED)
        self.assertEqual(model2, MODEL2_EXPECTED)
        self.assertNotEqual(model1, model2)
        for row in self.dictionary:
            if row["model1_status"].startswith("CANDIDATE") or row["model2_status"].startswith(
                "CANDIDATE"
            ):
                self.assertLess(float(row["missing_pct"]), 50)
                risk_field = (
                    "model1_leakage_risk"
                    if row["model1_status"].startswith("CANDIDATE")
                    else "model2_leakage_risk"
                )
                self.assertNotIn(row[risk_field], {"HIGH", "DIRECT"})

    def test_obvious_identifiers_metadata_and_empty_fields_are_excluded(self) -> None:
        for name in ("year", "economy", "economycode", "regionwb", "pop_adult", "wgt"):
            self.assertEqual(self.by_name[name]["model1_status"], "EXCLUDE_METADATA")
            self.assertEqual(self.by_name[name]["model2_status"], "EXCLUDE_METADATA")
        self.assertEqual(self.by_name["wpid_random"]["model1_status"], "EXCLUDE_IDENTIFIER")
        self.assertEqual(self.by_name["urbanicity"]["model2_status"], "EXCLUDE_NO_VARIANCE")
        self.assertEqual(self.by_name["fin50"]["model1_status"], "EXCLUDE_ALL_MISSING")

    def test_summary_reconciles_target_counts(self) -> None:
        summary = json.loads((OUTPUT_DIR / "phase2_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["variable_count"], 199)
        self.assertEqual(summary["target_distributions"]["account_fin"], {"0": 514, "1": 537})
        self.assertEqual(summary["target_distributions"]["account_mob"], {"0": 440, "1": 611})

    def test_codebook_coverage_and_internet_crosswalk(self) -> None:
        without_codebook_page = [row["variable"] for row in self.dictionary if not row["codebook_pages"]]
        self.assertEqual(without_codebook_page, ["year"])
        self.assertEqual(self.by_name["internet_use"]["codebook_variable"], "internet")
        self.assertTrue(all(row["definition"] for row in self.dictionary))


MODEL1_EXPECTED = {
    "female",
    "age",
    "educ",
    "inc_q",
    "emp_in",
    "internet_use",
    "con1",
    "fin46",
    "fin24c",
    "con9",
    "con11",
    "con12",
    "con14",
    "con16",
    "con18",
    "con20",
}

MODEL2_EXPECTED = MODEL1_EXPECTED | {
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


if __name__ == "__main__":
    unittest.main()
