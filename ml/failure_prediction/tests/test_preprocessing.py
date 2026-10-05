"""Tests verifying road failure data preprocessing, validation, and imputation."""

import numpy as np
import pandas as pd
import pytest

from ml.common.exceptions import RoadXDataError
from ml.failure_prediction.preprocessing import RoadFailurePreprocessor
from ml.failure_prediction.schemas import RoadFailureInput


def test_valid_record_passes_validation():
    """Verify standard valid road segment features pass validation."""
    preprocessor = RoadFailurePreprocessor()
    valid_data = {
        "road_age_years": 8.5,
        "road_length_m": 450.0,
        "lane_count": 2,
        "road_quality_score": 0.55,
        "traffic_volume": 18000.0,
        "heavy_vehicle_ratio": 0.22,
        "average_speed_kmph": 48.0,
        "rainfall_7d_mm": 35.0,
        "rainfall_30d_mm": 120.0,
        "temperature_avg_c": 28.0,
        "flood_events_30d": 1,
        "days_since_repair": 340.0,
        "previous_repairs": 2,
        "previous_failures": 1,
        "citizen_complaints_30d": 4,
        "pothole_count": 5,
        "crack_ratio": 0.12,
    }
    validated = preprocessor.validate_record(valid_data)
    assert validated["road_age_years"] == 8.5
    assert validated["lane_count"] == 2


@pytest.mark.parametrize(
    "invalid_patch, error_pattern",
    [
        ({"road_age_years": -2.0}, "Negative road age"),
        ({"road_length_m": 0.0}, "non-positive road length"),
        ({"lane_count": 0}, "Invalid lane count"),
        ({"road_quality_score": 1.5}, r"outside \[0, 1\]"),
        ({"traffic_volume": -100.0}, "Negative traffic volume"),
        ({"heavy_vehicle_ratio": 1.4}, r"outside \[0, 1\]"),
        ({"rainfall_7d_mm": -10.0}, "Negative precipitation"),
        ({"flood_events_30d": -1}, "Negative flood event"),
        ({"days_since_repair": -5.0}, "Negative days since repair"),
        ({"crack_ratio": 1.2}, r"Crack ratio outside \[0, 1\]"),
        ({"pothole_count": -3}, "Negative pothole count"),
    ],
)
def test_invalid_values_raise_data_error(invalid_patch, error_pattern):
    """Verify physical bounds violations raise descriptive RoadXDataError."""
    preprocessor = RoadFailurePreprocessor()
    base_data = {
        "road_age_years": 5.0,
        "road_length_m": 300.0,
        "lane_count": 2,
        "road_quality_score": 0.7,
        "traffic_volume": 12000.0,
        "heavy_vehicle_ratio": 0.15,
        "average_speed_kmph": 50.0,
        "rainfall_7d_mm": 10.0,
        "rainfall_30d_mm": 40.0,
        "temperature_avg_c": 25.0,
        "flood_events_30d": 0,
        "days_since_repair": 120.0,
        "previous_repairs": 1,
        "previous_failures": 0,
        "citizen_complaints_30d": 1,
        "pothole_count": 2,
        "crack_ratio": 0.05,
    }
    base_data.update(invalid_patch)
    with pytest.raises(RoadXDataError, match=error_pattern):
        preprocessor.validate_record(base_data)


def test_missing_columns_raise_error():
    """Verify validate_dataframe flags missing required feature columns."""
    preprocessor = RoadFailurePreprocessor()
    incomplete_df = pd.DataFrame([{"road_age_years": 4.0, "traffic_volume": 10000.0}])
    with pytest.raises(RoadXDataError, match="missing required feature columns"):
        preprocessor.validate_dataframe(incomplete_df, is_training=False)


def test_preprocessor_imputation_without_leakage():
    """Verify preprocessor fits medians on training data and imputes missing values."""
    preprocessor = RoadFailurePreprocessor()
    train_data = pd.DataFrame([
        {
            "road_age_years": 2.0, "road_length_m": 200.0, "lane_count": 2,
            "road_quality_score": 0.8, "traffic_volume": 10000.0, "heavy_vehicle_ratio": 0.1,
            "average_speed_kmph": 60.0, "rainfall_7d_mm": 10.0, "rainfall_30d_mm": 30.0,
            "temperature_avg_c": 24.0, "flood_events_30d": 0, "days_since_repair": 100.0,
            "previous_repairs": 1, "previous_failures": 0, "citizen_complaints_30d": 2,
            "pothole_count": 1, "crack_ratio": 0.02,
        },
        {
            "road_age_years": 10.0, "road_length_m": 400.0, "lane_count": 2,
            "road_quality_score": 0.4, "traffic_volume": 30000.0, "heavy_vehicle_ratio": 0.3,
            "average_speed_kmph": 40.0, "rainfall_7d_mm": 50.0, "rainfall_30d_mm": 150.0,
            "temperature_avg_c": 28.0, "flood_events_30d": 1, "days_since_repair": 500.0,
            "previous_repairs": 3, "previous_failures": 2, "citizen_complaints_30d": 8,
            "pothole_count": 7, "crack_ratio": 0.18,
        },
    ])

    preprocessor.fit(train_data)
    assert preprocessor.is_fitted
    assert preprocessor.imputation_medians_["road_age_years"] == 6.0  # Median of [2.0, 10.0]

    # Test DataFrame with missing value
    test_data = train_data.copy()
    test_data.loc[0, "road_age_years"] = np.nan
    transformed = preprocessor.transform(test_data)
    assert transformed.loc[0, "road_age_years"] == 6.0
