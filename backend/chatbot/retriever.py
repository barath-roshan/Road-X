"""Knowledge Base Retrieval Service for RoadX RAG Pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.chatbot.chunker import DocumentChunk, DocumentChunker
from backend.chatbot.embeddings import BaseEmbeddingProvider, RoadXEmbeddingProvider
from backend.chatbot.vector_store import SearchResult, VectorStore
from backend.config import chatbot_settings
from ml.common.logging_config import get_logger

logger = get_logger(__name__)


class KnowledgeRetriever:
    """Retrieval service managing knowledge document ingestion and vector similarity queries."""

    def __init__(
        self,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        chunker: Optional[DocumentChunker] = None,
        knowledge_file_path: Optional[Path | str] = None,
    ) -> None:
        self.embedding_provider = embedding_provider or RoadXEmbeddingProvider()
        self.chunker = chunker or DocumentChunker()
        self.vector_store = VectorStore(embedding_dim=self.embedding_provider.embedding_dim)
        
        # Default knowledge path
        if knowledge_file_path:
            self.knowledge_path = Path(knowledge_file_path)
        else:
            self.knowledge_path = Path(__file__).parent.parent.parent / "data" / "knowledge" / "roadx_faq.json"

        self._is_indexed = False
        self._auto_ingest()

    def _auto_ingest(self) -> None:
        """Automatically ingest standard knowledge documents if file exists."""
        if self.knowledge_path.exists():
            try:
                with open(self.knowledge_path, "r", encoding="utf-8") as f:
                    docs = json.load(f)
                if isinstance(docs, list):
                    self.ingest_documents(docs)
                    logger.info("Successfully ingested %d knowledge docs from %s", len(docs), self.knowledge_path)
            except Exception as e:
                logger.error("Failed to auto-ingest knowledge base file: %s", e)

    def ingest_documents(self, documents: List[Dict[str, Any]]) -> int:
        """Ingest document dicts, chunk them, embed, and store in vector index.

        Returns:
            Total number of chunks indexed.
        """
        chunks = self.chunker.chunk_documents(documents)
        if not chunks:
            return 0

        chunk_texts = [c.text for c in chunks]
        embeddings = self.embedding_provider.embed_batch(chunk_texts)
        self.vector_store.add_chunks(chunks, embeddings)
        self._is_indexed = True
        return len(chunks)

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> List[SearchResult]:
        """Retrieve top relevant knowledge base chunks for user query.

        Args:
            query: Citizen question text.
            top_k: Maximum matches to return.
            min_score: Minimum relevance score filter.

        Returns:
            List of SearchResult objects with chunk content and metadata.
        """
        if not query or not query.strip() or not self._is_indexed:
            return []

        k = top_k if top_k is not None else chatbot_settings.rag_top_k
        min_s = min_score if min_score is not None else chatbot_settings.rag_min_score

        query_vec = self.embedding_provider.embed_text(query)
        return self.vector_store.similarity_search(query_vec, top_k=k, min_score=min_s)
