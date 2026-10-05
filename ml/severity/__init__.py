"""Damage Severity Estimation module for RoadX (Phase 4).

Estimates physical defect intensity, road surface hazard rating, and structural
damage magnitude using normalized outputs from the Phase 3 damage detection model
and optional road infrastructure context.
"""

from ml.severity.config import SeverityConfig, severity_config
from ml.severity.evaluate import evaluate_severity_model, score_to_level
from ml.severity.features import SeverityFeatureExtractor
from ml.severity.model import DamageSeverityModel
from ml.severity.predict import DamageSeverityPredictor, predict_damage_severity
from ml.severity.preprocessing import SeverityPreprocessor
from ml.severity.schemas import (
    DamageSeverityLevel,
    DamageSeverityResponse,
    RoadContextInput,
    SeverityPredictionOutput,
)

__all__ = [
    "SeverityConfig",
    "severity_config",
    "DamageSeverityLevel",
    "RoadContextInput",
    "SeverityPredictionOutput",
    "DamageSeverityResponse",
    "SeverityFeatureExtractor",
    "SeverityPreprocessor",
    "DamageSeverityModel",
    "DamageSeverityPredictor",
    "predict_damage_severity",
    "evaluate_severity_model",
    "score_to_level",
]
