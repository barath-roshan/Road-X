"""SQLAlchemy model for Maintenance Work Orders."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.grievance import Grievance
    from backend.models.road import RoadSegment
    from backend.models.user import User


class WorkOrderStatus(str, enum.Enum):
    """Controlled lifecycle status enum for work orders."""

    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class WorkOrder(Base):
    """SQLAlchemy model representing a government-approved maintenance work order."""

    __tablename__ = "work_orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    grievance_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("grievances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    road_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_contractor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    status: Mapped[WorkOrderStatus] = mapped_column(
        Enum(WorkOrderStatus), nullable=False, default=WorkOrderStatus.OPEN, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    grievance: Mapped[Grievance] = relationship("Grievance")
    road_segment: Mapped[RoadSegment | None] = relationship("RoadSegment")
    officer: Mapped[User | None] = relationship("User", foreign_keys=[created_by])
    contractor: Mapped[User | None] = relationship("User", foreign_keys=[assigned_contractor_id])
