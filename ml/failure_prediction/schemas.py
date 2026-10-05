"""Input and output validation schemas for road failure prediction (Phase 2)."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class FailureRiskLevel(str, Enum):
    """Categorical risk tiers for predicted road failure."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RoadFailureInput(BaseModel):
    """Pydantic schema representing the operational features of a road segment at observation time."""

    segment_id: Optional[str] = Field(default="SEG-UNKNOWN", description="Road segment identifier")
    observation_date: Optional[str] = Field(default=None, description="Observation date (YYYY-MM-DD)")
    road_age_years: float = Field(ge=0.0, description="Age of road segment since construction/repaving in years")
    road_length_m: float = Field(gt=0.0, description="Length of road segment in meters")
    lane_count: int = Field(ge=1, description="Number of traffic lanes")
    road_quality_score: float = Field(ge=0.0, le=1.0, description="Pavement quality index (1.0 = perfect, 0.0 = failed)")
    traffic_volume: float = Field(ge=0.0, description="Average daily vehicles")
    heavy_vehicle_ratio: float = Field(ge=0.0, le=1.0, description="Proportion of heavy commercial vehicles/trucks")
    average_speed_kmph: float = Field(ge=0.0, description="Average recorded vehicular speed in km/h")
    rainfall_7d_mm: float = Field(ge=0.0, description="Precipitation accumulated over previous 7 days in mm")
    rainfall_30d_mm: float = Field(ge=0.0, description="Precipitation accumulated over previous 30 days in mm")
    temperature_avg_c: float = Field(description="Average ambient temperature in Celsius")
    flood_events_30d: int = Field(ge=0, description="Number of waterlogging/flood events in last 30 days")
    days_since_repair: float = Field(ge=0.0, description="Elapsed days since most recent maintenance or repair")
    previous_repairs: int = Field(ge=0, description="Total historical repairs logged for segment")
    previous_failures: int = Field(ge=0, description="Total historical critical failures logged for segment")
    citizen_complaints_30d: int = Field(ge=0, description="Citizen complaints received for this segment in last 30 days")
    pothole_count: int = Field(ge=0, description="Detected or reported pothole count")
    crack_ratio: float = Field(ge=0.0, le=1.0, description="Fraction of road surface with visible cracks")

    @field_validator("rainfall_30d_mm")
    @classmethod
    def validate_rainfall_consistency(cls, v: float, info) -> float:
        """Ensure 30d rainfall is not less than 7d rainfall when both are present."""
        rainfall_7d = info.data.get("rainfall_7d_mm")
        if rainfall_7d is not None and v < rainfall_7d:
            # Allow minor measurement variances but warn or clamp if physically inconsistent
            return max(v, rainfall_7d)
        return v


class FailurePredictionOutput(BaseModel):
    """Schema representing prediction result for road failure risk within next 30 days."""

    failure_probability: float = Field(ge=0.0, le=1.0, description="Calibrated failure probability (0.0 - 1.0)")
    risk_level: FailureRiskLevel = Field(description="Assigned administrative risk tier")
    model_version: str = Field(description="Model artifact version")
    top_contributing_factors: List[str] = Field(default_factory=list, description="Primary feature contributors to risk")


# Backward compatibility aliases
RoadGrievanceInput = RoadFailureInput
RoadFailurePredictionResponse = FailurePredictionOutput
