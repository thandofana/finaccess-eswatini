"""Generate and validate the Phase 10 API contract artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import pandas as pd
from fastapi.testclient import TestClient

from api.app.main import app
from api.app.schemas import AssessmentRequest
from api.app.service import PredictionService
from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.deliverables import render_delivery_checklist, validate_completed_phase_files


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_10"
EXAMPLE_REQUEST_PATH = PROJECT_ROOT / "api" / "examples" / "assessment_request.json"
EXAMPLE_RESPONSE_PATH = PROJECT_ROOT / "api" / "examples" / "assessment_response.json"
FIXED_ASSESSMENT_ID = "phase10-validated-example"


def _report(summary: dict[str, object], cases: pd.DataFrame) -> str:
    results = summary["example_results"]
    return "\n".join(
        [
            "# Phase 10 Prediction API Report",
            "",
            "The API validates one 18-field profile and returns separately generated financial-inclusion and mobile-money results with five model-derived SHAP factors each.",
            "",
            "## Endpoints",
            "",
            "- `GET /health` verifies both pipeline and explainer artifacts.",
            "- `POST /api/v1/assessment` runs the combined assessment.",
            "- `/docs`, `/redoc`, and `/openapi.json` expose the documented contract.",
            "",
            "## Validated example",
            "",
            f"- Financial inclusion: {results['financial_inclusion']['answer']} ({results['financial_inclusion']['probability_percent']:.1f}%)",
            f"- Mobile money adoption: {results['mobile_money_adoption']['answer']} ({results['mobile_money_adoption']['probability_percent']:.1f}%)",
            "- The natural-language factors come directly from the persisted SHAP explainers.",
            "",
            "## Error and integrity behaviour",
            "",
            f"- {int((cases['passed']).sum())}/{len(cases)} contract scenarios passed.",
            "- Invalid categories, missing/extra fields, and contradictory routing receive structured `422` responses.",
            "- Inference failures return a sanitized `500`; artifact integrity failures return `503`.",
            "- Submitted profiles are not persisted by the API.",
            "",
            "## Boundaries",
            "",
            "- The 0.50 classification threshold remains provisional.",
            "- Predictions and SHAP factors are not causal, eligibility, or creditworthiness determinations.",
            "- CORS and deployment configuration remain reserved for their approved later phases.",
            "",
        ]
    )


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = json.loads(EXAMPLE_REQUEST_PATH.read_text(encoding="utf-8"))
    validated_request = AssessmentRequest.model_validate(payload)
    service = PredictionService()
    example_response = service.assess(validated_request, assessment_id=FIXED_ASSESSMENT_ID)
    EXAMPLE_RESPONSE_PATH.write_text(
        json.dumps(example_response.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    cases: list[dict[str, object]] = []
    with TestClient(app) as client:
        health = client.get("/health")
        cases.append({"case": "health_ready", "expected_status": 200, "actual_status": health.status_code})
        valid = client.post("/api/v1/assessment", json=payload)
        cases.append({"case": "valid_assessment", "expected_status": 200, "actual_status": valid.status_code})

        invalid_category = dict(payload, female="Unknown")
        response = client.post("/api/v1/assessment", json=invalid_category)
        cases.append({"case": "invalid_category", "expected_status": 422, "actual_status": response.status_code})

        inconsistent = dict(payload, internet_engagement_level="Daily internet use")
        response = client.post("/api/v1/assessment", json=inconsistent)
        cases.append({"case": "inconsistent_internet_routing", "expected_status": 422, "actual_status": response.status_code})

        missing = dict(payload)
        missing.pop("educ")
        response = client.post("/api/v1/assessment", json=missing)
        cases.append({"case": "missing_field", "expected_status": 422, "actual_status": response.status_code})

        extra = dict(payload, target="account_fin")
        response = client.post("/api/v1/assessment", json=extra)
        cases.append({"case": "extra_field", "expected_status": 422, "actual_status": response.status_code})

        no_phone_conflict = dict(payload, phone_access_tier="No personal mobile phone")
        response = client.post("/api/v1/assessment", json=no_phone_conflict)
        cases.append({"case": "inconsistent_phone_routing", "expected_status": 422, "actual_status": response.status_code})

        openapi = client.get("/openapi.json")
        cases.append({"case": "openapi_contract", "expected_status": 200, "actual_status": openapi.status_code})
        openapi_document = openapi.json()

    cases_frame = pd.DataFrame(cases)
    cases_frame["passed"] = cases_frame["expected_status"] == cases_frame["actual_status"]
    cases_frame.to_csv(output_dir / "validation_cases.csv", index=False)
    if not cases_frame["passed"].all():
        raise RuntimeError("One or more API contract scenarios failed.")

    endpoint_contract = {
        "openapi": openapi_document["openapi"],
        "title": openapi_document["info"]["title"],
        "version": openapi_document["info"]["version"],
        "paths": {
            path: sorted(method.upper() for method in operations)
            for path, operations in openapi_document["paths"].items()
        },
        "assessment_request_fields": list(AssessmentRequest.model_fields),
        "assessment_request_field_count": len(AssessmentRequest.model_fields),
        "extra_fields_forbidden": AssessmentRequest.model_config["extra"] == "forbid",
        "response_schema": "AssessmentResponse",
        "validation_error_schema": "ErrorResponse",
    }
    (output_dir / "endpoint_contract.json").write_text(
        json.dumps(endpoint_contract, indent=2), encoding="utf-8"
    )

    response_data = example_response.model_dump(mode="json")
    summary: dict[str, object] = {
        "phase": 10,
        "status": "PASS_WITH_NOTES",
        "scope": "Combined FastAPI prediction and explanation service",
        "service_version": "1.0.0",
        "request_fields": len(AssessmentRequest.model_fields),
        "endpoints": ["GET /", "GET /health", "POST /api/v1/assessment", "GET /docs", "GET /openapi.json"],
        "models_loaded": service.health_models,
        "example_results": {
            "financial_inclusion": {
                "answer": response_data["financial_inclusion"]["answer"],
                "probability": response_data["financial_inclusion"]["probability"],
                "probability_percent": response_data["financial_inclusion"]["probability_percent"],
                "factors": len(response_data["financial_inclusion"]["main_factors"]),
            },
            "mobile_money_adoption": {
                "answer": response_data["mobile_money_adoption"]["answer"],
                "probability": response_data["mobile_money_adoption"]["probability"],
                "probability_percent": response_data["mobile_money_adoption"]["probability_percent"],
                "factors": len(response_data["mobile_money_adoption"]["main_factors"]),
            },
        },
        "validation_cases": int(len(cases_frame)),
        "validation_cases_passed": int(cases_frame["passed"].sum()),
        "profiles_persisted": False,
        "cors_configured": False,
        "deployment_started": False,
        "frontend_started": False,
        "limitations": [
            "0.50 thresholds remain provisional",
            "the service is a proof of concept rather than a decision authority",
            "SHAP factors explain model behaviour rather than causation",
            "CORS and hosting remain for later approved phases",
        ],
    }
    (output_dir / "phase10_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "api_report.md").write_text(_report(summary, cases_frame), encoding="utf-8")
    (output_dir / "deliverable_checklist.md").write_text(
        render_delivery_checklist(PROJECT_ROOT, through_phase=10), encoding="utf-8"
    )
    missing = validate_completed_phase_files(PROJECT_ROOT, through_phase=10)
    if missing:
        raise RuntimeError(f"Completed-phase deliverables are missing: {missing}")
    summary["deliverable_validation"] = {
        "passed": True,
        "phases_checked": list(range(1, 11)),
        "missing_files": {},
        "checklist": "reports/phase_10/deliverable_checklist.md",
    }
    (output_dir / "phase10_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    print(json.dumps(run(args.output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
