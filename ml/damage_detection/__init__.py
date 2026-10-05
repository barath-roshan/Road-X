"""Road Damage Detection module for RoadX (Phase 3).

Integrates the pre-existing trained pothole detection and segmentation model
(models/pathole_detection.pt) via a clean adapter abstraction layer (ExistingPotholeModelAdapter),
normalizing framework predictions into unified RoadX schemas.
"""

from ml.damage_detection.adapter import ExistingPotholeModelAdapter
from ml.damage_detection.config import DamageDetectionConfig, damage_detection_config
from ml.damage_detection.detector import RoadDamageDetector
from ml.damage_detection.schemas import (
    DamageDetection,
    DetectedDamageItem,
    RoadDamageDetectionResponse,
)

__all__ = [
    "RoadDamageDetector",
    "ExistingPotholeModelAdapter",
    "RoadDamageDetectionResponse",
    "DetectedDamageItem",
    "DamageDetection",
    "DamageDetectionConfig",
    "damage_detection_config",
]
