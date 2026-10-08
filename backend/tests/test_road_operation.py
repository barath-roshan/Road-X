"""Unit tests for Road Operations Service, state machine transitions, validations, and role permissions."""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from backend.models.road_operation import RoadOperationStatus, RoadOperationType
from backend.models.user import User, UserRole
from backend.models.road import RoadSegment
from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.work_order import WorkOrder, WorkOrderStatus
from backend.security import UserContext, UnauthorizedError, InvalidStateTransitionError
from backend.services.road_operation_service import RoadOperationService
from backend.schemas.road_operation import RoadOperationCreate, RoadOperationUpdate
from pydantic import ValidationError
from ml.common.exceptions import RoadXDataError


@pytest.fixture
def test_setup(db_session: Session):
    """Seed test users and road segment."""
    gov = User(name="Officer Dave", email="dave@gov.in", role=UserRole.GOVERNMENT_OFFICER)
    citizen = User(name="Citizen Charlie", email="charlie@citizen.com", role=UserRole.CITIZEN)
    contractor = User(name="Contractor Alice", email="alice@contractor.com", role=UserRole.CONTRACTOR)

    db_session.add_all([gov, citizen, contractor])
    db_session.flush()

    road1 = RoadSegment(segment_id="SEG-MAIN", road_name="Main Street", area="Central", latitude=12.97, longitude=77.59)
    road2 = RoadSegment(segment_id="SEG-ALT", road_name="Bypass Road", area="Central", latitude=12.98, longitude=77.60)
    db_session.add_all([road1, road2])
    db_session.flush()

    gr = Grievance(
        citizen_id=citizen.id,
        road_id=road1.id,
        description="Hazardous pothole",
        issue_category="POTHOLE",
        latitude=12.97,
        longitude=77.59,
        status=GrievanceStatus.IN_PROGRESS,
    )
    db_session.add(gr)
    db_session.flush()

    wo = WorkOrder(
        grievance_id=gr.id,
        road_id=road1.id,
        created_by=gov.id,
        assigned_contractor_id=contractor.id,
        title="Repair Main Street Pothole",
        description="Asphalt compaction",
        priority="HIGH",
        status=WorkOrderStatus.IN_PROGRESS,
    )
    db_session.add(wo)
    db_session.commit()

    return {
        "gov": gov,
        "citizen": citizen,
        "contractor": contractor,
        "road1": road1,
        "road2": road2,
        "gr": gr,
        "wo": wo,
    }


def test_road_operation_role_permissions(db_session: Session, test_setup: dict):
    """Verify that only GOVERNMENT_OFFICER can create and mutate road operations."""
    service = RoadOperationService(db_session)

    gov_actor = UserContext(user_id=test_setup["gov"].id, role=UserRole.GOVERNMENT_OFFICER)
    citizen_actor = UserContext(user_id=test_setup["citizen"].id, role=UserRole.CITIZEN)
    contractor_actor = UserContext(user_id=test_setup["contractor"].id, role=UserRole.CONTRACTOR)

    now = datetime.now(timezone.utc)
    payload = RoadOperationCreate(
        title="Main Street Closure",
        description="Road closure for asphalt resurfacing",
        reason="Resurfacing work",
        operation_type=RoadOperationType.ROAD_CLOSURE,
        road_id=test_setup["road1"].id,
        start_time=now,
        expected_end_time=now + timedelta(days=2),
    )

    # Citizen cannot create -> UnauthorizedError
    with pytest.raises(UnauthorizedError):
        service.create_operation(citizen_actor, payload)

    # Contractor cannot create -> UnauthorizedError
    with pytest.raises(UnauthorizedError):
        service.create_operation(contractor_actor, payload)

    # Government officer can create -> Success
    op_read = service.create_operation(gov_actor, payload)
    assert op_read.title == "Main Street Closure"
    assert op_read.status == RoadOperationStatus.PLANNED


def test_road_operation_validation_rules(db_session: Session, test_setup: dict):
    """Verify input date validation and foreign key existence checks."""
    service = RoadOperationService(db_session)
    gov_actor = UserContext(user_id=test_setup["gov"].id, role=UserRole.GOVERNMENT_OFFICER)
    now = datetime.now(timezone.utc)

    # Invalid end time (end <= start)
    with pytest.raises((RoadXDataError, ValidationError)):
        service.create_operation(
            gov_actor,
            RoadOperationCreate(
                title="Invalid Time Operation",
                description="Test description",
                reason="Test reason",
                start_time=now,
                expected_end_time=now - timedelta(hours=1),
            ),
        )

    # Invalid road_id -> RoadXDataError
    with pytest.raises(RoadXDataError):
        service.create_operation(
            gov_actor,
            RoadOperationCreate(
                title="Invalid Road",
                description="Test description",
                reason="Test reason",
                road_id="NON_EXISTENT_ROAD_ID",
                start_time=now,
                expected_end_time=now + timedelta(hours=5),
            ),
        )


def test_road_operation_lifecycle_and_audit_history(db_session: Session, test_setup: dict):
    """Verify complete lifecycle PLANNED -> ACTIVE -> COMPLETED and audit event logging."""
    service = RoadOperationService(db_session)
    gov_actor = UserContext(user_id=test_setup["gov"].id, role=UserRole.GOVERNMENT_OFFICER)
    now = datetime.now(timezone.utc)

    # 1. Create Operation
    op = service.create_operation(
        gov_actor,
        RoadOperationCreate(
            title="Bridge Maintenance",
            description="Lifting bridge deck",
            reason="Scheduled structural maintenance",
            operation_type=RoadOperationType.MAINTENANCE_WORK,
            road_id=test_setup["road1"].id,
            grievance_id=test_setup["gr"].id,
            work_order_id=test_setup["wo"].id,
            start_time=now,
            expected_end_time=now + timedelta(days=3),
            alternative_route_name="Bypass Detour",
            alternative_route_instructions="Take Bypass Road north for 2km",
            alternative_road_id=test_setup["road2"].id,
            alternative_distance_km=2.5,
        ),
    )
    assert op.status == RoadOperationStatus.PLANNED

    # 2. Activate Operation
    act_op = service.activate_operation(gov_actor, op.id, notes="Crews deployed on-site")
    assert act_op.status == RoadOperationStatus.ACTIVE

    # Cannot re-activate or perform illegal transition (e.g. PLANNED -> COMPLETED is permitted, but COMPLETED -> ACTIVE is blocked)
    comp_op = service.complete_operation(gov_actor, op.id, notes="Resurfacing completed cleanly")
    assert comp_op.status == RoadOperationStatus.COMPLETED
    assert comp_op.actual_end_time is not None

    # Cannot activate a completed operation -> InvalidStateTransitionError
    with pytest.raises(InvalidStateTransitionError):
        service.activate_operation(gov_actor, op.id)

    # Check Audit History
    detail = service.get_operation_government(gov_actor, op.id)
    assert len(detail.history) >= 3
    event_types = [e.event_type for e in detail.history]
    assert "ROAD_OPERATION_CREATED" in event_types
    assert "ROAD_OPERATION_ACTIVATED" in event_types
    assert "ROAD_OPERATION_COMPLETED" in event_types


def test_road_operation_citizen_visibility(db_session: Session, test_setup: dict):
    """Verify citizen public listing and detail reading for active and planned operations."""
    service = RoadOperationService(db_session)
    gov_actor = UserContext(user_id=test_setup["gov"].id, role=UserRole.GOVERNMENT_OFFICER)
    now = datetime.now(timezone.utc)

    op1 = service.create_operation(
        gov_actor,
        RoadOperationCreate(
            title="Active Closure",
            description="Main street blocked",
            reason="Pothole repair",
            start_time=now,
            expected_end_time=now + timedelta(days=1),
            status=RoadOperationStatus.PLANNED,
        ),
    )

    # Activate op1
    service.activate_operation(gov_actor, op1.id)

    # Citizen list active operations
    c_list = service.list_operations_citizen(active_only=True)
    assert len(c_list) >= 1
    titles = [item.title for item in c_list]
    assert "Active Closure" in titles

    # Citizen read detail
    c_detail = service.get_operation_citizen(op1.id)
    assert c_detail.title == "Active Closure"
    assert c_detail.status == RoadOperationStatus.ACTIVE
