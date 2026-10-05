"""Time-to-Failure Prediction module for RoadX (Phase 7).

Forecasts expected remaining operational days before critical road failure
and predicts survival probability curves across 30, 90, 180, and 365 day horizons.
"""

from ml.time_to_failure.predictor import TimeToFailurePredictor
from ml.time_to_failure.survival_model import WeibullSurvivalModel, KaplanMeierEstimator
from ml.time_to_failure.preprocessing import SurvivalPreprocessor
from ml.time_to_failure.features import SurvivalFeatureBuilder
from ml.time_to_failure.schemas import (
    ConfidenceIntervalDays,
    SurvivalProbabilities,
    TimeToFailureOutput,
    TimeToFailureRiskLevel,
)

__all__ = [
    "TimeToFailurePredictor",
    "WeibullSurvivalModel",
    "KaplanMeierEstimator",
    "SurvivalPreprocessor",
    "SurvivalFeatureBuilder",
    "ConfidenceIntervalDays",
    "SurvivalProbabilities",
    "TimeToFailureOutput",
    "TimeToFailureRiskLevel",
]
