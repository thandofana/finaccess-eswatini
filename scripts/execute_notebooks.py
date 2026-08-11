"""Execute completed-phase notebooks and persist their visible outputs safely."""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Sequence

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import nbformat
from nbclient import NotebookClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOKS = (
    PROJECT_ROOT / "notebooks" / "01_data_understanding.ipynb",
    PROJECT_ROOT / "notebooks" / "02_data_dictionary_feature_eligibility.ipynb",
    PROJECT_ROOT / "notebooks" / "03_data_cleaning_preprocessing.ipynb",
    PROJECT_ROOT / "notebooks" / "04_exploratory_analysis.ipynb",
    PROJECT_ROOT / "notebooks" / "05_statistical_analysis.ipynb",
    PROJECT_ROOT / "notebooks" / "06_feature_engineering.ipynb",
    PROJECT_ROOT / "notebooks" / "07_financial_inclusion_model.ipynb",
    PROJECT_ROOT / "notebooks" / "08_mobile_money_model.ipynb",
    PROJECT_ROOT / "notebooks" / "09_model_explainability.ipynb",
    PROJECT_ROOT / "notebooks" / "10_prediction_api.ipynb",
    PROJECT_ROOT / "notebooks" / "11_web_application.ipynb",
    PROJECT_ROOT / "notebooks" / "12_deployment.ipynb",
    PROJECT_ROOT / "notebooks" / "13_portfolio_polish.ipynb",
)
KERNEL_NAME = "finaccess-eswatini"


def execute_notebook(source: Path, destination: Path, timeout: int) -> dict[str, int]:
    notebook = nbformat.read(source, as_version=4)
    notebook.metadata["kernelspec"] = {
        "display_name": "FinAccess Eswatini",
        "language": "python",
        "name": KERNEL_NAME,
    }
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    for cell in code_cells:
        cell.execution_count = None
        cell.outputs = []
        cell.metadata.pop("execution", None)

    client = NotebookClient(
        notebook,
        timeout=timeout,
        kernel_name=KERNEL_NAME,
        allow_errors=False,
        record_timing=False,
        resources={"metadata": {"path": str(PROJECT_ROOT)}},
    )
    client.execute()

    output_count = sum(len(cell.get("outputs", [])) for cell in code_cells)
    image_count = sum(
        1
        for cell in code_cells
        for output in cell.get("outputs", [])
        if "image/png" in output.get("data", {})
    )
    if any(cell.execution_count is None for cell in code_cells):
        raise RuntimeError(f"One or more code cells did not execute in {source.name}.")
    if output_count == 0:
        raise RuntimeError(f"No visible output was produced by {source.name}.")

    nbformat.write(notebook, destination)
    return {
        "code_cells": len(code_cells),
        "outputs": output_count,
        "embedded_png_outputs": image_count,
    }


def run(notebooks: Sequence[Path] = DEFAULT_NOTEBOOKS, timeout: int = 600) -> list[dict[str, object]]:
    missing = [str(path) for path in notebooks if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Notebook files not found: {missing}")

    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="finaccess-notebooks-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        completed: list[tuple[Path, Path]] = []
        for source in notebooks:
            destination = temporary_root / source.name
            metrics = execute_notebook(source, destination, timeout)
            completed.append((source, destination))
            results.append({"notebook": source.name, **metrics})

        # Replace originals only after all notebooks have executed successfully.
        for source, destination in completed:
            shutil.copyfile(destination, source)
    return results


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=600, help="Maximum seconds per notebook cell.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    for result in run(timeout=args.timeout):
        print(
            f"{result['notebook']}: {result['code_cells']} code cells, "
            f"{result['outputs']} outputs, {result['embedded_png_outputs']} embedded PNG outputs"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
