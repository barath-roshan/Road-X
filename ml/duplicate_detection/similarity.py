"""Semantic similarity calculator consuming Phase 5 complaint embeddings."""

from __future__ import annotations

from typing import Optional
import numpy as np

from ml.complaint_intelligence.embedder import ComplaintEmbedder


class SimilarityCalculator:
    """Calculates semantic similarity between complaint text pairs using Phase 5 vector embeddings."""

    def __init__(self, embedder: Optional[ComplaintEmbedder] = None) -> None:
        self.embedder = embedder or ComplaintEmbedder()

    def compute_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity score between two 1D numpy embedding vectors.

        Args:
            vec1: 1D float32 numpy array.
            vec2: 1D float32 numpy array.

        Returns:
            Cosine similarity float bounded in [0.0, 1.0].
        """
        if vec1 is None or vec2 is None or len(vec1) == 0 or len(vec2) == 0:
            return 0.0

        if vec1.shape != vec2.shape:
            # Handle dimension mismatch by truncating to min length
            min_dim = min(len(vec1), len(vec2))
            vec1 = vec1[:min_dim]
            vec2 = vec2[:min_dim]

        norm1 = float(np.linalg.norm(vec1))
        norm2 = float(np.linalg.norm(vec2))

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        dot_product = float(np.dot(vec1, vec2))
        similarity = dot_product / (norm1 * norm2)

        # Clamp numerical float errors to [0.0, 1.0] range
        return float(max(0.0, min(1.0, similarity)))

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic text similarity between two raw complaint text strings.

        Args:
            text1: Complaint text A.
            text2: Complaint text B.

        Returns:
            Cosine similarity score in range [0.0, 1.0].
        """
        if not text1 or not text2 or not text1.strip() or not text2.strip():
            return 0.0

        vec1 = self.embedder.embed(text1)
        vec2 = self.embedder.embed(text2)

        return self.compute_cosine_similarity(vec1, vec2)
