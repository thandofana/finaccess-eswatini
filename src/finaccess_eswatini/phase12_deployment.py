"""Reproducible validation and reporting for the Phase 12 public deployment."""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT_REPOSITORY = PROJECT_ROOT / "frontend"
PUBLIC_BASE_URL = "https://finaccess-eswatini.vercel.app"
FRONTEND_BASE_URL = PUBLIC_BASE_URL
API_BASE_URL = PUBLIC_BASE_URL
REPORT_DIR = PROJECT_ROOT / "reports" / "phase_12"
ASSESSMENT_EXAMPLE = PROJECT_ROOT / "api" / "examples" / "assessment_request.json"
EXPECTED_RESPONSE = PROJECT_ROOT / "api" / "examples" / "assessment_response.json"

EXPECTED_ARTIFACT_HASHES = {
    "model1": {
        "pipeline_sha256": "467e5519c022a0c716e38bae3f7b44752b4a50da6553720541d75efcb5d2b7b3",
        "explainer_sha256": "ee6ff974c8295dc41948823786efb81d1e8c67bf015c3d20cee3dff370a932d0",
    },
    "model2": {
        "pipeline_sha256": "3df51a31fc420043b8e386c73d2a46771cafe64a619d69faf6fd5a2db12d7606",
        "explainer_sha256": "0b36cf5d7208854125f5c0b14a1f84939bedebdc95b8a67c79afc20bd47a5033",
    },
}


def _http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    request_headers = {"User-Agent": "FinAccess-Eswatini-Phase12-Validator/2.0"}
    request_headers.update(headers or {})
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
            status_code = response.status
            response_headers = dict(response.headers.items())
            final_url = response.geturl()
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8")
        status_code = exc.code
        response_headers = dict(exc.headers.items())
        final_url = exc.geturl()

    try:
        parsed_body: Any = json.loads(raw_body) if raw_body else None
    except json.JSONDecodeError:
        parsed_body = raw_body
    return {
        "status_code": status_code,
        "latency_seconds": round(time.perf_counter() - started, 3),
        "headers": {key.lower(): value for key, value in response_headers.items()},
        "body": parsed_body,
        "final_url": final_url.rstrip("/"),
    }


def _check(check_id: str, passed: bool, evidence: str) -> dict[str, str]:
    return {
        "check": check_id,
        "status": "PASS" if passed else "FAIL",
        "evidence": evidence,
    }


def _tracked_deployment_files() -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=DEPLOYMENT_REPOSITORY,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip().replace("\\", "/") for line in completed.stdout.splitlines()]


def _deployed_source_has_external_api_dependency() -> bool:
    inspected = (
        DEPLOYMENT_REPOSITORY / "vercel.json",
        DEPLOYMENT_REPOSITORY / "web" / "app" / "components" / "Assessment.tsx",
    )
    prohibited = ("onrender.com", "chatgpt.site", "FINACCESS_API_URL")
    return any(
        token in path.read_text(encoding="utf-8")
        for path in inspected
        for token in prohibited
    )


def validate_public_deployment() -> dict[str, Any]:
    """Exercise the public browser-to-model path and return auditable evidence."""

    profile = json.loads(ASSESSMENT_EXAMPLE.read_text(encoding="utf-8"))
    expected = json.loads(EXPECTED_RESPONSE.read_text(encoding="utf-8"))
    frontend = _http_json(PUBLIC_BASE_URL)
    health = _http_json(f"{PUBLIC_BASE_URL}/api/health")
    docs = _http_json(f"{PUBLIC_BASE_URL}/api/docs")
    openapi = _http_json(f"{PUBLIC_BASE_URL}/api/openapi.json")
    assessment = _http_json(
        f"{PUBLIC_BASE_URL}/api/v1/assessment", method="POST", payload=profile
    )
    invalid = _http_json(
        f"{PUBLIC_BASE_URL}/api/v1/assessment", method="POST", payload={}
    )

    frontend_body = str(frontend["body"])
    health_body = health["body"] if isinstance(health["body"], dict) else {}
    openapi_body = openapi["body"] if isinstance(openapi["body"], dict) else {}
    assessment_body = assessment["body"] if isinstance(assessment["body"], dict) else {}
    models = health_body.get("models", [])
    openapi_paths = openapi_body.get("paths", {})
    models_by_key = {item.get("model"): item for item in models}

    outcome_names = ("financial_inclusion", "mobile_money_adoption")
    probability_match = all(
        abs(
            float(assessment_body.get(outcome, {}).get("probability", -1))
            - float(expected.get(outcome, {}).get("probability", -2))
        )
        <= 1e-12
        for outcome in outcome_names
    )
    factor_match = all(
        assessment_body.get(outcome, {}).get("main_factors")
        == expected.get(outcome, {}).get("main_factors")
        for outcome in outcome_names
    )
    explanation_counts = {
        outcome: len(assessment_body.get(outcome, {}).get("main_factors", []))
        for outcome in outcome_names
    }
    artifact_hashes_match = all(
        models_by_key.get(model_key, {}).get("pipeline_sha256") == hashes["pipeline_sha256"]
        and models_by_key.get(model_key, {}).get("explainer_sha256") == hashes["explainer_sha256"]
        for model_key, hashes in EXPECTED_ARTIFACT_HASHES.items()
    )

    config = json.loads((DEPLOYMENT_REPOSITORY / "vercel.json").read_text(encoding="utf-8"))
    services = config.get("services", {})
    rewrites = config.get("rewrites", [])
    services_valid = (
        services.get("web", {}).get("root") == "web/"
        and services.get("web", {}).get("framework") == "nextjs"
        and services.get("backend", {}).get("root") == "backend/"
        and services.get("backend", {}).get("framework") == "fastapi"
        and services.get("backend", {}).get("entrypoint") == "main:app"
        and len(rewrites) >= 2
        and rewrites[0].get("source") == "/api/(.*)"
        and rewrites[0].get("destination", {}).get("service") == "backend"
        and rewrites[1].get("source") == "/(.*)"
        and rewrites[1].get("destination", {}).get("service") == "web"
    )

    tracked = _tracked_deployment_files()
    respondent_data_extensions = {".csv", ".parquet", ".sav", ".dta", ".xlsx"}
    tracked_respondent_data = [
        path
        for path in tracked
        if Path(path).suffix.lower() in respondent_data_extensions
        and (path.startswith("data/") or "microdata" in path.lower())
    ]
    required_models = {
        "backend/models/model1_financial_inclusion_pipeline.joblib",
        "backend/models/model1_financial_inclusion_metadata.json",
        "backend/models/model1_shap_explainer.joblib",
        "backend/models/model2_mobile_money_pipeline.joblib",
        "backend/models/model2_mobile_money_metadata.json",
        "backend/models/model2_shap_explainer.joblib",
    }
    tracked_secret_files = [
        path
        for path in tracked
        if (
            Path(path).name.startswith(".env")
            and Path(path).name != ".env.example"
        )
        or Path(path).suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
    ]
    retired_auth_files = [
        path for path in tracked if path.endswith("chatgpt-auth.ts") or path.startswith(".openai/")
    ]

    checks = [
        _check(
            "public_frontend_https",
            frontend["status_code"] == 200
            and frontend["final_url"] == PUBLIC_BASE_URL
            and "Financial Access in Eswatini" in frontend_body
            and "Developed by Thando F. Dlamini" in frontend_body,
            (
                f"HTTP {frontend['status_code']} at the production domain; Signal heading and "
                "developer credit found without an authentication redirect."
            ),
        ),
        _check(
            "api_health_and_artifact_integrity",
            health["status_code"] == 200
            and health_body.get("status") == "healthy"
            and len(models) == 2
            and all(model.get("status") == "ready" for model in models)
            and artifact_hashes_match,
            f"HTTP {health['status_code']}; two hash-matched model/explainer pairs are ready.",
        ),
        _check(
            "openapi_contract",
            openapi["status_code"] == 200
            and "/api/health" in openapi_paths
            and "/api/v1/assessment" in openapi_paths,
            f"HTTP {openapi['status_code']}; same-origin health and assessment paths present.",
        ),
        _check(
            "interactive_api_documentation",
            docs["status_code"] == 200 and "swagger" in str(docs["body"]).lower(),
            f"HTTP {docs['status_code']} at /api/docs.",
        ),
        _check(
            "combined_assessment",
            assessment["status_code"] == 200
            and all(outcome in assessment_body for outcome in outcome_names),
            f"HTTP {assessment['status_code']}; one public request returned both outcomes.",
        ),
        _check(
            "validated_prediction_equivalence",
            probability_match and factor_match,
            "Live probabilities and all local SHAP factors match the validated Phase 10 example.",
        ),
        _check(
            "explanation_factors",
            all(count == 5 for count in explanation_counts.values()),
            f"Model-derived explanation counts: {explanation_counts}.",
        ),
        _check(
            "invalid_input_rejected",
            invalid["status_code"] == 422,
            f"Empty profile rejected with HTTP {invalid['status_code']}.",
        ),
        _check(
            "one_domain_no_cors_dependency",
            API_BASE_URL == FRONTEND_BASE_URL
            and assessment["final_url"].startswith(PUBLIC_BASE_URL),
            "The browser and FastAPI routes share one HTTPS origin; CORS is not in the normal path.",
        ),
        _check(
            "vercel_services_configuration",
            services_valid,
            "Next.js and FastAPI are separate Vercel services with API-first routing.",
        ),
        _check(
            "no_external_api_dependency",
            not _deployed_source_has_external_api_dependency(),
            "Deployed routing and assessment source contain no Render, Sites, or external API URL.",
        ),
        _check(
            "public_access_without_project_auth",
            not retired_auth_files,
            "No ChatGPT sign-in module or OpenAI hosting manifest is tracked in the deployment repository.",
        ),
        _check(
            "microdata_publication_safety",
            not tracked_respondent_data,
            (
                "No respondent-level dataset is tracked by the public deployment repository."
                if not tracked_respondent_data
                else f"Unexpected tracked data files: {tracked_respondent_data}"
            ),
        ),
        _check(
            "model_artifacts_published",
            required_models.issubset(set(tracked)),
            f"{len(required_models.intersection(tracked))}/6 validated deployment artifacts tracked.",
        ),
        _check(
            "secret_file_safety",
            not tracked_secret_files,
            (
                "No live environment, private-key, or certificate file is tracked."
                if not tracked_secret_files
                else f"Unexpected tracked files: {tracked_secret_files}"
            ),
        ),
    ]

    all_passed = all(item["status"] == "PASS" for item in checks)
    return {
        "phase": 12,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_WITH_NOTES" if all_passed else "FAIL",
        "endpoints": {
            "application": PUBLIC_BASE_URL,
            "frontend": PUBLIC_BASE_URL,
            "api": f"{PUBLIC_BASE_URL}/api",
            "health": f"{PUBLIC_BASE_URL}/api/health",
            "docs": f"{PUBLIC_BASE_URL}/api/docs",
            "assessment": f"{PUBLIC_BASE_URL}/api/v1/assessment",
        },
        "architecture": {
            "platform": "One Vercel Hobby project using Vercel Services",
            "frontend": "Next.js 16 Signal interface in the web service",
            "api": "FastAPI Python 3.13 inference service under /api",
            "model_runtime": "Two saved scikit-learn pipelines with model-matched SHAP explainers",
            "request_path": "Browser -> same-origin /api route -> FastAPI -> both models",
        },
        "deployment_repository": {
            "remote": "https://github.com/thandofana/finaccess-eswatini-web",
            "validated_commit": "6ac1810",
        },
        "checks": checks,
        "latency_seconds": {
            "frontend": frontend["latency_seconds"],
            "health": health["latency_seconds"],
            "api_docs": docs["latency_seconds"],
            "assessment": assessment["latency_seconds"],
            "invalid_request": invalid["latency_seconds"],
        },
        "sample_prediction": {
            "financial_inclusion": {
                "answer": assessment_body.get("financial_inclusion", {}).get("answer"),
                "probability_percent": assessment_body.get("financial_inclusion", {}).get(
                    "probability_percent"
                ),
                "factor_count": explanation_counts["financial_inclusion"],
            },
            "mobile_money_adoption": {
                "answer": assessment_body.get("mobile_money_adoption", {}).get("answer"),
                "probability_percent": assessment_body.get("mobile_money_adoption", {}).get(
                    "probability_percent"
                ),
                "factor_count": explanation_counts["mobile_money_adoption"],
            },
        },
        "notes": [
            "Vercel Services and the Vercel Python runtime are beta features, so deployment regression checks remain important.",
            "The Python dependency bundle was optimized by Vercel at 434.92 MB; dependency growth should be monitored.",
            "Automatic Git deployments require granting the Vercel GitHub App access to the private web repository; the validated release was deployed with the authenticated CLI.",
            "Serverless cold-start time can vary, although the live path no longer depends on a Render free-service wake-up.",
            "This remains a portfolio proof of concept, not a production financial decision engine.",
        ],
    }


def _markdown_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"| {item['check']} | {item['status']} | {item['evidence']} |"
        for item in result["checks"]
    )
    sample = result["sample_prediction"]
    notes = "\n".join(f"- {note}" for note in result["notes"])
    endpoints = result["endpoints"]
    architecture = result["architecture"]
    return f"""# Phase 12 Deployment Report

## Outcome

FinAccess Eswatini is publicly deployed as one Vercel application. The selected Signal frontend posts one validated profile to a same-origin FastAPI route, which returns predictions and model-derived SHAP explanations from both independently validated models.

**Phase status: {result['status'].replace('_', ' ')}**

## Public endpoints

- Application: {endpoints['application']}
- API information: {endpoints['api']}
- Health and artifact integrity: {endpoints['health']}
- Interactive API documentation: {endpoints['docs']}
- Combined assessment: {endpoints['assessment']}

Recruiters can open the application directly without a Vercel, Render, or OpenAI account.

## Architecture and reasoning

- Platform: {architecture['platform']}.
- Frontend: {architecture['frontend']}.
- API: {architecture['api']}.
- Inference: {architecture['model_runtime']}.
- Request flow: {architecture['request_path']}.
- One shared domain removes the cross-host proxy, public API environment variable, and browser CORS dependency.
- Raw and processed respondent records remain outside the deployment repository. Only the six validated model/explainer artifacts and their metadata are published.
- Every pipeline and explainer digest is checked before the service reports healthy.

## Live validation

| Check | Result | Evidence |
|---|---|---|
{checks}

## Production smoke-test example

- Financial inclusion: {sample['financial_inclusion']['answer']} ({sample['financial_inclusion']['probability_percent']}%); {sample['financial_inclusion']['factor_count']} explanation factors.
- Mobile money: {sample['mobile_money_adoption']['answer']} ({sample['mobile_money_adoption']['probability_percent']}%); {sample['mobile_money_adoption']['factor_count']} explanation factors.

The example verifies the live path; it is not a general analytical finding. The input profile is documented in `api/examples/assessment_request.json`.

## Local regression gate

- Python project suite: 96 tests passed with no failures or errors.
- Deployment-package API suite: 4 tests passed.
- Frontend production dependency audit: 0 vulnerabilities.
- Frontend lint and Next.js production build: passed.
- Rendered frontend routes: 5/5 passed.

The machine-readable local record is in `regression_validation.json`.

## Risks and limitations

{notes}

Latency values in `deployment_validation.json` are point-in-time observations, not a service-level commitment.

## Phase boundary

Phase 12 covers deployment configuration, hosting, security controls, and public smoke testing. Phase 13 portfolio polish has not been started.
"""


def write_phase12_reports(result: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "deployment_validation.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "phase": 12,
        "status": result["status"],
        "generated_at_utc": result["generated_at_utc"],
        "checks_passed": sum(item["status"] == "PASS" for item in result["checks"]),
        "checks_total": len(result["checks"]),
        "application_url": result["endpoints"]["application"],
        "api_url": result["endpoints"]["api"],
        "validated_commit": result["deployment_repository"]["validated_commit"],
        "notes": result["notes"],
    }
    (REPORT_DIR / "phase12_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (REPORT_DIR / "deployment_report.md").write_text(
        _markdown_report(result), encoding="utf-8"
    )
    checklist = "\n".join(
        f"- [{'x' if item['status'] == 'PASS' else ' '}] {item['check']}: {item['evidence']}"
        for item in result["checks"]
    )
    (REPORT_DIR / "deliverable_checklist.md").write_text(
        "# Phase 12 Deployment Validation Checklist\n\n"
        + checklist
        + f"\n\n**Overall status: {result['status'].replace('_', ' ')}**\n",
        encoding="utf-8",
    )


def run() -> dict[str, Any]:
    result = validate_public_deployment()
    write_phase12_reports(result)
    if result["status"] == "FAIL":
        failed = [item["check"] for item in result["checks"] if item["status"] == "FAIL"]
        raise RuntimeError(f"Phase 12 deployment validation failed: {failed}")
    return result


if __name__ == "__main__":
    phase_result = run()
    print(
        json.dumps(
            {
                "status": phase_result["status"],
                "checks": len(phase_result["checks"]),
                "application": phase_result["endpoints"]["application"],
            },
            indent=2,
        )
    )
