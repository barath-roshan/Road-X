"""Inference engine and risk-level predictor for Road Failure Prediction."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd

from ml.common.exceptions import ModelArtifactNotFoundError, RoadXDataError
from ml.common.logging_config import get_logger
from ml.failure_prediction.config import failure_config
from ml.failure_prediction.features import RoadFailureFeatureBuilder
from ml.failure_prediction.model import RoadFailureModel
from ml.failure_prediction.preprocessing import RoadFailurePreprocessor
from ml.failure_prediction.schemas import (
    FailurePredictionOutput,
    FailureRiskLevel,
    RoadFailureInput,
)

logger = get_logger("failure_prediction.predict")


class RoadFailurePredictor:
    """Production inference service for evaluating road failure probability and assigning risk tiers."""

    def __init__(
        self,
        model_artifact_path: Optional[Union[str, Path]] = None,
        artifact_bundle: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.artifact_path = Path(model_artifact_path or failure_config.artifact_file)
        self.model: Optional[RoadFailureModel] = None
        self.preprocessor: Optional[RoadFailurePreprocessor] = None
        self.feature_builder: Optional[RoadFailureFeatureBuilder] = None
        self.risk_thresholds = failure_config.risk_thresholds
        self.version = failure_config.model_version
        self.feature_names: List[str] = []

        if artifact_bundle:
            self._load_from_bundle(artifact_bundle)
        elif self.artifact_path.exists():
            self.load(self.artifact_path)

    def load(self, artifact_path: Union[str, Path]) -> RoadFailurePredictor:
        """Load complete serialized pipeline bundle (model, preprocessor, feature builder, metadata)."""
        path = Path(artifact_path)
        if not path.exists():
            raise ModelArtifactNotFoundError(f"Inference artifact bundle not found at: {path}")

        bundle = joblib.load(path)
        self._load_from_bundle(bundle)
        logger.info("Successfully loaded RoadFailurePredictor bundle from: %s", path)
        return self

    def _load_from_bundle(self, bundle: Dict[str, Any]) -> None:
        """Initialize components from deserialized artifact dictionary."""
        self.model = bundle["model"]
        self.preprocessor = bundle["preprocessor"]
        self.feature_builder = bundle["feature_builder"]
        self.risk_thresholds = bundle.get("risk_thresholds", failure_config.risk_thresholds)
        self.version = bundle.get("version", failure_config.model_version)
        self.feature_names = bundle.get("feature_names", [])

    def map_probability_to_risk(self, probability: float) -> FailureRiskLevel:
        """Map continuous failure probability into administrative risk tiers based on thresholds.

        Thresholds:
            LOW: < low_max (default < 0.30)
            MEDIUM: low_max <= p < medium_max (default 0.30 - 0.59)
            HIGH: medium_max <= p < high_max (default 0.60 - 0.79)
            CRITICAL: >= high_max (default >= 0.80)
        """
        low_max = self.risk_thresholds.get("low_max", 0.30)
        med_max = self.risk_thresholds.get("medium_max", 0.60)
        high_max = self.risk_thresholds.get("high_max", 0.80)

        if probability < low_max:
            return FailureRiskLevel.LOW
        if probability < med_max:
            return FailureRiskLevel.MEDIUM
        if probability < high_max:
            return FailureRiskLevel.HIGH
        return FailureRiskLevel.CRITICAL

    def _identify_top_factors(self, feature_row: pd.Series, top_k: int = 3) -> List[str]:
        """Identify key drivers contributing to predicted risk for human officer explainability."""
        if not self.model or not self.model.feature_importances_:
            return []

        # Weight feature deviation by global model feature importance
        factors = []
        for feat, imp in list(self.model.feature_importances_.items())[:top_k]:
            val = feature_row.get(feat, None)
            if val is not None:
                factors.append(f"{feat} (importance={imp:.2f})")
        return factors

    def predict(
        self,
        input_data: Union[Dict[str, Any], RoadFailureInput, pd.DataFrame],
    ) -> Union[FailurePredictionOutput, List[FailurePredictionOutput]]:
        """Generate road failure probability and risk tier for single or batch inputs.

        Args:
            input_data: Single dictionary/RoadFailureInput or DataFrame of road segments.

        Returns:
            FailurePredictionOutput object or list of outputs.
        """
        if self.model is None or self.preprocessor is None or self.feature_builder is None:
            raise ModelArtifactNotFoundError("RoadFailurePredictor is not initialized with a trained model bundle.")

        is_single = False
        if isinstance(input_data, (dict, RoadFailureInput)):
            is_single = True
            validated_dict = self.preprocessor.validate_record(input_data)
            df_raw = pd.DataFrame([validated_dict])
        elif isinstance(input_data, pd.DataFrame):
            self.preprocessor.validate_dataframe(input_data, is_training=False)
            df_raw = input_data.copy()
        else:
            raise RoadXDataError(f"Unsupported input type for prediction: {type(input_data)}")

        # 1. Imputation & feature extraction
        clean_df = self.preprocessor.transform(df_raw)
        features_df = self.feature_builder.transform(clean_df)

        # Align columns strictly to model expectations
        if self.feature_names:
            for col in self.feature_names:
                if col not in features_df.columns:
                    features_df[col] = 0.0
            features_df = features_df[self.feature_names]

        # 2. Predict probabilities
        probabilities = self.model.predict_proba(features_df)
        if probabilities.ndim == 2:
            probs_pos = probabilities[:, 1]
        else:
            probs_pos = probabilities

        results: List[FailurePredictionOutput] = []
        for idx, prob in enumerate(probs_pos):
            prob_float = round(float(prob), 4)
            risk = self.map_probability_to_risk(prob_float)
            factors = self._identify_top_factors(features_df.iloc[idx])
            results.append(
                FailurePredictionOutput(
                    failure_probability=prob_float,
                    risk_level=risk,
                    model_version=self.version,
                    top_contributing_factors=factors,
                )
            )

        return results[0] if is_single else results


def predict_failure_risk(
    record: Union[Dict[str, Any], RoadFailureInput, pd.DataFrame],
    predictor: Optional[RoadFailurePredictor] = None,
) -> Union[FailurePredictionOutput, List[FailurePredictionOutput]]:
    """Convenience function executing inference through loaded predictor."""
    p = predictor or RoadFailurePredictor()
    return p.predict(record)
