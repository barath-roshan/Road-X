"""Repository for RoadSegment entity persistence operations."""

from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from backend.models.road import RoadSegment
from backend.repositories.base_repository import BaseRepository


class RoadRepository(BaseRepository[RoadSegment]):
    """RoadRepository managing RoadSegment database operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(RoadSegment, db)

    def get_by_segment_id(self, segment_id: str) -> Optional[RoadSegment]:
        """Fetch road segment by unique string segment_id (e.g. SEG-MH-4001)."""
        return self.db.query(RoadSegment).filter(RoadSegment.segment_id == segment_id.strip()).first()
