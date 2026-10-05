"""Safety-First rule engine enforcing mandatory administrative priority guardrails."""

from __future__ import annotations

from typing import Tuple, List

from ml.priority_engine.config import config
from ml.priority_engine.schemas import (
    MaintenancePriorityLevel,
    PrioritySignalEvidence,
)
from ml.complaint_intelligence.schemas import SafetyRiskLevel, UrgencyLevel


class PriorityRuleEngine:
    """Enforces safety guardrail rules to prevent critical hazards or imminent failure threats

    from being diluted by low average scoring.
    """

    def apply_guardrails(
        self,
        raw_score: float,
        assigned_level: MaintenancePriorityLevel,
        evidence: PrioritySignalEvidence,
    ) -> Tuple[float, MaintenancePriorityLevel, List[str]]:
        """Apply safety-first guardrail rules to raw score and assigned priority level.

        Returns:
            Tuple of (adjusted_score, adjusted_level, guardrail_triggers_list).
        """
        if not config.enable_safety_guardrails:
            return raw_score, assigned_level, []

        adjusted_score = raw_score
        adjusted_level = assigned_level
        triggers: List[str] = []

        # 1. Critical Damage Severity or Critical Failure Risk Guardrail
        is_critical_severity = (
            evidence.severity_level and str(evidence.severity_level).upper() == "CRITICAL"
        )
        is_critical_failure = (
            evidence.failure_risk_level and str(evidence.failure_risk_level).upper() == "CRITICAL"
        )
        if is_critical_severity or is_critical_failure:
            if adjusted_score < config.score_thresholds["CRITICAL_MIN_SCORE"]:
                adjusted_score = max(adjusted_score, config.score_thresholds["CRITICAL_MIN_SCORE"])
            adjusted_level = MaintenancePriorityLevel.CRITICAL
            triggers.append(
                "Safety Guardrail Triggered: Critical damage severity or structural failure risk enforces CRITICAL priority."
            )

        # 2. Critical Complaint Response Urgency Guardrail
        if evidence.urgency == UrgencyLevel.CRITICAL:
            if adjusted_score < 75.0:
                adjusted_score = max(adjusted_score, 75.0)
            if adjusted_level in (MaintenancePriorityLevel.LOW, MaintenancePriorityLevel.MEDIUM):
                adjusted_level = MaintenancePriorityLevel.HIGH
            triggers.append(
                "Safety Guardrail Triggered: Critical citizen complaint urgency enforces minimum HIGH priority."
            )

        # 3. High Public Safety Risk Guardrail
        if evidence.safety_risk == SafetyRiskLevel.HIGH:
            if adjusted_score < config.guardrail_min_high_score:
                adjusted_score = max(adjusted_score, config.guardrail_min_high_score)
            if adjusted_level in (MaintenancePriorityLevel.LOW, MaintenancePriorityLevel.MEDIUM):
                adjusted_level = MaintenancePriorityLevel.HIGH
            triggers.append(
                "Safety Guardrail Triggered: High public safety hazard risk enforces minimum HIGH priority."
            )

        # 4. Imminent Time-to-Failure Window Guardrail (< 14 days remaining)
        if (
            evidence.estimated_time_to_failure_days is not None
            and evidence.estimated_time_to_failure_days <= config.time_to_failure_critical_window_days
        ):
            if adjusted_score < 70.0:
                adjusted_score = max(adjusted_score, 70.0)
            if adjusted_level in (MaintenancePriorityLevel.LOW, MaintenancePriorityLevel.MEDIUM):
                adjusted_level = MaintenancePriorityLevel.HIGH
            triggers.append(
                f"Safety Guardrail Triggered: Imminent time-to-failure window ({evidence.estimated_time_to_failure_days:.1f} days remaining) enforces minimum HIGH priority."
            )

        return float(adjusted_score), adjusted_level, triggers
