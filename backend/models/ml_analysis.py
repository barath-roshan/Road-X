"""SQLAlchemy model for persistent ML analysis execution results."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict
from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.grievance import Grievance


class MLAnalysisResult(Base):
    """SQLAlchemy model storing execution outputs of Phase 9/10 Unified ML Pipeline."""

    __tablename__ = "ml_analysis_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    grievance_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("grievances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pipeline_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")
    overall_status: Mapped[str] = mapped_column(String(20), nullable=False, default="SUCCESS")
    total_duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Structured ML module JSON payloads
    failure_prediction: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    damage_detection: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    severity_prediction: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    complaint_analysis: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    duplicate_detection: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    time_to_failure: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    maintenance_priority: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    stage_summaries: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    grievance: Mapped[Grievance] = relationship("Grievance", back_populates="ml_analyses")
