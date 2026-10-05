"""Configuration parameters for Road Failure Prediction pipeline (Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from ml.common.config import settings


@dataclass
class FailurePredictionConfig:
    """Hyperparameters, feature specifications, risk thresholds, and artifact paths."""

    model_name: str = "road_failure_xgboost"
    model_version: str = "v1"
    target_column: str = "failure_next_30d"

    # Raw features present in the dataset
    raw_feature_columns: List[str] = field(
        default_factory=lambda: [
            "road_age_years",
            "road_length_m",
            "lane_count",
            "road_quality_score",
            "traffic_volume",
            "heavy_vehicle_ratio",
            "average_speed_kmph",
            "rainfall_7d_mm",
            "rainfall_30d_mm",
            "temperature_avg_c",
            "flood_events_30d",
            "days_since_repair",
            "previous_repairs",
            "previous_failures",
            "citizen_complaints_30d",
            "pothole_count",
            "crack_ratio",
        ]
    )

    metadata_columns: List[str] = field(
        default_factory=lambda: [
            "segment_id",
            "observation_date",
        ]
    )

    # Engineered feature names produced by RoadFailureFeatureBuilder
    engineered_feature_columns: List[str] = field(
        default_factory=lambda: [
            "traffic_stress",
            "repair_aging",
            "damage_indicator",
            "weather_stress",
            "structural_vulnerability",
            "complaint_pressure",
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

    # XGBoost default hyperparameter configuration
    xgboost_params: Dict[str, any] = field(
        default_factory=lambda: {
            "n_estimators": 300,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "eval_metric": "logloss",
            "random_state": 42,
        }
    )

    # Temporal split configuration
    temporal_split_ratio: float = 0.80  # Chronological train/test partition

    # Artifact paths
    raw_data_path: Path = field(
        default_factory=lambda: settings.raw_data_dir / "synthetic_road_failure_data.csv"
    )
    artifact_dir: Path = field(
        default_factory=lambda: settings.models_dir / "failure_prediction"
    )
    artifact_file: Path = field(
        default_factory=lambda: settings.models_dir / "failure_prediction" / "model_artifact.joblib"
    )
    metadata_file: Path = field(
        default_factory=lambda: settings.models_dir / "failure_prediction" / "metadata.json"
    )


failure_config = FailurePredictionConfig()
