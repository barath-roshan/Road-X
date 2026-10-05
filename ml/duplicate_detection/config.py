"""Configuration settings and parameters for Duplicate Complaint Detection (Phase 6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ml.common.config import settings


@dataclass
class DuplicateDetectionConfig:
    """Configuration settings for candidate retrieval, proximity decay, and duplicate scoring."""

    model_dir: Path = field(
        default_factory=lambda: settings.models_dir / "duplicate_detection"
    )
    raw_dataset_path: Path = field(
        default_factory=lambda: settings.raw_data_dir / "synthetic_duplicate_complaints.csv"
    )

    # Heuristic scoring weights (must sum to 1.0 when all features are available)
    text_similarity_weight: float = 0.50
    geo_proximity_weight: float = 0.30
    temporal_proximity_weight: float = 0.20

    # Exponential decay parameters
    geo_decay_distance_m: float = 500.0  # 500 meters characteristic decay scale
    time_decay_hours: float = 168.0  # 7 days (168 hours) characteristic decay scale

    # Candidate retrieval and classification threshold
    duplicate_score_threshold: float = 0.65
    top_k_candidates: int = 10
    random_state: int = 42
    model_version: str = "v1"

    def ensure_directories(self) -> None:
        """Create artifact directory structure if needed."""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        (self.model_dir / "metadata").mkdir(parents=True, exist_ok=True)


config = DuplicateDetectionConfig()
