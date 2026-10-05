"""Human-readable explanation generator compiling evidence justifications for government officers."""

from __future__ import annotations

from typing import List, Dict, Optional

from ml.priority_engine.schemas import PrioritySignalEvidence
from ml.complaint_intelligence.schemas import SafetyRiskLevel, UrgencyLevel


class PriorityExplainer:
    """Generates transparent, human-readable supporting evidence bullet points and missing signal disclosures."""

    def generate_explanations(
        self,
        evidence: PrioritySignalEvidence,
        guardrail_triggers: Optional[List[str]] = None,
    ) -> List[str]:
        """Generate human-readable reason bullet points strictly grounded in input evidence."""
        reasons: List[str] = []

        # 1. Failure Prediction Evidence
        if evidence.failure_probability is not None and evidence.failure_probability >= 0.60:
            reasons.append(
                f"High predicted road failure risk ({evidence.failure_probability * 100.0:.1f}% failure probability within 30 days)."
            )
        elif evidence.failure_risk_level in ("HIGH", "CRITICAL"):
            reasons.append(f"Elevated road failure risk level ({evidence.failure_risk_level}).")

        # 2. Damage Severity Evidence
        if evidence.severity_score is not None and evidence.severity_score >= 60.0:
            reasons.append(
                f"Severe physical pavement damage detected (Severity Score: {evidence.severity_score:.1f}/100)."
            )
        elif evidence.severity_level in ("HIGH", "CRITICAL"):
            reasons.append(f"High physical defect severity level ({evidence.severity_level}).")

        # 3. Public Safety Risk Evidence
        if evidence.safety_risk == SafetyRiskLevel.HIGH:
            reasons.append("High public safety hazard risk identified in citizen complaint report.")

        # 4. Citizen Complaint Urgency Evidence
        if evidence.urgency in (UrgencyLevel.HIGH, UrgencyLevel.CRITICAL):
            reasons.append(
                f"High citizen grievance response urgency ({evidence.urgency.value})."
            )

        # 5. Time-to-Failure Horizon Evidence
        if evidence.estimated_time_to_failure_days is not None and evidence.estimated_time_to_failure_days <= 60.0:
            reasons.append(
                f"Short remaining operational lifespan before structural failure ({evidence.estimated_time_to_failure_days:.1f} days remaining)."
            )

        # 6. Related Duplicate Complaint Volume Evidence
        if evidence.related_complaint_count is not None and evidence.related_complaint_count >= 2:
            reasons.append(
                f"Multiple duplicate citizen reports logged addressing this issue ({evidence.related_complaint_count} related complaints)."
            )

        # 7. Include Guardrail Triggers if any
        if guardrail_triggers:
            reasons.extend(guardrail_triggers)

        # Default fallback explanation if score is low
        if not reasons:
            reasons.append("Routine maintenance inspection recommended based on operational telemetry.")

        return reasons
