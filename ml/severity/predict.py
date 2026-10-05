"""Inference engine and predictor for Damage Severity Estimation (Phase 4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd

from ml.common.exceptions import ModelArtifactNotFoundError, RoadXDataError
from ml.common.logging_config import get_logger
from ml.damage_detection.schemas import RoadDamageDetectionResponse
from ml.severity.config import severity_config
from ml.severity.evaluate import score_to_level
from ml.severity.features import SeverityFeatureExtractor
from ml.severity.model import DamageSeverityModel
from ml.severity.preprocessing import SeverityPreprocessor
from ml.severity.schemas import (
    DamageSeverityLevel,
    RoadContextInput,
    SeverityPredictionOutput,
)

logger = get_logger("severity.predict")


class DamageSeverityPredictor:
    """Production inference service for estimating road damage severity scores and levels."""

    def __init__(
        self,
        model_artifact_path: Optional[Union[str, Path]] = None,
        artifact_bundle: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.artifact_path = Path(model_artifact_path or severity_config.artifact_file)
        self.model: Optional[DamageSeverityModel] = None
        self.preprocessor: Optional[SeverityPreprocessor] = None
        self.feature_extractor: Optional[SeverityFeatureExtractor] = None
        self.level_thresholds = severity_config.level_thresholds
        self.version = severity_config.model_version
        self.feature_names: List[str] = []

        if artifact_bundle:
            self._load_from_bundle(artifact_bundle)
        elif self.artifact_path.exists():
            self.load(self.artifact_path)

    def load(self, artifact_path: Union[str, Path]) -> DamageSeverityPredictor:
        """Load complete serialized severity pipeline bundle."""
        path = Path(artifact_path)
        if not path.exists():
            raise ModelArtifactNotFoundError(f"Severity artifact bundle not found at: {path}")

        bundle = joblib.load(path)
        self._load_from_bundle(bundle)
        logger.info("Successfully loaded DamageSeverityPredictor bundle from: %s", path)
        return self

    def _load_from_bundle(self, bundle: Dict[str, Any]) -> None:
        """Initialize components from deserialized artifact dictionary."""
        self.model = bundle["model"]
        self.preprocessor = bundle["preprocessor"]
        self.feature_extractor = bundle["feature_extractor"]
        self.level_thresholds = bundle.get("level_thresholds", severity_config.level_thresholds)
        self.version = bundle.get("version", severity_config.model_version)
        self.feature_names = bundle.get("feature_names", [])

    def map_score_to_level(self, score: float) -> DamageSeverityLevel:
        """Map continuous severity score (0.0 to 100.0) into categorical presentation level."""
        return score_to_level(score, self.level_thresholds)

    def _extract_contributing_factors(
        self,
        feature_dict: Dict[str, float],
        top_k: int = 3,
    ) -> List[str]:
        """Derive model-driven explanation factors for predicted severity."""
        if not self.model or not self.model.feature_importances_:
            return []

        factors = []
        importances = self.model.feature_importances_

        # Sort features by global model importance
        sorted_feats = sorted(importances.items(), key=lambda x: x[1], reverse=True)

        for feat, imp in sorted_feats[:top_k]:
            val = feature_dict.get(feat, None)
            if val is not None:
                if feat == "total_area_ratio":
                    factors.append(f"damaged surface area ratio ({val:.2f})")
                elif feat == "detection_count":
                    factors.append(f"multiple defect instances detected ({int(val)})")
                elif feat == "quality_defect_ratio":
                    factors.append(f"high defect density relative to road quality ({val:.2f})")
                elif feat == "road_quality_score":
                    factors.append(f"poor underlying pavement quality index ({val:.2f})")
                elif feat == "traffic_damage_interaction":
                    factors.append(f"high heavy vehicular traffic exposure ({val:.0f})")
                else:
                    factors.append(f"{feat.replace('_', ' ')} (val={val}, weight={imp:.2f})")

        return factors

    def predict(
        self,
        detections: Union[RoadDamageDetectionResponse, Dict[str, Any]],
        road_context: Optional[Union[RoadContextInput, Dict[str, Any]]] = None,
    ) -> SeverityPredictionOutput:
        """Estimate damage severity score and presentation level for a detection report.

        Args:
            detections: Normalized vision detection output from Phase 3 detector.
            road_context: Optional road segment infrastructure context.

        Returns:
            SeverityPredictionOutput schema object.
        """
        if self.model is None or self.preprocessor is None or self.feature_extractor is None:
            raise ModelArtifactNotFoundError("DamageSeverityPredictor is not initialized with a trained model bundle.")

        # 1. Extract feature dictionary
        feat_dict = self.feature_extractor.extract_from_detection_response(detections, road_context)
        validated_dict = self.preprocessor.validate_record(feat_dict)

        # Convert to DataFrame
        df_raw = pd.DataFrame([validated_dict])
        clean_df = self.preprocessor.transform(df_raw)
        features_df = self.feature_extractor.transform(clean_df)

        # Align column order strictly to model expectations
        if self.feature_names:
            for col in self.feature_names:
                if col not in features_df.columns:
                    features_df[col] = 0.0
            features_df = features_df[self.feature_names]

        # 2. Predict continuous severity score
        score_arr = self.model.predict(features_df)
        raw_score = float(score_arr[0])
        score = round(float(np.clip(raw_score, 0.0, 100.0)), 1)

        # 3. Map to presentation level
        level = self.map_score_to_level(score)

        # 4. Extract model-driven explanation factors
        factors = self._extract_contributing_factors(feat_dict)

        return SeverityPredictionOutput(
            severity_score=score,
            severity_level=level,
            contributing_factors=factors,
            model_version=self.version,
        )


def predict_damage_severity(
    detections: Union[RoadDamageDetectionResponse, Dict[str, Any]],
    road_context: Optional[Union[RoadContextInput, Dict[str, Any]]] = None,
    predictor: Optional[DamageSeverityPredictor] = None,
) -> SeverityPredictionOutput:
    """Convenience function executing severity estimation through loaded predictor."""
    p = predictor or DamageSeverityPredictor()
    return p.predict(detections=detections, road_context=road_context)
