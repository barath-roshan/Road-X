"""Stage handlers for RoadX Unified ML Pipeline execution stages."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from ml.common.logging_config import get_logger
from ml.pipeline.config import pipeline_config
from ml.pipeline.context import MLPipelineContext
from ml.pipeline.schemas import PipelineStageStatus

# Import predictor interfaces
from ml.failure_prediction.predict import RoadFailurePredictor
from ml.failure_prediction.schemas import RoadFailureInput
from ml.damage_detection.detector import RoadDamageDetector
from ml.severity.predict import DamageSeverityPredictor
from ml.severity.schemas import RoadContextInput
from ml.complaint_intelligence.analyzer import ComplaintAnalyzer
from ml.duplicate_detection.detector import DuplicateDetector
from ml.duplicate_detection.schemas import ComplaintRecord
from ml.time_to_failure.predictor import TimeToFailurePredictor
from ml.priority_engine.engine import MaintenancePriorityEngine
from ml.priority_engine.schemas import MaintenancePriorityInput

logger = get_logger("pipeline.stages")


def _extract_model_version(obj: Any) -> str:
    """Helper to extract model version string safely even when objects are mocked."""
    if obj is None:
        return "v1"
    ver = getattr(obj, "version", getattr(obj, "model_version", "v1"))
    if isinstance(ver, str) and not ver.startswith("<MagicMock"):
        return ver
    return "v1"


def execute_failure_prediction_stage(
    context: MLPipelineContext,
    predictor: Optional[RoadFailurePredictor],
    default_flags: Dict[str, bool],
) -> None:
    """Execute Phase 2 Road Failure Prediction stage."""
    stage_name = "failure_prediction"
    if not context.is_stage_enabled(stage_name, default_flags):
        context.record_stage_summary(stage_name, PipelineStageStatus.SKIPPED, 0.0, error_message="Stage disabled")
        return

    road_data = context.input_data.road_data
    if road_data is None:
        context.record_stage_summary(
            stage_name, PipelineStageStatus.SKIPPED, 0.0, error_message="No road_data payload provided"
        )
        return

    if predictor is None:
        context.record_stage_summary(
            stage_name, PipelineStageStatus.UNAVAILABLE, 0.0, error_message="RoadFailurePredictor unavailable"
        )
        return

    start_t = time.perf_counter()
    try:
        if isinstance(road_data, dict):
            road_input = RoadFailureInput(**road_data)
        else:
            road_input = road_data

        if context.input_data.road_segment_id and not road_input.segment_id:
            road_input.segment_id = context.input_data.road_segment_id

        result = predictor.predict(road_input)
        duration_ms = (time.perf_counter() - start_t) * 1000.0

        context.failure_prediction = result
        context.record_stage_summary(
            stage_name, PipelineStageStatus.SUCCESS, duration_ms, model_version=_extract_model_version(predictor)
        )
        logger.info("Failure prediction stage completed in %.2f ms", duration_ms)
    except Exception as e:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("Failure prediction stage failed: %s", e)
        context.record_stage_summary(
            stage_name,
            PipelineStageStatus.FAILED,
            duration_ms,
            error_code="FAILURE_PREDICTION_ERROR",
            error_message=str(e),
        )


def execute_damage_detection_stage(
    context: MLPipelineContext,
    detector: Optional[RoadDamageDetector],
    default_flags: Dict[str, bool],
) -> None:
    """Execute Phase 3 Road Damage Detection stage."""
    stage_name = "damage_detection"
    if not context.is_stage_enabled(stage_name, default_flags):
        context.record_stage_summary(stage_name, PipelineStageStatus.SKIPPED, 0.0, error_message="Stage disabled")
        return

    image = context.input_data.image
    if image is None:
        context.record_stage_summary(
            stage_name, PipelineStageStatus.SKIPPED, 0.0, error_message="No image payload provided"
        )
        return

    if detector is None:
        context.record_stage_summary(
            stage_name, PipelineStageStatus.UNAVAILABLE, 0.0, error_message="RoadDamageDetector unavailable"
        )
        return

    start_t = time.perf_counter()
    try:
        result = detector.detect(image)
        duration_ms = (time.perf_counter() - start_t) * 1000.0

        context.damage_detection = result
        context.record_stage_summary(
            stage_name, PipelineStageStatus.SUCCESS, duration_ms, model_version=_extract_model_version(result)
        )
        logger.info("Damage detection stage completed in %.2f ms", duration_ms)
    except Exception as e:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("Damage detection stage failed: %s", e)
        context.record_stage_summary(
            stage_name,
            PipelineStageStatus.FAILED,
            duration_ms,
            error_code="DAMAGE_DETECTION_ERROR",
            error_message=str(e),
        )


def execute_severity_stage(
    context: MLPipelineContext,
    predictor: Optional[DamageSeverityPredictor],
    default_flags: Dict[str, bool],
) -> None:
    """Execute Phase 4 Damage Severity Estimation stage."""
    stage_name = "severity"
    if not context.is_stage_enabled(stage_name, default_flags):
        context.record_stage_summary(stage_name, PipelineStageStatus.SKIPPED, 0.0, error_message="Stage disabled")
        return

    # Severity depends on Phase 3 Damage Detection
    if context.damage_detection is None:
        context.record_stage_summary(
            stage_name,
            PipelineStageStatus.UNAVAILABLE,
            0.0,
            error_message="Damage detection output unavailable for severity estimation",
        )
        return

    if predictor is None:
        context.record_stage_summary(
            stage_name, PipelineStageStatus.UNAVAILABLE, 0.0, error_message="DamageSeverityPredictor unavailable"
        )
        return

    start_t = time.perf_counter()
    try:
        road_context = context.input_data.road_context
        if isinstance(road_context, dict):
            ctx_input = RoadContextInput(**road_context)
        else:
            ctx_input = road_context

        result = predictor.predict(detections=context.damage_detection, road_context=ctx_input)
        duration_ms = (time.perf_counter() - start_t) * 1000.0

        context.severity_prediction = result
        context.record_stage_summary(
            stage_name, PipelineStageStatus.SUCCESS, duration_ms, model_version=_extract_model_version(predictor)
        )
        logger.info("Severity estimation stage completed in %.2f ms", duration_ms)
    except Exception as e:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("Severity estimation stage failed: %s", e)
        context.record_stage_summary(
            stage_name,
            PipelineStageStatus.FAILED,
            duration_ms,
            error_code="SEVERITY_PREDICTION_ERROR",
            error_message=str(e),
        )


def execute_complaint_intelligence_stage(
    context: MLPipelineContext,
    analyzer: Optional[ComplaintAnalyzer],
    default_flags: Dict[str, bool],
) -> None:
    """Execute Phase 5 Complaint Intelligence stage."""
    stage_name = "complaint_intelligence"
    if not context.is_stage_enabled(stage_name, default_flags):
        context.record_stage_summary(stage_name, PipelineStageStatus.SKIPPED, 0.0, error_message="Stage disabled")
        return

    text = context.input_data.complaint_text
    if not text:
        context.record_stage_summary(
            stage_name, PipelineStageStatus.SKIPPED, 0.0, error_message="No complaint_text provided"
        )
        return

    if analyzer is None:
        context.record_stage_summary(
            stage_name, PipelineStageStatus.UNAVAILABLE, 0.0, error_message="ComplaintAnalyzer unavailable"
        )
        return

    start_t = time.perf_counter()
    try:
        result = analyzer.analyze(text)
        duration_ms = (time.perf_counter() - start_t) * 1000.0

        context.complaint_analysis = result
        context.record_stage_summary(
            stage_name, PipelineStageStatus.SUCCESS, duration_ms, model_version=_extract_model_version(analyzer)
        )
        logger.info("Complaint intelligence stage completed in %.2f ms", duration_ms)
    except Exception as e:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("Complaint intelligence stage failed: %s", e)
        context.record_stage_summary(
            stage_name,
            PipelineStageStatus.FAILED,
            duration_ms,
            error_code="COMPLAINT_ANALYSIS_ERROR",
            error_message=str(e),
        )


def execute_duplicate_detection_stage(
    context: MLPipelineContext,
    detector: Optional[DuplicateDetector],
    default_flags: Dict[str, bool],
) -> None:
    """Execute Phase 6 Duplicate Complaint Detection stage."""
    stage_name = "duplicate_detection"
    if not context.is_stage_enabled(stage_name, default_flags):
        context.record_stage_summary(stage_name, PipelineStageStatus.SKIPPED, 0.0, error_message="Stage disabled")
        return

    existing_complaints = context.input_data.existing_complaints
    if not existing_complaints:
        context.record_stage_summary(
            stage_name,
            PipelineStageStatus.SKIPPED,
            0.0,
            error_message="No existing_complaints candidate pool provided for comparison",
        )
        return

    if detector is None:
        context.record_stage_summary(
            stage_name, PipelineStageStatus.UNAVAILABLE, 0.0, error_message="DuplicateDetector unavailable"
        )
        return

    start_t = time.perf_counter()
    try:
        # Obtain target ComplaintRecord
        if context.input_data.new_complaint_record:
            target_record = context.input_data.new_complaint_record
        elif context.input_data.complaint_text:
            target_record = ComplaintRecord(
                grievance_id=context.input_data.complaint_id or "COMP-NEW",
                text=context.input_data.complaint_text,
            )
        else:
            context.record_stage_summary(
                stage_name,
                PipelineStageStatus.SKIPPED,
                0.0,
                error_message="No target complaint text or record available for duplicate matching",
            )
            return

        result = detector.detect_duplicates(new_complaint=target_record, existing_complaints=existing_complaints)
        duration_ms = (time.perf_counter() - start_t) * 1000.0

        context.duplicate_detection = result
        context.record_stage_summary(
            stage_name, PipelineStageStatus.SUCCESS, duration_ms, model_version=_extract_model_version(detector)
        )
        logger.info("Duplicate detection stage completed in %.2f ms", duration_ms)
    except Exception as e:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("Duplicate detection stage failed: %s", e)
        context.record_stage_summary(
            stage_name,
            PipelineStageStatus.FAILED,
            duration_ms,
            error_code="DUPLICATE_DETECTION_ERROR",
            error_message=str(e),
        )


def execute_time_to_failure_stage(
    context: MLPipelineContext,
    predictor: Optional[TimeToFailurePredictor],
    default_flags: Dict[str, bool],
) -> None:
    """Execute Phase 7 Time-to-Failure Prediction stage."""
    stage_name = "time_to_failure"
    if not context.is_stage_enabled(stage_name, default_flags):
        context.record_stage_summary(stage_name, PipelineStageStatus.SKIPPED, 0.0, error_message="Stage disabled")
        return

    road_data = context.input_data.road_data
    if road_data is None:
        context.record_stage_summary(
            stage_name, PipelineStageStatus.SKIPPED, 0.0, error_message="No road_data payload provided"
        )
        return

    if predictor is None:
        context.record_stage_summary(
            stage_name, PipelineStageStatus.UNAVAILABLE, 0.0, error_message="TimeToFailurePredictor unavailable"
        )
        return

    start_t = time.perf_counter()
    try:
        if isinstance(road_data, dict):
            road_input = RoadFailureInput(**road_data)
        else:
            road_input = road_data

        if context.input_data.road_segment_id and not road_input.segment_id:
            road_input.segment_id = context.input_data.road_segment_id

        result = predictor.predict(road_input)
        duration_ms = (time.perf_counter() - start_t) * 1000.0

        context.time_to_failure = result
        context.record_stage_summary(
            stage_name, PipelineStageStatus.SUCCESS, duration_ms, model_version=_extract_model_version(predictor)
        )
        logger.info("Time-to-failure prediction stage completed in %.2f ms", duration_ms)
    except Exception as e:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("Time-to-failure prediction stage failed: %s", e)
        context.record_stage_summary(
            stage_name,
            PipelineStageStatus.FAILED,
            duration_ms,
            error_code="TIME_TO_FAILURE_ERROR",
            error_message=str(e),
        )


def execute_maintenance_priority_stage(
    context: MLPipelineContext,
    engine: Optional[MaintenancePriorityEngine],
    default_flags: Dict[str, bool],
) -> None:
    """Execute Phase 8 Maintenance Priority Engine stage."""
    stage_name = "maintenance_priority"
    if not context.is_stage_enabled(stage_name, default_flags):
        context.record_stage_summary(stage_name, PipelineStageStatus.SKIPPED, 0.0, error_message="Stage disabled")
        return

    if engine is None:
        context.record_stage_summary(
            stage_name, PipelineStageStatus.UNAVAILABLE, 0.0, error_message="MaintenancePriorityEngine unavailable"
        )
        return

    start_t = time.perf_counter()
    try:
        priority_input = MaintenancePriorityInput(
            road_segment_id=context.input_data.road_segment_id or "SEG-UNKNOWN",
            complaint_id=context.input_data.complaint_id or "COMP-UNKNOWN",
            failure_prediction=context.failure_prediction,
            severity_prediction=context.severity_prediction,
            complaint_analysis=context.complaint_analysis,
            duplicate_detection=context.duplicate_detection,
            time_to_failure=context.time_to_failure,
        )

        result = engine.prioritize(priority_input)
        duration_ms = (time.perf_counter() - start_t) * 1000.0

        context.maintenance_priority = result
        context.record_stage_summary(
            stage_name, PipelineStageStatus.SUCCESS, duration_ms, model_version=_extract_model_version(engine)
        )
        logger.info("Maintenance priority stage completed in %.2f ms", duration_ms)
    except Exception as e:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("Maintenance priority stage failed: %s", e)
        context.record_stage_summary(
            stage_name,
            PipelineStageStatus.FAILED,
            duration_ms,
            error_code="MAINTENANCE_PRIORITY_ERROR",
            error_message=str(e),
        )
