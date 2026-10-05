"""Unit tests for survival feature builder and temporal leakage prevention."""

from ml.failure_prediction.schemas import RoadFailureInput
from ml.time_to_failure.features import SurvivalFeatureBuilder, compute_survival_features
from ml.time_to_failure.config import config


def test_survival_feature_builder_single():
    builder = SurvivalFeatureBuilder()
    inp = RoadFailureInput(
        segment_id="SEG-001",
        road_age_years=5.0,
        road_length_m=500.0,
        lane_count=2,
        road_quality_score=0.6,
        traffic_volume=10000.0,
        heavy_vehicle_ratio=0.2,
        average_speed_kmph=40.0,
        rainfall_7d_mm=30.0,
        rainfall_30d_mm=100.0,
        temperature_avg_c=30.0,
        flood_events_30d=1,
        days_since_repair=365.0,
        previous_repairs=1,
        previous_failures=0,
        citizen_complaints_30d=3,
        pothole_count=2,
        crack_ratio=0.05,
    )

    feat_dict = builder.transform_single(inp)

    assert "traffic_stress" in feat_dict
    assert "repair_aging" in feat_dict
    assert "damage_indicator" in feat_dict
    assert "weather_stress" in feat_dict
    assert "structural_vulnerability" in feat_dict
    assert "complaint_pressure" in feat_dict

    # Check engineered values
    assert feat_dict["traffic_stress"] == 2000.0
    assert feat_dict["structural_vulnerability"] == 2.0  # 5.0 * (1 - 0.6)
