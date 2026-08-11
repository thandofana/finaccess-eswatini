"""Build the Phase 12 portfolio notebook; execution is handled separately."""

from __future__ import annotations

from pathlib import Path

import nbformat


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESTINATION = PROJECT_ROOT / "notebooks" / "12_deployment.ipynb"


def build() -> Path:
    notebook = nbformat.v4.new_notebook()
    notebook.metadata.update(
        {
            "kernelspec": {
                "display_name": "FinAccess Eswatini",
                "language": "python",
                "name": "finaccess-eswatini",
            },
            "language_info": {"name": "python", "version": "3"},
        }
    )
    notebook.cells = [
        nbformat.v4.new_markdown_cell(
            """# Phase 12 — Deployment

This notebook records reproducible evidence for the public FinAccess Eswatini deployment. It validates the selected Signal frontend, the same-origin FastAPI service, both model/explainer pairs, input validation, prediction equivalence, and deployment-repository safety.

It does not begin Phase 13 portfolio polish."""
        ),
        nbformat.v4.new_code_cell(
            """from finaccess_eswatini.phase12_deployment import run

deployment = run()
print(f\"Phase status: {deployment['status'].replace('_', ' ')}\")
print(f\"Validated at: {deployment['generated_at_utc']}\")
print(f\"Frontend: {deployment['endpoints']['frontend']}\")
print(f\"API: {deployment['endpoints']['api']}\")"""
        ),
        nbformat.v4.new_markdown_cell("## Public validation checks"),
        nbformat.v4.new_code_cell(
            """import pandas as pd

checks = pd.DataFrame(deployment['checks'])
checks"""
        ),
        nbformat.v4.new_markdown_cell("## End-to-end smoke-test output"),
        nbformat.v4.new_code_cell(
            """for outcome, result in deployment['sample_prediction'].items():
    label = outcome.replace('_', ' ').title()
    print(f\"{label}: {result['answer']}\")
    print(f\"  Estimated likelihood: {result['probability_percent']}%\")
    print(f\"  Model-generated factors: {result['factor_count']}\")"""
        ),
        nbformat.v4.new_markdown_cell("## Point-in-time response observations"),
        nbformat.v4.new_code_cell(
            """pd.Series(deployment['latency_seconds'], name='seconds').to_frame()"""
        ),
        nbformat.v4.new_markdown_cell(
            """## Deployment decisions and limitations

- One Vercel Hobby project deploys the standard Next.js frontend and FastAPI backend as separate Vercel Services.
- The frontend posts directly to `/api/v1/assessment` on the same public domain, so no cross-host proxy, external API URL, or browser CORS configuration is required.
- The FastAPI service verifies the SHA-256 digest of each pipeline and model-matched SHAP explainer before reporting healthy.
- Raw and processed respondent microdata are excluded from the deployment repository.
- Vercel Services and its Python runtime are beta features; the optimized Python bundle size and serverless cold-start behaviour remain deployment risks to monitor.
- Automatic Git deployments require granting the Vercel GitHub App access to the private web repository; this validated release used the authenticated Vercel CLI.
- The system remains a portfolio proof of concept, not a production financial decision engine."""
        ),
    ]
    nbformat.write(notebook, DESTINATION)
    return DESTINATION


if __name__ == "__main__":
    print(build())
