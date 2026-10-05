"""Tests verifying failure prediction schemas and risk level models."""

import pytest
from ml.common.exceptions import RoadXDataError
from ml.failure_prediction.features import RoadFailureFeatureBuilder
from ml.failure_prediction.preprocessing import RoadFailurePreprocessor
from ml.failure_prediction.schemas import (
    FailurePredictionOutput,
    FailureRiskLevel,
    RoadFailureInput,
    RoadGrievanceInput,
)


def test_road_failure_input_valid():
    """Verify standard valid road segment record validates through schema."""
    input_data = RoadFailureInput(
        segment_id="SEG-1001",
        observation_date="2025-05-15",
        road_age_years=6.5,
        road_length_m=500.0,
        lane_count=2,
        road_quality_score=0.62,
        traffic_volume=15000.0,
        heavy_vehicle_ratio=0.18,
        average_speed_kmph=52.0,
        rainfall_7d_mm=25.0,
        rainfall_30d_mm=110.0,
        temperature_avg_c=29.0,
        flood_events_30d=1,
        days_since_repair=360.0,
        previous_repairs=2,
        previous_failures=1,
        citizen_complaints_30d=3,
        pothole_count=4,
        crack_ratio=0.08,
    )
    assert input_data.segment_id == "SEG-1001"
    assert input_data.road_age_years == 6.5
    assert input_data.lane_count == 2


def test_failure_data_preprocessor_validation():
    """Verify preprocessor flags invalid bounds and negative values."""
    preprocessor = RoadFailurePreprocessor()

    invalid_age = {
        "road_age_years": -3.0,
        "road_length_m": 400.0,
        "lane_count": 2,
        "road_quality_score": 0.5,
        "traffic_volume": 10000.0,
        "heavy_vehicle_ratio": 0.1,
        "average_speed_kmph": 50.0,
        "rainfall_7d_mm": 10.0,
        "rainfall_30d_mm": 50.0,
        "temperature_avg_c": 25.0,
        "flood_events_30d": 0,
        "days_since_repair": 100.0,
        "previous_repairs": 0,
        "previous_failures": 0,
        "citizen_complaints_30d": 1,
        "pothole_count": 1,
        "crack_ratio": 0.05,
    }
    with pytest.raises(RoadXDataError, match="Negative road age"):
        preprocessor.validate_record(invalid_age)


def test_failure_feature_extractor():
    """Verify feature extractor generates non-empty engineered indices."""
    extractor = RoadFailureFeatureBuilder(include_raw=True)
    record_dict = {
        "road_age_years": 8.0,
        "road_length_m": 400.0,
        "lane_count": 2,
        "road_quality_score": 0.45,
        "traffic_volume": 20000.0,
        "heavy_vehicle_ratio": 0.25,
        "average_speed_kmph": 45.0,
        "rainfall_7d_mm": 30.0,
        "rainfall_30d_mm": 120.0,
        "temperature_avg_c": 28.0,
        "flood_events_30d": 1,
        "days_since_repair": 400.0,
        "previous_repairs": 2,
        "previous_failures": 1,
        "citizen_complaints_30d": 5,
        "pothole_count": 6,
        "crack_ratio": 0.12,
    }
    features = extractor.extract_features(record_dict)

    assert "traffic_stress" in features
    assert "weather_stress" in features
    assert "damage_indicator" in features
    assert features["traffic_stress"] > 0


def test_failure_prediction_output():
    """Verify FailurePredictionOutput conforms to schema constraints."""
    output = FailurePredictionOutput(
        failure_probability=0.82,
        risk_level=FailureRiskLevel.CRITICAL,
        top_contributing_factors=["structural_vulnerability", "damage_indicator"],
        model_version="v1",
    )
    assert output.risk_level == FailureRiskLevel.CRITICAL
    assert output.failure_probability == 0.82
    assert output.model_version == "v1"
