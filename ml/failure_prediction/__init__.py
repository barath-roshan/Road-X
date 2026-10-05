"""Road Failure Prediction ML module for RoadX.

Provides schemas, preprocessing, feature extraction, and predictive models
estimating the risk and likelihood of imminent structural failure in reported roads.
"""

from ml.failure_prediction.config import FailurePredictionConfig, failure_config
from ml.failure_prediction.features import FailureFeatureExtractor
from ml.failure_prediction.model import RoadFailurePredictionModel
from ml.failure_prediction.preprocessing import FailureDataPreprocessor
from ml.failure_prediction.schemas import (
    FailurePredictionOutput,
    FailureRiskLevel,
    RoadGrievanceInput,
)

__all__ = [
    "FailurePredictionConfig",
    "failure_config",
    "FailureDataPreprocessor",
    "FailureFeatureExtractor",
    "RoadFailurePredictionModel",
    "RoadGrievanceInput",
    "FailurePredictionOutput",
    "FailureRiskLevel",
]
