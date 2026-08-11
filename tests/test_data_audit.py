from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from finaccess_eswatini.data_audit import DEFAULT_INPUT, build_audit, run


class DataAuditUnitTests(unittest.TestCase):
    def test_synthetic_audit_detects_missingness_duplicates_and_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "sample.csv"
            with source.open("w", encoding="utf-8", newline="") as destination:
                writer = csv.writer(destination)
                writer.writerow(["id", "account_fin", "account_mob", "empty"])
                writer.writerows(
                    [
                        ["a", "1", "0", ""],
                        ["b", "0", "1", ""],
                        ["b", "0", "1", ""],
                    ]
                )

            summary, profiles, _ = build_audit(source)

            self.assertEqual(summary["shape"], {"rows": 3, "columns": 4})
            self.assertEqual(summary["duplicates"]["duplicate_rows_excluding_first"], 1)
            self.assertTrue(summary["targets"]["account_fin"]["valid_binary_0_1"])
            self.assertEqual(summary["missingness"]["all_missing_columns"], ["empty"])
            self.assertEqual(len(profiles), 4)

    def test_report_files_are_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory) / "report"
            summary = run(DEFAULT_INPUT, output_directory)
            self.assertEqual(summary["shape"], {"rows": 1051, "columns": 199})
            for filename in (
                "audit_summary.json",
                "column_profile.csv",
                "value_set_summary.csv",
                "special_code_inventory.csv",
                "data_quality_report.md",
            ):
                self.assertTrue((output_directory / filename).is_file())


class RawDatasetContractTests(unittest.TestCase):
    def test_expected_dataset_contract(self) -> None:
        summary, _, _ = build_audit(DEFAULT_INPUT)
        self.assertEqual(summary["shape"], {"rows": 1051, "columns": 199})
        self.assertEqual(
            summary["source"]["sha256"],
            "4968eaa568df1ddf8d5fadea39f4797d1bdecc2c3f941546936a200ce4bc210c",
        )
        self.assertTrue(summary["targets"]["account_fin"]["valid_binary_0_1"])
        self.assertTrue(summary["targets"]["account_mob"]["valid_binary_0_1"])


if __name__ == "__main__":
    unittest.main()
