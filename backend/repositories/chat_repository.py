"""Repository for managing ChatConversation and ChatMessage persistence in SQLAlchemy."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.models.chat import ChatConversation, ChatMessage, ChatRole


class ChatRepository:
    """SQLAlchemy Repository handling CRUD operations for Chat Conversations and Messages."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_conversation(
        self, citizen_id: str, title: Optional[str] = None
    ) -> ChatConversation:
        """Create a new chat conversation session for a citizen."""
        conversation = ChatConversation(
            citizen_id=citizen_id,
            title=title or "Citizen Chat Session",
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def list_conversations_by_citizen(
        self, citizen_id: str, skip: int = 0, limit: int = 100
    ) -> List[ChatConversation]:
        """Retrieve paginated list of conversations owned by citizen."""
        return (
            self.db.query(ChatConversation)
            .filter(ChatConversation.citizen_id == citizen_id)
            .order_by(ChatConversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_conversation(self, conversation_id: str) -> Optional[ChatConversation]:
        """Retrieve conversation by ID."""
        return (
            self.db.query(ChatConversation)
            .filter(ChatConversation.id == conversation_id)
            .first()
        )

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation session and all its messages."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False

        self.db.delete(conversation)
        self.db.commit()
        return True

    def add_message(
        self,
        conversation_id: str,
        role: ChatRole | str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatMessage:
        """Add a new message (user/assistant) to conversation and update updated_at timestamp."""
        role_enum = ChatRole(role) if isinstance(role, str) else role
        sources_str = json.dumps(sources) if sources else None

        message = ChatMessage(
            conversation_id=conversation_id,
            role=role_enum,
            content=content,
            sources_json=sources_str,
        )
        self.db.add(message)

        # Update conversation timestamp
        conversation = self.get_conversation(conversation_id)
        if conversation:
            conversation.updated_at = datetime.now(timezone.utc)


        self.db.commit()
        self.db.refresh(message)
        return message

    def get_messages_by_conversation(self, conversation_id: str) -> List[ChatMessage]:
        """Retrieve all chronological messages for a conversation."""
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
