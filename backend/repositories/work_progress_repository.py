"""Repository for WorkProgress persistence and query operations."""

from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from backend.models.work_progress import WorkProgress
from backend.repositories.base_repository import BaseRepository


class WorkProgressRepository(BaseRepository[WorkProgress]):
    """WorkProgressRepository managing contractor progress updates database operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(WorkProgress, db)

    def get_by_work_order(self, work_order_id: str) -> List[WorkProgress]:
        """Fetch all progress entries recorded for a specific work order, ordered chronologically."""
        return (
            self.db.query(WorkProgress)
            .filter(WorkProgress.work_order_id == work_order_id)
            .order_by(WorkProgress.created_at.asc())
            .all()
        )
