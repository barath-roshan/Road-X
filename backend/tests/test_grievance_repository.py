"""Unit tests for GrievanceRepository and GrievanceService."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.models.grievance import GrievanceStatus
from backend.schemas.grievance import GrievanceCreate, GrievanceUpdate
from backend.schemas.road import RoadCreate
from backend.schemas.user import UserCreate
from backend.services.grievance_service import GrievanceService
from backend.services.user_service import UserService
from backend.repositories.road_repository import RoadRepository
from ml.common.exceptions import RoadXDataError


def test_create_and_retrieve_grievance_with_relationships(db_session: Session):
    """Test creating grievance linked to citizen user and road segment."""
    user_service = UserService(db_session)
    road_repo = RoadRepository(db_session)
    grievance_service = GrievanceService(db_session)

    # 1. Create user and road segment
    user = user_service.create_user(UserCreate(name="Citizen Anita", email="anita@example.com"))
    from backend.models.road import RoadSegment
    road = road_repo.add(RoadSegment(segment_id="SEG-TEST-100", road_name="Station Road"))

    # 2. Create grievance report
    payload = GrievanceCreate(
        citizen_id=user.id,
        road_id=road.id,
        issue_category="POTHOLE",
        description="Deep pothole in left lane near station entrance.",
        latitude=19.0760,
        longitude=72.8777,
    )
    grievance = grievance_service.create_grievance(payload)

    assert grievance.id is not None
    assert grievance.status == GrievanceStatus.SUBMITTED
    assert grievance.citizen_id == user.id
    assert grievance.road_id == road.id

    # 3. Test relationship access
    assert grievance.citizen.name == "Citizen Anita"
    assert grievance.road_segment.road_name == "Station Road"


def test_update_grievance_lifecycle_status(db_session: Session):
    """Test updating grievance lifecycle status."""
    service = GrievanceService(db_session)
    grievance = service.create_grievance(
        GrievanceCreate(issue_category="CRACK", description="Surface crack expanding rapidly.")
    )

    assert grievance.status == GrievanceStatus.SUBMITTED

    # Update status to UNDER_REVIEW
    updated = service.update_grievance(grievance.id, GrievanceUpdate(status=GrievanceStatus.UNDER_REVIEW))
    assert updated.status == GrievanceStatus.UNDER_REVIEW


def test_invalid_citizen_id_raises_error(db_session: Session):
    """Test passing invalid citizen_id raises RoadXDataError."""
    service = GrievanceService(db_session)
    payload = GrievanceCreate(
        citizen_id="non-existent-user-id",
        issue_category="POTHOLE",
        description="Pothole complaint.",
    )
    with pytest.raises(RoadXDataError, match="does not exist"):
        service.create_grievance(payload)
