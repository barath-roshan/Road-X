"""Repository for GovernmentReview persistence operations."""

from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from backend.models.government_review import GovernmentReview
from backend.repositories.base_repository import BaseRepository


class GovernmentReviewRepository(BaseRepository[GovernmentReview]):
    """GovernmentReviewRepository managing government grievance review decisions."""

    def __init__(self, db: Session) -> None:
        super().__init__(GovernmentReview, db)

    def get_latest_for_grievance(self, grievance_id: str) -> Optional[GovernmentReview]:
        """Fetch the most recent government review decision for a grievance."""
        return (
            self.db.query(GovernmentReview)
            .filter(GovernmentReview.grievance_id == grievance_id)
            .order_by(GovernmentReview.created_at.desc())
            .first()
        )
