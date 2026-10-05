"""Configuration settings and constants for Complaint Intelligence (Phase 5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from ml.common.config import settings


# Taxonomy definitions for RoadX citizen complaints
DEFAULT_ISSUE_CATEGORIES: List[str] = [
    "POTHOLE",
    "ROAD_CRACK",
    "ROAD_SURFACE_DAMAGE",
    "WATERLOGGING",
    "FLOODING",
    "STREETLIGHT",
    "ACCIDENT",
    "ROAD_OBSTRUCTION",
    "DEBRIS",
    "TRAFFIC_SIGNAL",
    "ROAD_CLOSURE",
    "OTHER",
]

DEFAULT_URGENCY_LEVELS: List[str] = [
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
]

DEFAULT_SAFETY_RISK_LEVELS: List[str] = [
    "LOW",
    "MEDIUM",
    "HIGH",
]

DEFAULT_LOCATION_TYPES: List[str] = [
    "ROAD",
    "LANDMARK",
    "AREA",
    "LOCALITY",
    "BUS_STOP",
    "INTERSECTION",
]


@dataclass
class ComplaintIntelligenceConfig:
    """Configuration container for complaint intelligence models and pipelines."""

    model_dir: Path = field(
        default_factory=lambda: settings.models_dir / "complaint_intelligence"
    )
    raw_dataset_path: Path = field(
        default_factory=lambda: settings.raw_data_dir / "synthetic_citizen_complaints.csv"
    )

    issue_categories: List[str] = field(default_factory=lambda: list(DEFAULT_ISSUE_CATEGORIES))
    urgency_levels: List[str] = field(default_factory=lambda: list(DEFAULT_URGENCY_LEVELS))
    safety_risk_levels: List[str] = field(default_factory=lambda: list(DEFAULT_SAFETY_RISK_LEVELS))
    location_types: List[str] = field(default_factory=lambda: list(DEFAULT_LOCATION_TYPES))

    # Vectorizer parameters
    max_features: int = 1000
    ngram_range: Tuple[int, int] = (1, 2)
    sublinear_tf: bool = True
    embedding_dim: int = 300

    # Training parameters
    test_size: float = 0.2
    random_state: int = 42
    model_version: str = "v1"

    def ensure_directories(self) -> None:
        """Create artifact directory structure if needed."""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        (self.model_dir / "issue_classifier").mkdir(parents=True, exist_ok=True)
        (self.model_dir / "urgency_classifier").mkdir(parents=True, exist_ok=True)
        (self.model_dir / "safety_classifier").mkdir(parents=True, exist_ok=True)
        (self.model_dir / "metadata").mkdir(parents=True, exist_ok=True)


config = ComplaintIntelligenceConfig()
