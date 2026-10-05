"""Tests verifying civil engineering feature derivation and correctness."""

import pandas as pd
import pytest

from ml.failure_prediction.features import RoadFailureFeatureBuilder


def test_engineered_features_calculation():
    """Verify exact mathematical computation of engineered road stress indicators."""
    builder = RoadFailureFeatureBuilder(include_raw=True)

    input_df = pd.DataFrame([{
        "road_age_years": 8.0,
        "road_length_m": 500.0,
        "lane_count": 2,
        "road_quality_score": 0.40,
        "traffic_volume": 20000.0,
        "heavy_vehicle_ratio": 0.25,
        "average_speed_kmph": 45.0,
        "rainfall_7d_mm": 40.0,
        "rainfall_30d_mm": 160.0,
        "temperature_avg_c": 30.0,
        "flood_events_30d": 2,
        "days_since_repair": 730.5,
        "previous_repairs": 1,
        "previous_failures": 1,
        "citizen_complaints_30d": 6,
        "pothole_count": 8,
        "crack_ratio": 0.10,
    }])

    feat_df = builder.build_features(input_df)

    # 1. Traffic stress = 20000.0 * 0.25 = 5000.0
    assert feat_df.loc[0, "traffic_stress"] == pytest.approx(5000.0)

    # 2. Repair aging = 730.5 / (365.25 * (1 + 1)) = 730.5 / 730.5 = 1.0
    assert feat_df.loc[0, "repair_aging"] == pytest.approx(1.0)

    # 3. Damage indicator = (8 * 0.7) + (0.10 * 100 * 0.3) = 5.6 + 3.0 = 8.6
    assert feat_df.loc[0, "damage_indicator"] == pytest.approx(8.6)

    # 4. Weather stress = 160 * (1 + 2*0.5) + (40 * 1.5) = 160 * 2.0 + 60 = 320 + 60 = 380.0
    assert feat_df.loc[0, "weather_stress"] == pytest.approx(380.0)

    # 5. Structural vulnerability = 8.0 * (1.0 - 0.40) = 8.0 * 0.60 = 4.80
    assert feat_df.loc[0, "structural_vulnerability"] == pytest.approx(4.80)

    # 6. Complaint pressure = 6 / ((20000 / 1000) + 1) = 6 / 21
    assert feat_df.loc[0, "complaint_pressure"] == pytest.approx(6.0 / 21.0)


def test_feature_builder_columns_consistency():
    """Verify feature builder preserves expected column names and schema."""
    builder = RoadFailureFeatureBuilder(include_raw=True)
    input_df = pd.DataFrame([{
        "road_age_years": 4.0, "road_length_m": 200.0, "lane_count": 1,
        "road_quality_score": 0.8, "traffic_volume": 5000.0, "heavy_vehicle_ratio": 0.1,
        "average_speed_kmph": 50.0, "rainfall_7d_mm": 10.0, "rainfall_30d_mm": 25.0,
        "temperature_avg_c": 22.0, "flood_events_30d": 0, "days_since_repair": 200.0,
        "previous_repairs": 0, "previous_failures": 0, "citizen_complaints_30d": 1,
        "pothole_count": 1, "crack_ratio": 0.02,
    }])
    output_df = builder.transform(input_df)

    expected_engineered = [
        "traffic_stress", "repair_aging", "damage_indicator",
        "weather_stress", "structural_vulnerability", "complaint_pressure",
    ]
    for col in expected_engineered:
        assert col in output_df.columns
    assert len(output_df.columns) == 17 + 6  # 17 raw + 6 engineered = 23 columns
