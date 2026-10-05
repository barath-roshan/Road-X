"""Model encapsulation for Damage Severity Estimation (Phase 4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator

from ml.common.base import BaseModel
from ml.common.exceptions import ModelArtifactNotFoundError, ModelNotFittedError
from ml.common.logging_config import get_logger
from ml.severity.config import severity_config

logger = get_logger("severity.model")


class DamageSeverityModel(BaseModel):
    """Encapsulates tabular regression models (Ridge, Random Forest, XGBoost) for RoadX severity estimation."""

    def __init__(
        self,
        estimator: Optional[BaseEstimator] = None,
        model_name: str = severity_config.model_name,
        version: str = severity_config.model_version,
    ) -> None:
        super().__init__(model_name=model_name, version=version)
        self.estimator = estimator
        self.feature_names_: List[str] = []
        self.feature_importances_: Dict[str, float] = {}
        self.training_metadata: Dict[str, Any] = {}

    def train(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        feature_names: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> DamageSeverityModel:
        """Fit the underlying regressor on feature matrix X and continuous target y."""
        if self.estimator is None:
            raise ValueError("No estimator specified for training.")

        if isinstance(X, pd.DataFrame):
            self.feature_names_ = list(X.columns)
        elif feature_names:
            self.feature_names_ = list(feature_names)

        logger.info("Training %s (%s) on %d samples", self.model_name, type(self.estimator).__name__, len(X))
        self.estimator.fit(X, y, **kwargs)
        self._is_fitted = True

        self._extract_feature_importances()
        return self

    def _extract_feature_importances(self) -> None:
        """Extract feature importances or coefficient magnitudes."""
        if not self._is_fitted or not self.feature_names_:
            return

        importances: Optional[np.ndarray] = None
        if hasattr(self.estimator, "feature_importances_"):
            importances = self.estimator.feature_importances_
        elif hasattr(self.estimator, "coef_"):
            importances = np.abs(self.estimator.coef_)

        if importances is not None and len(importances) == len(self.feature_names_):
            total = float(np.sum(importances))
            norm_importances = (importances / total) if total > 0 else importances
            self.feature_importances_ = {
                feat: round(float(imp), 4)
                for feat, imp in sorted(zip(self.feature_names_, norm_importances), key=lambda x: x[1], reverse=True)
            }

    def predict(self, X: Union[pd.DataFrame, np.ndarray], *args: Any, **kwargs: Any) -> np.ndarray:
        """Predict continuous severity score (0.0 to 100.0)."""
        if not self._is_fitted or self.estimator is None:
            raise ModelNotFittedError(f"Model '{self.model_name}' has not been fitted or loaded.")

        raw_preds = self.estimator.predict(X, *args, **kwargs)
        # Clip predicted severity score between 0.0 and 100.0
        return np.clip(raw_preds, 0.0, 100.0)

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray], *args: Any, **kwargs: Any) -> Any:
        """Regression models return None for class probability queries."""
        return None

    def save(self, path: Union[str, Path]) -> None:
        """Persist model artifact to disk."""
        if not self._is_fitted:
            raise ModelNotFittedError("Cannot save an unfitted model.")
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "model_name": self.model_name,
            "version": self.version,
            "estimator": self.estimator,
            "feature_names": self.feature_names_,
            "feature_importances": self.feature_importances_,
            "metadata": self.metadata,
            "training_metadata": self.training_metadata,
        }
        joblib.dump(payload, save_path)
        logger.info("Saved severity model artifact to %s", save_path)

    @classmethod
    def load(cls, path: Union[str, Path]) -> DamageSeverityModel:
        """Load persisted model artifact from disk."""
        load_path = Path(path)
        if not load_path.exists():
            raise ModelArtifactNotFoundError(f"Severity model artifact not found at: {load_path}")

        payload = joblib.load(load_path)
        instance = cls(
            estimator=payload["estimator"],
            model_name=payload.get("model_name", "road_damage_severity"),
            version=payload.get("version", "v1"),
        )
        instance.feature_names_ = payload.get("feature_names", [])
        instance.feature_importances_ = payload.get("feature_importances", {})
        instance.metadata = payload.get("metadata", {})
        instance.training_metadata = payload.get("training_metadata", {})
        instance._is_fitted = True
        logger.info("Loaded severity model '%s' (v%s) from %s", instance.model_name, instance.version, load_path)
        return instance
