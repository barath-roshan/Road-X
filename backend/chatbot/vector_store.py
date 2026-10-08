"""In-memory Vector Store for RoadX RAG Knowledge Base chunk indexing and similarity search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np

from backend.chatbot.chunker import DocumentChunk


@dataclass
class SearchResult:
    """SearchResult container wrapping matched DocumentChunk and score."""

    chunk: DocumentChunk
    score: float


class VectorStore:
    """Lightweight vector index supporting cosine similarity search over document chunks."""

    def __init__(self, embedding_dim: int = 300) -> None:
        self.embedding_dim = embedding_dim
        self.chunks: List[DocumentChunk] = []
        self.vectors: np.ndarray = np.empty((0, embedding_dim), dtype=np.float32)

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: np.ndarray) -> None:
        """Add document chunks and their normalized embedding vectors to the vector store.

        Args:
            chunks: List of DocumentChunk instances.
            embeddings: 2D numpy array of shape (N, embedding_dim).
        """
        if not chunks:
            return

        if len(chunks) != embeddings.shape[0]:
            raise ValueError(
                f"Mismatch between number of chunks ({len(chunks)}) and embeddings ({embeddings.shape[0]})"
            )

        # Normalize vectors for fast cosine similarity dot product
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_vectors = (embeddings / norms).astype(np.float32)

        self.chunks.extend(chunks)
        if self.vectors.shape[0] == 0:
            self.vectors = normalized_vectors
        else:
            self.vectors = np.vstack([self.vectors, normalized_vectors]).astype(np.float32)

    def similarity_search(
        self,
        query_vector: np.ndarray,
        top_k: int = 3,
        min_score: float = 0.05,
    ) -> List[SearchResult]:
        """Perform cosine similarity search against indexed document chunks.

        Args:
            query_vector: 1D or 2D query embedding vector.
            top_k: Maximum number of top relevant chunks to return.
            min_score: Minimum similarity score threshold for filtering.

        Returns:
            List of SearchResult objects sorted by descending similarity score.
        """
        if self.vectors.shape[0] == 0 or not self.chunks:
            return []

        # Ensure 1D vector
        vec = query_vector.flatten()
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm

        # Compute cosine similarity matrix via matrix multiplication
        scores = np.dot(self.vectors, vec)

        # Sort indices in descending order
        top_indices = np.argsort(scores)[::-1]

        results: List[SearchResult] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < min_score:
                continue

            results.append(SearchResult(chunk=self.chunks[idx], score=score))
            if len(results) >= top_k:
                break

        return results

    def clear(self) -> None:
        """Clear all indexed chunks and vectors."""
        self.chunks = []
        self.vectors = np.empty((0, self.embedding_dim), dtype=np.float32)
