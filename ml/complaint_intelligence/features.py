"""Feature extraction pipeline using TF-IDF for text vectorization."""

from __future__ import annotations

from pathlib import Path
from typing import List, Union, Any, Optional
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

from ml.common.exceptions import RoadXModelError, ModelNotFittedError, ModelArtifactNotFoundError
from ml.complaint_intelligence.config import config


class ComplaintFeatureExtractor:
    """TF-IDF Feature Extractor for converting cleaned complaint text into numeric features."""

    def __init__(
        self,
        max_features: Optional[int] = None,
        ngram_range: Optional[tuple[int, int]] = None,
        sublinear_tf: Optional[bool] = None,
    ) -> None:
        self.max_features = max_features or config.max_features
        self.ngram_range = ngram_range or config.ngram_range
        self.sublinear_tf = sublinear_tf if sublinear_tf is not None else config.sublinear_tf

        self.vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            sublinear_tf=self.sublinear_tf,
            lowercase=True,
            strip_accents="unicode",
        )
        self._is_fitted: bool = False

    @property
    def is_fitted(self) -> bool:
        """Returns True if feature vectorizer has been fit on text data."""
        return self._is_fitted

    def fit(self, texts: List[str]) -> ComplaintFeatureExtractor:
        """Fit vectorizer vocabulary on a list of complaint text strings."""
        if not texts:
            raise RoadXModelError("Cannot fit TF-IDF vectorizer on empty text list.")
        self.vectorizer.fit(texts)
        self._is_fitted = True
        return self

    def transform(self, texts: List[str]) -> Any:
        """Transform text list into sparse TF-IDF feature matrix."""
        if not self._is_fitted:
            raise ModelNotFittedError("TF-IDF vectorizer must be fitted before calling transform().")
        return self.vectorizer.transform(texts)

    def fit_transform(self, texts: List[str]) -> Any:
        """Fit vocabulary and return transformed sparse feature matrix."""
        if not texts:
            raise RoadXModelError("Cannot fit_transform TF-IDF vectorizer on empty text list.")
        matrix = self.vectorizer.fit_transform(texts)
        self._is_fitted = True
        return matrix

    def save(self, path: Union[str, Path]) -> None:
        """Persist fitted vectorizer to disk using joblib."""
        if not self._is_fitted:
            raise ModelNotFittedError("Cannot save un-fitted vectorizer.")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"vectorizer": self.vectorizer, "is_fitted": self._is_fitted}, path)

    @classmethod
    def load(cls, path: Union[str, Path]) -> ComplaintFeatureExtractor:
        """Load fitted vectorizer from disk artifact."""
        path = Path(path)
        if not path.exists():
            raise ModelArtifactNotFoundError(f"Vectorizer artifact not found at: {path}")

        data = joblib.load(path)
        instance = cls()
        instance.vectorizer = data["vectorizer"]
        instance._is_fitted = data.get("is_fitted", True)
        return instance
