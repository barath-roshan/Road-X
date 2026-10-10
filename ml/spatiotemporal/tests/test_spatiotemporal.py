"""Unit and Integration tests for Phase 20 Advanced Spatiotemporal ML."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.failure_prediction.schemas import FailurePredictionOutput, FailureRiskLevel, RoadFailureInput
from ml.spatiotemporal.config import spatiotemporal_config
from ml.spatiotemporal.dataset import SpatiotemporalDatasetBuilder
from ml.spatiotemporal.model import SpatiotemporalFailureModel
from ml.spatiotemporal.predict import SpatiotemporalPredictor
from ml.spatiotemporal.spatial import SpatialFeatureBuilder, haversine_distance_km
from ml.spatiotemporal.temporal import TemporalFeatureBuilder


def test_haversine_distance():
    """Test Great Circle Haversine distance calculation."""
    # Distance between Bangalore center (12.9716, 77.5946) and point 0.05 degrees away (~7.8 km)
    d = haversine_distance_km(12.9716, 77.5946, 13.0216, 77.5946)
    assert 5.0 < d < 10.0

    # Same point distance should be 0.0
    d_zero = haversine_distance_km(12.9716, 77.5946, 12.9716, 77.5946)
    assert d_zero == 0.0


def test_spatial_feature_builder():
    """Test spatial coordinate assignment, distance calculation, and neighbor context statistics."""
    spatial_builder = SpatialFeatureBuilder(radius_km=10.0)

    df_sample = pd.DataFrame([
        {"segment_id": "SEG-0001", "observation_date": "2025-01-01", "road_quality_score": 0.8, "pothole_count": 2, "failure_next_30d": 0},
        {"segment_id": "SEG-0002", "observation_date": "2025-01-01", "road_quality_score": 0.4, "pothole_count": 8, "failure_next_30d": 1},
    ])

    features_df = spatial_builder.build_spatial_features(df_sample)

    assert "latitude" in features_df.columns
    assert "longitude" in features_df.columns
    assert "dist_to_center_km" in features_df.columns
    assert "spatial_cluster" in features_df.columns
    assert "neighbor_quality_avg" in features_df.columns
    assert "neighbor_pothole_avg" in features_df.columns
    assert "neighbor_failure_rate" in features_df.columns

    assert len(features_df) == 2
    assert features_df["dist_to_center_km"].iloc[0] >= 0.0


def test_temporal_feature_builder():
    """Test calendar cycles, seasonal assignment, and segment rolling window statistics."""
    temporal_builder = TemporalFeatureBuilder()

    df_sample = pd.DataFrame([
        {"segment_id": "SEG-0001", "observation_date": "2025-01-01", "road_quality_score": 0.9, "pothole_count": 1},
        {"segment_id": "SEG-0001", "observation_date": "2025-01-15", "road_quality_score": 0.8, "pothole_count": 3},
        {"segment_id": "SEG-0001", "observation_date": "2025-02-01", "road_quality_score": 0.7, "pothole_count": 5},
    ])

    temp_features = temporal_builder.build_temporal_features(df_sample)

    assert "month" in temp_features.columns
    assert "is_monsoon" in temp_features.columns
    assert "day_of_year_sin" in temp_features.columns
    assert "day_of_year_cos" in temp_features.columns
    assert "quality_rolling_3obs_mean" in temp_features.columns
    assert "quality_decay_rate" in temp_features.columns
    assert "pothole_trend_3obs" in temp_features.columns

    # Verify rolling mean calculation
    assert temp_features["quality_rolling_3obs_mean"].iloc[0] == 0.9
    assert temp_features["quality_rolling_3obs_mean"].iloc[2] == pytest.approx((0.9 + 0.8 + 0.7) / 3.0)


def test_temporal_leakage_prevention():
    """Audit test verifying that future observation updates at t+1 do NOT alter feature matrix at timestamp t."""
    dataset_builder = SpatiotemporalDatasetBuilder()

    t1_df = pd.DataFrame([
        {"segment_id": "SEG-0001", "observation_date": "2025-01-01", "road_quality_score": 0.8, "pothole_count": 2},
    ])

    t2_df = pd.DataFrame([
        {"segment_id": "SEG-0001", "observation_date": "2025-01-01", "road_quality_score": 0.8, "pothole_count": 2},
        {"segment_id": "SEG-0001", "observation_date": "2025-06-01", "road_quality_score": 0.2, "pothole_count": 25},  # Future observation
    ])

    feats_t1, _ = dataset_builder.build_feature_matrix(t1_df)
    feats_t2, _ = dataset_builder.build_feature_matrix(t2_df)

    # Feature values for timestamp t (index 0) must remain identical regardless of future records t+1
    row_t1 = feats_t1.iloc[0]
    row_t2_at_t1 = feats_t2.iloc[0]

    for col in ["quality_rolling_3obs_mean", "quality_decay_rate", "neighbor_quality_avg"]:
        assert pytest.approx(row_t1[col], abs=1e-4) == row_t2_at_t1[col]


def test_chronological_data_split():
    """Test chronological partitioning ensuring training observations precede test observations."""
    builder = SpatiotemporalDatasetBuilder()

    df_sample = pd.DataFrame([
        {"segment_id": "SEG-0001", "observation_date": "2025-01-01"},
        {"segment_id": "SEG-0001", "observation_date": "2025-02-01"},
        {"segment_id": "SEG-0001", "observation_date": "2025-03-01"},
        {"segment_id": "SEG-0001", "observation_date": "2025-04-01"},
        {"segment_id": "SEG-0001", "observation_date": "2025-05-01"},
    ])

    train_df, test_df = builder.chronological_split(df_sample, split_ratio=0.8)

    assert len(train_df) == 4
    assert len(test_df) == 1
    assert train_df["observation_date"].max() <= test_df["observation_date"].min()


def test_spatiotemporal_predictor(tmp_path: Path):
    """Test SpatiotemporalPredictor inference, probability mapping, and output schemas."""
    predictor = SpatiotemporalPredictor()

    sample_input = RoadFailureInput(
        segment_id="SEG-0001",
        road_age_years=6.0,
        road_length_m=500.0,
        lane_count=2,
        road_quality_score=0.45,
        traffic_volume=15000.0,
        heavy_vehicle_ratio=0.25,
        average_speed_kmph=45.0,
        rainfall_7d_mm=45.0,
        rainfall_30d_mm=180.0,
        temperature_avg_c=28.0,
        flood_events_30d=1,
        days_since_repair=240.0,
        previous_repairs=2,
        previous_failures=1,
        citizen_complaints_30d=5,
        pothole_count=6,
        crack_ratio=0.15,
    )

    result = predictor.predict(sample_input)

    assert isinstance(result, FailurePredictionOutput)
    assert 0.0 <= result.failure_probability <= 1.0
    assert result.risk_level in [FailureRiskLevel.LOW, FailureRiskLevel.MEDIUM, FailureRiskLevel.HIGH, FailureRiskLevel.CRITICAL]
    assert isinstance(result.top_contributing_factors, list)
