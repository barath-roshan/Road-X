"""SQLAlchemy model for administrative workflow history and audit events."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.grievance import Grievance
    from backend.models.work_order import WorkOrder
    from backend.models.user import User


class WorkflowEventType(str, enum.Enum):
    """Event type identifiers for audit history tracing."""

    GRIEVANCE_SUBMITTED = "GRIEVANCE_SUBMITTED"
    GRIEVANCE_REVIEWED = "GRIEVANCE_REVIEWED"
    GRIEVANCE_ACCEPTED = "GRIEVANCE_ACCEPTED"
    GRIEVANCE_REJECTED = "GRIEVANCE_REJECTED"
    WORK_ORDER_CREATED = "WORK_ORDER_CREATED"
    WORK_ORDER_ASSIGNED = "WORK_ORDER_ASSIGNED"
    WORK_VERIFICATION_SUBMITTED = "WORK_VERIFICATION_SUBMITTED"
    WORK_VERIFICATION_APPROVED = "WORK_VERIFICATION_APPROVED"
    WORK_VERIFICATION_REJECTED = "WORK_VERIFICATION_REJECTED"


class WorkflowEvent(Base):
    """SQLAlchemy model tracking immutable workflow history events."""

    __tablename__ = "workflow_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    grievance_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("grievances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_order_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    event_type: Mapped[WorkflowEventType] = mapped_column(
        Enum(WorkflowEventType), nullable=False, index=True
    )
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    grievance: Mapped[Grievance] = relationship("Grievance")
    work_order: Mapped[WorkOrder | None] = relationship("WorkOrder")
    actor: Mapped[User | None] = relationship("User")
