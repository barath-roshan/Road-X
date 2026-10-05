"""Configuration parameters for Damage Severity Estimation module (Phase 4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from ml.common.config import settings


@dataclass
class SeverityConfig:
    """Settings, feature definitions, presentation thresholds, and artifact destinations."""

    model_name: str = "road_damage_severity_xgboost"
    model_version: str = "v1"
    problem_type: str = "regression"
    target_column: str = "severity_score"

    # Raw features derived from detection outputs and optional road context
    raw_feature_columns: List[str] = field(
        default_factory=lambda: [
            "detection_count",
            "total_area_ratio",
            "max_area_ratio",
            "avg_area_ratio",
            "max_confidence",
            "avg_confidence",
            "total_bbox_area",
            "max_bbox_area",
            "road_quality_score",
            "traffic_volume",
            "heavy_vehicle_ratio",
            "road_age_years",
            "citizen_complaints_30d",
        ]
    )

    # Engineered interaction features
    engineered_feature_columns: List[str] = field(
        default_factory=lambda: [
            "traffic_damage_interaction",
            "quality_defect_ratio",
            "complaint_defect_interaction",
        ]
    )

    # Configurable score-to-level presentation category thresholds
    # Score range: 0.0 to 100.0
    level_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "low_max": 30.0,      # 0.0 - 29.9 -> LOW
            "medium_max": 60.0,   # 30.0 - 59.9 -> MEDIUM
            "high_max": 80.0,     # 60.0 - 79.9 -> HIGH
                                  # >= 80.0     -> CRITICAL
        }
    )

    # XGBoost Regressor default hyperparameter configuration
    xgboost_params: Dict[str, any] = field(
        default_factory=lambda: {
            "n_estimators": 200,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
        }
    )

    # Artifact destinations
    raw_data_path: Path = field(
        default_factory=lambda: settings.raw_data_dir / "synthetic_damage_severity_data.csv"
    )
    artifact_dir: Path = field(
        default_factory=lambda: settings.models_dir / "severity"
    )
    artifact_file: Path = field(
        default_factory=lambda: settings.models_dir / "severity" / "model_artifact.joblib"
    )
    metadata_file: Path = field(
        default_factory=lambda: settings.models_dir / "severity" / "metadata.json"
    )


severity_config = SeverityConfig()
