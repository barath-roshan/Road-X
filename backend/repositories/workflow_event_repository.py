"""Repository for WorkflowEvent audit history logging and queries."""

from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from backend.models.workflow_event import WorkflowEvent
from backend.repositories.base_repository import BaseRepository


class WorkflowEventRepository(BaseRepository[WorkflowEvent]):
    """WorkflowEventRepository managing workflow audit history traces."""

    def __init__(self, db: Session) -> None:
        super().__init__(WorkflowEvent, db)

    def get_history_for_grievance(self, grievance_id: str) -> List[WorkflowEvent]:
        """Fetch complete chronological event audit trail for a grievance."""
        return (
            self.db.query(WorkflowEvent)
            .filter(WorkflowEvent.grievance_id == grievance_id)
            .order_by(WorkflowEvent.created_at.asc())
            .all()
        )
