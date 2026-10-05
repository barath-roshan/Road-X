"""Configuration parameters for Road Failure Prediction pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from ml.common.config import settings


@dataclass
class FailurePredictionConfig:
    """Hyperparameters, feature definitions, and artifact destinations for failure prediction."""

    model_name: str = "road_failure_classifier"
    model_version: str = "0.1.0"
    target_column: str = "will_fail_critical"
    
    # Core feature columns utilized by the failure prediction model
    numerical_features: List[str] = field(
        default_factory=lambda: [
            "estimated_depth_cm",
            "estimated_area_sqm",
            "rainfall_recent_mm",
            "road_age_years",
        ]
    )
    categorical_features: List[str] = field(
        default_factory=lambda: [
            "road_type",
            "surface_type",
            "reported_damage_type",
            "traffic_volume_estimate",
        ]
    )

    # Risk classification thresholds
    critical_threshold: float = 0.80
    high_threshold: float = 0.60
    medium_threshold: float = 0.35

    # Artifact persistence path
    artifact_path: Path = field(
        default_factory=lambda: settings.models_dir / "failure_prediction" / "model.joblib"
    )


failure_config = FailurePredictionConfig()
