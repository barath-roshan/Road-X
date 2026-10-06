"""Business logic service for Citizen Grievances."""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models.grievance import Grievance, GrievanceStatus
from backend.repositories.grievance_repository import GrievanceRepository
from backend.repositories.user_repository import UserRepository
from backend.repositories.road_repository import RoadRepository
from backend.schemas.grievance import GrievanceCreate, GrievanceUpdate
from ml.common.exceptions import RoadXDataError


class GrievanceService:
    """GrievanceService coordinating validation, user/road references, and persistence."""

    def __init__(self, db: Session) -> None:
        self.grievance_repo = GrievanceRepository(db)
        self.user_repo = UserRepository(db)
        self.road_repo = RoadRepository(db)

    def create_grievance(self, payload: GrievanceCreate) -> Grievance:
        """Create a new citizen grievance report after validating references."""
        # 1. Validate citizen user ID if provided
        if payload.citizen_id:
            citizen = self.user_repo.get_by_id(payload.citizen_id)
            if not citizen:
                raise RoadXDataError(f"Referenced citizen user ID '{payload.citizen_id}' does not exist.")

        # 2. Resolve road_id from direct road_id UUID or string segment_id
        resolved_road_id = payload.road_id
        if not resolved_road_id and payload.road_segment_id:
            road_seg = self.road_repo.get_by_segment_id(payload.road_segment_id)
            if road_seg:
                resolved_road_id = road_seg.id

        if resolved_road_id:
            road_seg = self.road_repo.get_by_id(resolved_road_id)
            if not road_seg:
                raise RoadXDataError(f"Referenced road segment ID '{resolved_road_id}' does not exist.")

        grievance = Grievance(
            citizen_id=payload.citizen_id,
            road_id=resolved_road_id,
            issue_category=payload.issue_category.strip().upper(),
            description=payload.description.strip(),
            latitude=payload.latitude,
            longitude=payload.longitude,
            status=GrievanceStatus.SUBMITTED,
        )
        return self.grievance_repo.add(grievance)

    def get_grievance(self, grievance_id: str) -> Grievance:
        """Fetch grievance report by ID or raise exception."""
        grievance = self.grievance_repo.get_by_id(grievance_id)
        if not grievance:
            raise RoadXDataError(f"Grievance with ID '{grievance_id}' not found.")
        return grievance

    def list_grievances(
        self,
        status: Optional[GrievanceStatus] = None,
        issue_category: Optional[str] = None,
        road_id: Optional[str] = None,
        citizen_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Grievance]:
        """List and filter grievances."""
        return self.grievance_repo.filter_grievances(
            status=status,
            issue_category=issue_category,
            road_id=road_id,
            citizen_id=citizen_id,
            skip=skip,
            limit=limit,
        )

    def update_grievance(self, grievance_id: str, payload: GrievanceUpdate) -> Grievance:
        """Update grievance attributes and lifecycle status."""
        grievance = self.get_grievance(grievance_id)

        if payload.issue_category is not None:
            grievance.issue_category = payload.issue_category.strip().upper()
        if payload.description is not None:
            grievance.description = payload.description.strip()
        if payload.status is not None:
            grievance.status = payload.status
        if payload.latitude is not None:
            grievance.latitude = payload.latitude
        if payload.longitude is not None:
            grievance.longitude = payload.longitude

        return self.grievance_repo.update(grievance)
