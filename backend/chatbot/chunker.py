"""Deterministic document chunking utility for RoadX RAG Knowledge Base."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class DocumentChunk:
    """Metadata-rich chunk container for document similarity indexing."""

    chunk_id: str
    document_id: str
    title: str
    source: str
    category: str
    version: str
    text: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk metadata to dictionary representation."""
        return asdict(self)


class DocumentChunker:
    """Splits knowledge documents into deterministic, metadata-preserving text chunks."""

    def __init__(self, max_chunk_chars: int = 400, overlap_chars: int = 50) -> None:
        self.max_chunk_chars = max(100, max_chunk_chars)
        self.overlap_chars = max(0, min(overlap_chars, self.max_chunk_chars // 2))

    def chunk_document(self, doc: Dict[str, Any]) -> List[DocumentChunk]:
        """Split a single knowledge document into structured chunks.

        Args:
            doc: Dictionary containing document_id, title, source, category, version, and content/text.

        Returns:
            List of DocumentChunk instances.
        """
        doc_id = str(doc.get("document_id", "doc_unknown"))
        title = str(doc.get("title", "Untitled Document"))
        source = str(doc.get("source", "RoadX Knowledge Base"))
        category = str(doc.get("category", "General Guidance"))
        version = str(doc.get("version", "1.0"))
        content = str(doc.get("content") or doc.get("text") or "").strip()

        if not content:
            return []

        # Split content into sentences/paragraphs
        raw_segments = re.split(r"(?<=[.!?\n])\s+", content)
        chunks: List[DocumentChunk] = []

        current_text = ""
        chunk_idx = 0

        for segment in raw_segments:
            seg = segment.strip()
            if not seg:
                continue

            if len(current_text) + len(seg) + 1 <= self.max_chunk_chars:
                current_text = f"{current_text} {seg}".strip() if current_text else seg
            else:
                if current_text:
                    chunk_id = f"{doc_id}_chunk_{chunk_idx}"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            document_id=doc_id,
                            title=title,
                            source=source,
                            category=category,
                            version=version,
                            text=current_text,
                        )
                    )
                    chunk_idx += 1

                # Carry over overlap if available
                overlap = current_text[-self.overlap_chars :] if len(current_text) > self.overlap_chars else ""
                current_text = f"{overlap} {seg}".strip() if overlap else seg

        if current_text:
            chunk_id = f"{doc_id}_chunk_{chunk_idx}"
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    title=title,
                    source=source,
                    category=category,
                    version=version,
                    text=current_text,
                )
            )

        return chunks

    def chunk_documents(self, docs: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """Chunk a list of knowledge documents."""
        all_chunks: List[DocumentChunk] = []
        for doc in docs:
            all_chunks.extend(self.chunk_document(doc))
        return all_chunks
