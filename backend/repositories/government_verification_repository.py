"""Repository for GovernmentVerification persistence operations."""

from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from backend.models.government_verification import GovernmentVerification
from backend.repositories.base_repository import BaseRepository


class GovernmentVerificationRepository(BaseRepository[GovernmentVerification]):
    """GovernmentVerificationRepository managing officer completion verification records."""

    def __init__(self, db: Session) -> None:
        super().__init__(GovernmentVerification, db)

    def get_by_work_order_id(self, work_order_id: str) -> List[GovernmentVerification]:
        """Fetch all verification decisions for a work order."""
        return (
            self.db.query(GovernmentVerification)
            .filter(GovernmentVerification.work_order_id == work_order_id)
            .order_by(GovernmentVerification.created_at.desc())
            .all()
        )
