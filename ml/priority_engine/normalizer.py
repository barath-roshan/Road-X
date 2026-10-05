"""Signal normalizer scaling multi-source ML outputs to uniform 0.0 - 100.0 risk scores."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from ml.priority_engine.schemas import (
    MaintenancePriorityInput,
    PrioritySignalEvidence,
)
from ml.complaint_intelligence.schemas import SafetyRiskLevel, UrgencyLevel


class PriorityNormalizer:
    """Normalizes heterogeneous ML module outputs (probabilities, scores, days, complaint counts)

    into calibrated 0.0 - 100.0 risk feature scores.
    """

    def extract_evidence(self, input_data: MaintenancePriorityInput) -> PrioritySignalEvidence:
        """Extract evidence signal values from input schema."""
        fail_prob: Optional[float] = None
        fail_level: Optional[str] = None
        if input_data.failure_prediction is not None:
            fail_prob = input_data.failure_prediction.failure_probability
            fail_level = str(input_data.failure_prediction.risk_level.value)

        sev_score: Optional[float] = None
        sev_level: Optional[str] = None
        if input_data.severity_prediction is not None:
            sev_score = input_data.severity_prediction.severity_score
            sev_level = str(input_data.severity_prediction.severity_level.value)

        safety_risk: Optional[SafetyRiskLevel] = None
        urgency: Optional[UrgencyLevel] = None
        issue_cat: Optional[Any] = None
        if input_data.complaint_analysis is not None:
            safety_risk = input_data.complaint_analysis.safety_risk
            urgency = input_data.complaint_analysis.urgency
            issue_cat = input_data.complaint_analysis.issue_category

        related_count: Optional[int] = None
        if input_data.duplicate_detection is not None:
            related_count = len(input_data.duplicate_detection.possible_duplicate_grievance_ids)

        ttf_days: Optional[float] = None
        surv_30d: Optional[float] = None
        if input_data.time_to_failure is not None:
            ttf_days = input_data.time_to_failure.estimated_time_to_failure_days
            surv_30d = input_data.time_to_failure.survival_probabilities.day_30

        return PrioritySignalEvidence(
            failure_probability=fail_prob,
            failure_risk_level=fail_level,
            severity_score=sev_score,
            severity_level=sev_level,
            safety_risk=safety_risk,
            urgency=urgency,
            issue_category=issue_cat,
            related_complaint_count=related_count,
            estimated_time_to_failure_days=ttf_days,
            survival_probability_30d=surv_30d,
            traffic_volume=input_data.traffic_volume,
        )

    def normalize_signals(
        self, evidence: PrioritySignalEvidence
    ) -> Tuple[Dict[str, float], List[str]]:
        """Normalize available evidence signals into [0.0, 100.0] scores and compile missing notices.

        Returns:
            Tuple of (normalized_scores_dict, missing_notices_list).
        """
        scores: Dict[str, float] = {}
        missing_notices: List[str] = []

        # 1. Failure Risk Normalization
        if evidence.failure_probability is not None:
            scores["failure_risk"] = float(evidence.failure_probability * 100.0)
        elif evidence.failure_risk_level:
            level = str(evidence.failure_risk_level).upper()
            mapping = {"CRITICAL": 95.0, "HIGH": 75.0, "MEDIUM": 45.0, "LOW": 15.0}
            scores["failure_risk"] = mapping.get(level, 30.0)
        else:
            missing_notices.append("Phase 2 Road Failure Risk prediction was unavailable.")

        # 2. Damage Severity Normalization
        if evidence.severity_score is not None:
            scores["severity"] = float(max(0.0, min(100.0, evidence.severity_score)))
        elif evidence.severity_level:
            level = str(evidence.severity_level).upper()
            mapping = {"CRITICAL": 95.0, "HIGH": 75.0, "MEDIUM": 45.0, "LOW": 15.0}
            scores["severity"] = mapping.get(level, 30.0)
        else:
            missing_notices.append("Phase 4 Visual Damage Severity estimation was unavailable.")

        # 3. Public Safety Risk Normalization
        if evidence.safety_risk is not None:
            level = str(evidence.safety_risk.value).upper()
            mapping = {"HIGH": 90.0, "MEDIUM": 50.0, "LOW": 10.0}
            scores["safety_risk"] = mapping.get(level, 30.0)
        else:
            missing_notices.append("Phase 5 Public Safety Risk classification was unavailable.")

        # 4. Complaint Urgency Normalization
        if evidence.urgency is not None:
            level = str(evidence.urgency.value).upper()
            mapping = {"CRITICAL": 100.0, "HIGH": 75.0, "MEDIUM": 45.0, "LOW": 15.0}
            scores["urgency"] = mapping.get(level, 30.0)
        else:
            missing_notices.append("Phase 5 Complaint Response Urgency classification was unavailable.")

        # 5. Time-to-Failure Normalization
        if evidence.estimated_time_to_failure_days is not None:
            days = float(max(0.0, evidence.estimated_time_to_failure_days))
            # Exponential decay: 0 days -> 100.0 score, 60 days -> 36.8 score, 180 days -> 5.0 score
            scores["time_to_failure"] = float(100.0 * math.exp(-days / 60.0))
        else:
            missing_notices.append("Phase 7 Time-to-Failure remaining life prediction was unavailable.")

        # 6. Related Complaint Volume Normalization
        if evidence.related_complaint_count is not None and evidence.related_complaint_count > 0:
            count = evidence.related_complaint_count
            # Logarithmic scaling: 1 complaint -> 17.3, 5 -> 44.8, 10 -> 59.9
            scores["complaint_volume"] = float(min(100.0, 25.0 * math.log(1.0 + count)))
        else:
            missing_notices.append("Phase 6 Related Duplicate Complaint count was unavailable.")

        return scores, missing_notices
