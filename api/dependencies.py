"""FastAPI Dependency Injection providers for RoadX Services and Security Context."""

from __future__ import annotations

import uuid
from typing import Optional
from fastapi import Header, Request

from api.service import MLInferenceService
from backend.models.user import UserRole
from backend.security import UserContext


def get_ml_service(request: Request) -> MLInferenceService:
    """Dependency provider returning singleton MLInferenceService from app state."""
    service: Optional[MLInferenceService] = getattr(request.app.state, "ml_service", None)
    if service is None:
        service = MLInferenceService()
        request.app.state.ml_service = service
    return service


def get_request_id(request: Request) -> str:
    """Dependency provider returning unique trace request identifier."""
    request_id: Optional[str] = getattr(request.state, "request_id", None)
    if not request_id:
        request_id = f"req-{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
    return request_id


def get_current_actor(
    x_actor_user_id: Optional[str] = Header(default=None, alias="X-Actor-User-ID"),
    x_actor_role: Optional[str] = Header(default="GOVERNMENT_OFFICER", alias="X-Actor-Role"),
) -> UserContext:
    """Dependency provider building active UserContext actor from headers (or officer default)."""
    parsed_role = UserRole.GOVERNMENT_OFFICER
    if x_actor_role:
        try:
            parsed_role = UserRole(x_actor_role.strip().upper())
        except ValueError:
            parsed_role = UserRole.GOVERNMENT_OFFICER

    return UserContext(
        user_id=x_actor_user_id or "off-default-001",
        role=parsed_role,
    )
