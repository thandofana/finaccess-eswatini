from __future__ import annotations

import json
import unittest

from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.deliverables import PHASE_DELIVERABLES, validate_completed_phase_files


class ProjectStructureTests(unittest.TestCase):
    def test_completed_phase_deliverables_exist(self) -> None:
        self.assertEqual(validate_completed_phase_files(PROJECT_ROOT), {})

    def test_notebooks_are_valid_and_phase_aligned(self) -> None:
        for phase in sorted(PHASE_DELIVERABLES):
            notebook_path = PROJECT_ROOT / PHASE_DELIVERABLES[phase][0]
            notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
            self.assertEqual(notebook["nbformat"], 4)
            self.assertGreaterEqual(len(notebook["cells"]), 3)
            source = "".join(
                line
                for cell in notebook["cells"]
                for line in cell.get("source", [])
            )
            self.assertIn(f"Phase {phase}", source)


if __name__ == "__main__":
    unittest.main()
