"""Unit tests for RoadXPipeline orchestrator (Phase 9)."""

from unittest.mock import MagicMock
import pytest

from ml.common.exceptions import RoadXDataError
from ml.pipeline.orchestrator import RoadXPipeline
from ml.pipeline.schemas import PipelineInput, PipelineStageStatus
from ml.failure_prediction.schemas import FailurePredictionOutput, FailureRiskLevel
from ml.complaint_intelligence.schemas import (
    ComplaintAnalysisResponse,
    IssueCategory,
    UrgencyLevel,
    SafetyRiskLevel,
)
from ml.priority_engine.schemas import (
    MaintenancePriorityOutput,
    MaintenancePriorityLevel,
    PrioritySignalEvidence,
)


def create_mock_pipeline():
    """Helper creating a RoadXPipeline instance with mocked predictors."""
    failure_pred = MagicMock()
    failure_pred.predict.return_value = FailurePredictionOutput(
        failure_probability=0.75,
        risk_level=FailureRiskLevel.HIGH,
        model_version="v1",
        top_contributing_factors=["pavement_age"],
    )

    damage_det = MagicMock()

    sev_pred = MagicMock()

    complaint_ana = MagicMock()
    complaint_ana.analyze.return_value = ComplaintAnalysisResponse(
        issue_category=IssueCategory.POTHOLE,
        issue_confidence=0.92,
        urgency=UrgencyLevel.HIGH,
        urgency_confidence=0.88,
        safety_risk=SafetyRiskLevel.HIGH,
        safety_confidence=0.85,
        location_mentions=[],
        embedding_available=True,
        model_version="v1",
    )

    dup_det = MagicMock()

    ttf_pred = MagicMock()

    pri_eng = MagicMock()
    pri_eng.prioritize.return_value = MaintenancePriorityOutput(
        road_segment_id="SEG-100",
        complaint_id="COMP-200",
        priority_score=78.5,
        priority_level=MaintenancePriorityLevel.HIGH,
        evidence=PrioritySignalEvidence(failure_probability=0.75, safety_risk=SafetyRiskLevel.HIGH),
        reasons=["High failure risk", "High safety risk"],
        missing_evidence_notices=["Image damage severity unavailable"],
        requires_government_review=True,
        model_version="v1",
    )

    pipeline = RoadXPipeline(
        failure_predictor=failure_pred,
        damage_detector=damage_det,
        severity_predictor=sev_pred,
        complaint_analyzer=complaint_ana,
        duplicate_detector=dup_det,
        time_to_failure_predictor=ttf_pred,
        priority_engine=pri_eng,
        auto_load=False,
    )
    return pipeline


def test_pipeline_partial_execution_complaint_only():
    pipeline = create_mock_pipeline()

    input_payload = {
        "road_segment_id": "SEG-100",
        "complaint_id": "COMP-200",
        "complaint_text": "Deep pothole causing accidents near bus stand.",
    }

    result = pipeline.run(input_payload)

    assert result.overall_status == "SUCCESS"
    assert result.road_segment_id == "SEG-100"
    assert result.complaint_id == "COMP-200"
    assert result.complaint_analysis is not None
    assert result.complaint_analysis.issue_category == IssueCategory.POTHOLE
    assert result.maintenance_priority is not None
    assert result.maintenance_priority.priority_level == MaintenancePriorityLevel.HIGH

    # Verification of skipped stages
    assert result.stage_summaries["failure_prediction"].status == PipelineStageStatus.SKIPPED
    assert result.stage_summaries["damage_detection"].status == PipelineStageStatus.SKIPPED
    assert result.stage_summaries["severity"].status == PipelineStageStatus.UNAVAILABLE
    assert result.stage_summaries["complaint_intelligence"].status == PipelineStageStatus.SUCCESS


def test_pipeline_stage_override():
    pipeline = create_mock_pipeline()

    input_payload = {
        "complaint_text": "Road surface cracking.",
        "enabled_stages": {"complaint_intelligence": False},
    }

    result = pipeline.run(input_payload)
    assert result.stage_summaries["complaint_intelligence"].status == PipelineStageStatus.SKIPPED
    assert result.complaint_analysis is None


def test_pipeline_invalid_input_validation():
    pipeline = create_mock_pipeline()

    # Invalid latitude
    invalid_payload = {
        "road_data": {"latitude": 120.0, "longitude": 80.0, "pavement_age_years": 5.0}
    }

    with pytest.raises(RoadXDataError, match="Latitude out of valid range"):
        pipeline.run(invalid_payload)
