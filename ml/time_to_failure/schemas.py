"""Input and output Pydantic validation schemas for Time-to-Failure Prediction (Phase 7)."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from ml.failure_prediction.schemas import RoadFailureInput


class TimeToFailureRiskLevel(str, Enum):
    """Categorical risk level based on predicted remaining operational lifetime."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConfidenceIntervalDays(BaseModel):
    """Confidence interval bounds for predicted time-to-failure (in days)."""

    lower_bound: float = Field(ge=0.0, description="Lower bound (95% CI) of estimated days to failure")
    upper_bound: float = Field(ge=0.0, description="Upper bound (95% CI) of estimated days to failure")

    @field_validator("lower_bound", "upper_bound")
    @classmethod
    def round_bounds(cls, v: float) -> float:
        """Round confidence interval values to 1 decimal place."""
        return round(float(max(0.0, v)), 1)


class SurvivalProbabilities(BaseModel):
    """Predicted survival probabilities at standard forward operational horizons."""

    day_30: float = Field(ge=0.0, le=1.0, description="P(operational > 30 days)")
    day_90: float = Field(ge=0.0, le=1.0, description="P(operational > 90 days)")
    day_180: float = Field(ge=0.0, le=1.0, description="P(operational > 180 days)")
    day_365: float = Field(ge=0.0, le=1.0, description="P(operational > 365 days)")

    @field_validator("day_30", "day_90", "day_180", "day_365")
    @classmethod
    def round_probability(cls, v: float) -> float:
        """Round survival probabilities to 4 decimal places bounded in [0.0, 1.0]."""
        return round(float(max(0.0, min(1.0, v))), 4)


class TimeToFailureOutput(BaseModel):
    """Schema representing estimated remaining operational life and survival prognosis."""

    segment_id: str = Field(description="Road segment unique identifier")
    observation_date: Optional[str] = Field(default=None, description="Observation timestamp (YYYY-MM-DD)")
    estimated_time_to_failure_days: float = Field(
        ge=0.0, description="Estimated median remaining operational days before failure"
    )
    estimated_failure_date: Optional[str] = Field(
        default=None, description="Projected calendar date of structural failure (YYYY-MM-DD)"
    )
    confidence_interval_days: ConfidenceIntervalDays = Field(
        description="95% confidence interval for remaining operational days"
    )
    survival_probabilities: SurvivalProbabilities = Field(
        description="Survival probabilities across 30, 90, 180, and 365 day horizons"
    )
    risk_level: TimeToFailureRiskLevel = Field(description="Assigned municipal priority risk level")
    model_version: str = Field(default="v1", description="Time-to-failure model version identifier")
    top_contributing_risk_factors: List[str] = Field(
        default_factory=list, description="Primary feature drivers accelerating deterioration"
    )

    @field_validator("estimated_time_to_failure_days")
    @classmethod
    def round_days(cls, v: float) -> float:
        """Round estimated days to failure to 1 decimal place."""
        return round(float(max(0.0, v)), 1)
