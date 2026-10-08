"""SQLAlchemy model for persistent user notifications and multi-channel delivery metadata."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.user import User


class NotificationChannel(str, enum.Enum):
    """Notification delivery channel."""

    IN_APP = "IN_APP"
    SMS = "SMS"


class DeliveryStatus(str, enum.Enum):
    """Notification delivery status lifecycle."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class NotificationType(str, enum.Enum):
    """Supported notification trigger event types."""

    GRIEVANCE_ACCEPTED = "GRIEVANCE_ACCEPTED"
    GRIEVANCE_REJECTED = "GRIEVANCE_REJECTED"
    WORK_ORDER_ASSIGNED = "WORK_ORDER_ASSIGNED"
    WORK_STARTED = "WORK_STARTED"
    WORK_PROGRESS_UPDATED = "WORK_PROGRESS_UPDATED"
    WORK_VERIFICATION_SUBMITTED = "WORK_VERIFICATION_SUBMITTED"
    WORK_VERIFICATION_APPROVED = "WORK_VERIFICATION_APPROVED"
    WORK_VERIFICATION_REJECTED = "WORK_VERIFICATION_REJECTED"
    ROAD_OPERATION_ACTIVATED = "ROAD_OPERATION_ACTIVATED"
    ROAD_OPERATION_COMPLETED = "ROAD_OPERATION_COMPLETED"
    ROAD_OPERATION_CANCELLED = "ROAD_OPERATION_CANCELLED"


class Notification(Base):
    """SQLAlchemy model tracking in-app and external user notifications."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    recipient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel), nullable=False, default=NotificationChannel.IN_APP, index=True
    )
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus), nullable=False, default=DeliveryStatus.PENDING, index=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    recipient: Mapped[User] = relationship("User")
