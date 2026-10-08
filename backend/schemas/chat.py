"""Pydantic schemas and DTOs for Citizen Chatbot and RAG APIs."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


from backend.models.chat import ChatRole


class SourceMetadataRead(BaseModel):
    """Source attribution metadata container."""

    title: str = Field(..., description="Document or dataset title")
    category: str = Field(..., description="Source category or classification")
    source: str = Field(..., description="Originating authority or system")
    document_id: Optional[str] = Field(None, description="Document unique identifier")
    chunk_id: Optional[str] = Field(None, description="Chunk unique identifier")
    relevance_score: Optional[float] = Field(None, description="Similarity score (0.0 to 1.0)")


class ChatMessageCreate(BaseModel):
    """Payload for submitting a user message to the chatbot."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Citizen question or message text (1-1000 characters)",
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure message is not purely whitespace."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Chat message content cannot be empty or blank whitespace.")
        return cleaned


class ChatMessageRead(BaseModel):
    """Response DTO representing a saved chat message."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: ChatRole
    content: str
    sources: Optional[List[SourceMetadataRead]] = Field(default=None, description="Retrieved RAG source attribution metadata")
    created_at: datetime

    @classmethod
    def from_model(cls, message_model: Any) -> ChatMessageRead:
        """Convert SQLAlchemy ChatMessage model to Pydantic DTO with sources parsing."""
        sources = None
        if hasattr(message_model, "sources_json") and message_model.sources_json:
            try:
                raw_sources = json.loads(message_model.sources_json)
                if isinstance(raw_sources, list):
                    sources = [SourceMetadataRead(**s) for s in raw_sources]
            except Exception:
                sources = None

        return cls(
            id=message_model.id,
            conversation_id=message_model.conversation_id,
            role=message_model.role,
            content=message_model.content,
            sources=sources,
            created_at=message_model.created_at,
        )


class ChatConversationCreate(BaseModel):
    """Payload for creating a new chat session."""

    title: Optional[str] = Field(
        default="Citizen Chat Session",
        max_length=255,
        description="Custom title for the conversation session",
    )


class ChatConversationRead(BaseModel):
    """Detailed response DTO for a conversation session with full message history."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    citizen_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageRead] = Field(default_factory=list)


class ChatConversationSummaryRead(BaseModel):
    """Summary DTO for listing citizen chat sessions."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    citizen_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(default=0, description="Total messages in session")



class ChatResponseRead(BaseModel):
    """Full API response payload after sending a message to the chatbot."""

    conversation_id: str
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    sources: List[SourceMetadataRead] = Field(default_factory=list)
