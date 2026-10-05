"""DuplicateScorer combining text similarity, spatial, and temporal proximity evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from ml.common.base import BaseModel
from ml.common.exceptions import ModelNotFittedError, ModelArtifactNotFoundError, RoadXModelError
from ml.duplicate_detection.config import config
from ml.duplicate_detection.features import GeographicTemporalFeatureBuilder
from ml.duplicate_detection.schemas import DuplicateCandidate, DuplicateEvidence


class DuplicateScorer(BaseModel):
    """Scorer calculating composite duplicate likelihood scores for candidate complaints.

    Supports both transparent heuristic scoring with feature re-weighting and supervised
    LogisticRegression classification when labeled training pairs exist.
    """

    def __init__(
        self,
        text_weight: float = config.text_similarity_weight,
        geo_weight: float = config.geo_proximity_weight,
        time_weight: float = config.temporal_proximity_weight,
        threshold: float = config.duplicate_score_threshold,
        version: str = "v1",
    ) -> None:
        super().__init__(model_name="DuplicateScorer", version=version)
        self.text_weight = text_weight
        self.geo_weight = geo_weight
        self.time_weight = time_weight
        self.threshold = threshold
        self.feature_builder = GeographicTemporalFeatureBuilder()

        # Supervised logistic regression classifier instance
        self.clf: Optional[LogisticRegression] = None
        self._is_supervised: bool = False

    def compute_heuristic_score(self, evidence: DuplicateEvidence) -> float:
        """Compute composite duplicate likelihood score using dynamically re-weighted heuristic rules."""
        text_sim = float(evidence.text_similarity)
        geo_score, time_score = self.feature_builder.compute_proximity_scores(evidence)

        # Dynamic feature weight normalization depending on feature availability
        available_weights = [self.text_weight]
        feature_values = [text_sim]

        if geo_score is not None:
            available_weights.append(self.geo_weight)
            feature_values.append(geo_score)

        if time_score is not None:
            available_weights.append(self.time_weight)
            feature_values.append(time_score)

        total_weight = sum(available_weights)
        if total_weight <= 0:
            return text_sim

        normalized_weights = [w / total_weight for w in available_weights]
        composite_score = sum(w * v for w, v in zip(normalized_weights, feature_values))

        # Bonus multiplier if issue categories match
        if evidence.same_issue_category is True:
            composite_score = min(1.0, composite_score * 1.05)
        elif evidence.same_issue_category is False:
            composite_score = composite_score * 0.90

        return float(max(0.0, min(1.0, composite_score)))

    def train(self, X: Any, y: List[int], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Train supervised LogisticRegression classifier on tabular evidence feature matrix X."""
        if len(y) == 0:
            raise RoadXModelError("Cannot train DuplicateScorer on empty label set.")

        self.clf = LogisticRegression(
            C=1.0,
            max_iter=1000,
            class_weight="balanced",
            solver="lbfgs",
            random_state=config.random_state,
        )
        self.clf.fit(X, y)
        self._is_fitted = True
        self._is_supervised = True
        self.metadata = {
            "model_name": self.model_name,
            "version": self.version,
            "n_samples": X.shape[0] if hasattr(X, "shape") else len(y),
            "threshold": self.threshold,
        }
        return self.metadata

    def predict(self, X: Any, *args: Any, **kwargs: Any) -> List[int]:
        """Predict binary duplicate class labels (1 = duplicate, 0 = distinct)."""
        if not self._is_fitted or self.clf is None:
            raise ModelNotFittedError("DuplicateScorer has not been fit with a supervised model.")
        probas = self.predict_proba(X)
        return [1 if p >= self.threshold else 0 for p in probas]

    def predict_proba(self, X: Any, *args: Any, **kwargs: Any) -> np.ndarray:
        """Predict probability of duplicate relationship for feature matrix X."""
        if not self._is_fitted or self.clf is None:
            raise ModelNotFittedError("DuplicateScorer has not been fit with a supervised model.")
        raw_probas = self.clf.predict_proba(X)
        # Class index 1 corresponds to duplicate class
        if raw_probas.ndim == 2 and raw_probas.shape[1] > 1:
            return raw_probas[:, 1]
        return raw_probas.ravel()

    def score_candidate(
        self, candidate_id: str, evidence: DuplicateEvidence
    ) -> DuplicateCandidate:
        """Calculate duplicate score for candidate complaint and return DuplicateCandidate object.

        Args:
            candidate_id: Grievance ID of candidate complaint.
            evidence: DuplicateEvidence breakdown object.

        Returns:
            DuplicateCandidate Pydantic model.
        """
        if self._is_fitted and self.clf is not None:
            # Build feature vector [text_sim, geo_score_or_0, time_score_or_0, category_match_or_0]
            geo_score, time_score = self.feature_builder.compute_proximity_scores(evidence)
            cat_match = 1.0 if evidence.same_issue_category is True else 0.0
            feat_vec = np.array(
                [
                    [
                        evidence.text_similarity,
                        geo_score if geo_score is not None else 0.0,
                        time_score if time_score is not None else 0.0,
                        cat_match,
                    ]
                ],
                dtype=np.float32,
            )
            prob = float(self.predict_proba(feat_vec)[0])
            score = prob
        else:
            # Transparent heuristic score calculation
            score = self.compute_heuristic_score(evidence)

        is_cand = score >= self.threshold

        return DuplicateCandidate(
            grievance_id=candidate_id,
            duplicate_score=score,
            is_candidate=is_cand,
            evidence=evidence,
        )

    def save(self, path: Union[str, Path]) -> None:
        """Save DuplicateScorer artifact to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        artifact = {
            "model_name": self.model_name,
            "version": self.version,
            "text_weight": self.text_weight,
            "geo_weight": self.geo_weight,
            "time_weight": self.time_weight,
            "threshold": self.threshold,
            "is_fitted": self._is_fitted,
            "is_supervised": self._is_supervised,
            "clf": self.clf,
            "metadata": self.metadata,
        }
        joblib.dump(artifact, path)

    @classmethod
    def load(cls, path: Union[str, Path]) -> DuplicateScorer:
        """Load DuplicateScorer artifact from disk."""
        path = Path(path)
        if not path.exists():
            raise ModelArtifactNotFoundError(f"DuplicateScorer artifact not found at: {path}")

        data = joblib.load(path)
        instance = cls(
            text_weight=data.get("text_weight", config.text_similarity_weight),
            geo_weight=data.get("geo_weight", config.geo_proximity_weight),
            time_weight=data.get("time_weight", config.temporal_proximity_weight),
            threshold=data.get("threshold", config.duplicate_score_threshold),
            version=data.get("version", "v1"),
        )
        instance.clf = data.get("clf")
        instance._is_fitted = data.get("is_fitted", False)
        instance._is_supervised = data.get("is_supervised", False)
        instance.metadata = data.get("metadata", {})
        return instance
