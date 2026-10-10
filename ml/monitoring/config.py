"""Configuration parameters for Phase 21 MLflow tracking, candidate evaluation, telemetry, and drift monitoring."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from ml.common.config import settings


@dataclass
class MonitoringConfig:
    """Configuration container for experiment tracking, telemetry, and drift parameters."""

    # MLflow tracking settings
    mlflow_enabled: bool = field(
        default_factory=lambda: os.getenv("ROADX_MLFLOW_ENABLED", "true").lower() in ("true", "1")
    )
    mlflow_tracking_uri: str = field(
        default_factory=lambda: os.getenv(
            "ROADX_MLFLOW_TRACKING_URI",
            f"file:///{ (settings.models_dir / 'mlruns').as_posix() }",
        )
    )
    mlflow_experiment_name: str = field(
        default_factory=lambda: os.getenv("ROADX_MLFLOW_EXPERIMENT", "RoadX_Failure_Prediction")
    )
    mlflow_registered_model_name: str = field(
        default_factory=lambda: os.getenv("ROADX_MLFLOW_REGISTERED_MODEL", "RoadX_Spatiotemporal_Model")
    )

    # Candidate evaluation & promotion criteria defaults
    min_acceptance_f1: float = 0.75
    min_acceptance_roc_auc: float = 0.85
    min_acceptance_precision: float = 0.75
    min_acceptance_recall: float = 0.70

    # Feature Drift thresholds
    psi_moderate_threshold: float = 0.10  # PSI >= 0.10 indicates moderate drift
    psi_high_threshold: float = 0.25      # PSI >= 0.25 indicates significant drift
    ks_pvalue_threshold: float = 0.05      # KS p-value < 0.05 indicates statistically significant distribution shift

    # Artifact paths
    monitoring_dir: Path = field(
        default_factory=lambda: settings.models_dir / "monitoring"
    )
    reference_data_path: Path = field(
        default_factory=lambda: settings.models_dir / "monitoring" / "reference_features.csv"
    )
    telemetry_log_path: Path = field(
        default_factory=lambda: settings.models_dir / "monitoring" / "telemetry_summary.json"
    )


monitoring_config = MonitoringConfig()
