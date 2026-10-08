"""Citizen Chatbot Service orchestrating conversation sessions, hybrid RAG context, LLM generation, and persistence."""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session

from backend.chatbot.context_builder import ContextBuilder
from backend.chatbot.llm_provider import get_llm_provider
from backend.models.chat import ChatRole
from backend.models.user import UserRole
from backend.repositories.chat_repository import ChatRepository
from backend.schemas.chat import (
    ChatConversationRead,
    ChatConversationSummaryRead,
    ChatMessageRead,
    ChatResponseRead,
    SourceMetadataRead,
)
from backend.security import UserContext, UnauthorizedError
from ml.common.exceptions import RoadXDataError
from ml.common.logging_config import get_logger

logger = get_logger("backend.services.chatbot_service")


class CitizenChatbotService:
    """Service handling Citizen Chatbot RAG execution, ownership security, and conversation state."""

    def __init__(
        self,
        db: Session,
        context_builder: Optional[ContextBuilder] = None,
    ) -> None:
        self.db = db
        self.repo = ChatRepository(db)
        self.context_builder = context_builder or ContextBuilder()

    def _verify_conversation_ownership(self, actor: UserContext, conversation_id: str):
        """Enforce citizen role and ownership of specified conversation session."""
        actor.require_role(UserRole.CITIZEN)
        if not actor.user_id:
            raise UnauthorizedError("Citizen user_id is required.")

        conversation = self.repo.get_conversation(conversation_id)
        if not conversation:
            raise RoadXDataError(f"Chat conversation '{conversation_id}' not found.")

        if conversation.citizen_id != actor.user_id:
            raise UnauthorizedError(
                f"Citizen '{actor.user_id}' does not own conversation '{conversation_id}'."
            )

        return conversation

    def create_conversation(
        self, actor: UserContext, title: Optional[str] = None
    ) -> ChatConversationRead:
        """Create a new chat conversation for active citizen."""
        actor.require_role(UserRole.CITIZEN)
        if not actor.user_id:
            raise UnauthorizedError("Citizen user_id is required.")

        conversation = self.repo.create_conversation(
            citizen_id=actor.user_id, title=title
        )
        return ChatConversationRead.model_validate(conversation)

    def list_conversations(
        self, actor: UserContext, skip: int = 0, limit: int = 100
    ) -> List[ChatConversationSummaryRead]:
        """List active citizen's conversations with message counts."""
        actor.require_role(UserRole.CITIZEN)
        if not actor.user_id:
            raise UnauthorizedError("Citizen user_id is required.")

        conversations = self.repo.list_conversations_by_citizen(
            citizen_id=actor.user_id, skip=skip, limit=limit
        )

        summaries = []
        for conv in conversations:
            msg_count = len(conv.messages) if conv.messages else 0
            summaries.append(
                ChatConversationSummaryRead(
                    id=conv.id,
                    citizen_id=conv.citizen_id,
                    title=conv.title,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                    message_count=msg_count,
                )
            )
        return summaries

    def get_conversation(
        self, actor: UserContext, conversation_id: str
    ) -> ChatConversationRead:
        """Get detailed conversation session and message history."""
        conversation = self._verify_conversation_ownership(actor, conversation_id)
        
        # Build message DTOs
        messages_dto = []
        for msg in conversation.messages:
            messages_dto.append(ChatMessageRead.from_model(msg))

        return ChatConversationRead(
            id=conversation.id,
            citizen_id=conversation.citizen_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=messages_dto,
        )

    def process_message(
        self, actor: UserContext, conversation_id: str, content: str
    ) -> ChatResponseRead:
        """Process user chat question, perform hybrid RAG retrieval, generate grounded answer, and persist."""
        conversation = self._verify_conversation_ownership(actor, conversation_id)

        cleaned_content = content.strip()
        if not cleaned_content:
            raise RoadXDataError("Message content cannot be empty.")

        # 1. Save user message to database
        user_msg_model = self.repo.add_message(
            conversation_id=conversation.id,
            role=ChatRole.USER,
            content=cleaned_content,
        )

        # 2. Retrieve hybrid context (DB citizen account + Vector RAG chunks)
        hybrid_context = self.context_builder.build_hybrid_context(
            db=self.db, actor=actor, query=cleaned_content
        )

        context_text = hybrid_context["context_text"]
        sources = hybrid_context["sources"]

        # 3. Call LLM provider with system grounding prompt
        llm = get_llm_provider()
        try:
            assistant_response_text = llm.generate_response(
                user_query=cleaned_content, context_text=context_text
            )
        except Exception as e:
            logger.error("Error during LLM response generation: %s", e)
            assistant_response_text = (
                "I apologize, but I encountered a service error while processing your request. "
                "Please check back in a few moments."
            )

        # 4. Save assistant response to database
        assistant_msg_model = self.repo.add_message(
            conversation_id=conversation.id,
            role=ChatRole.ASSISTANT,
            content=assistant_response_text,
            sources=sources,
        )

        # 5. Format DTOs and return
        user_msg_dto = ChatMessageRead.from_model(user_msg_model)
        assistant_msg_dto = ChatMessageRead.from_model(assistant_msg_model)
        source_dtos = [SourceMetadataRead(**s) for s in sources]

        return ChatResponseRead(
            conversation_id=conversation.id,
            user_message=user_msg_dto,
            assistant_message=assistant_msg_dto,
            sources=source_dtos,
        )
