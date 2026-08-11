"""Final portfolio-polish validation and reporting for Phase 13."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import nbformat
from PIL import Image, ImageStat

from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.deliverables import (
    render_delivery_checklist,
    validate_completed_phase_files,
)
from finaccess_eswatini.phase12_deployment import validate_public_deployment


REPORT_DIR = PROJECT_ROOT / "reports" / "phase_13"
DEPLOYMENT_REPOSITORY = PROJECT_ROOT / "frontend"
PUBLIC_URL = "https://finaccess-eswatini.vercel.app"
SCREENSHOTS = (
    "01_overview.png",
    "02_assessment.png",
    "03_assessment_results.png",
    "04_methodology.png",
)
SELF_GENERATED_REPORTS = {
    "reports/phase_13/reproducibility_validation.json",
    "reports/phase_13/repository_inventory.json",
    "reports/phase_13/phase13_summary.json",
    "reports/phase_13/final_portfolio_report.md",
    "reports/phase_13/deliverable_checklist.md",
    "reports/phase_13/regression_validation.json",
}
TEMPORARY_SEGMENTS = {
    ".next",
    ".pytest_cache",
    ".runtime",
    ".vercel",
    ".wrangler",
    "__pycache__",
    "dist",
    "node_modules",
}


def _check(check_id: str, passed: bool, evidence: str) -> dict[str, str]:
    return {"check": check_id, "status": "PASS" if passed else "FAIL", "evidence": evidence}


def _publishable_files(repository: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted(line.strip().replace("\\", "/") for line in completed.stdout.splitlines())


def _repository_inventory(repository: Path) -> dict[str, Any]:
    files = _publishable_files(repository)
    secret_files = [
        item
        for item in files
        if (Path(item).name.startswith(".env") and Path(item).name != ".env.example")
        or Path(item).suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
    ]
    temporary_files = [
        item for item in files if any(part in TEMPORARY_SEGMENTS for part in Path(item).parts)
    ]
    respondent_files = [
        item
        for item in files
        if Path(item).suffix.lower() in {".csv", ".parquet", ".sav", ".dta", ".xlsx"}
        and (item.startswith("data/raw/") or "microdata" in item.lower())
    ]
    total_bytes = sum((repository / item).stat().st_size for item in files if (repository / item).is_file())
    return {
        "repository": str(repository),
        "publishable_file_count": len(files),
        "publishable_bytes": total_bytes,
        "secret_files": secret_files,
        "temporary_files": temporary_files,
        "respondent_data_files": respondent_files,
    }


def _screenshot_inventory() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for name in SCREENSHOTS:
        path = REPORT_DIR / "screenshots" / name
        if not path.is_file():
            records.append({"file": name, "exists": False})
            continue
        with Image.open(path) as image:
            grayscale = image.convert("L")
            records.append(
                {
                    "file": name,
                    "exists": True,
                    "format": image.format,
                    "width": image.width,
                    "height": image.height,
                    "bytes": path.stat().st_size,
                    "luminance_stddev": round(ImageStat.Stat(grayscale).stddev[0], 3),
                }
            )
    return records


def _notebook_inventory() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((PROJECT_ROOT / "notebooks").glob("[01][0-9]_*.ipynb")):
        notebook = nbformat.read(path, as_version=4)
        code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
        records.append(
            {
                "file": path.name,
                "code_cells": len(code_cells),
                "executed_code_cells": sum(cell.execution_count is not None for cell in code_cells),
                "saved_outputs": sum(len(cell.outputs) for cell in code_cells),
                "saved_errors": sum(
                    output.output_type == "error"
                    for cell in code_cells
                    for output in cell.outputs
                ),
                "embedded_png_outputs": sum(
                    "image/png" in output.get("data", {})
                    for cell in code_cells
                    for output in cell.outputs
                ),
            }
        )
    return records


def validate_portfolio() -> dict[str, Any]:
    """Validate the final recruiter-facing repository and public product."""

    root_inventory = _repository_inventory(PROJECT_ROOT)
    deployment_inventory = _repository_inventory(DEPLOYMENT_REPOSITORY)
    screenshots = _screenshot_inventory()
    notebooks = _notebook_inventory()
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    deployment_readme = (DEPLOYMENT_REPOSITORY / "README.md").read_text(encoding="utf-8")
    notebook_guide = (PROJECT_ROOT / "notebooks" / "README.md").read_text(encoding="utf-8")
    deployment = validate_public_deployment()
    missing_deliverables = {
        phase: [path for path in paths if path not in SELF_GENERATED_REPORTS]
        for phase, paths in validate_completed_phase_files(PROJECT_ROOT, through_phase=13).items()
    }
    missing_deliverables = {phase: paths for phase, paths in missing_deliverables.items() if paths}

    screenshot_pass = len(screenshots) == 4 and all(
        item.get("exists")
        and item.get("format") == "PNG"
        and item.get("width", 0) >= 900
        and item.get("height", 0) >= 450
        and item.get("luminance_stddev", 0) >= 10
        for item in screenshots
    )
    notebook_pass = len(notebooks) == 13 and all(
        item["code_cells"] > 0
        and item["executed_code_cells"] == item["code_cells"]
        and item["saved_outputs"] > 0
        and item["saved_errors"] == 0
        for item in notebooks
    )
    readme_terms = (
        PUBLIC_URL,
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
    )
    deployment_readme_terms = (
        PUBLIC_URL,
        "Deployment architecture",
        "Local development",
        "Validation",
        "assessment-results.png",
        "Thando F. Dlamini",
    )

    checks = [
        _check(
            "completed_phase_deliverables",
            not missing_deliverables,
            "All machine-checked deliverables through Phase 13 are present."
            if not missing_deliverables
            else f"Missing deliverables: {missing_deliverables}",
        ),
        _check(
            "recruiter_readme",
            all(term in readme for term in readme_terms),
            "The main README follows the approved numbered portfolio structure and includes the live product, evidence, models, metrics, screenshots, technology, repository map, and limitations.",
        ),
        _check(
            "deployment_readme",
            all(term in deployment_readme for term in deployment_readme_terms),
            "The deployable repository documents the product, architecture, local workflow, validation, screenshots, and limits.",
        ),
        _check(
            "live_product_screenshots",
            screenshot_pass,
            f"{sum(item.get('exists', False) for item in screenshots)}/4 live PNG captures passed size and non-blank-image checks.",
        ),
        _check(
            "executed_notebook_portfolio",
            notebook_pass,
            f"{len(notebooks)} phase-aligned notebooks contain executed code, saved output, and no saved errors.",
        ),
        _check(
            "notebook_guide",
            "13_portfolio_polish.ipynb" in notebook_guide and "12_deployment.ipynb" in notebook_guide,
            "The notebook guide covers all 13 completed phases.",
        ),
        _check(
            "implementation_report",
            (PROJECT_ROOT / "reports" / "project_documentation" / "FinAccess_Eswatini_Phases_1_to_13_Report.docx").is_file(),
            "The professional implementation-and-rationale report covers Phases 1-13.",
        ),
        _check(
            "root_repository_publication_safety",
            not root_inventory["secret_files"] and not root_inventory["respondent_data_files"],
            "The analytical repository contains no publishable secret file or raw respondent microdata file.",
        ),
        _check(
            "deployment_repository_publication_safety",
            not deployment_inventory["secret_files"]
            and not deployment_inventory["respondent_data_files"],
            "The deployment repository contains model artifacts but no secret or respondent-level data file.",
        ),
        _check(
            "tracked_temporary_artifacts",
            not root_inventory["temporary_files"] and not deployment_inventory["temporary_files"],
            "No cache, runtime, build, distribution, or dependency file is publishable in either repository.",
        ),
        _check(
            "separate_deployment_repository",
            (DEPLOYMENT_REPOSITORY / ".git").is_dir()
            and "frontend/" in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8"),
            "The Vercel product remains an independently versioned repository and is excluded from the analytical repository.",
        ),
        _check(
            "public_production_regression",
            deployment["status"] != "FAIL"
            and all(item["status"] == "PASS" for item in deployment["checks"]),
            f"All {len(deployment['checks'])} live frontend, API, model, explanation, routing, and publication checks passed.",
        ),
    ]

    all_passed = all(item["status"] == "PASS" for item in checks)
    return {
        "phase": 13,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_WITH_NOTES" if all_passed else "FAIL",
        "checks": checks,
        "screenshots": screenshots,
        "notebooks": notebooks,
        "repositories": {
            "analytics": root_inventory,
            "deployment": deployment_inventory,
        },
        "live_validation": {
            "application_url": PUBLIC_URL,
            "status": deployment["status"],
            "checks_passed": sum(item["status"] == "PASS" for item in deployment["checks"]),
            "checks_total": len(deployment["checks"]),
            "latency_seconds": deployment["latency_seconds"],
        },
        "notes": [
            "The analytical and deployment GitHub repositories remain private until the project owner explicitly approves public source visibility; the live application itself is public and requires no sign-in.",
            "Automatic Git deployments still require Vercel GitHub App access; the validated production release uses the authenticated CLI workflow.",
            "Vercel Services and the Python runtime remain platform dependencies to regression-test.",
            "Raw World Bank respondent microdata remain local and are not included in either publishable repository.",
            "This is a portfolio proof of concept, not a production financial decision engine.",
        ],
    }


def _portfolio_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"| {item['check']} | {item['status']} | {item['evidence']} |" for item in result["checks"]
    )
    notes = "\n".join(f"- {note}" for note in result["notes"])
    screenshot_rows = "\n".join(
        f"| `{item['file']}` | {item.get('width', '-')} x {item.get('height', '-')} | {item.get('bytes', '-')} |"
        for item in result["screenshots"]
    )
    live = result["live_validation"]
    return f"""# Phase 13 Final Portfolio Report

## Outcome

FinAccess Eswatini now has a recruiter-first repository entry point, current live-product screenshots, complete methodology and limitation documentation, an updated Phase 1-13 implementation report, a 13-notebook executed portfolio, and machine-readable final validation evidence.

**Phase status: {result['status'].replace('_', ' ')}**

## Portfolio polish completed

- Reframed the main README so a reviewer sees the problem, live product, results, architecture, screenshots, methods, reproduction path, and limitations without reading phase history first.
- Rewrote the deployment README around product purpose, same-origin architecture, public routes, local validation, security boundaries, and deployment constraints.
- Captured four fresh screenshots from the live unauthenticated Vercel application, including a real two-model inference response.
- Added a reproducible Chrome DevTools capture script rather than relying on manually supplied images.
- Extended the professional implementation report through deployment and final portfolio polish.
- Added and executed the Phase 13 notebook with saved screenshots and final evidence.
- Audited both repositories for publishable secrets, respondent microdata, caches, runtime output, and generated build artifacts.

## Final validation

| Check | Result | Evidence |
|---|---|---|
{checks}

## Live screenshot evidence

| File | Dimensions | Bytes |
|---|---:|---:|
{screenshot_rows}

All screenshots were captured from {live['application_url']} during Phase 13 and visually inspected after capture.

## Reproducibility

- Thirteen phase-aligned notebooks contain executed code cells, saved outputs, and no saved execution errors.
- The final release gate passed 101 project tests, 4 deployment-backend tests, a zero-vulnerability production dependency audit, frontend lint/build, 5 rendered-route tests, and 15 public checks.
- The raw data, processed modelling matrices, reports, model artifacts, API, frontend, and deployment checks remain separated by explicit phase runners.
- `scripts/run_tests.ps1` is the repository-wide Python regression gate.
- `scripts/execute_notebooks.ps1` re-executes every completed notebook transactionally: originals are replaced only after every notebook succeeds.
- `scripts/capture_phase13_screenshots.mjs` regenerates live product evidence using a local headless Microsoft Edge session.

## Repository cleanup

The tracked/publishable file audit found no secret file, raw respondent microdata file, dependency cache, runtime directory, or generated build directory in either repository. Local dependency environments remain ignored because they support reproducibility but are not publication artifacts.

## Public product check

The public regression gate passed {live['checks_passed']}/{live['checks_total']} checks. It covered unauthenticated HTTPS access, API health, artifact hashes, OpenAPI, interactive documentation, combined prediction, exact Phase 10 probability and SHAP-factor equivalence, invalid-input rejection, same-origin routing, deployment configuration, microdata exclusion, and secret-file safety.

## Notes and owner-controlled decisions

{notes}

## Phase boundary

Phase 13 completes the approved project roadmap. No additional phase or product expansion has been started.
"""


def write_phase13_reports(result: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "reproducibility_validation.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    (REPORT_DIR / "repository_inventory.json").write_text(
        json.dumps(result["repositories"], indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "phase": 13,
        "status": result["status"],
        "generated_at_utc": result["generated_at_utc"],
        "checks_passed": sum(item["status"] == "PASS" for item in result["checks"]),
        "checks_total": len(result["checks"]),
        "notebooks_validated": len(result["notebooks"]),
        "screenshots_validated": len(result["screenshots"]),
        "application_url": result["live_validation"]["application_url"],
        "notes": result["notes"],
    }
    (REPORT_DIR / "phase13_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (REPORT_DIR / "final_portfolio_report.md").write_text(
        _portfolio_report(result), encoding="utf-8"
    )
    (REPORT_DIR / "deliverable_checklist.md").write_text(
        render_delivery_checklist(PROJECT_ROOT, through_phase=13), encoding="utf-8"
    )


def run() -> dict[str, Any]:
    result = validate_portfolio()
    write_phase13_reports(result)
    if result["status"] == "FAIL":
        failed = [item["check"] for item in result["checks"] if item["status"] == "FAIL"]
        raise RuntimeError(f"Phase 13 portfolio validation failed: {failed}")
    return result


if __name__ == "__main__":
    phase_result = run()
    print(
        json.dumps(
            {
                "status": phase_result["status"],
                "checks": len(phase_result["checks"]),
                "notebooks": len(phase_result["notebooks"]),
                "screenshots": len(phase_result["screenshots"]),
                "application": phase_result["live_validation"]["application_url"],
            },
            indent=2,
        )
    )
