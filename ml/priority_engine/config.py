"""Configuration settings and parameters for Maintenance Priority Engine (Phase 8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from ml.common.config import settings


@dataclass
class MaintenancePriorityConfig:
    """Configuration container for maintenance prioritization weights, thresholds, and guardrails."""

    model_dir: Path = field(
        default_factory=lambda: settings.models_dir / "priority_engine"
    )
    raw_dataset_path: Path = field(
        default_factory=lambda: settings.raw_data_dir / "synthetic_priority_data.csv"
    )

    # Base signal weights (dynamically re-normalized when signals are absent)
    failure_risk_weight: float = 0.25
    severity_weight: float = 0.25
    safety_risk_weight: float = 0.20
    time_to_failure_weight: float = 0.15
    urgency_weight: float = 0.10
    complaint_volume_weight: float = 0.05

    # Composite Priority Score Thresholds (0.0 to 100.0)
    score_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "CRITICAL_MIN_SCORE": 80.0,
            "HIGH_MIN_SCORE": 60.0,
            "MEDIUM_MIN_SCORE": 35.0,
        }
    )

    # Safety Guardrails: Ensures high safety risks or short failure windows cannot fall below HIGH priority
    enable_safety_guardrails: bool = True
    guardrail_min_high_score: float = 65.0
    time_to_failure_critical_window_days: float = 14.0

    model_version: str = "v1"

    def ensure_directories(self) -> None:
        """Create artifact directory structure if needed."""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        (self.model_dir / "metadata").mkdir(parents=True, exist_ok=True)


config = MaintenancePriorityConfig()
