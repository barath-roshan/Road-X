"""SQLAlchemy model for Road Operations (closures, restrictions, maintenance detour management)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.grievance import Grievance
    from backend.models.road import RoadSegment
    from backend.models.user import User
    from backend.models.work_order import WorkOrder


class RoadOperationType(str, enum.Enum):
    """Categorical classification of road operation / restriction activity."""

    ROAD_CLOSURE = "ROAD_CLOSURE"
    LANE_RESTRICTION = "LANE_RESTRICTION"
    MAINTENANCE_WORK = "MAINTENANCE_WORK"
    DETOUR = "DETOUR"
    HAZARD_BLOCK = "HAZARD_BLOCK"


class RoadOperationStatus(str, enum.Enum):
    """Controlled lifecycle stages for road operations."""

    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RoadOperation(Base):
    """SQLAlchemy model representing a municipal road operation (closure, restriction, detour)."""

    __tablename__ = "road_operations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    road_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    grievance_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("grievances.id", ondelete="SET NULL"), nullable=True, index=True
    )
    work_order_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    operation_type: Mapped[RoadOperationType] = mapped_column(
        Enum(RoadOperationType), nullable=False, default=RoadOperationType.ROAD_CLOSURE, index=True
    )
    status: Mapped[RoadOperationStatus] = mapped_column(
        Enum(RoadOperationStatus), nullable=False, default=RoadOperationStatus.PLANNED, index=True
    )

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Alternative Route Information
    alternative_route_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    alternative_route_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    alternative_road_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True
    )
    alternative_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    road_segment: Mapped[RoadSegment | None] = relationship("RoadSegment", foreign_keys=[road_id])
    alternative_road_segment: Mapped[RoadSegment | None] = relationship("RoadSegment", foreign_keys=[alternative_road_id])
    grievance: Mapped[Grievance | None] = relationship("Grievance")
    work_order: Mapped[WorkOrder | None] = relationship("WorkOrder")
    officer: Mapped[User | None] = relationship("User", foreign_keys=[created_by])
    events: Mapped[List[RoadOperationEvent]] = relationship(
        "RoadOperationEvent", back_populates="operation", cascade="all, delete-orphan"
    )


class RoadOperationEvent(Base):
    """SQLAlchemy model tracking immutable road operation history events."""

    __tablename__ = "road_operation_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    operation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("road_operations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    operation: Mapped[RoadOperation] = relationship("RoadOperation", back_populates="events")
    actor: Mapped[User | None] = relationship("User")
