"""Unit and integration tests for MaintenancePriorityEngine pipeline."""

import pytest
from pydantic import ValidationError
from ml.priority_engine.engine import MaintenancePriorityEngine
from ml.priority_engine.schemas import (
    MaintenancePriorityInput,
    MaintenancePriorityOutput,
    MaintenancePriorityLevel,
)
from ml.failure_prediction.schemas import FailurePredictionOutput, FailureRiskLevel
from ml.severity.schemas import SeverityPredictionOutput, DamageSeverityLevel
from ml.complaint_intelligence.schemas import (
    ComplaintAnalysisResponse,
    IssueCategory,
    UrgencyLevel,
    SafetyRiskLevel,
)
from ml.time_to_failure.schemas import (
    TimeToFailureOutput,
    ConfidenceIntervalDays,
    SurvivalProbabilities,
    TimeToFailureRiskLevel,
)


def test_engine_high_failure_risk_increases_priority():
    engine = MaintenancePriorityEngine()

    inp_low = MaintenancePriorityInput(
        failure_prediction=FailurePredictionOutput(
            failure_probability=0.20, risk_level=FailureRiskLevel.LOW, model_version="v1"
        )
    )
    inp_high = MaintenancePriorityInput(
        failure_prediction=FailurePredictionOutput(
            failure_probability=0.85, risk_level=FailureRiskLevel.HIGH, model_version="v1"
        )
    )

    out_low = engine.prioritize(inp_low)
    out_high = engine.prioritize(inp_high)

    assert out_high.priority_score > out_low.priority_score


def test_engine_high_severity_increases_priority():
    engine = MaintenancePriorityEngine()

    inp_low = MaintenancePriorityInput(
        severity_prediction=SeverityPredictionOutput(
            severity_score=20.0, severity_level=DamageSeverityLevel.LOW, model_version="v1"
        )
    )
    inp_high = MaintenancePriorityInput(
        severity_prediction=SeverityPredictionOutput(
            severity_score=90.0, severity_level=DamageSeverityLevel.CRITICAL, model_version="v1"
        )
    )

    out_low = engine.prioritize(inp_low)
    out_high = engine.prioritize(inp_high)

    assert out_high.priority_score > out_low.priority_score


def test_engine_short_time_to_failure_increases_urgency():
    engine = MaintenancePriorityEngine()

    inp = MaintenancePriorityInput(
        time_to_failure=TimeToFailureOutput(
            segment_id="SEG-10",
            estimated_time_to_failure_days=10.0,
            confidence_interval_days=ConfidenceIntervalDays(lower_bound=8.0, upper_bound=12.0),
            survival_probabilities=SurvivalProbabilities(
                day_30=0.2, day_90=0.05, day_180=0.01, day_365=0.0
            ),
            risk_level=TimeToFailureRiskLevel.CRITICAL,
            model_version="v1",
        )
    )

    out = engine.prioritize(inp)
    assert out.priority_level in (MaintenancePriorityLevel.HIGH, MaintenancePriorityLevel.CRITICAL)


def test_engine_missing_signals_handling():
    engine = MaintenancePriorityEngine()
    # Test completely empty input: should run safely without raising exceptions
    inp_empty = MaintenancePriorityInput()
    out = engine.prioritize(inp_empty)

    assert isinstance(out, MaintenancePriorityOutput)
    assert out.priority_level == MaintenancePriorityLevel.LOW
    assert len(out.missing_evidence_notices) > 0


def test_engine_determinism():
    engine = MaintenancePriorityEngine()
    inp = MaintenancePriorityInput(
        road_segment_id="SEG-42",
        failure_prediction=FailurePredictionOutput(
            failure_probability=0.65, risk_level=FailureRiskLevel.HIGH, model_version="v1"
        ),
    )

    out1 = engine.prioritize(inp)
    out2 = engine.prioritize(inp)

    assert out1.priority_score == out2.priority_score
    assert out1.priority_level == out2.priority_level
    assert out1.reasons == out2.reasons


def test_engine_invalid_probability_rejection():
    # Negative probability should be rejected by Pydantic schema validation
    with pytest.raises(ValidationError):
        FailurePredictionOutput(
            failure_probability=-0.5, risk_level=FailureRiskLevel.LOW, model_version="v1"
        )
