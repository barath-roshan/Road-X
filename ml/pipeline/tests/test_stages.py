"""Unit tests for individual pipeline stage handlers (Phase 9)."""

from unittest.mock import MagicMock
import pytest

from ml.pipeline.context import MLPipelineContext
from ml.pipeline.schemas import PipelineInput, PipelineStageStatus
from ml.pipeline.stages import (
    execute_complaint_intelligence_stage,
    execute_damage_detection_stage,
    execute_duplicate_detection_stage,
    execute_failure_prediction_stage,
    execute_maintenance_priority_stage,
    execute_severity_stage,
    execute_time_to_failure_stage,
)
from ml.damage_detection.schemas import RoadDamageDetectionResponse, DamageDetection
from ml.complaint_intelligence.schemas import (
    ComplaintAnalysisResponse,
    IssueCategory,
    UrgencyLevel,
    SafetyRiskLevel,
)


def test_failure_prediction_stage_missing_payload():
    inp = PipelineInput(road_segment_id="SEG-1")
    ctx = MLPipelineContext(inp)
    flags = {"failure_prediction": True}

    execute_failure_prediction_stage(ctx, predictor=MagicMock(), default_flags=flags)
    assert ctx.stage_summaries["failure_prediction"].status == PipelineStageStatus.SKIPPED
    assert "No road_data" in ctx.stage_summaries["failure_prediction"].error_message


def test_severity_stage_missing_damage_detection_dependency():
    inp = PipelineInput(road_segment_id="SEG-1", road_context={"surface_type": "ASPHALT"})
    ctx = MLPipelineContext(inp)
    flags = {"severity": True}

    # Damage detection output is None in context
    execute_severity_stage(ctx, predictor=MagicMock(), default_flags=flags)
    assert ctx.stage_summaries["severity"].status == PipelineStageStatus.UNAVAILABLE
    assert "Damage detection output unavailable" in ctx.stage_summaries["severity"].error_message
    assert ctx.severity_prediction is None


def test_complaint_intelligence_stage_success():
    inp = PipelineInput(complaint_text="Huge pothole on Main Street creating traffic hazard.")
    ctx = MLPipelineContext(inp)
    flags = {"complaint_intelligence": True}

    mock_analyzer = MagicMock()
    mock_analyzer.analyze.return_value = ComplaintAnalysisResponse(
        issue_category=IssueCategory.POTHOLE,
        issue_confidence=0.95,
        urgency=UrgencyLevel.HIGH,
        urgency_confidence=0.90,
        safety_risk=SafetyRiskLevel.HIGH,
        safety_confidence=0.88,
        location_mentions=[],
        embedding_available=True,
        model_version="v1",
    )

    execute_complaint_intelligence_stage(ctx, analyzer=mock_analyzer, default_flags=flags)
    assert ctx.stage_summaries["complaint_intelligence"].status == PipelineStageStatus.SUCCESS
    assert ctx.complaint_analysis is not None
    assert ctx.complaint_analysis.issue_category == IssueCategory.POTHOLE


def test_stage_failure_isolation():
    inp = PipelineInput(image="invalid_path.jpg")
    ctx = MLPipelineContext(inp)
    flags = {"damage_detection": True}

    mock_detector = MagicMock()
    mock_detector.detect.side_effect = ValueError("Corrupted image format")

    execute_damage_detection_stage(ctx, detector=mock_detector, default_flags=flags)
    assert ctx.stage_summaries["damage_detection"].status == PipelineStageStatus.FAILED
    assert ctx.stage_summaries["damage_detection"].error_code == "DAMAGE_DETECTION_ERROR"
    assert "Corrupted image format" in ctx.stage_summaries["damage_detection"].error_message
