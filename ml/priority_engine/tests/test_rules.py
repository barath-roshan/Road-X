"""Unit tests for PriorityRuleEngine safety guardrail rules."""

from ml.priority_engine.rules import PriorityRuleEngine
from ml.priority_engine.schemas import (
    MaintenancePriorityLevel,
    PrioritySignalEvidence,
)
from ml.complaint_intelligence.schemas import SafetyRiskLevel, UrgencyLevel


def test_rule_engine_high_safety_guardrail():
    rule_engine = PriorityRuleEngine()

    evidence_safety = PrioritySignalEvidence(safety_risk=SafetyRiskLevel.HIGH)
    adj_score, adj_level, triggers = rule_engine.apply_guardrails(
        raw_score=30.0, assigned_level=MaintenancePriorityLevel.LOW, evidence=evidence_safety
    )

    assert adj_score >= 65.0
    assert adj_level in (MaintenancePriorityLevel.HIGH, MaintenancePriorityLevel.CRITICAL)
    assert len(triggers) >= 1


def test_rule_engine_critical_urgency_guardrail():
    rule_engine = PriorityRuleEngine()

    evidence_urgency = PrioritySignalEvidence(urgency=UrgencyLevel.CRITICAL)
    adj_score, adj_level, triggers = rule_engine.apply_guardrails(
        raw_score=40.0, assigned_level=MaintenancePriorityLevel.MEDIUM, evidence=evidence_urgency
    )

    assert adj_score >= 75.0
    assert adj_level in (MaintenancePriorityLevel.HIGH, MaintenancePriorityLevel.CRITICAL)
    assert len(triggers) >= 1


def test_rule_engine_short_ttf_window_guardrail():
    rule_engine = PriorityRuleEngine()

    evidence_ttf = PrioritySignalEvidence(estimated_time_to_failure_days=10.0)
    adj_score, adj_level, triggers = rule_engine.apply_guardrails(
        raw_score=25.0, assigned_level=MaintenancePriorityLevel.LOW, evidence=evidence_ttf
    )

    assert adj_score >= 70.0
    assert adj_level in (MaintenancePriorityLevel.HIGH, MaintenancePriorityLevel.CRITICAL)
    assert len(triggers) >= 1
