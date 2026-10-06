"""SQLAlchemy model for Citizen Grievance / Report entities."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.user import User
    from backend.models.road import RoadSegment
    from backend.models.evidence import Evidence
    from backend.models.ml_analysis import MLAnalysisResult


class GrievanceStatus(str, enum.Enum):
    """Lifecycle status stages for citizen grievances."""

    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class Grievance(Base):
    """SQLAlchemy model representing a citizen-reported road hazard or maintenance issue."""

    __tablename__ = "grievances"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    citizen_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    road_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    issue_category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[GrievanceStatus] = mapped_column(
        Enum(GrievanceStatus), nullable=False, default=GrievanceStatus.SUBMITTED, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    citizen: Mapped[User | None] = relationship("User", back_populates="grievances")
    road_segment: Mapped[RoadSegment | None] = relationship("RoadSegment", back_populates="grievances")
    evidence_items: Mapped[List[Evidence]] = relationship(
        "Evidence", back_populates="grievance", cascade="all, delete-orphan"
    )
    ml_analyses: Mapped[List[MLAnalysisResult]] = relationship(
        "MLAnalysisResult", back_populates="grievance", cascade="all, delete-orphan"
    )
