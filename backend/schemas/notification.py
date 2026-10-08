"""Pydantic schemas for Notification API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.models.notification import DeliveryStatus, NotificationChannel, NotificationType


class NotificationRead(BaseModel):
    """Notification response DTO."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    recipient_id: str
    notification_type: NotificationType
    title: str
    message: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    channel: NotificationChannel
    delivery_status: DeliveryStatus
    is_read: bool
    error_message: Optional[str] = None
    created_at: datetime
    read_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


class NotificationListResponse(BaseModel):
    """Paginated notification list response DTO."""

    items: List[NotificationRead]
    total: int
    unread_count: int
    page: int
    page_size: int


class MarkReadResponse(BaseModel):
    """Response DTO for mark-as-read action."""

    success: bool
    updated_count: int
    message: str
