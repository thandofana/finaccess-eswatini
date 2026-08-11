from __future__ import annotations

import json
import unittest

from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.phase11_frontend_validation import validate_frontend


class Phase11FrontendTests(unittest.TestCase):
    def test_all_frontend_contract_checks_pass(self) -> None:
        checks = validate_frontend()
        self.assertTrue(checks)
        self.assertTrue(all(check.passed for check in checks), [check for check in checks if not check.passed])

    def test_three_named_concepts_have_distinct_routes(self) -> None:
        summary = json.loads((PROJECT_ROOT / "reports/phase_11/phase11_summary.json").read_text(encoding="utf-8"))
        self.assertEqual([item["name"] for item in summary["concepts"]], ["The Ledger", "Open Field", "Signal"])
        self.assertEqual(len({item["route"] for item in summary["concepts"]}), 3)

    def test_each_concept_has_the_complete_product(self) -> None:
        summary = json.loads((PROJECT_ROOT / "reports/phase_11/phase11_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["product_areas_per_concept"], 5)
        self.assertEqual(summary["assessment_fields"], 17)

    def test_phase_boundary_is_preserved(self) -> None:
        summary = json.loads((PROJECT_ROOT / "reports/phase_11/phase11_summary.json").read_text(encoding="utf-8"))
        self.assertFalse(summary["deployment_started"])
        self.assertTrue(summary["concept_selected"])
        self.assertEqual(summary["selected_concept"], "Signal")

    def test_example_proves_both_real_models_and_explanations(self) -> None:
        example = json.loads((PROJECT_ROOT / "reports/phase_11/phase11_summary.json").read_text(encoding="utf-8"))["end_to_end_example"]
        self.assertAlmostEqual(example["financial_inclusion_probability_percent"], 26.9)
        self.assertAlmostEqual(example["mobile_money_probability_percent"], 36.8)
        self.assertEqual(example["model_derived_factors_per_outcome"], 5)


if __name__ == "__main__":
    unittest.main()
