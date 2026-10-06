"""Service layer for RoadX FastAPI ML Service.

Decouples FastAPI HTTP route controllers from Phase 9 Unified ML Pipeline orchestrator.
"""

from __future__ import annotations

import io
import time
from typing import Any, Dict, Optional
from PIL import Image

from ml.common.logging_config import get_logger
from ml.pipeline.orchestrator import RoadXPipeline
from ml.pipeline.schemas import PipelineInput, UnifiedPipelineResult
from api.schemas.requests import MLAnalyzeRequest
from api.schemas.responses import MLAnalyzeResponse

logger = get_logger("api.service")


class ServiceError(Exception):
    """Base exception class for API service layer errors."""

    def __init__(self, message: str, code: str = "SERVICE_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ModelNotReadyError(ServiceError):
    """Raised when pipeline is invoked before successful initialization."""

    def __init__(self, message: str = "The ML pipeline is not ready.") -> None:
        super().__init__(message, code="MODEL_NOT_READY")


class InvalidInputError(ServiceError):
    """Raised when request payload or file format validation fails at service layer."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INVALID_INPUT")


class InferenceFailedError(ServiceError):
    """Raised when internal pipeline execution fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INFERENCE_FAILED")


class MLInferenceService:
    """Production service container managing single RoadXPipeline instance lifetime."""

    def __init__(self, pipeline: Optional[RoadXPipeline] = None) -> None:
        self.pipeline: Optional[RoadXPipeline] = pipeline
        self._is_ready: bool = False
        self._init_error: Optional[str] = None
        self._init_time_ms: float = 0.0

    @property
    def is_ready(self) -> bool:
        """Check if pipeline is loaded and ready for inference."""
        return self._is_ready and self.pipeline is not None

    @property
    def init_error(self) -> Optional[str]:
        """Return initialization error message if loading failed."""
        return self._init_error

    def initialize(self) -> None:
        """Initialize the unified ML pipeline once during application startup."""
        start_t = time.perf_counter()
        logger.info("Initializing MLInferenceService unified pipeline singleton...")

        try:
            if self.pipeline is None:
                self.pipeline = RoadXPipeline(auto_load=True)

            self._is_ready = True
            self._init_error = None
            self._init_time_ms = (time.perf_counter() - start_t) * 1000.0

            logger.info(
                "MLInferenceService initialized successfully in %.2f ms.",
                self._init_time_ms,
            )
        except Exception as e:
            self._is_ready = False
            self._init_error = str(e)
            logger.error("Failed to initialize MLInferenceService pipeline: %s", e, exc_info=True)

    def analyze(
        self, request: MLAnalyzeRequest, request_id: Optional[str] = None
    ) -> MLAnalyzeResponse:
        """Execute unified ML pipeline analysis for an incoming request.

        Args:
            request: Validated API request model.
            request_id: Correlation identifier.

        Returns:
            MLAnalyzeResponse output.
        """
        if not self.is_ready or self.pipeline is None:
            logger.warning("[%s] Rejecting request: ML pipeline is not ready.", request_id)
            raise ModelNotReadyError("The ML pipeline is not ready.")

        logger.info(
            "[%s] Executing pipeline analysis (road_segment_id=%s, complaint_id=%s)",
            request_id,
            request.road_segment_id,
            request.complaint_id,
        )

        pipeline_input: PipelineInput = request.to_pipeline_input()

        try:
            result: UnifiedPipelineResult = self.pipeline.run(pipeline_input)
            
            # Map UnifiedPipelineResult into MLAnalyzeResponse
            response_dict = result.model_dump()
            response_dict["request_id"] = request_id
            return MLAnalyzeResponse(**response_dict)

        except Exception as e:
            logger.error("[%s] Pipeline execution error: %s", request_id, e, exc_info=True)
            raise InferenceFailedError(f"ML pipeline execution failed: {e}") from e

    def analyze_image(
        self,
        image_bytes: bytes,
        filename: str,
        road_context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> MLAnalyzeResponse:
        """Execute damage detection pipeline over uploaded image bytes.

        Args:
            image_bytes: Raw binary content of uploaded image.
            filename: Name of uploaded file.
            road_context: Optional surface context.
            request_id: Correlation identifier.

        Returns:
            MLAnalyzeResponse containing damage detection results.
        """
        if not self.is_ready or self.pipeline is None:
            logger.warning("[%s] Rejecting image request: ML pipeline is not ready.", request_id)
            raise ModelNotReadyError("The ML pipeline is not ready.")

        if not image_bytes:
            raise InvalidInputError("Uploaded image file is empty.")

        # Validate image readable by PIL
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            pil_image.verify()
            # Re-open after verify() as verify alters image stream
            pil_image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            logger.warning("[%s] Corrupted or unreadable image uploaded (%s): %s", request_id, filename, e)
            raise InvalidInputError(f"Uploaded file '{filename}' is not a valid or readable image.") from e

        logger.info("[%s] Processing image analysis for file '%s'", request_id, filename)

        pipeline_input = PipelineInput(
            image=pil_image,
            road_context=road_context,
            enabled_stages={
                "damage_detection": True,
                "severity": True if road_context else False,
                "maintenance_priority": True,
            },
        )

        try:
            result = self.pipeline.run(pipeline_input)
            response_dict = result.model_dump()
            response_dict["request_id"] = request_id
            return MLAnalyzeResponse(**response_dict)
        except Exception as e:
            logger.error("[%s] Image analysis pipeline error: %s", request_id, e, exc_info=True)
            raise InferenceFailedError(f"Image analysis pipeline failed: {e}") from e
