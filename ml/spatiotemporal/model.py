"""Spatiotemporal Model Encapsulation for Road Failure Prediction (Phase 20)."""

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
from ml.spatiotemporal.config import spatiotemporal_config

logger = get_logger("spatiotemporal.model")


class SpatiotemporalFailureModel(BaseModel):
    """Encapsulates predictive spatiotemporal models trained on road condition, spatial, and temporal features."""

    def __init__(
        self,
        estimator: Optional[BaseEstimator] = None,
        model_name: str = spatiotemporal_config.model_name,
        version: str = spatiotemporal_config.model_version,
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
    ) -> SpatiotemporalFailureModel:
        """Fit underlying spatiotemporal classifier on feature matrix X and target y."""
        if self.estimator is None:
            raise ValueError("No estimator specified for spatiotemporal model training.")

        if isinstance(X, pd.DataFrame):
            self.feature_names_ = list(X.columns)
        elif feature_names:
            self.feature_names_ = list(feature_names)

        logger.info("Training %s on %d samples with %d features", self.model_name, len(X), len(self.feature_names_))
        self.estimator.fit(X, y, **kwargs)
        self._is_fitted = True

        self._extract_feature_importances()
        return self

    def _extract_feature_importances(self) -> None:
        """Extract feature importances from calibrated or base estimator."""
        if not self._is_fitted or not self.feature_names_:
            return

        estimator = self.estimator
        # Handle CalibratedClassifierCV
        if hasattr(estimator, "calibrated_classifiers_") and estimator.calibrated_classifiers_:
            base = estimator.calibrated_classifiers_[0].estimator
            if hasattr(base, "feature_importances_"):
                importances = base.feature_importances_
            else:
                return
        elif hasattr(estimator, "feature_importances_"):
            importances = estimator.feature_importances_
        else:
            return

        if len(importances) == len(self.feature_names_):
            total = float(np.sum(importances))
            norm_importances = (importances / total) if total > 0 else importances
            self.feature_importances_ = {
                feat: round(float(imp), 4)
                for feat, imp in sorted(zip(self.feature_names_, norm_importances), key=lambda x: x[1], reverse=True)
            }

    def predict(self, X: Union[pd.DataFrame, np.ndarray], *args: Any, **kwargs: Any) -> np.ndarray:
        """Generate binary failure prediction (0 = Stable, 1 = Failure Expected in 30d)."""
        if not self._is_fitted or self.estimator is None:
            raise ModelNotFittedError(f"Spatiotemporal model '{self.model_name}' is not fitted.")
        return self.estimator.predict(X, *args, **kwargs)

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray], *args: Any, **kwargs: Any) -> np.ndarray:
        """Generate failure probability array [N, 2]."""
        if not self._is_fitted or self.estimator is None:
            raise ModelNotFittedError(f"Spatiotemporal model '{self.model_name}' is not fitted.")
        if hasattr(self.estimator, "predict_proba"):
            return self.estimator.predict_proba(X, *args, **kwargs)
        raise NotImplementedError("Estimator does not support predict_proba.")

    def save(self, path: Union[str, Path]) -> None:
        """Persist model and metadata to disk via joblib."""
        if not self._is_fitted:
            raise ModelNotFittedError("Cannot save unfitted model.")
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "model_name": self.model_name,
            "version": self.version,
            "estimator": self.estimator,
            "feature_names": self.feature_names_,
            "feature_importances": self.feature_importances_,
            "training_metadata": self.training_metadata,
        }
        joblib.dump(payload, save_path)
        logger.info("Saved spatiotemporal model artifact to %s", save_path)

    @classmethod
    def load(cls, path: Union[str, Path]) -> SpatiotemporalFailureModel:
        """Load persisted spatiotemporal model artifact from disk."""
        load_path = Path(path)
        if not load_path.exists():
            raise ModelArtifactNotFoundError(f"Spatiotemporal artifact not found at: {load_path}")

        payload = joblib.load(load_path)
        instance = cls(
            estimator=payload["estimator"],
            model_name=payload.get("model_name", "spatiotemporal_failure_model"),
            version=payload.get("version", "v2.0_spatiotemporal"),
        )
        instance.feature_names_ = payload.get("feature_names", [])
        instance.feature_importances_ = payload.get("feature_importances", {})
        instance.training_metadata = payload.get("training_metadata", {})
        instance._is_fitted = True
        logger.info("Loaded spatiotemporal model artifact '%s' from %s", instance.model_name, load_path)
        return instance
