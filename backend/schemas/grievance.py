"""Pydantic schemas for Citizen Grievance entities."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.models.grievance import GrievanceStatus
from backend.schemas.evidence import EvidenceRead
from backend.schemas.ml_analysis import MLAnalysisRead


class GrievanceBase(BaseModel):
    """Base fields for Grievance payload."""

    issue_category: str = Field(
        min_length=1, max_length=50, description="Category of reported defect (e.g. POTHOLE, CRACK)"
    )
    description: str = Field(min_length=1, description="Natural language citizen issue description")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Incident latitude")
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Incident longitude")

    @field_validator("description", "issue_category")
    @classmethod
    def clean_text(cls, v: str) -> str:
        """Strip whitespace and enforce non-empty string."""
        stripped = str(v).strip()
        if not stripped:
            raise ValueError("String field cannot be empty or whitespace only.")
        return stripped


class GrievanceCreate(GrievanceBase):
    """Request schema for creating a grievance report."""

    citizen_id: Optional[str] = Field(default=None, description="Optional associated user UUID")
    road_id: Optional[str] = Field(default=None, description="Optional associated road segment UUID")
    road_segment_id: Optional[str] = Field(
        default=None, description="Optional road segment_id string (e.g. SEG-MH-4001) for lookup"
    )


class GrievanceUpdate(BaseModel):
    """Request schema for updating grievance status or details."""

    issue_category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, min_length=1)
    status: Optional[GrievanceStatus] = Field(default=None, description="Updated lifecycle status")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)


class GrievanceRead(GrievanceBase):
    """Response schema for Grievance entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique UUID identifier for grievance report")
    citizen_id: Optional[str] = Field(default=None, description="Citizen user ID")
    road_id: Optional[str] = Field(default=None, description="Road segment database ID")
    status: GrievanceStatus = Field(description="Current grievance lifecycle status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    evidence_items: List[EvidenceRead] = Field(default_factory=list, description="Attached evidence metadata")
    ml_analyses: List[MLAnalysisRead] = Field(default_factory=list, description="Stored ML analysis results")
