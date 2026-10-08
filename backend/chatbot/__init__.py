"""RoadX Citizen Chatbot and RAG Subsystem Package."""

from backend.chatbot.chunker import DocumentChunk, DocumentChunker
from backend.chatbot.embeddings import BaseEmbeddingProvider, RoadXEmbeddingProvider
from backend.chatbot.vector_store import VectorStore, SearchResult
from backend.chatbot.retriever import KnowledgeRetriever
from backend.chatbot.context_builder import ContextBuilder
from backend.chatbot.prompts import SYSTEM_GROUNDING_PROMPT, build_chat_prompt
from backend.chatbot.llm_provider import LLMProvider, MockLLMProvider, get_llm_provider

__all__ = [
    "DocumentChunk",
    "DocumentChunker",
    "BaseEmbeddingProvider",
    "RoadXEmbeddingProvider",
    "VectorStore",
    "SearchResult",
    "KnowledgeRetriever",
    "ContextBuilder",
    "SYSTEM_GROUNDING_PROMPT",
    "build_chat_prompt",
    "LLMProvider",
    "MockLLMProvider",
    "get_llm_provider",
]
