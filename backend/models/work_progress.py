"""SQLAlchemy model for Contractor Work Progress updates."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.work_order import WorkOrder
    from backend.models.user import User


class WorkProgress(Base):
    """SQLAlchemy model representing a progress update log recorded by a contractor."""

    __tablename__ = "work_progresses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    work_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contractor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    progress_percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    work_order: Mapped[WorkOrder] = relationship("WorkOrder")
    contractor: Mapped[User] = relationship("User")
