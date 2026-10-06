"""SQLAlchemy model for User actor entities (Citizen, Officer, Contractor)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.grievance import Grievance


class UserRole(str, enum.Enum):
    """Supported actor roles within RoadX governance model."""

    CITIZEN = "CITIZEN"
    GOVERNMENT_OFFICER = "GOVERNMENT_OFFICER"
    CONTRACTOR = "CONTRACTOR"


class User(Base):
    """SQLAlchemy model representing a platform user."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.CITIZEN
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    grievances: Mapped[List[Grievance]] = relationship(
        "Grievance", back_populates="citizen", cascade="all, delete-orphan"
    )
