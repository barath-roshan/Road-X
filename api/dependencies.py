"""FastAPI Dependency Injection providers for RoadX ML Service."""

from __future__ import annotations

import uuid
from typing import Optional
from fastapi import Request

from api.service import MLInferenceService


def get_ml_service(request: Request) -> MLInferenceService:
    """Dependency provider returning singleton MLInferenceService from app state.

    Args:
        request: Incoming FastAPI request instance.

    Returns:
        MLInferenceService instance.
    """
    service: Optional[MLInferenceService] = getattr(request.app.state, "ml_service", None)
    if service is None:
        # Fallback container if accessed before lifespan
        service = MLInferenceService()
        request.app.state.ml_service = service
    return service


def get_request_id(request: Request) -> str:
    """Dependency provider returning unique trace request identifier.

    Args:
        request: Incoming FastAPI request instance.

    Returns:
        String request_id.
    """
    request_id: Optional[str] = getattr(request.state, "request_id", None)
    if not request_id:
        request_id = f"req-{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
    return request_id
