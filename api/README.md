# FinAccess Eswatini Prediction API

FastAPI service for one combined financial-access assessment. A validated request is passed independently through the financial-inclusion and mobile-money pipelines, and both responses include model-derived SHAP factors.

## Endpoints

- `GET /health` — validate service readiness and artifact integrity.
- `POST /api/v1/assessment` — run both predictions from one profile.
- `GET /docs` — interactive OpenAPI documentation.
- `GET /openapi.json` — machine-readable contract.

## Run locally

From the project root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_api.ps1
```

Then open `http://127.0.0.1:8000/docs`. The example request is in `api/examples/assessment_request.json`.

The API does not persist submitted profiles. The `0.50` decision threshold is explicitly identified as provisional, and explanations describe model behaviour rather than causation.
