"""Configuration settings and constants for Time-to-Failure Prediction (Phase 7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

from ml.common.config import settings

# Base feature names matching Phase 2 schema
BASE_FEATURE_NAMES: List[str] = [
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

# Engineered civil engineering distress indicators
ENGINEERED_FEATURE_NAMES: List[str] = [
    "traffic_stress",
    "repair_aging",
    "damage_indicator",
    "weather_stress",
    "structural_vulnerability",
    "complaint_pressure",
]

ALL_FEATURE_NAMES: List[str] = BASE_FEATURE_NAMES + ENGINEERED_FEATURE_NAMES


@dataclass
class TimeToFailureConfig:
    """Configuration container for survival analysis modeling and remaining life prediction."""

    model_dir: Path = field(
        default_factory=lambda: settings.models_dir / "time_to_failure"
    )
    raw_dataset_path: Path = field(
        default_factory=lambda: settings.raw_data_dir / "synthetic_time_to_failure_data.csv"
    )

    base_features: List[str] = field(default_factory=lambda: list(BASE_FEATURE_NAMES))
    engineered_features: List[str] = field(default_factory=lambda: list(ENGINEERED_FEATURE_NAMES))
    all_features: List[str] = field(default_factory=lambda: list(ALL_FEATURE_NAMES))

    # Standard survival probability evaluation horizons (in days)
    evaluation_horizons_days: List[int] = field(
        default_factory=lambda: [30, 90, 180, 365]
    )

    # Risk level threshold bounds (remaining days)
    # CRITICAL: < 30 days, HIGH: 30-90 days, MEDIUM: 90-180 days, LOW: >= 180 days
    risk_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "CRITICAL_MAX_DAYS": 30.0,
            "HIGH_MAX_DAYS": 90.0,
            "MEDIUM_MAX_DAYS": 180.0,
        }
    )

    test_size: float = 0.2
    random_state: int = 42
    model_version: str = "v1"

    def ensure_directories(self) -> None:
        """Create required artifact directory structure."""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        (self.model_dir / "metadata").mkdir(parents=True, exist_ok=True)


config = TimeToFailureConfig()
