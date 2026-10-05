"""Configuration parameters for Road Damage Detection module."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set

from ml.common.config import settings


@dataclass
class DamageDetectionConfig:
    """Settings and hyperparameter defaults for computer vision damage detection."""

    model_name: str = "pothole_yolo_segmentation"
    model_version: str = "v1"

    # Relative path to existing trained weights checkpoint
    model_path: Path = field(
        default_factory=lambda: settings.models_dir / "pathole_detection.pt"
    )

    # Configurable detection thresholds
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45

    # Target class mappings (maps model index or class string to canonical RoadX names)
    canonical_class_map: dict[str, str] = field(
        default_factory=lambda: {
            "pothole": "pothole",
            "pathole": "pothole",
            "crack": "crack",
            "alligator crack": "crack",
        }
    )

    # Valid image extensions
    supported_extensions: Set[str] = field(
        default_factory=lambda: {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    )


damage_detection_config = DamageDetectionConfig()
