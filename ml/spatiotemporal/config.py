"""Configuration settings for Advanced Spatiotemporal ML (Phase 20)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from ml.common.config import settings


@dataclass
class SpatiotemporalConfig:
    """Hyperparameters, spatial/temporal feature columns, and artifact paths."""

    model_name: str = "road_failure_spatiotemporal_xgboost"
    model_version: str = "v2.0_spatiotemporal"
    target_column: str = "failure_next_30d"

    # Spatial Feature Configurations
    default_center_lat: float = 12.9716  # Default reference city lat (e.g. Bangalore/Municipal center)
    default_center_lon: float = 77.5946  # Default reference city lon
    spatial_radius_km: float = 5.0       # Spatial neighborhood radius in kilometers
    n_spatial_clusters: int = 5          # Number of spatial geographic clusters

    spatial_feature_columns: List[str] = field(
        default_factory=lambda: [
            "latitude",
            "longitude",
            "dist_to_center_km",
            "spatial_cluster",
            "neighbor_quality_avg",
            "neighbor_pothole_avg",
            "neighbor_failure_rate",
        ]
    )

    # Temporal Feature Configurations
    temporal_feature_columns: List[str] = field(
        default_factory=lambda: [
            "month",
            "day_of_week",
            "is_monsoon",
            "day_of_year_sin",
            "day_of_year_cos",
            "quality_rolling_3obs_mean",
            "quality_decay_rate",
            "pothole_trend_3obs",
        ]
    )

    # Risk level threshold configuration
    risk_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "low_max": 0.30,
            "medium_max": 0.60,
            "high_max": 0.80,
        }
    )

    # XGBoost hyperparameter configuration for spatiotemporal model
    xgboost_params: Dict[str, any] = field(
        default_factory=lambda: {
            "n_estimators": 350,
            "max_depth": 6,
            "learning_rate": 0.04,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "eval_metric": "logloss",
            "random_state": 42,
        }
    )

    # Temporal split configuration
    temporal_split_ratio: float = 0.80  # Chronological train/test split ratio

    # Artifact paths
    artifact_dir: Path = field(
        default_factory=lambda: settings.models_dir / "spatiotemporal"
    )
    artifact_file: Path = field(
        default_factory=lambda: settings.models_dir / "spatiotemporal" / "spatiotemporal_model_artifact.joblib"
    )
    metadata_file: Path = field(
        default_factory=lambda: settings.models_dir / "spatiotemporal" / "metadata.json"
    )


spatiotemporal_config = SpatiotemporalConfig()
