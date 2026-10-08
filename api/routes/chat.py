"""API Router for Citizen Chatbot and RAG assistant (/api/v1/citizen/chat/...)."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.config import api_settings
from api.dependencies import get_current_actor
from backend.database import get_db
from backend.schemas.chat import (
    ChatConversationCreate,
    ChatConversationRead,
    ChatConversationSummaryRead,
    ChatMessageCreate,
    ChatResponseRead,
)
from backend.security import UserContext, UnauthorizedError
from backend.services.chatbot_service import CitizenChatbotService
from ml.common.exceptions import RoadXDataError

router = APIRouter(prefix=f"{api_settings.api_prefix}/citizen/chat", tags=["Citizen Chatbot RAG"])


@router.post(
    "/conversations",
    response_model=ChatConversationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Citizen Chat Conversation Session",
    description="Initializes a new persistent chat session for the requesting citizen actor.",
)
def create_chat_conversation(
    payload: Optional[ChatConversationCreate] = None,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> ChatConversationRead:
    """Create a new citizen chat session."""
    service = CitizenChatbotService(db)
    try:
        title = payload.title if payload else None
        return service.create_conversation(actor=actor, title=title)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/conversations",
    response_model=List[ChatConversationSummaryRead],
    summary="List Citizen's Chat Conversations",
    description="Returns all active and past chat sessions owned by the authenticated citizen.",
)
def list_chat_conversations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[ChatConversationSummaryRead]:
    """Retrieve chat conversation sessions for current citizen."""
    service = CitizenChatbotService(db)
    try:
        return service.list_conversations(actor=actor, skip=skip, limit=limit)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/conversations/{conversation_id}",
    response_model=ChatConversationRead,
    summary="Get Chat Conversation History",
    description="Returns detailed chat session view and complete chronological message history for owned conversation.",
)
def get_chat_conversation(
    conversation_id: str,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> ChatConversationRead:
    """Retrieve conversation details and message history."""
    service = CitizenChatbotService(db)
    try:
        return service.get_conversation(actor=actor, conversation_id=conversation_id)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatResponseRead,
    status_code=status.HTTP_200_OK,
    summary="Send Message to Chatbot & Get Grounded RAG Answer",
    description="Processes citizen question using hybrid PostgreSQL context and Vector RAG knowledge, returning grounded answer and source metadata.",
)
def send_chat_message(
    conversation_id: str,
    payload: ChatMessageCreate,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> ChatResponseRead:
    """Submit message to conversation session and generate RAG assistant response."""
    service = CitizenChatbotService(db)
    try:
        return service.process_message(
            actor=actor, conversation_id=conversation_id, content=payload.content
        )
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
