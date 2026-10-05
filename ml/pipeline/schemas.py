"""Pydantic schemas and data containers for RoadX Unified ML Pipeline (Phase 9)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator

from ml.common.exceptions import RoadXDataError
from ml.failure_prediction.schemas import FailurePredictionOutput, RoadFailureInput
from ml.damage_detection.schemas import RoadDamageDetectionResponse
from ml.severity.schemas import RoadContextInput, SeverityPredictionOutput
from ml.complaint_intelligence.schemas import ComplaintAnalysisResponse
from ml.duplicate_detection.schemas import ComplaintRecord, DuplicateDetectionResponse
from ml.time_to_failure.schemas import TimeToFailureOutput
from ml.priority_engine.schemas import MaintenancePriorityOutput


class PipelineStageStatus(str, Enum):
    """Execution status for an individual pipeline stage."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    UNAVAILABLE = "UNAVAILABLE"


class PipelineStageSummary(BaseModel):
    """Execution summary and latency record for a specific pipeline stage."""

    stage_name: str = Field(description="Identifier name of the pipeline stage")
    status: PipelineStageStatus = Field(description="Stage execution status")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Stage latency in milliseconds")
    error_code: Optional[str] = Field(default=None, description="Structured error code if failed")
    error_message: Optional[str] = Field(default=None, description="Descriptive error message if failed")
    model_version: Optional[str] = Field(default=None, description="Model version utilized in stage")


class PipelineInput(BaseModel):
    """Comprehensive input container passed into RoadX Unified ML Pipeline."""

    road_segment_id: Optional[str] = Field(default=None, description="Road segment identifier")
    complaint_id: Optional[str] = Field(default=None, description="Citizen complaint identifier")

    # Module-specific input payloads
    road_data: Optional[Union[Dict[str, Any], RoadFailureInput]] = Field(
        default=None, description="Road segment tabular condition features (Phase 2 / Phase 7)"
    )
    complaint_text: Optional[str] = Field(
        default=None, description="Citizen natural language complaint text (Phase 5)"
    )
    image: Optional[Any] = Field(
        default=None, description="Road image filepath, numpy array, PIL Image, or bytes (Phase 3)"
    )
    road_context: Optional[Union[Dict[str, Any], RoadContextInput]] = Field(
        default=None, description="Road surface context for damage severity estimation (Phase 4)"
    )

    # Context for duplicate detection
    new_complaint_record: Optional[ComplaintRecord] = Field(
        default=None, description="New complaint record structure for duplicate analysis (Phase 6)"
    )
    existing_complaints: Optional[List[ComplaintRecord]] = Field(
        default=None, description="Historical complaint records pool for duplicate candidate retrieval (Phase 6)"
    )

    # Optional stage overrides
    enabled_stages: Optional[Dict[str, bool]] = Field(
        default=None, description="Map of stage names to boolean activation flags"
    )

    @field_validator("complaint_text")
    @classmethod
    def clean_text(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from complaint text if provided."""
        if v is not None:
            v_str = str(v).strip()
            return v_str if v_str else None
        return None

    @field_validator("road_data")
    @classmethod
    def validate_road_coordinates(
        cls, v: Optional[Union[Dict[str, Any], RoadFailureInput]]
    ) -> Optional[Union[Dict[str, Any], RoadFailureInput]]:
        """Validate geographic coordinates if present in road_data."""
        if v is None:
            return None

        data_dict = v if isinstance(v, dict) else v.model_dump()
        lat = data_dict.get("latitude")
        lon = data_dict.get("longitude")

        if lat is not None and not (-90.0 <= float(lat) <= 90.0):
            raise RoadXDataError(f"Latitude out of valid range [-90, 90]: {lat}")
        if lon is not None and not (-180.0 <= float(lon) <= 180.0):
            raise RoadXDataError(f"Longitude out of valid range [-180, 180]: {lon}")

        return v


class UnifiedPipelineResult(BaseModel):
    """Unified response object returned by the RoadX Unified ML Pipeline."""

    pipeline_version: str = Field(default="v1", description="Unified pipeline version identifier")
    timestamp_utc: str = Field(description="ISO-8601 execution timestamp in UTC")
    overall_status: str = Field(
        description="Overall pipeline status: SUCCESS, PARTIAL_SUCCESS, or FAILED"
    )

    road_segment_id: Optional[str] = Field(default=None, description="Road segment ID")
    complaint_id: Optional[str] = Field(default=None, description="Complaint ID")

    # Structured ML Module Outputs
    failure_prediction: Optional[FailurePredictionOutput] = Field(
        default=None, description="Phase 2 Road Failure Prediction output"
    )
    damage_detection: Optional[RoadDamageDetectionResponse] = Field(
        default=None, description="Phase 3 Road Damage Detection output"
    )
    severity_prediction: Optional[SeverityPredictionOutput] = Field(
        default=None, description="Phase 4 Damage Severity Estimation output"
    )
    complaint_analysis: Optional[ComplaintAnalysisResponse] = Field(
        default=None, description="Phase 5 Complaint Intelligence output"
    )
    duplicate_detection: Optional[DuplicateDetectionResponse] = Field(
        default=None, description="Phase 6 Duplicate Complaint Detection output"
    )
    time_to_failure: Optional[TimeToFailureOutput] = Field(
        default=None, description="Phase 7 Time-to-Failure Prediction output"
    )
    maintenance_priority: Optional[MaintenancePriorityOutput] = Field(
        default=None, description="Phase 8 Maintenance Priority Recommendation output"
    )

    # Operational Metadata & Profiling
    stage_summaries: Dict[str, PipelineStageSummary] = Field(
        default_factory=dict, description="Summary details and latencies for each pipeline stage"
    )
    total_duration_ms: float = Field(
        default=0.0, ge=0.0, description="Total pipeline execution latency in milliseconds"
    )
