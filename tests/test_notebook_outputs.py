from __future__ import annotations

import base64
import io
import unittest

import nbformat
from PIL import Image

from finaccess_eswatini.data_audit import PROJECT_ROOT


NOTEBOOKS = tuple(sorted((PROJECT_ROOT / "notebooks").glob("[01][0-9]_*.ipynb")))


class NotebookOutputTests(unittest.TestCase):
    def test_all_completed_notebooks_have_saved_outputs(self) -> None:
        self.assertEqual(len(NOTEBOOKS), 13)
        for path in NOTEBOOKS:
            notebook = nbformat.read(path, as_version=4)
            code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
            self.assertTrue(code_cells, path.name)
            self.assertTrue(
                all(cell.execution_count is not None for cell in code_cells),
                f"{path.name} has unexecuted code cells",
            )
            self.assertGreater(
                sum(len(cell.outputs) for cell in code_cells),
                0,
                f"{path.name} has no saved outputs",
            )
            error_outputs = [
                output
                for cell in code_cells
                for output in cell.outputs
                if output.output_type == "error"
            ]
            self.assertEqual(error_outputs, [], f"{path.name} contains saved execution errors")

    def test_phase4_contains_embedded_graphs(self) -> None:
        path = PROJECT_ROOT / "notebooks" / "04_exploratory_analysis.ipynb"
        notebook = nbformat.read(path, as_version=4)
        png_outputs = [
            output
            for cell in notebook.cells
            if cell.cell_type == "code"
            for output in cell.outputs
            if "image/png" in output.get("data", {})
        ]
        self.assertGreaterEqual(len(png_outputs), 3)
        for output in png_outputs:
            encoded = output["data"]["image/png"]
            self.assertGreater(len(encoded), 10_000)
            with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreaterEqual(image.width, 900)
                self.assertGreaterEqual(image.height, 400)

    def test_phase6_contains_embedded_feature_graph(self) -> None:
        path = PROJECT_ROOT / "notebooks" / "06_feature_engineering.ipynb"
        notebook = nbformat.read(path, as_version=4)
        png_outputs = [
            output
            for cell in notebook.cells
            if cell.cell_type == "code"
            for output in cell.outputs
            if "image/png" in output.get("data", {})
        ]
        self.assertGreaterEqual(len(png_outputs), 1)
        for output in png_outputs:
            encoded = output["data"]["image/png"]
            self.assertGreater(len(encoded), 10_000)
            with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreaterEqual(image.width, 900)
                self.assertGreaterEqual(image.height, 600)

    def test_phase7_contains_embedded_model_graphs(self) -> None:
        path = PROJECT_ROOT / "notebooks" / "07_financial_inclusion_model.ipynb"
        notebook = nbformat.read(path, as_version=4)
        png_outputs = [
            output
            for cell in notebook.cells
            if cell.cell_type == "code"
            for output in cell.outputs
            if "image/png" in output.get("data", {})
        ]
        self.assertGreaterEqual(len(png_outputs), 2)
        for output in png_outputs:
            encoded = output["data"]["image/png"]
            self.assertGreater(len(encoded), 10_000)
            with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreaterEqual(image.width, 900)
                self.assertGreaterEqual(image.height, 400)

    def test_phase8_contains_embedded_model_graphs(self) -> None:
        path = PROJECT_ROOT / "notebooks" / "08_mobile_money_model.ipynb"
        notebook = nbformat.read(path, as_version=4)
        png_outputs = [
            output
            for cell in notebook.cells
            if cell.cell_type == "code"
            for output in cell.outputs
            if "image/png" in output.get("data", {})
        ]
        self.assertGreaterEqual(len(png_outputs), 2)
        for output in png_outputs:
            encoded = output["data"]["image/png"]
            self.assertGreater(len(encoded), 10_000)
            with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreaterEqual(image.width, 900)
                self.assertGreaterEqual(image.height, 400)

    def test_phase9_contains_embedded_explanation_graphs(self) -> None:
        path = PROJECT_ROOT / "notebooks" / "09_model_explainability.ipynb"
        notebook = nbformat.read(path, as_version=4)
        png_outputs = [
            output
            for cell in notebook.cells
            if cell.cell_type == "code"
            for output in cell.outputs
            if "image/png" in output.get("data", {})
        ]
        self.assertGreaterEqual(len(png_outputs), 2)
        for output in png_outputs:
            encoded = output["data"]["image/png"]
            self.assertGreater(len(encoded), 10_000)
            with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreaterEqual(image.width, 900)
                self.assertGreaterEqual(image.height, 400)

    def test_phase11_contains_embedded_social_preview(self) -> None:
        path = PROJECT_ROOT / "notebooks" / "11_web_application.ipynb"
        notebook = nbformat.read(path, as_version=4)
        png_outputs = [
            output
            for cell in notebook.cells
            if cell.cell_type == "code"
            for output in cell.outputs
            if "image/png" in output.get("data", {})
        ]
        self.assertGreaterEqual(len(png_outputs), 1)
        encoded = png_outputs[0]["data"]["image/png"]
        with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
            self.assertEqual(image.format, "PNG")
            self.assertGreaterEqual(image.width, 1200)
            self.assertGreaterEqual(image.height, 630)

    def test_saved_notebooks_use_project_kernel_metadata(self) -> None:
        for path in NOTEBOOKS:
            notebook = nbformat.read(path, as_version=4)
            self.assertEqual(notebook.metadata.kernelspec.name, "finaccess-eswatini")
            self.assertEqual(notebook.metadata.kernelspec.display_name, "FinAccess Eswatini")


if __name__ == "__main__":
    unittest.main()
