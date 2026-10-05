"""Input and output validation schemas for Damage Severity Estimation (Phase 4)."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class DamageSeverityLevel(str, Enum):
    """Categorical presentation levels for estimated road damage severity."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RoadContextInput(BaseModel):
    """Optional road infrastructure context provided alongside vision detection results."""

    road_quality_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Pavement quality index (1.0 = perfect, 0.0 = failed)"
    )
    traffic_volume: Optional[float] = Field(
        default=None, ge=0.0, description="Average daily vehicle volume"
    )
    heavy_vehicle_ratio: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Proportion of commercial heavy vehicles"
    )
    road_age_years: Optional[float] = Field(
        default=None, ge=0.0, description="Pavement age in years"
    )
    citizen_complaints_30d: Optional[int] = Field(
        default=None, ge=0, description="Citizen complaints logged for road segment in last 30 days"
    )


class SeverityPredictionOutput(BaseModel):
    """Schema representing estimated damage severity for a reported road defect or image."""

    severity_score: float = Field(
        ge=0.0, le=100.0, description="Continuous estimated severity score (0.0 = minimal, 100.0 = catastrophic)"
    )
    severity_level: DamageSeverityLevel = Field(
        description="Categorical severity presentation level (LOW, MEDIUM, HIGH, CRITICAL)"
    )
    contributing_factors: List[str] = Field(
        default_factory=list, description="Primary feature drivers contributing to estimated severity"
    )
    model_version: str = Field(default="v1", description="Severity model version identifier")

    @field_validator("severity_score")
    @classmethod
    def round_score(cls, v: float) -> float:
        """Round score to 1 decimal place bounded in [0.0, 100.0]."""
        return round(float(max(0.0, min(100.0, v))), 1)


# Backward compatibility alias
DamageSeverityResponse = SeverityPredictionOutput
