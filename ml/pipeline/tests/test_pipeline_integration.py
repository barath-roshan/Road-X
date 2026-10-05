"""Integration test for RoadX Unified ML Pipeline with real default model artifacts (Phase 9)."""

import pytest
from ml.pipeline.orchestrator import RoadXPipeline
from ml.pipeline.schemas import PipelineInput, PipelineStageStatus
from ml.duplicate_detection.schemas import ComplaintRecord


def test_pipeline_integration_real_predictors():
    """Test pipeline execution using auto-loaded default trained predictors across tabular, text, and priority engine."""
    pipeline = RoadXPipeline(auto_load=True)

    sample_road_data = {
        "segment_id": "SEG-INTEG-001",
        "road_age_years": 8.5,
        "road_length_m": 1200.0,
        "lane_count": 2,
        "road_quality_score": 0.45,
        "traffic_volume": 12000.0,
        "heavy_vehicle_ratio": 0.25,
        "average_speed_kmph": 50.0,
        "rainfall_7d_mm": 45.0,
        "rainfall_30d_mm": 150.0,
        "temperature_avg_c": 28.0,
        "flood_events_30d": 1,
        "days_since_repair": 360.0,
        "previous_repairs": 2,
        "previous_failures": 1,
        "citizen_complaints_30d": 3,
        "pothole_count": 4,
        "crack_ratio": 0.25,
    }

    complaint_text = "Severe potholes near Central Hospital and water ponding during rains."

    existing_complaints = [
        ComplaintRecord(
            grievance_id="COMP-HIST-1",
            text="Hospital road has big potholes causing water accumulation.",
            latitude=13.0827,
            longitude=80.2707,
        )
    ]

    pipeline_input = PipelineInput(
        road_segment_id="SEG-INTEG-001",
        complaint_id="COMP-INTEG-001",
        road_data=sample_road_data,
        complaint_text=complaint_text,
        existing_complaints=existing_complaints,
    )

    result = pipeline.run(pipeline_input)

    assert result is not None
    assert result.pipeline_version == "v1"
    assert result.road_segment_id == "SEG-INTEG-001"
    assert result.complaint_id == "COMP-INTEG-001"

    # Stage statuses checks
    assert result.stage_summaries["failure_prediction"].status == PipelineStageStatus.SUCCESS
    assert result.failure_prediction is not None
    assert result.failure_prediction.failure_probability > 0.0

    assert result.stage_summaries["complaint_intelligence"].status == PipelineStageStatus.SUCCESS
    assert result.complaint_analysis is not None

    assert result.stage_summaries["duplicate_detection"].status == PipelineStageStatus.SUCCESS
    assert result.duplicate_detection is not None

    assert result.stage_summaries["time_to_failure"].status == PipelineStageStatus.SUCCESS
    assert result.time_to_failure is not None
    assert result.time_to_failure.estimated_time_to_failure_days > 0.0

    assert result.stage_summaries["maintenance_priority"].status == PipelineStageStatus.SUCCESS
    assert result.maintenance_priority is not None
    assert 0.0 <= result.maintenance_priority.priority_score <= 100.0

    # Image damage detection was not provided in input
    assert result.stage_summaries["damage_detection"].status == PipelineStageStatus.SKIPPED
    assert result.stage_summaries["severity"].status == PipelineStageStatus.UNAVAILABLE
