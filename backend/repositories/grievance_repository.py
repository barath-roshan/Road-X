"""Repository for Grievance entity persistence and query operations."""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models.grievance import Grievance, GrievanceStatus
from backend.repositories.base_repository import BaseRepository


class GrievanceRepository(BaseRepository[Grievance]):
    """GrievanceRepository managing citizen grievance persistence."""

    def __init__(self, db: Session) -> None:
        super().__init__(Grievance, db)

    def filter_grievances(
        self,
        status: Optional[GrievanceStatus] = None,
        issue_category: Optional[str] = None,
        road_id: Optional[str] = None,
        citizen_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Grievance]:
        """Query and filter grievances with pagination."""
        query = self.db.query(Grievance)

        if status is not None:
            query = query.filter(Grievance.status == status)
        if issue_category is not None:
            query = query.filter(Grievance.issue_category == issue_category)
        if road_id is not None:
            query = query.filter(Grievance.road_id == road_id)
        if citizen_id is not None:
            query = query.filter(Grievance.citizen_id == citizen_id)

        return query.order_by(Grievance.created_at.desc()).offset(skip).limit(limit).all()
