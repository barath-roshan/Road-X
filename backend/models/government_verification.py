"""SQLAlchemy model for Government Officer work completion verifications."""

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


class VerificationDecision(str, enum.Enum):
    """Government officer verification decision options."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"


class GovernmentVerification(Base):
    """SQLAlchemy model representing government officer verification of contractor repair completion."""

    __tablename__ = "government_verifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    work_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    grievance_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("grievances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    officer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    decision: Mapped[VerificationDecision] = mapped_column(Enum(VerificationDecision), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    work_order: Mapped[WorkOrder] = relationship("WorkOrder")
    grievance: Mapped[Grievance] = relationship("Grievance")
    officer: Mapped[User | None] = relationship("User")
