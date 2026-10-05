"""Pydantic schemas and enums for Complaint Intelligence (Phase 5)."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class IssueCategory(str, Enum):
    """Categorical classification of road grievance issues."""

    POTHOLE = "POTHOLE"
    ROAD_CRACK = "ROAD_CRACK"
    ROAD_SURFACE_DAMAGE = "ROAD_SURFACE_DAMAGE"
    WATERLOGGING = "WATERLOGGING"
    FLOODING = "FLOODING"
    STREETLIGHT = "STREETLIGHT"
    ACCIDENT = "ACCIDENT"
    ROAD_OBSTRUCTION = "ROAD_OBSTRUCTION"
    DEBRIS = "DEBRIS"
    TRAFFIC_SIGNAL = "TRAFFIC_SIGNAL"
    ROAD_CLOSURE = "ROAD_CLOSURE"
    OTHER = "OTHER"


class UrgencyLevel(str, Enum):
    """Urgency tier for prioritizing citizen grievance response."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SafetyRiskLevel(str, Enum):
    """Estimated safety hazard level posed by reported grievance."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class LocationEntityType(str, Enum):
    """Entity categorization for extracted location references."""

    ROAD = "ROAD"
    LANDMARK = "LANDMARK"
    AREA = "AREA"
    LOCALITY = "LOCALITY"
    BUS_STOP = "BUS_STOP"
    INTERSECTION = "INTERSECTION"


class LocationMention(BaseModel):
    """Extracted text location entity reference from grievance report."""

    text: str = Field(description="Extracted location text snippet")
    type: LocationEntityType = Field(description="Categorical entity type")
    start_idx: Optional[int] = Field(default=None, description="Start char index in text")
    end_idx: Optional[int] = Field(default=None, description="End char index in text")


class ComplaintAnalysisRequest(BaseModel):
    """Input payload for natural language citizen complaint analysis."""

    text: str = Field(min_length=1, description="Raw citizen grievance text description")

    @field_validator("text")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Ensure input text is non-empty after stripping whitespace."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Complaint text cannot be empty or whitespace only.")
        return v


class ComplaintAnalysisResponse(BaseModel):
    """Structured response object containing extracted grievance insights."""

    issue_category: IssueCategory = Field(description="Predicted primary issue category")
    issue_confidence: float = Field(
        ge=0.0, le=1.0, description="Model prediction confidence score for issue category"
    )

    urgency: UrgencyLevel = Field(description="Predicted grievance response urgency level")
    urgency_confidence: float = Field(
        ge=0.0, le=1.0, description="Model prediction confidence score for urgency"
    )

    safety_risk: SafetyRiskLevel = Field(description="Predicted potential safety hazard level")
    safety_confidence: float = Field(
        ge=0.0, le=1.0, description="Model prediction confidence score for safety risk"
    )

    location_mentions: List[LocationMention] = Field(
        default_factory=list, description="Extracted geographic location entity mentions"
    )

    embedding_available: bool = Field(
        default=True, description="Flag indicating whether semantic vector embedding was generated"
    )
    model_version: str = Field(default="v1", description="Complaint intelligence model version identifier")

    @field_validator("issue_confidence", "urgency_confidence", "safety_confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        """Ensure confidence values are rounded to 4 decimal places bounded in [0.0, 1.0]."""
        return round(float(max(0.0, min(1.0, v))), 4)
