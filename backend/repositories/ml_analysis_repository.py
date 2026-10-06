"""Repository for MLAnalysisResult entity persistence operations."""

from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from backend.models.ml_analysis import MLAnalysisResult
from backend.repositories.base_repository import BaseRepository


class MLAnalysisRepository(BaseRepository[MLAnalysisResult]):
    """MLAnalysisRepository managing stored pipeline prediction outputs."""

    def __init__(self, db: Session) -> None:
        super().__init__(MLAnalysisResult, db)

    def get_by_grievance_id(self, grievance_id: str) -> List[MLAnalysisResult]:
        """Fetch all stored ML analysis outputs for a given grievance ID."""
        return (
            self.db.query(MLAnalysisResult)
            .filter(MLAnalysisResult.grievance_id == grievance_id)
            .order_by(MLAnalysisResult.created_at.desc())
            .all()
        )
