"""Text classification models for Issue Category, Urgency, and Safety Risk (Phase 5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple, Union, Optional
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier

from ml.common.base import BaseModel
from ml.common.exceptions import ModelNotFittedError, ModelArtifactNotFoundError, RoadXModelError
from ml.complaint_intelligence.config import config
from ml.complaint_intelligence.schemas import IssueCategory, UrgencyLevel, SafetyRiskLevel


class TextClassifierBase(BaseModel):
    """Base class wrapping sklearn classifier for multi-class text categorization."""

    def __init__(self, model_name: str, allowed_classes: List[str], version: str = "v1") -> None:
        super().__init__(model_name=model_name, version=version)
        self.allowed_classes = allowed_classes
        self.clf = LogisticRegression(
            C=1.0,
            max_iter=1000,
            class_weight="balanced",
            solver="lbfgs",
            random_state=config.random_state,
        )

    def train(self, X: Any, y: List[str], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Train classifier on feature matrix X and string labels y."""
        if len(y) == 0:
            raise RoadXModelError("Cannot train classifier on empty label set.")

        self.clf.fit(X, y)
        self._is_fitted = True
        self.metadata = {
            "model_name": self.model_name,
            "version": self.version,
            "classes": list(self.clf.classes_),
            "n_samples": X.shape[0] if hasattr(X, "shape") else len(y),
        }
        return self.metadata

    def predict(self, X: Any, *args: Any, **kwargs: Any) -> List[str]:
        """Predict target class names for feature matrix X."""
        if not self._is_fitted:
            raise ModelNotFittedError(f"{self.model_name} must be trained before predicting.")
        predictions = self.clf.predict(X)
        return list(predictions)

    def predict_proba(self, X: Any, *args: Any, **kwargs: Any) -> np.ndarray:
        """Predict class probability distribution for feature matrix X."""
        if not self._is_fitted:
            raise ModelNotFittedError(f"{self.model_name} must be trained before calling predict_proba.")
        return self.clf.predict_proba(X)

    def predict_with_confidence(self, X: Any) -> List[Tuple[str, float]]:
        """Predict top class and return its calibrated probability confidence score."""
        if not self._is_fitted:
            raise ModelNotFittedError(f"{self.model_name} must be trained before predicting.")

        probas = self.predict_proba(X)
        classes = self.clf.classes_
        results = []

        for row in probas:
            top_idx = int(np.argmax(row))
            predicted_label = str(classes[top_idx])
            confidence = float(row[top_idx])
            results.append((predicted_label, confidence))

        return results

    def save(self, path: Union[str, Path]) -> None:
        """Save trained classifier artifact to disk."""
        if not self._is_fitted:
            raise ModelNotFittedError(f"Cannot save un-fitted {self.model_name}.")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        artifact = {
            "model_name": self.model_name,
            "version": self.version,
            "allowed_classes": self.allowed_classes,
            "clf": self.clf,
            "is_fitted": self._is_fitted,
            "metadata": self.metadata,
        }
        joblib.dump(artifact, path)

    @classmethod
    def load(cls, path: Union[str, Path]) -> TextClassifierBase:
        """Load trained classifier artifact from disk."""
        if not path.exists():
            raise ModelArtifactNotFoundError(f"Classifier artifact not found at: {path}")

        data = joblib.load(path)

        if cls is TextClassifierBase:
            instance = cls(
                model_name=data.get("model_name", "TextClassifier"),
                allowed_classes=data.get("allowed_classes", []),
                version=data.get("version", "v1"),
            )
        else:
            instance = cls(version=data.get("version", "v1"))

        instance.clf = data["clf"]
        instance._is_fitted = data.get("is_fitted", True)
        instance.metadata = data.get("metadata", {})
        return instance


class IssueClassifier(TextClassifierBase):
    """Classifier predicting primary RoadX grievance issue category."""

    def __init__(self, version: str = "v1") -> None:
        super().__init__(
            model_name="IssueClassifier",
            allowed_classes=config.issue_categories,
            version=version,
        )


class UrgencyClassifier(TextClassifierBase):
    """Classifier predicting citizen complaint response urgency level."""

    def __init__(self, version: str = "v1") -> None:
        super().__init__(
            model_name="UrgencyClassifier",
            allowed_classes=config.urgency_levels,
            version=version,
        )


class SafetyRiskClassifier(TextClassifierBase):
    """Classifier predicting road hazard safety risk level."""

    def __init__(self, version: str = "v1") -> None:
        super().__init__(
            model_name="SafetyRiskClassifier",
            allowed_classes=config.safety_risk_levels,
            version=version,
        )
