"""Repository for WorkOrder persistence and query operations."""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models.work_order import WorkOrder, WorkOrderStatus
from backend.repositories.base_repository import BaseRepository


class WorkOrderRepository(BaseRepository[WorkOrder]):
    """WorkOrderRepository managing maintenance work order database operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(WorkOrder, db)

    def get_by_grievance_id(self, grievance_id: str) -> List[WorkOrder]:
        """Fetch all work orders generated for a specific grievance."""
        return (
            self.db.query(WorkOrder)
            .filter(WorkOrder.grievance_id == grievance_id)
            .order_by(WorkOrder.created_at.desc())
            .all()
        )

    def filter_work_orders(
        self,
        status: Optional[WorkOrderStatus] = None,
        priority: Optional[str] = None,
        assigned_contractor_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WorkOrder]:
        """Query work orders with optional status, priority, and contractor filters."""
        query = self.db.query(WorkOrder)

        if status is not None:
            query = query.filter(WorkOrder.status == status)
        if priority is not None:
            query = query.filter(WorkOrder.priority == priority.upper())
        if assigned_contractor_id is not None:
            query = query.filter(WorkOrder.assigned_contractor_id == assigned_contractor_id)

        return query.order_by(WorkOrder.created_at.desc()).offset(skip).limit(limit).all()
