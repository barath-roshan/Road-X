"""Unified ML pipeline inference endpoints for RoadX FastAPI Service."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from api.config import api_settings
from api.dependencies import get_ml_service, get_request_id
from api.schemas.requests import (
    CandidateEvaluationRequest,
    DriftAnalysisRequest,
    MLAnalyzeRequest,
)
from api.schemas.responses import APIErrorResponse, MLAnalyzeResponse
from api.service import (
    InferenceFailedError,
    InvalidInputError,
    MLInferenceService,
    ModelNotReadyError,
)
from ml.monitoring.config import monitoring_config
from ml.monitoring.drift import DriftAnalyzer
from ml.monitoring.evaluator import CandidateModelEvaluator
from ml.monitoring.telemetry import telemetry
from ml.monitoring.tracker import MLflowTracker

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


@router.get(
    "/ml/monitoring/telemetry",
    summary="Get Operational Inference Telemetry",
    description="Retrieve aggregated metrics on request counts, error rates, latencies, and model invocations.",
    status_code=status.HTTP_200_OK,
)
def get_inference_telemetry() -> Dict[str, Any]:
    """Return live operational telemetry summary."""
    return telemetry.get_metrics()


@router.get(
    "/ml/monitoring/experiments",
    summary="List MLflow Experiment History",
    description="Retrieve recorded experiment tracking summaries from local/MLflow history.",
    status_code=status.HTTP_200_OK,
)
def list_experiment_history() -> List[Dict[str, Any]]:
    """Return recorded experiment training runs and metrics."""
    tracker = MLflowTracker()
    return tracker.get_experiment_history()


@router.post(
    "/ml/monitoring/drift",
    summary="Analyze Feature and Data Drift",
    description="Compute statistical drift (PSI and KS test) between reference baseline and monitored observations.",
    status_code=status.HTTP_200_OK,
)
def analyze_feature_drift(payload: DriftAnalysisRequest) -> Dict[str, Any]:
    """Execute statistical distribution drift detection."""
    if not payload.current_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_CURRENT_DATA", "message": "current_data list cannot be empty."},
        )

    curr_df = pd.DataFrame(payload.current_data)

    if payload.reference_data:
        ref_df = pd.DataFrame(payload.reference_data)
    elif monitoring_config.reference_data_path.exists():
        try:
            ref_df = pd.read_csv(monitoring_config.reference_data_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "REF_DATA_READ_ERROR", "message": f"Failed to load reference dataset: {e}"},
            )
    else:
        return {
            "timestamp": pd.Timestamp.utcnow().isoformat(),
            "overall_drift_detected": False,
            "overall_status": "NO_REFERENCE_DATA",
            "features_analyzed": 0,
            "features_with_drift": [],
            "feature_results": {},
            "schema_warnings": ["No reference dataset provided and no persisted baseline found."],
            "notes": "Reference baseline is required to calculate distribution drift.",
        }

    analyzer = DriftAnalyzer()
    report = analyzer.analyze(
        reference_data=ref_df,
        current_data=curr_df,
        feature_columns=payload.features,
    )
    return report.to_dict()


@router.post(
    "/ml/monitoring/evaluate",
    summary="Evaluate Candidate Model for Promotion",
    description="Compare candidate model metrics against active baseline against acceptance thresholds.",
    status_code=status.HTTP_200_OK,
)
def evaluate_candidate_model(payload: CandidateEvaluationRequest) -> Dict[str, Any]:
    """Evaluate candidate model metrics against baseline."""
    evaluator = CandidateModelEvaluator()
    decision = evaluator.evaluate_candidate(
        candidate_metrics=payload.candidate_metrics,
        baseline_metrics=payload.baseline_metrics,
        candidate_version=payload.candidate_version,
        baseline_version=payload.baseline_version,
    )
    return decision.to_dict()
