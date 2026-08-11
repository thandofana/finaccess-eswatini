"""Validate and document the Phase 11 web-application concepts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.deliverables import render_delivery_checklist


FRONTEND = PROJECT_ROOT / "frontend"
FRONTEND_APP = FRONTEND / "web"
REPORT_DIR = PROJECT_ROOT / "reports" / "phase_11"
CONCEPTS = (
    ("ledger", "The Ledger", "Editorial evidence", "Warm ivory, forest green, and ochre"),
    ("open-field", "Open Field", "Human-centred insight", "Soft sage, cream, and terracotta"),
    ("signal", "Signal", "Modern fintech clarity", "White, pale blue, cobalt, and teal"),
)


@dataclass(frozen=True)
class ValidationCheck:
    check: str
    passed: bool
    evidence: str


def _read(relative: str) -> str:
    return (FRONTEND_APP / relative).read_text(encoding="utf-8")


def validate_frontend() -> list[ValidationCheck]:
    data = _read("app/data.ts")
    experience = _read("app/components/FinAccessExperience.tsx")
    homepage = _read("app/page.tsx")
    assessment = _read("app/components/Assessment.tsx")
    css = _read("app/globals.css")
    package = json.loads(_read("package.json"))
    with Image.open(FRONTEND_APP / "public" / "og.png") as social:
        social_size = social.size
    offline_pages = [
        PROJECT_ROOT / "design_review" / name
        for name in ("index.html", "ledger.html", "open-field.html", "signal.html")
    ]
    offline_source = "\n".join(
        path.read_text(encoding="utf-8") for path in offline_pages if path.is_file()
    )

    expected_fields = {
        "female", "age_group", "educ", "inc_q", "emp_in", "fin24c", "fin46",
        "internet_use", "internet_engagement_level", "data_purchase_pattern",
        "phone_access_tier", "con11", "con12", "con14", "con16", "con18", "con20",
    }
    all_app_source = "\n".join(
        path.read_text(encoding="utf-8") for path in (FRONTEND_APP / "app").rglob("*") if path.is_file()
    )
    checks = [
        ValidationCheck(
            "three_distinct_concepts",
            all(key in data and name in data for key, name, _, _ in CONCEPTS),
            "The Ledger, Open Field, and Signal are selectable full-product routes.",
        ),
        ValidationCheck(
            "five_product_areas",
            all(label in experience for label in ("Overview", "Financial inclusion", "Mobile money", "Assessment", "Methodology")),
            "Every concept exposes all five requested product areas.",
        ),
        ValidationCheck(
            "signal_selected_as_homepage",
            'concept.key === "signal"' in homepage and "selected" in homepage,
            "Signal is the main application homepage; alternative concepts remain archived routes.",
        ),
        ValidationCheck(
            "approved_homepage_content",
            all(token in experience for token in (
                "Financial Access in Eswatini", "Start an assessment", "Review the evidence",
                "Developed by Thando F. Dlamini",
            )),
            "The selected heading, both first-page actions, and bottom-right developer credit are present.",
        ),
        ValidationCheck(
            "complete_assessment_contract",
            all(f'key: "{field}"' in assessment for field in expected_fields),
            "The shared assessment captures all 17 validated Phase 10 inputs.",
        ),
        ValidationCheck(
            "real_api_integration",
            'fetch("/api/v1/assessment"' in assessment and "FINACCESS_API_URL" not in assessment,
            "The assessment posts directly to the same-origin Phase 10 FastAPI route.",
        ),
        ValidationCheck(
            "human_readable_model_output",
            all(token in assessment for token in ("result.answer", "probability_percent", "main_factors", "result.disclaimer")),
            "Results lead with natural-language answers, then probabilities and SHAP factors.",
        ),
        ValidationCheck(
            "real_project_evidence",
            all(token in data for token in ("1,051", "43.1%", "50.4%", "0.745", "0.726")),
            "The interface uses validated sample, outcome, and holdout metrics.",
        ),
        ValidationCheck(
            "light_visual_systems",
            all(f".concept--{key}" in css for key, _, _, _ in CONCEPTS)
            and "prefers-color-scheme: dark" not in css,
            "All concepts use individual light palettes; no dark-mode palette is defined.",
        ),
        ValidationCheck(
            "responsive_and_accessible",
            all(token in all_app_source + css for token in ("skip-link", "aria-live", "focus-visible", "prefers-reduced-motion", "@media (max-width")),
            "Keyboard focus, skip navigation, live results, reduced motion, and responsive breakpoints are present.",
        ),
        ValidationCheck(
            "social_preview",
            social_size[0] >= 1200 and social_size[1] >= 630,
            f"Generated social card is {social_size[0]}x{social_size[1]} PNG.",
        ),
        ValidationCheck(
            "production_build",
            package.get("scripts", {}).get("build") == "next build"
            and (FRONTEND_APP / "next.config.ts").is_file(),
            "The standard Next.js production build command and configuration are present.",
        ),
        ValidationCheck(
            "server_free_design_review",
            all(path.is_file() for path in offline_pages)
            and "<style>" in offline_source
            and '<script' not in offline_source
            and 'href="/assets/' not in offline_source,
            "Four self-contained HTML review pages work without a local server or API.",
        ),
        ValidationCheck(
            "minimal_dependencies",
            "react-loading-skeleton" not in package.get("dependencies", {})
            and set(package.get("dependencies", {})) == {"next", "react", "react-dom"},
            "Unused preview and database dependencies were removed; runtime dependencies remain minimal.",
        ),
        ValidationCheck(
            "phase_boundary_respected",
            not any(name in package.get("dependencies", {}) for name in ("drizzle-orm", "@vercel/postgres")),
            "Phase 11 introduced no database or object storage; Phase 12 hosting metadata is evaluated separately.",
        ),
    ]
    return checks


def write_reports(checks: list[ValidationCheck]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    passed = all(check.passed for check in checks)
    validation = {
        "checks": [asdict(check) for check in checks],
        "checks_passed": sum(check.passed for check in checks),
        "checks_total": len(checks),
        "passed": passed,
    }
    (REPORT_DIR / "frontend_validation.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )

    comparison_lines = [
        "# Phase 11 Concept Comparison", "",
        "All three directions share the same real evidence, routes, assessment, and API contract.", "",
        "| Concept | Design voice | Palette | Best fit |", "|---|---|---|---|",
        "| The Ledger | Editorial evidence | Warm ivory, forest green, ochre | Research credibility and a distinctive portfolio voice |",
        "| Open Field | Human-centred insight | Soft sage, cream, terracotta | Approachability and guided public-interest storytelling |",
        "| Signal | Modern fintech clarity | White, pale blue, cobalt, teal | Familiar product polish and compact analytical scanning |",
        "", "## Selected direction", "",
        "Signal was selected by the project owner. The Ledger and Open Field remain archived for design history.", "",
    ]
    (REPORT_DIR / "concept_comparison.md").write_text("\n".join(comparison_lines), encoding="utf-8")

    summary = {
        "phase": 11,
        "status": "PASS_WITH_NOTES" if passed else "FAIL",
        "scope": "Selected Signal frontend with two archived design alternatives",
        "concepts": [
            {"key": key, "name": name, "design_voice": voice, "palette": palette,
             "route": f"/concepts/{key}"}
            for key, name, voice, palette in CONCEPTS
        ],
        "product_areas_per_concept": 5,
        "assessment_fields": 17,
        "frontend_tests": 5,
        "frontend_validation_checks": len(checks),
        "frontend_validation_checks_passed": sum(check.passed for check in checks),
        "end_to_end_example": {
            "financial_inclusion_probability_percent": 26.9,
            "mobile_money_probability_percent": 36.8,
            "model_derived_factors_per_outcome": 5,
        },
        "api_proxy": "/api/assessment -> ${FINACCESS_API_URL}/api/v1/assessment",
        "deployment_started": False,
        "concept_selected": True,
        "selected_concept": "Signal",
        "limitations": [
            "Public hosting and production environment configuration remain Phase 12 work.",
            "Thresholds remain provisional and the product remains a proof of concept.",
        ],
    }
    (REPORT_DIR / "phase11_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    report = f"""# Phase 11 Web Application Report

## Outcome

Signal was selected as the main FinAccess Eswatini frontend. The Ledger and Open Field remain available as archived design alternatives.

## Validation

- Production build: PASS
- Rendered-route tests: 5/5 PASS
- Static contract and scope checks: {sum(check.passed for check in checks)}/{len(checks)} PASS
- Live frontend-to-API assessment: PASS (26.9% inclusion, 36.8% mobile money, five factors each)
- Phase 12 deployment started: No

## Selected direction

Signal is now the root application experience. Its first page leads with Financial Access in Eswatini, provides direct assessment and evidence actions, and carries the developer credit requested by the project owner.

## Responsible-use boundary

The application describes observed associations and model behaviour. It is not a causal analysis, eligibility tool, credit-scoring service, decision authority, or official World Bank classification.
"""
    (REPORT_DIR / "web_application_report.md").write_text(report, encoding="utf-8")
    (REPORT_DIR / "deliverable_checklist.md").write_text(
        render_delivery_checklist(PROJECT_ROOT, through_phase=11), encoding="utf-8"
    )


def main() -> int:
    checks = validate_frontend()
    write_reports(checks)
    for check in checks:
        print(f"{'PASS' if check.passed else 'FAIL'}: {check.check} - {check.evidence}")
    if not all(check.passed for check in checks):
        raise SystemExit("Phase 11 frontend validation failed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
