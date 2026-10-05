"""Model encapsulation for Road Failure Prediction (Phase 2)."""

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
from ml.failure_prediction.config import failure_config

logger = get_logger("failure_prediction.model")


class RoadFailureModel(BaseModel):
    """Encapsulates predictive tabular models (Logistic Regression, Random Forest, XGBoost) for RoadX."""

    def __init__(
        self,
        estimator: Optional[BaseEstimator] = None,
        model_name: str = failure_config.model_name,
        version: str = failure_config.model_version,
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
    ) -> RoadFailureModel:
        """Fit the underlying estimator on feature matrix X and target y."""
        if self.estimator is None:
            raise ValueError("No estimator specified for training.")

        if isinstance(X, pd.DataFrame):
            self.feature_names_ = list(X.columns)
        elif feature_names:
            self.feature_names_ = list(feature_names)

        logger.info("Training %s (%s) on %d samples", self.model_name, type(self.estimator).__name__, len(X))
        self.estimator.fit(X, y, **kwargs)
        self._is_fitted = True

        # Extract feature importances if available
        self._extract_feature_importances()
        return self

    def _extract_feature_importances(self) -> None:
        """Extract coefficients or tree feature importances if supported by estimator."""
        if not self._is_fitted or not self.feature_names_:
            return

        importances: Optional[np.ndarray] = None
        if hasattr(self.estimator, "feature_importances_"):
            importances = self.estimator.feature_importances_
        elif hasattr(self.estimator, "coef_"):
            importances = np.abs(self.estimator.coef_[0])

        if importances is not None and len(importances) == len(self.feature_names_):
            # Normalize to sum to 1.0 for comparability
            total = float(np.sum(importances))
            norm_importances = (importances / total) if total > 0 else importances
            self.feature_importances_ = {
                feat: round(float(imp), 4)
                for feat, imp in sorted(zip(self.feature_names_, norm_importances), key=lambda x: x[1], reverse=True)
            }

    def predict(self, X: Union[pd.DataFrame, np.ndarray], *args: Any, **kwargs: Any) -> np.ndarray:
        """Generate binary failure prediction (0 = Stable, 1 = Failure Expected in 30d)."""
        if not self._is_fitted or self.estimator is None:
            raise ModelNotFittedError(f"Model '{self.model_name}' has not been fitted or loaded.")
        return self.estimator.predict(X, *args, **kwargs)

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray], *args: Any, **kwargs: Any) -> np.ndarray:
        """Generate failure probability array (shape [N, 2] or positive class probabilities)."""
        if not self._is_fitted or self.estimator is None:
            raise ModelNotFittedError(f"Model '{self.model_name}' has not been fitted or loaded.")
        if hasattr(self.estimator, "predict_proba"):
            return self.estimator.predict_proba(X, *args, **kwargs)
        if hasattr(self.estimator, "decision_function"):
            # Fallback sigmoid for estimators with only decision_function
            df_vals = self.estimator.decision_function(X)
            probs_pos = 1.0 / (1.0 + np.exp(-df_vals))
            return np.vstack([1.0 - probs_pos, probs_pos]).T
        raise NotImplementedError("Estimator does not support probability estimation.")

    def save(self, path: Union[str, Path]) -> None:
        """Persist model and metadata via joblib."""
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
        logger.info("Saved model artifact to %s", save_path)

    @classmethod
    def load(cls, path: Union[str, Path]) -> RoadFailureModel:
        """Load persisted model artifact from disk."""
        load_path = Path(path)
        if not load_path.exists():
            raise ModelArtifactNotFoundError(f"Model artifact not found at: {load_path}")

        payload = joblib.load(load_path)
        instance = cls(
            estimator=payload["estimator"],
            model_name=payload.get("model_name", "road_failure_model"),
            version=payload.get("version", "v1"),
        )
        instance.feature_names_ = payload.get("feature_names", [])
        instance.feature_importances_ = payload.get("feature_importances", {})
        instance.metadata = payload.get("metadata", {})
        instance.training_metadata = payload.get("training_metadata", {})
        instance._is_fitted = True
        logger.info("Loaded model artifact '%s' (v%s) from %s", instance.model_name, instance.version, load_path)
        return instance


# Backward compatibility alias
RoadFailurePredictionModel = RoadFailureModel
