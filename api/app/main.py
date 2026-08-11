"""FastAPI application exposing the combined financial-access assessment."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.app.schemas import AssessmentRequest, AssessmentResponse, ErrorResponse, HealthResponse
from api.app.service import (
    SERVICE_VERSION,
    ArtifactIntegrityError,
    InferenceError,
    PredictionService,
    get_prediction_service,
)


def configured_cors_origins(value: str | None = None) -> list[str]:
    """Return unique, explicit browser origins from the deployment setting."""

    raw = os.getenv("FINACCESS_CORS_ORIGINS", "") if value is None else value
    origins: list[str] = []
    for item in raw.split(","):
        origin = item.strip().rstrip("/")
        if origin and origin != "*" and origin not in origins:
            origins.append(origin)
    return origins


app = FastAPI(
    title="FinAccess Eswatini Prediction API",
    summary="Combined financial-inclusion and mobile-money assessment API.",
    description=(
        "A portfolio proof-of-concept that validates one profile, runs two independently "
        "trained pipelines, and returns model-derived SHAP explanations."
    ),
    version=SERVICE_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

cors_origins = configured_cors_origins()
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        max_age=600,
    )

ServiceDependency = Annotated[PredictionService, Depends(get_prediction_service)]


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": details,
            }
        },
    )


@app.exception_handler(InferenceError)
async def inference_error_handler(_: Request, __: InferenceError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INFERENCE_ERROR",
                "message": "The assessment could not be completed safely.",
                "details": [],
            }
        },
    )


@app.exception_handler(ArtifactIntegrityError)
async def artifact_error_handler(_: Request, __: ArtifactIntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": {
                "code": "SERVICE_NOT_READY",
                "message": "Validated model artifacts are unavailable or failed integrity checks.",
                "details": [],
            }
        },
    )


@app.get("/", tags=["service"])
def service_information() -> dict[str, str]:
    return {
        "service": "FinAccess Eswatini Prediction API",
        "version": SERVICE_VERSION,
        "health": "/health",
        "documentation": "/docs",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": ErrorResponse}},
    tags=["service"],
)
def health(service: ServiceDependency) -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="FinAccess Eswatini Prediction API",
        version=SERVICE_VERSION,
        models=service.health_models,
    )


@app.post(
    "/api/v1/assessment",
    response_model=AssessmentResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Invalid or internally inconsistent profile."},
        500: {"model": ErrorResponse, "description": "Safe inference could not be completed."},
        503: {"model": ErrorResponse, "description": "Validated artifacts are unavailable."},
    },
    tags=["assessment"],
)
def assess_profile(request: AssessmentRequest, service: ServiceDependency) -> AssessmentResponse:
    return service.assess(request)
