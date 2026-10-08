"""Unified ML pipeline inference endpoints for RoadX FastAPI Service."""

from __future__ import annotations

import json
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from api.config import api_settings
from api.dependencies import get_ml_service, get_request_id
from api.schemas.requests import MLAnalyzeRequest
from api.schemas.responses import APIErrorResponse, MLAnalyzeResponse
from api.service import (
    InferenceFailedError,
    InvalidInputError,
    MLInferenceService,
    ModelNotReadyError,
)

HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

router = APIRouter(prefix=api_settings.api_prefix, tags=["ML Pipeline"])


@router.post(
    "/ml/analyze",
    response_model=MLAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Unified ML Pipeline",
    description=(
        "Executes the RoadX Unified ML Pipeline over single or combined input payloads "
        "(tabular road data, citizen complaint text, image path, duplicate records, etc.)."
    ),
    responses={
        status.HTTP_200_OK: {"description": "Successful pipeline inference."},
        status.HTTP_400_BAD_REQUEST: {"model": APIErrorResponse, "description": "Invalid input payload."},
        HTTP_422: {"description": "Schema validation failure."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": APIErrorResponse,
            "description": "ML pipeline service not ready or models uninitialized.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": APIErrorResponse,
            "description": "Pipeline execution runtime failure.",
        },
    },
)
def analyze_grievance(
    payload: MLAnalyzeRequest,
    service: MLInferenceService = Depends(get_ml_service),
    request_id: str = Depends(get_request_id),
) -> MLAnalyzeResponse:
    """Execute unified ML pipeline analysis for JSON request payload."""
    try:
        return service.analyze(request=payload, request_id=request_id)
    except ModelNotReadyError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": e.code, "message": e.message, "request_id": request_id},
        ) from e
    except InvalidInputError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message, "request_id": request_id},
        ) from e
    except InferenceFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": e.code, "message": e.message, "request_id": request_id},
        ) from e


@router.post(
    "/ml/damage/analyze",
    response_model=MLAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Visual Damage Detection",
    description="Uploads a road surface image to analyze road damage, potholes, severity, and maintenance priority.",
    responses={
        status.HTTP_200_OK: {"description": "Successful damage detection inference."},
        status.HTTP_400_BAD_REQUEST: {
            "model": APIErrorResponse,
            "description": "Unsupported file format, corrupt image, or oversized payload.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": APIErrorResponse,
            "description": "ML pipeline service not ready.",
        },
    },
)
async def analyze_damage_image(
    file: UploadFile = File(..., description="Road image file (JPEG, PNG, WebP)"),
    road_context_json: Optional[str] = Form(
        default=None, description="Optional JSON string containing RoadContextInput payload"
    ),
    service: MLInferenceService = Depends(get_ml_service),
    request_id: str = Depends(get_request_id),
) -> MLAnalyzeResponse:
    """Execute damage detection pipeline over uploaded image file."""
    # 1. Content-Type & Extension validation
    content_type = (file.content_type or "").lower()
    filename = file.filename or "uploaded_image.jpg"
    
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    valid_exts = {"jpg", "jpeg", "png", "webp"}
    
    if content_type not in api_settings.allowed_image_content_types and ext not in valid_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": f"Unsupported file type '{content_type or ext}'. Allowed types: JPEG, PNG, WebP.",
                "request_id": request_id,
            },
        )

    # 2. Read image content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "FILE_READ_ERROR",
                "message": f"Failed to read uploaded file: {e}",
                "request_id": request_id,
            },
        ) from e

    # 3. File size check
    if len(content) > api_settings.max_image_size_bytes:
        max_mb = api_settings.max_image_size_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"File size exceeds maximum allowed limit of {max_mb:.1f} MB.",
                "request_id": request_id,
            },
        )

    # 4. Parse optional road context JSON if provided
    parsed_road_context = None
    if road_context_json:
        try:
            parsed_road_context = json.loads(road_context_json)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_JSON",
                    "message": f"Invalid road_context_json payload: {e}",
                    "request_id": request_id,
                },
            ) from e

    # 5. Invoke ML Service
    try:
        return service.analyze_image(
            image_bytes=content,
            filename=filename,
            road_context=parsed_road_context,
            request_id=request_id,
        )
    except ModelNotReadyError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": e.code, "message": e.message, "request_id": request_id},
        ) from e
    except InvalidInputError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message, "request_id": request_id},
        ) from e
    except InferenceFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": e.code, "message": e.message, "request_id": request_id},
        ) from e
