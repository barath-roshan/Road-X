"""Unit tests for PriorityNormalizer signal extraction and score scaling."""

from ml.priority_engine.normalizer import PriorityNormalizer
from ml.priority_engine.schemas import MaintenancePriorityInput
from ml.failure_prediction.schemas import FailurePredictionOutput, FailureRiskLevel
from ml.severity.schemas import SeverityPredictionOutput, DamageSeverityLevel


def test_normalizer_extraction_and_scaling():
    normalizer = PriorityNormalizer()
    inp = MaintenancePriorityInput(
        road_segment_id="SEG-100",
        failure_prediction=FailurePredictionOutput(
            failure_probability=0.85,
            risk_level=FailureRiskLevel.HIGH,
            model_version="v1",
        ),
        severity_prediction=SeverityPredictionOutput(
            severity_score=75.0,
            severity_level=DamageSeverityLevel.HIGH,
            model_version="v1",
        ),
    )

    evidence = normalizer.extract_evidence(inp)
    assert evidence.failure_probability == 0.85
    assert evidence.severity_score == 75.0

    scores, missing = normalizer.normalize_signals(evidence)
    assert scores["failure_risk"] == 85.0
    assert scores["severity"] == 75.0
    assert len(missing) > 0  # Notices for missing signals
