"""Pydantic schemas for Citizen Platform operations."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.models.grievance import GrievanceStatus
from backend.schemas.evidence import EvidenceCreate, EvidenceRead


class CitizenGrievanceCreate(BaseModel):
    """Payload schema for citizen grievance submission."""

    issue_category: str = Field(
        default="POTHOLE",
        min_length=1,
        max_length=50,
        description="Category of reported defect (e.g. POTHOLE, WATERLOGGING)",
    )
    description: str = Field(
        min_length=5,
        max_length=2000,
        description="Natural language issue description provided by citizen",
    )
    latitude: float = Field(ge=-90.0, le=90.0, description="Incident latitude (-90 to +90)")
    longitude: float = Field(ge=-180.0, le=180.0, description="Incident longitude (-180 to +180)")
    road_id: Optional[str] = Field(default=None, description="Optional database road segment ID")
    road_segment_id: Optional[str] = Field(
        default=None, description="Optional road segment string identifier (e.g. SEG-BLR-101)"
    )
    evidence_items: Optional[List[EvidenceCreate]] = Field(
        default=None, description="Optional initial evidence file metadata items"
    )

    @field_validator("description", "issue_category")
    @classmethod
    def clean_text(cls, v: str) -> str:
        """Strip whitespace and enforce non-empty string."""
        stripped = str(v).strip()
        if not stripped:
            raise ValueError("Text field cannot be empty or whitespace only.")
        return stripped


class CitizenMLSummaryRead(BaseModel):
    """Citizen-safe high-level ML decision support summary."""

    model_config = ConfigDict(from_attributes=True)

    detected_issue: Optional[str] = Field(default=None, description="ML identified issue category")
    severity_level: Optional[str] = Field(default=None, description="Estimated severity level (e.g. HIGH)")
    risk_level: Optional[str] = Field(default=None, description="Road risk level (e.g. ELEVATED)")
    priority_level: Optional[str] = Field(default=None, description="Recommended maintenance priority")


class CitizenWorkProgressRead(BaseModel):
    """Citizen-safe work progress and repair status summary."""

    model_config = ConfigDict(from_attributes=True)

    work_order_id: Optional[str] = Field(default=None, description="Associated work order ID")
    status: Optional[str] = Field(default=None, description="Current work order status")
    progress_percentage: Optional[int] = Field(default=0, ge=0, le=100, description="Completion percentage (0-100)")
    last_updated_at: Optional[datetime] = Field(default=None, description="Timestamp of latest progress update")
    status_display: Optional[str] = Field(default=None, description="Citizen-friendly status message")


class CitizenRejectionInfoRead(BaseModel):
    """Information presented to citizen if repair completion was reverted for rework."""

    model_config = ConfigDict(from_attributes=True)

    is_reverted_for_rework: bool = Field(
        default=False, description="True if government audit requested contractor rework"
    )
    public_message: Optional[str] = Field(
        default=None, description="Citizen-friendly message regarding rework status"
    )


class CitizenTimelineItemRead(BaseModel):
    """Citizen-friendly chronological timeline event."""

    model_config = ConfigDict(from_attributes=True)

    event_type: str = Field(description="Internal event type name")
    status: Optional[str] = Field(default=None, description="Grievance status at event time")
    timestamp: datetime = Field(description="Timestamp of event")
    public_message: str = Field(description="Human-readable citizen-friendly progress description")


class CitizenGrievanceDetailsRead(BaseModel):
    """Complete citizen-safe view of a submitted grievance report."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique grievance UUID")
    citizen_id: str = Field(description="Citizen user ID")
    road_id: Optional[str] = Field(default=None, description="Road segment ID")
    road_name: Optional[str] = Field(default=None, description="Physical road segment name")
    issue_category: str = Field(description="Issue category classification")
    description: str = Field(description="Citizen grievance description")
    latitude: float = Field(description="Latitude coordinate")
    longitude: float = Field(description="Longitude coordinate")
    status: GrievanceStatus = Field(description="Current grievance lifecycle status")
    created_at: datetime = Field(description="Submission timestamp")
    updated_at: datetime = Field(description="Last updated timestamp")

    evidence_items: List[EvidenceRead] = Field(default_factory=list, description="Attached evidence metadata")
    ml_summary: Optional[CitizenMLSummaryRead] = Field(default=None, description="High-level ML analysis summary")
    work_progress: Optional[CitizenWorkProgressRead] = Field(default=None, description="Repair progress status")
    rejection_info: Optional[CitizenRejectionInfoRead] = Field(default=None, description="Rework status info")
    timeline: List[CitizenTimelineItemRead] = Field(default_factory=list, description="Citizen-safe timeline items")
