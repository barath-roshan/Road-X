"""Request validation schemas for RoadX ML FastAPI Service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from ml.failure_prediction.schemas import RoadFailureInput
from ml.severity.schemas import RoadContextInput
from ml.duplicate_detection.schemas import ComplaintRecord
from ml.pipeline.schemas import PipelineInput


# Aliases for request payload typing
RoadDataRequestPayload = Union[RoadFailureInput, Dict[str, Any]]
RoadContextRequestPayload = Union[RoadContextInput, Dict[str, Any]]


class MLAnalyzeRequest(BaseModel):
    """JSON Request model for unified ML pipeline analysis endpoint `/api/v1/ml/analyze`."""

    road_segment_id: Optional[str] = Field(
        default=None,
        description="Road segment identifier for tabular failure prediction & priority engine",
        examples=["SEG-MH-4001"],
    )
    complaint_id: Optional[str] = Field(
        default=None,
        description="Citizen complaint identifier",
        examples=["CMP-2026-9812"],
    )
    road_data: Optional[RoadDataRequestPayload] = Field(
        default=None,
        description="Road segment tabular condition features (Phase 2 & Phase 7)",
        examples=[
            {
                "segment_id": "SEG-MH-4001",
                "road_age_years": 4.5,
                "road_length_m": 1200.0,
                "lane_count": 2,
                "road_quality_score": 0.42,
                "traffic_volume": 4500.0,
                "heavy_vehicle_ratio": 0.25,
                "average_speed_kmph": 45.0,
                "rainfall_7d_mm": 85.0,
                "rainfall_30d_mm": 210.0,
                "temperature_avg_c": 31.5,
                "flood_events_30d": 1,
                "days_since_repair": 420.0,
                "previous_repairs": 3,
                "previous_failures": 1,
                "citizen_complaints_30d": 8,
                "pothole_count": 5,
                "crack_ratio": 0.35,
            }
        ],
    )
    complaint_text: Optional[str] = Field(
        default=None,
        description="Citizen natural language complaint text description (Phase 5)",
        examples=["Deep pothole near the main market junction causing traffic jams and vehicle damage."],
    )
    image: Optional[str] = Field(
        default=None,
        description="Optional local image file path or reference for visual damage detection",
        examples=["data/raw/sample_pothole.jpg"],
    )
    road_context: Optional[RoadContextRequestPayload] = Field(
        default=None,
        description="Road surface context for damage severity estimation (Phase 4)",
        examples=[
            {
                "road_type": "URBAN_ARTERIAL",
                "speed_limit_kmh": 60.0,
                "traffic_volume_category": "HIGH",
            }
        ],
    )
    new_complaint_record: Optional[ComplaintRecord] = Field(
        default=None,
        description="New complaint record structure for duplicate complaint detection (Phase 6)",
    )
    existing_complaints: Optional[List[ComplaintRecord]] = Field(
        default=None,
        description="Historical complaint pool for candidate retrieval in duplicate detection (Phase 6)",
    )
    enabled_stages: Optional[Dict[str, bool]] = Field(
        default=None,
        description="Optional stage activation flags overriding pipeline defaults",
        examples=[
            {
                "failure_prediction": True,
                "damage_detection": False,
                "complaint_intelligence": True,
            }
        ],
    )

    def to_pipeline_input(self) -> PipelineInput:
        """Convert API request model into Phase 9 PipelineInput."""
        return PipelineInput(
            road_segment_id=self.road_segment_id,
            complaint_id=self.complaint_id,
            road_data=self.road_data,
            complaint_text=self.complaint_text,
            image=self.image,
            road_context=self.road_context,
            new_complaint_record=self.new_complaint_record,
            existing_complaints=self.existing_complaints,
            enabled_stages=self.enabled_stages,
        )


class DriftAnalysisRequest(BaseModel):
    """Request payload for data and feature drift analysis."""

    current_data: List[Dict[str, Any]] = Field(
        ...,
        description="Batch of current/incoming feature records observed during inference",
    )
    reference_data: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional reference baseline dataset. If omitted, uses default reference baseline if available.",
    )
    features: Optional[List[str]] = Field(
        default=None,
        description="Subset of feature columns to evaluate for distribution shift",
    )


class CandidateEvaluationRequest(BaseModel):
    """Request payload for candidate model evaluation and promotion check."""

    candidate_metrics: Dict[str, float] = Field(
        ...,
        description="Evaluation metrics for candidate model",
    )
    baseline_metrics: Dict[str, float] = Field(
        ...,
        description="Evaluation metrics for active baseline model",
    )
    candidate_version: str = Field(
        default="v2.0_candidate",
        description="Version identifier of candidate model",
    )
    baseline_version: str = Field(
        default="v1.0_baseline",
        description="Version identifier of active baseline model",
    )
