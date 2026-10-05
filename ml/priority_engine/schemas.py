"""Pydantic request/response schemas and enums for Maintenance Priority Engine (Phase 8)."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator

from ml.failure_prediction.schemas import FailurePredictionOutput
from ml.severity.schemas import SeverityPredictionOutput
from ml.complaint_intelligence.schemas import (
    ComplaintAnalysisResponse,
    IssueCategory,
    UrgencyLevel,
    SafetyRiskLevel,
)
from ml.duplicate_detection.schemas import DuplicateDetectionResponse
from ml.time_to_failure.schemas import TimeToFailureOutput


class MaintenancePriorityLevel(str, Enum):
    """Categorical maintenance priority level assigned for government officer review."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PrioritySignalEvidence(BaseModel):
    """Granular evidence breakdown compiled from individual ML module outputs."""

    failure_probability: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Predicted road failure probability (Phase 2)"
    )
    failure_risk_level: Optional[str] = Field(
        default=None, description="Assigned failure risk tier (Phase 2)"
    )
    severity_score: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Estimated damage severity score (Phase 4)"
    )
    severity_level: Optional[str] = Field(
        default=None, description="Assigned damage severity level (Phase 4)"
    )
    safety_risk: Optional[SafetyRiskLevel] = Field(
        default=None, description="Predicted public safety risk level (Phase 5)"
    )
    urgency: Optional[UrgencyLevel] = Field(
        default=None, description="Predicted citizen complaint response urgency (Phase 5)"
    )
    issue_category: Optional[IssueCategory] = Field(
        default=None, description="Predicted primary grievance issue category (Phase 5)"
    )
    related_complaint_count: Optional[int] = Field(
        default=None, ge=0, description="Number of related duplicate citizen reports (Phase 6)"
    )
    estimated_time_to_failure_days: Optional[float] = Field(
        default=None, ge=0.0, description="Estimated remaining operational days before failure (Phase 7)"
    )
    survival_probability_30d: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="P(survives > 30 days) (Phase 7)"
    )
    traffic_volume: Optional[float] = Field(
        default=None, ge=0.0, description="Average daily traffic volume exposure"
    )


class MaintenancePriorityInput(BaseModel):
    """Input container for multi-signal maintenance prioritization."""

    road_segment_id: Optional[str] = Field(default="SEG-UNKNOWN", description="Road segment identifier")
    complaint_id: Optional[str] = Field(default="COMP-UNKNOWN", description="Citizen complaint identifier")

    failure_prediction: Optional[FailurePredictionOutput] = Field(
        default=None, description="Output from Phase 2 Failure Prediction"
    )
    severity_prediction: Optional[SeverityPredictionOutput] = Field(
        default=None, description="Output from Phase 4 Damage Severity Estimation"
    )
    complaint_analysis: Optional[ComplaintAnalysisResponse] = Field(
        default=None, description="Output from Phase 5 Complaint Intelligence"
    )
    duplicate_detection: Optional[DuplicateDetectionResponse] = Field(
        default=None, description="Output from Phase 6 Duplicate Detection"
    )
    time_to_failure: Optional[TimeToFailureOutput] = Field(
        default=None, description="Output from Phase 7 Time-to-Failure Prediction"
    )
    traffic_volume: Optional[float] = Field(
        default=None, ge=0.0, description="Optional traffic volume attribute"
    )


class MaintenancePriorityOutput(BaseModel):
    """Structured response object containing prioritized maintenance recommendation and evidence."""

    road_segment_id: str = Field(description="Target road segment identifier")
    complaint_id: str = Field(description="Target citizen complaint identifier")
    priority_score: float = Field(
        ge=0.0, le=100.0, description="Composite maintenance priority score (0.0 to 100.0)"
    )
    priority_level: MaintenancePriorityLevel = Field(
        description="Assigned administrative priority level (LOW, MEDIUM, HIGH, CRITICAL)"
    )
    evidence: PrioritySignalEvidence = Field(description="Granular signal evidence breakdown")
    reasons: List[str] = Field(
        default_factory=list, description="Human-readable supporting evidence bullet points"
    )
    missing_evidence_notices: List[str] = Field(
        default_factory=list, description="Disclosures for ML signals that were unavailable"
    )
    requires_government_review: bool = Field(
        default=True, description="Human-in-the-loop governance review requirement flag"
    )
    model_version: str = Field(default="v1", description="Priority engine model version identifier")
    disclaimer: str = Field(
        default=(
            "AI recommends maintenance priority for assisted government review. "
            "Final work order dispatch requires government officer approval."
        ),
        description="Government human-in-the-loop governance safeguard notice",
    )

    @field_validator("priority_score")
    @classmethod
    def round_score(cls, v: float) -> float:
        """Round priority score to 1 decimal place bounded in [0.0, 100.0]."""
        return round(float(max(0.0, min(100.0, v))), 1)
