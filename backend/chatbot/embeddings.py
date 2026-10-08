"""Embedding generator abstraction leveraging existing RoadX ComplaintEmbedder (Phase 5/6 baseline)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List
import numpy as np

from backend.config import chatbot_settings
from ml.complaint_intelligence.embedder import ComplaintEmbedder


class BaseEmbeddingProvider(ABC):
    """Abstract base class for vector embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Generate a 1D float32 normalized embedding vector for text query or chunk."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Generate a 2D float32 numpy array of shape (N, dim) for multiple text strings."""
        pass


class RoadXEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider reusing ml.complaint_intelligence ComplaintEmbedder."""

    def __init__(self, embedding_dim: int | None = None) -> None:
        self.embedding_dim = embedding_dim or chatbot_settings.embedding_dim
        self._embedder = ComplaintEmbedder(embedding_dim=self.embedding_dim)

    def embed_text(self, text: str) -> np.ndarray:
        """Generate normalized 1D float32 vector representation."""
        return self._embedder.embed(text)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Generate normalized 2D matrix representation for batch of texts."""
        if not texts:
            return np.empty((0, self.embedding_dim), dtype=np.float32)

        vectors = [self.embed_text(t) for t in texts]
        return np.vstack(vectors).astype(np.float32)
