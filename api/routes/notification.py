"""API Router for User Notifications (/api/v1/notifications/...)."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.config import api_settings
from api.dependencies import get_current_actor
from backend.database import get_db
from backend.schemas.notification import (
    MarkReadResponse,
    NotificationListResponse,
    NotificationRead,
)
from backend.security import UserContext, UnauthorizedError
from backend.services.notification_service import NotificationService
from ml.common.exceptions import RoadXDataError

router = APIRouter(prefix=f"{api_settings.api_prefix}/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List User Notifications",
    description="Retrieve paginated notifications for the authenticated user.",
)
def list_user_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    """List authenticated user's notifications."""
    service = NotificationService(db)
    try:
        items, total, unread_count = service.list_user_notifications(
            actor=actor,
            unread_only=unread_only,
            page=page,
            page_size=page_size,
        )
        return NotificationListResponse(
            items=[NotificationRead.model_validate(item) for item in items],
            total=total,
            unread_count=unread_count,
            page=page,
            page_size=page_size,
        )
    except UnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/{notification_id}",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
    summary="Get User Notification Details",
    description="Retrieve specific notification details after enforcing recipient ownership.",
)
def get_user_notification(
    notification_id: str,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> NotificationRead:
    """Retrieve specific user notification."""
    service = NotificationService(db)
    try:
        notification = service.get_user_notification(actor, notification_id)
        return NotificationRead.model_validate(notification)
    except UnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RoadXDataError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/read-all",
    response_model=MarkReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark All User Notifications Read",
    description="Mark all unread notifications for the authenticated user as read.",
)
def mark_all_user_notifications_read(
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> MarkReadResponse:
    """Mark all notifications for authenticated user as read."""
    service = NotificationService(db)
    try:
        updated_count = service.mark_all_user_notifications_read(actor)
        db.commit()
        return MarkReadResponse(
            success=True,
            updated_count=updated_count,
            message=f"Marked {updated_count} notification(s) as read.",
        )
    except UnauthorizedError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
    summary="Mark Specific Notification Read",
    description="Mark a specific notification as read.",
)
def mark_user_notification_read(
    notification_id: str,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> NotificationRead:
    """Mark a specific notification as read."""
    service = NotificationService(db)
    try:
        notification = service.mark_notification_read(actor, notification_id)
        db.commit()
        db.refresh(notification)
        return NotificationRead.model_validate(notification)
    except UnauthorizedError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RoadXDataError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
