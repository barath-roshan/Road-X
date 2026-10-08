"""Repository for RoadOperation persistence and query operations."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.models.road_operation import RoadOperation, RoadOperationEvent, RoadOperationStatus, RoadOperationType
from backend.repositories.base_repository import BaseRepository


class RoadOperationRepository(BaseRepository[RoadOperation]):
    """RoadOperationRepository managing road operation and event persistence."""

    def __init__(self, db: Session) -> None:
        super().__init__(RoadOperation, db)

    def filter_operations(
        self,
        status: Optional[RoadOperationStatus] = None,
        operation_type: Optional[RoadOperationType] = None,
        road_id: Optional[str] = None,
        grievance_id: Optional[str] = None,
        work_order_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RoadOperation]:
        """Query road operations with filtering, active_only check, and pagination."""
        query = self.db.query(RoadOperation)

        if status is not None:
            query = query.filter(RoadOperation.status == status)
        elif active_only:
            query = query.filter(
                RoadOperation.status.in_([RoadOperationStatus.ACTIVE, RoadOperationStatus.PLANNED])
            )

        if operation_type is not None:
            query = query.filter(RoadOperation.operation_type == operation_type)
        if road_id is not None:
            query = query.filter(
                or_(
                    RoadOperation.road_id == road_id,
                    RoadOperation.alternative_road_id == road_id,
                )
            )
        if grievance_id is not None:
            query = query.filter(RoadOperation.grievance_id == grievance_id)
        if work_order_id is not None:
            query = query.filter(RoadOperation.work_order_id == work_order_id)
        if date_from is not None:
            query = query.filter(RoadOperation.start_time >= date_from)
        if date_to is not None:
            query = query.filter(RoadOperation.start_time <= date_to)

        return query.order_by(RoadOperation.created_at.desc()).offset(skip).limit(limit).all()

    def get_events_for_operation(self, operation_id: str) -> List[RoadOperationEvent]:
        """Fetch audit event history for a road operation in chronological order."""
        return (
            self.db.query(RoadOperationEvent)
            .filter(RoadOperationEvent.operation_id == operation_id)
            .order_by(RoadOperationEvent.created_at.asc())
            .all()
        )
