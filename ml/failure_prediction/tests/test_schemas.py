"""Tests verifying failure prediction schemas, preprocessing, and features."""

import pytest
from ml.common.exceptions import RoadXDataError
from ml.failure_prediction.features import FailureFeatureExtractor
from ml.failure_prediction.preprocessing import FailureDataPreprocessor
from ml.failure_prediction.schemas import (
    FailurePredictionOutput,
    FailureRiskLevel,
    RoadGrievanceInput,
)


def test_road_grievance_input_valid():
    """Verify standard valid grievance record validates through schema."""
    input_data = RoadGrievanceInput(
        complaint_id="GRV-1001",
        latitude=12.9716,
        longitude=77.5946,
        road_type="arterial",
        surface_type="asphalt",
        reported_damage_type="pothole",
        estimated_depth_cm=6.5,
        estimated_area_sqm=1.2,
        traffic_volume_estimate="high",
        rainfall_recent_mm=25.0,
        road_age_years=4.0,
    )
    assert input_data.complaint_id == "GRV-1001"
    assert input_data.latitude == 12.9716
    assert input_data.estimated_depth_cm == 6.5


def test_failure_data_preprocessor_validation():
    """Verify preprocessor flags invalid geographic coordinates and negative measurements."""
    preprocessor = FailureDataPreprocessor()

    invalid_lat = RoadGrievanceInput(
        complaint_id="GRV-ERR-1",
        latitude=95.0,  # Invalid latitude (> 90)
        longitude=77.0,
        reported_damage_type="pothole",
    )
    with pytest.raises(RoadXDataError, match="Invalid latitude"):
        preprocessor.validate_record(invalid_lat)

    invalid_depth = RoadGrievanceInput(
        complaint_id="GRV-ERR-2",
        latitude=13.0,
        longitude=80.0,
        reported_damage_type="pothole",
        estimated_depth_cm=-5.0,  # Invalid depth
    )
    with pytest.raises(RoadXDataError, match="Negative depth"):
        preprocessor.validate_record(invalid_depth)


def test_failure_feature_extractor():
    """Verify feature extractor generates non-empty engineered indices."""
    extractor = FailureFeatureExtractor()
    record_dict = {
        "estimated_depth_cm": 10.0,
        "estimated_area_sqm": 2.0,
        "rainfall_recent_mm": 30.0,
        "traffic_volume_estimate": "high",
    }
    features = extractor.extract_features(record_dict)

    assert "severity_index" in features
    assert "water_damage_risk" in features
    assert "traffic_stress_factor" in features
    assert features["severity_index"] > 0
    assert features["traffic_stress_factor"] > features["severity_index"]


def test_failure_prediction_output():
    """Verify FailurePredictionOutput conforms to schema constraints."""
    output = FailurePredictionOutput(
        complaint_id="GRV-1001",
        failure_probability=0.82,
        risk_level=FailureRiskLevel.CRITICAL,
        top_contributing_factors=["high_traffic_stress", "severe_depth"],
        model_version="0.1.0",
    )
    assert output.risk_level == FailureRiskLevel.CRITICAL
    assert output.failure_probability == 0.82
