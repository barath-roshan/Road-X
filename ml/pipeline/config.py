"""Configuration settings for RoadX Unified ML Pipeline (Phase 9)."""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel, Field


class PipelineConfig(BaseModel):
    """Configuration options governing pipeline orchestration and stage execution."""

    pipeline_version: str = Field(default="v1", description="Unified pipeline version string")

    # Default stage activation flags
    enable_failure_prediction: bool = Field(default=True, description="Execute Phase 2 Failure Prediction")
    enable_damage_detection: bool = Field(default=True, description="Execute Phase 3 Damage Detection")
    enable_severity: bool = Field(default=True, description="Execute Phase 4 Severity Estimation")
    enable_complaint_intelligence: bool = Field(default=True, description="Execute Phase 5 Complaint Intelligence")
    enable_duplicate_detection: bool = Field(default=True, description="Execute Phase 6 Duplicate Detection")
    enable_time_to_failure: bool = Field(default=True, description="Execute Phase 7 Time-to-Failure")
    enable_maintenance_priority: bool = Field(default=True, description="Execute Phase 8 Priority Engine")

    allow_partial_execution: bool = Field(default=True, description="Permit execution when partial input is provided")
    raise_on_required_failure: bool = Field(default=False, description="Raise exception if a required stage fails")

    def get_default_stage_flags(self) -> Dict[str, bool]:
        """Return dict of stage activation flags."""
        return {
            "failure_prediction": self.enable_failure_prediction,
            "damage_detection": self.enable_damage_detection,
            "severity": self.enable_severity,
            "complaint_intelligence": self.enable_complaint_intelligence,
            "duplicate_detection": self.enable_duplicate_detection,
            "time_to_failure": self.enable_time_to_failure,
            "maintenance_priority": self.enable_maintenance_priority,
        }


pipeline_config = PipelineConfig()
