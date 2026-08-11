from __future__ import annotations

import unittest

from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.phase13_portfolio import (
    REPORT_DIR,
    SCREENSHOTS,
    _notebook_inventory,
    _repository_inventory,
    _screenshot_inventory,
)


class Phase13PortfolioTests(unittest.TestCase):
    def test_live_screenshots_are_complete_and_nonblank(self) -> None:
        inventory = _screenshot_inventory()
        self.assertEqual([item["file"] for item in inventory], list(SCREENSHOTS))
        for item in inventory:
            self.assertTrue(item["exists"], item["file"])
            self.assertEqual(item["format"], "PNG")
            self.assertGreaterEqual(item["width"], 900)
            self.assertGreaterEqual(item["height"], 450)
            self.assertGreaterEqual(item["luminance_stddev"], 10)

    def test_all_thirteen_notebooks_have_saved_successful_outputs(self) -> None:
        inventory = _notebook_inventory()
        self.assertEqual(len(inventory), 13)
        for item in inventory:
            self.assertGreater(item["code_cells"], 0)
            self.assertEqual(item["executed_code_cells"], item["code_cells"])
            self.assertGreater(item["saved_outputs"], 0)
            self.assertEqual(item["saved_errors"], 0)

    def test_recruiter_readme_contains_final_contract(self) -> None:
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        for text in (
            "https://finaccess-eswatini.vercel.app",
            "## 1. Project Overview",
            "## 2. Project Objectives",
            "## 3. Dataset",
            "## 4. Project Workflow",
            "## 5. Exploratory Data Analysis",
            "## 6. Feature Engineering",
            "## 7. Models",
            "## 8. Results",
            "## 9. Final Solution",
            "## 10. Tech Stack",
            "## 11. Repository Structure",
            "Responsible Use and Limitations",
            "01_overview.png",
            "03_assessment_results.png",
            "Thando F. Dlamini",
        ):
            self.assertIn(text, readme)

    def test_both_repositories_exclude_secrets_data_and_temp_outputs(self) -> None:
        for repository in (PROJECT_ROOT, PROJECT_ROOT / "frontend"):
            inventory = _repository_inventory(repository)
            self.assertEqual(inventory["secret_files"], [])
            self.assertEqual(inventory["respondent_data_files"], [])
            self.assertEqual(inventory["temporary_files"], [])

    def test_phase13_reports_and_professional_document_exist(self) -> None:
        for name in (
            "reproducibility_validation.json",
            "repository_inventory.json",
            "phase13_summary.json",
            "final_portfolio_report.md",
            "deliverable_checklist.md",
            "regression_validation.json",
        ):
            self.assertTrue((REPORT_DIR / name).is_file(), name)
        self.assertTrue(
            (
                PROJECT_ROOT
                / "reports"
                / "project_documentation"
                / "FinAccess_Eswatini_Phases_1_to_13_Report.docx"
            ).is_file()
        )


if __name__ == "__main__":
    unittest.main()
