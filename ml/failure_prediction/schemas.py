"""Input and output validation schemas for road failure prediction."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FailureRiskLevel(str, Enum):
    """Categorical risk tiers for predicted road failure."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RoadGrievanceInput(BaseModel):
    """Schema representing citizen grievance and infrastructure context for failure prediction."""

    complaint_id: str = Field(description="Unique identifier of citizen road grievance")
    latitude: float = Field(description="Geographic latitude coordinate")
    longitude: float = Field(description="Geographic longitude coordinate")
    road_type: str = Field(default="arterial", description="Classification of road (e.g. arterial, highway, local)")
    surface_type: str = Field(default="asphalt", description="Pavement surface type (e.g. asphalt, concrete)")
    reported_damage_type: str = Field(description="Reported issue type (pothole, crack, flooding, accident, etc.)")
    estimated_depth_cm: Optional[float] = Field(default=None, description="Reported or detected depth in centimeters")
    estimated_area_sqm: Optional[float] = Field(default=None, description="Reported or detected area in square meters")
    traffic_volume_estimate: Optional[str] = Field(default="medium", description="Low, medium, high traffic density")
    rainfall_recent_mm: Optional[float] = Field(default=0.0, description="Recent cumulative rainfall in millimeters")
    road_age_years: Optional[float] = Field(default=None, description="Estimated years since last repaving/construction")


class FailurePredictionOutput(BaseModel):
    """Schema representing prediction result for road failure risk."""

    complaint_id: str = Field(description="Associated complaint identifier")
    failure_probability: float = Field(ge=0.0, le=1.0, description="Estimated probability of imminent road failure")
    risk_level: FailureRiskLevel = Field(description="Assigned categorical risk level")
    top_contributing_factors: List[str] = Field(default_factory=list, description="Primary drivers of failure risk")
    model_version: str = Field(description="Version of failure prediction model used")
