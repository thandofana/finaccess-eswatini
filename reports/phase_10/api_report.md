# Phase 10 Prediction API Report

The API validates one 18-field profile and returns separately generated financial-inclusion and mobile-money results with five model-derived SHAP factors each.

## Endpoints

- `GET /health` verifies both pipeline and explainer artifacts.
- `POST /api/v1/assessment` runs the combined assessment.
- `/docs`, `/redoc`, and `/openapi.json` expose the documented contract.

## Validated example

- Financial inclusion: This person is unlikely to be financially included. (26.9%)
- Mobile money adoption: This person is unlikely to use mobile money. (36.8%)
- The natural-language factors come directly from the persisted SHAP explainers.

## Error and integrity behaviour

- 8/8 contract scenarios passed.
- Invalid categories, missing/extra fields, and contradictory routing receive structured `422` responses.
- Inference failures return a sanitized `500`; artifact integrity failures return `503`.
- Submitted profiles are not persisted by the API.

## Boundaries

- The 0.50 classification threshold remains provisional.
- Predictions and SHAP factors are not causal, eligibility, or creditworthiness determinations.
- CORS and deployment configuration remain reserved for their approved later phases.
