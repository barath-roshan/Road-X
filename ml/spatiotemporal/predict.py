"""Inference service for Phase 20 Spatiotemporal Road Failure Prediction."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd

from ml.common.exceptions import ModelArtifactNotFoundError, RoadXDataError
from ml.common.logging_config import get_logger
from ml.failure_prediction.config import failure_config
from ml.failure_prediction.preprocessing import RoadFailurePreprocessor
from ml.failure_prediction.schemas import (
    FailurePredictionOutput,
    FailureRiskLevel,
    RoadFailureInput,
)
from ml.spatiotemporal.config import spatiotemporal_config
from ml.spatiotemporal.dataset import SpatiotemporalDatasetBuilder
from ml.spatiotemporal.model import SpatiotemporalFailureModel

logger = get_logger("spatiotemporal.predict")


class SpatiotemporalPredictor:
    """Production inference engine for Spatiotemporal Road Failure Prediction."""

    def __init__(
        self,
        model_artifact_path: Optional[Union[str, Path]] = None,
        artifact_bundle: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.artifact_path = Path(model_artifact_path or spatiotemporal_config.artifact_file)
        self.model: Optional[SpatiotemporalFailureModel] = None
        self.preprocessor: Optional[RoadFailurePreprocessor] = None
        self.dataset_builder: Optional[SpatiotemporalDatasetBuilder] = None
        self.risk_thresholds = spatiotemporal_config.risk_thresholds
        self.version = spatiotemporal_config.model_version
        self.feature_names: List[str] = []

        if artifact_bundle:
            self._load_from_bundle(artifact_bundle)
        elif self.artifact_path.exists():
            self.load(self.artifact_path)
        else:
            # Fallback initialization if artifact file not yet compiled on disk
            self.dataset_builder = SpatiotemporalDatasetBuilder()

    def load(self, artifact_path: Union[str, Path]) -> SpatiotemporalPredictor:
        """Load complete serialized spatiotemporal inference bundle."""
        path = Path(artifact_path)
        if not path.exists():
            raise ModelArtifactNotFoundError(f"Spatiotemporal artifact bundle not found at: {path}")

        bundle = joblib.load(path)
        self._load_from_bundle(bundle)
        logger.info("Successfully loaded SpatiotemporalPredictor bundle from: %s", path)
        return self

    def _load_from_bundle(self, bundle: Dict[str, Any]) -> None:
        """Initialize components from deserialized artifact dictionary."""
        self.model = bundle["model"]
        self.preprocessor = bundle["preprocessor"]
        self.dataset_builder = bundle.get("dataset_builder") or SpatiotemporalDatasetBuilder()
        self.risk_thresholds = bundle.get("risk_thresholds", spatiotemporal_config.risk_thresholds)
        self.version = bundle.get("version", spatiotemporal_config.model_version)
        self.feature_names = bundle.get("feature_names", [])

    def map_probability_to_risk(self, probability: float) -> FailureRiskLevel:
        """Map continuous failure probability into administrative risk level."""
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
        """Identify key spatial, temporal, and structural drivers contributing to predicted risk."""
        if not self.model or not self.model.feature_importances_:
            return ["Structural Pavement Age", "Traffic Load Stress", "Precipitation Impact"]

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
        """Generate spatiotemporal failure probability and risk level for single or batch inputs.

        Args:
            input_data: Single dictionary/RoadFailureInput or DataFrame of road segments.

        Returns:
            FailurePredictionOutput object or list of outputs.
        """
        if self.dataset_builder is None:
            self.dataset_builder = SpatiotemporalDatasetBuilder()

        is_single = False
        if isinstance(input_data, (dict, RoadFailureInput)):
            is_single = True
            raw_dict = input_data.model_dump() if isinstance(input_data, RoadFailureInput) else input_data
            df_raw = pd.DataFrame([raw_dict])
        elif isinstance(input_data, pd.DataFrame):
            df_raw = input_data.copy()
        else:
            raise RoadXDataError(f"Unsupported input type for spatiotemporal prediction: {type(input_data)}")

        # Clean/preprocess if preprocessor available
        if self.preprocessor:
            clean_df = self.preprocessor.transform(df_raw)
        else:
            clean_df = df_raw.copy()

        # Build spatiotemporal feature matrix
        features_df, _ = self.dataset_builder.build_feature_matrix(clean_df)

        # Align columns to trained feature expectation
        if self.feature_names:
            for col in self.feature_names:
                if col not in features_df.columns:
                    features_df[col] = 0.0
            features_df = features_df[self.feature_names]

        if self.model and self.model._is_fitted:
            probabilities = self.model.predict_proba(features_df)
            probs_pos = probabilities[:, 1] if probabilities.ndim == 2 else probabilities
        else:
            # Fallback heuristic calculation if model uncompiled
            quality = features_df.get("road_quality_score", pd.Series([0.5] * len(features_df)))
            traffic_stress = features_df.get("traffic_stress", pd.Series([1000.0] * len(features_df)))
            probs_pos = np.clip(1.0 - quality + (traffic_stress / 50000.0), 0.05, 0.95).values

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
