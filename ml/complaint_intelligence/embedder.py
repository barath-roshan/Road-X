"""Semantic embedding vector generator for citizen complaint text (Phase 5 -> Phase 6 interface)."""

from __future__ import annotations

from typing import Optional
import numpy as np

from ml.complaint_intelligence.config import config
from ml.complaint_intelligence.features import ComplaintFeatureExtractor
from ml.complaint_intelligence.preprocessing import ComplaintPreprocessor


class ComplaintEmbedder:
    """Generates numerical feature embedding vectors for citizen complaint text.

    Exposes a standardized embedding interface for downstream consumption,
    specifically Phase 6 Duplicate Complaint Detection.
    """

    def __init__(
        self,
        feature_extractor: Optional[ComplaintFeatureExtractor] = None,
        embedding_dim: int = 300,
    ) -> None:
        self.preprocessor = ComplaintPreprocessor()
        self.feature_extractor = feature_extractor
        self.embedding_dim = embedding_dim or config.embedding_dim

    def embed(self, text: str) -> np.ndarray:
        """Generate numerical embedding vector for input complaint text.

        Args:
            text: Citizen complaint description text string.

        Returns:
            1D float32 numpy ndarray of shape (embedding_dim,) containing normalized feature embedding.
        """
        if not text or not text.strip():
            return np.zeros(self.embedding_dim, dtype=np.float32)

        cleaned_text = self.preprocessor.clean_text(text)

        if self.feature_extractor is not None and self.feature_extractor.is_fitted:
            # Transform text into sparse TF-IDF feature row
            sparse_row = self.feature_extractor.transform([cleaned_text])
            dense_vec = sparse_row.toarray()[0].astype(np.float32)

            # Pad or truncate vector to match standard embedding_dim
            if len(dense_vec) < self.embedding_dim:
                vector = np.pad(dense_vec, (0, self.embedding_dim - len(dense_vec)), mode="constant")
            else:
                vector = dense_vec[: self.embedding_dim]
        else:
            # Fallback deterministic token hash embedding when feature extractor is not supplied
            vector = self._hash_embedding(cleaned_text, self.embedding_dim)

        # L2 Normalize non-zero vector
        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector = vector / norm

        return vector.astype(np.float32)

    def _hash_embedding(self, text: str, dim: int) -> np.ndarray:
        """Generate deterministic feature vector via feature hashing for raw text."""
        vec = np.zeros(dim, dtype=np.float32)
        tokens = text.lower().split()

        for token in tokens:
            idx = abs(hash(token)) % dim
            vec[idx] += 1.0

        return vec
