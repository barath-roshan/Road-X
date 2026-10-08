"""Repository for persistent notification queries, pagination, and status updates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from backend.models.notification import DeliveryStatus, Notification, NotificationChannel, NotificationType


class NotificationRepository:
    """Repository handling database interactions for notifications."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, notification_id: str) -> Optional[Notification]:
        """Fetch notification by ID."""
        return self.db.query(Notification).filter(Notification.id == notification_id).first()

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Notification]:
        """Fetch notification by idempotency key to prevent duplicate delivery."""
        if not idempotency_key:
            return None
        return (
            self.db.query(Notification)
            .filter(Notification.idempotency_key == idempotency_key)
            .first()
        )

    def list_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Notification], int]:
        """Retrieve paginated notifications for a specific recipient user."""
        query = self.db.query(Notification).filter(Notification.recipient_id == user_id)

        if unread_only:
            query = query.filter(Notification.is_read.is_(False))

        total = query.count()
        items = (
            query.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def count_unread(self, user_id: str) -> int:
        """Count total unread notifications for a user."""
        return (
            self.db.query(func.count(Notification.id))
            .filter(Notification.recipient_id == user_id, Notification.is_read.is_(False))
            .scalar()
            or 0
        )

    def mark_as_read(self, notification: Notification) -> Notification:
        """Mark a notification entity as read."""
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            self.db.flush()
        return notification

    def mark_all_as_read(self, user_id: str) -> int:
        """Mark all unread notifications for a user as read."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(Notification.recipient_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=now)
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount
