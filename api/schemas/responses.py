"""Response Pydantic models for RoadX FastAPI Service."""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from ml.pipeline.schemas import UnifiedPipelineResult


class HealthResponse(BaseModel):
    """Basic health check response schema for `/health`."""

    status: str = Field(default="healthy", description="Service health status", examples=["healthy"])
    service: str = Field(
        default="roadx-ml-service", description="Service identifier name", examples=["roadx-ml-service"]
    )
    version: str = Field(default="1.0.0", description="API version identifier", examples=["1.0.0"])


class ReadinessResponse(BaseModel):
    """Readiness probe response schema for `/ready`."""

    status: str = Field(
        description="Readiness status: 'ready' or 'not_ready'", examples=["ready", "not_ready"]
    )
    pipeline_loaded: bool = Field(
        description="Flag indicating whether unified ML pipeline is loaded and ready for inference",
        examples=[True],
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional diagnostic metrics or component load status"
    )


class APIErrorDetails(BaseModel):
    """Structured error payload details."""

    code: str = Field(
        description="Machine-readable error code",
        examples=["MODEL_NOT_READY", "VALIDATION_ERROR", "INFERENCE_ERROR", "BAD_REQUEST"],
    )
    message: str = Field(
        description="Human-readable error description",
        examples=["The ML pipeline is not initialized or model loading failed."],
    )
    request_id: Optional[str] = Field(
        default=None, description="Unique trace identifier for request correlation"
    )


class APIErrorResponse(BaseModel):
    """Top-level structured error response container."""

    error: APIErrorDetails = Field(description="Structured error detail object")


# Alias for backwards compatibility
APIError = APIErrorDetails


class MLAnalyzeResponse(UnifiedPipelineResult):
    """Response payload returned by `/api/v1/ml/analyze` extending `UnifiedPipelineResult`."""

    request_id: Optional[str] = Field(
        default=None, description="Unique correlation identifier for the HTTP request"
    )
