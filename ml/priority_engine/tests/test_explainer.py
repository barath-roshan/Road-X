"""Unit tests for PriorityExplainer evidence reasoning output."""

from ml.priority_engine.explainer import PriorityExplainer
from ml.priority_engine.schemas import PrioritySignalEvidence
from ml.complaint_intelligence.schemas import SafetyRiskLevel, UrgencyLevel


def test_explainer_generates_grounded_reasons():
    explainer = PriorityExplainer()
    evidence = PrioritySignalEvidence(
        failure_probability=0.85,
        severity_score=80.0,
        safety_risk=SafetyRiskLevel.HIGH,
        urgency=UrgencyLevel.HIGH,
        related_complaint_count=3,
        estimated_time_to_failure_days=25.0,
    )

    reasons = explainer.generate_explanations(evidence)

    assert len(reasons) >= 4
    assert any("failure risk" in r.lower() or "failure probability" in r.lower() for r in reasons)
    assert any("severity" in r.lower() for r in reasons)
    assert any("safety" in r.lower() for r in reasons)
    assert any("lifespan" in r.lower() or "remaining" in r.lower() for r in reasons)
