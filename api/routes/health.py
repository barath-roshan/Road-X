"""Health and readiness check endpoints for RoadX ML Service."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from api.config import api_settings
from api.dependencies import get_ml_service
from api.schemas.responses import HealthResponse, ReadinessResponse
from api.service import MLInferenceService

router = APIRouter(tags=["Health & Readiness"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns basic operational health status of the API service without invoking ML components.",
)
def check_health() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="roadx-ml-service",
        version=api_settings.version,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="ML Component Readiness Probe",
    description="Indicates whether required ML pipeline components and model artifacts are initialized.",
    responses={
        status.HTTP_200_OK: {"description": "ML pipeline loaded and ready for inference."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "ML pipeline failed initialization or component unavailable."
        },
    },
)
def check_readiness(
    response: Response,
    service: MLInferenceService = Depends(get_ml_service),
) -> ReadinessResponse:
    """Readiness check probing model artifact initialization status."""
    if service.is_ready:
        return ReadinessResponse(
            status="ready",
            pipeline_loaded=True,
            details={"service_version": api_settings.version},
        )

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="not_ready",
        pipeline_loaded=False,
        details={"error": service.init_error or "ML components failed loading"},
    )
