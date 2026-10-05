"""Road Failure Prediction ML module for RoadX (Phase 2).

Provides schemas, preprocessing, feature extraction, progressive model architectures
(Logistic Regression, Random Forest, XGBoost), probability calibration, and risk prediction.
"""

from ml.failure_prediction.config import FailurePredictionConfig, failure_config
from ml.failure_prediction.evaluate import evaluate_model, format_comparison_table
from ml.failure_prediction.features import (
    FailureFeatureExtractor,
    RoadFailureFeatureBuilder,
)
from ml.failure_prediction.model import (
    RoadFailureModel,
    RoadFailurePredictionModel,
)
from ml.failure_prediction.predict import (
    RoadFailurePredictor,
    predict_failure_risk,
)
from ml.failure_prediction.preprocessing import (
    FailureDataPreprocessor,
    RoadFailurePreprocessor,
)
from ml.failure_prediction.schemas import (
    FailurePredictionOutput,
    FailureRiskLevel,
    RoadFailureInput,
    RoadFailurePredictionResponse,
    RoadGrievanceInput,
)

__all__ = [
    "FailurePredictionConfig",
    "failure_config",
    "RoadFailureInput",
    "FailurePredictionOutput",
    "FailureRiskLevel",
    "RoadGrievanceInput",
    "RoadFailurePredictionResponse",
    "RoadFailurePreprocessor",
    "FailureDataPreprocessor",
    "RoadFailureFeatureBuilder",
    "FailureFeatureExtractor",
    "RoadFailureModel",
    "RoadFailurePredictionModel",
    "RoadFailurePredictor",
    "predict_failure_risk",
    "evaluate_model",
    "format_comparison_table",
]
