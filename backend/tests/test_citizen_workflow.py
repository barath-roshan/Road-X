"""Unit tests for Citizen Workflow Service, ownership isolation, timeline mapping, and governance rules."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.road import RoadSegment
from backend.models.user import User, UserRole
from backend.models.work_order import WorkOrder, WorkOrderStatus
from backend.models.government_verification import VerificationDecision
from backend.schemas.citizen import CitizenGrievanceCreate
from backend.schemas.completion_submission import CompletionSubmissionCreate
from backend.security import UserContext, UnauthorizedError, InvalidStateTransitionError
from backend.services.citizen_workflow_service import CitizenWorkflowService
from backend.services.contractor_workflow_service import ContractorWorkflowService
from backend.services.government_workflow_service import GovernmentWorkflowService
from ml.common.exceptions import RoadXDataError


@pytest.fixture
def citizen_setup_data(db_session: Session):
    """Seed test database with users, road segment, and initial grievances."""
    gov_user = User(
        name="Officer Bob",
        email="officer.bob@city.gov.in",
        role=UserRole.GOVERNMENT_OFFICER,
    )
    contractor_user = User(
        name="Contractor Alice",
        email="alice@buildcorp.com",
        role=UserRole.CONTRACTOR,
    )
    citizen_a = User(
        name="Dave Citizen",
        email="dave@example.com",
        role=UserRole.CITIZEN,
    )
    citizen_b = User(
        name="Eve Citizen",
        email="eve@example.com",
        role=UserRole.CITIZEN,
    )
    db_session.add_all([gov_user, contractor_user, citizen_a, citizen_b])
    db_session.flush()

    road = RoadSegment(
        segment_id="SEG-BLR-202",
        road_name="MG Road Sec 4",
        area="Indiranagar",
        latitude=12.9716,
        longitude=77.5946,
        road_type="ASPHALT",
    )
    db_session.add(road)
    db_session.commit()

    return {
        "gov_user": gov_user,
        "contractor_user": contractor_user,
        "citizen_a": citizen_a,
        "citizen_b": citizen_b,
        "road": road,
    }


def test_create_citizen_grievance_initial_status_submitted(db_session: Session, citizen_setup_data):
    """Verify citizen grievance creation forces initial status to SUBMITTED and logs workflow event."""
    service = CitizenWorkflowService(db_session)
    actor_a = UserContext(user_id=citizen_setup_data["citizen_a"].id, role=UserRole.CITIZEN)

    payload = CitizenGrievanceCreate(
        issue_category="POTHOLE",
        description="Dangerous deep pothole near bus stop",
        latitude=12.9720,
        longitude=77.5950,
        road_segment_id="SEG-BLR-202",
    )
    grievance = service.create_grievance(actor=actor_a, payload=payload)

    assert grievance.id is not None
    assert grievance.citizen_id == citizen_setup_data["citizen_a"].id
    assert grievance.status == GrievanceStatus.SUBMITTED
    assert grievance.road_id == citizen_setup_data["road"].id


def test_citizen_ownership_isolation(db_session: Session, citizen_setup_data):
    """Verify Citizen A can access their grievance, but Citizen B and Contractor are rejected."""
    service = CitizenWorkflowService(db_session)
    actor_a = UserContext(user_id=citizen_setup_data["citizen_a"].id, role=UserRole.CITIZEN)
    actor_b = UserContext(user_id=citizen_setup_data["citizen_b"].id, role=UserRole.CITIZEN)
    actor_contractor = UserContext(user_id=citizen_setup_data["contractor_user"].id, role=UserRole.CONTRACTOR)

    # Citizen A creates grievance
    payload = CitizenGrievanceCreate(
        issue_category="WATERLOGGING",
        description="Water accumulation on road after rain",
        latitude=12.9725,
        longitude=77.5955,
    )
    grievance = service.create_grievance(actor=actor_a, payload=payload)

    # Citizen A lists grievances -> contains created grievance
    grievances_a = service.list_citizen_grievances(actor=actor_a)
    assert len(grievances_a) == 1
    assert grievances_a[0].id == grievance.id

    # Citizen B lists grievances -> empty
    grievances_b = service.list_citizen_grievances(actor=actor_b)
    assert len(grievances_b) == 0

    # Citizen B attempts to access Citizen A's grievance details -> UnauthorizedError (403)
    with pytest.raises(UnauthorizedError) as exc_info:
        service.get_citizen_grievance_details(actor=actor_b, grievance_id=grievance.id)
    assert "does not own" in str(exc_info.value)

    # Contractor attempts to call citizen service -> UnauthorizedError (403)
    with pytest.raises(UnauthorizedError):
        service.get_citizen_grievance_details(actor=actor_contractor, grievance_id=grievance.id)


def test_citizen_attach_evidence_ownership_and_terminal_state(db_session: Session, citizen_setup_data):
    """Verify evidence attachment requires ownership and fails on terminal state."""
    service = CitizenWorkflowService(db_session)
    actor_a = UserContext(user_id=citizen_setup_data["citizen_a"].id, role=UserRole.CITIZEN)
    actor_b = UserContext(user_id=citizen_setup_data["citizen_b"].id, role=UserRole.CITIZEN)

    payload = CitizenGrievanceCreate(
        issue_category="STREETLIGHT",
        description="Streetlight non-functional",
        latitude=12.9730,
        longitude=77.5960,
    )
    grievance = service.create_grievance(actor=actor_a, payload=payload)

    # Citizen A attaches evidence -> succeeds
    ev = service.attach_evidence(
        actor=actor_a,
        grievance_id=grievance.id,
        file_name="dark_street.jpg",
        file_type="image/jpeg",
        storage_path="/uploads/dark_street.jpg",
        file_size_bytes=154000,
    )
    assert ev.id is not None
    assert ev.grievance_id == grievance.id

    # Citizen B attempts to attach evidence to Citizen A's grievance -> UnauthorizedError
    with pytest.raises(UnauthorizedError):
        service.attach_evidence(
            actor=actor_b,
            grievance_id=grievance.id,
            file_name="fake.jpg",
            file_type="image/jpeg",
            storage_path="/uploads/fake.jpg",
        )

    # Transition grievance to terminal RESOLVED state
    grievance.status = GrievanceStatus.RESOLVED
    db_session.commit()

    # Attachment to RESOLVED grievance fails
    with pytest.raises(InvalidStateTransitionError):
        service.attach_evidence(
            actor=actor_a,
            grievance_id=grievance.id,
            file_name="after.jpg",
            file_type="image/jpeg",
            storage_path="/uploads/after.jpg",
        )


def test_citizen_grievance_details_and_timeline(db_session: Session, citizen_setup_data):
    """Verify citizen details view returns timeline and work progress."""
    citizen_service = CitizenWorkflowService(db_session)
    gov_service = GovernmentWorkflowService(db_session)
    contractor_service = ContractorWorkflowService(db_session)

    actor_citizen = UserContext(user_id=citizen_setup_data["citizen_a"].id, role=UserRole.CITIZEN)
    actor_gov = UserContext(user_id=citizen_setup_data["gov_user"].id, role=UserRole.GOVERNMENT_OFFICER)
    actor_contractor = UserContext(user_id=citizen_setup_data["contractor_user"].id, role=UserRole.CONTRACTOR)

    # 1. Citizen creates grievance
    gr = citizen_service.create_grievance(
        actor=actor_citizen,
        payload=CitizenGrievanceCreate(
            issue_category="POTHOLE",
            description="Deep pothole in middle of road",
            latitude=12.9716,
            longitude=77.5946,
            road_segment_id="SEG-BLR-202",
        ),
    )

    # Check initial details view
    details1 = citizen_service.get_citizen_grievance_details(actor=actor_citizen, grievance_id=gr.id)
    assert details1.road_name == "MG Road Sec 4"
    assert details1.status == GrievanceStatus.SUBMITTED
    assert len(details1.timeline) >= 1
    assert "submitted" in details1.timeline[0].public_message.lower()

    # 2. Government accepts & creates work order
    from backend.models.government_review import ReviewDecision
    gov_service.review_grievance(
        actor=actor_gov,
        grievance_id=gr.id,
        decision=ReviewDecision.ACCEPT,
    )
    from backend.schemas.work_order import WorkOrderCreate
    wo = gov_service.create_and_assign_work_order(
        actor=actor_gov,
        grievance_id=gr.id,
        payload=WorkOrderCreate(
            title="Pothole patch repair",
            description="Patch pothole",
            assigned_contractor_id=citizen_setup_data["contractor_user"].id,
        ),
    )

    # 3. Contractor starts & updates progress
    contractor_service.start_work_order(actor=actor_contractor, work_order_id=wo.id)
    contractor_service.update_progress(actor=actor_contractor, work_order_id=wo.id, progress_percentage=60, note="60% paved")

    # Check updated citizen details view
    details2 = citizen_service.get_citizen_grievance_details(actor=actor_citizen, grievance_id=gr.id)
    assert details2.status == GrievanceStatus.IN_PROGRESS
    assert details2.work_progress is not None
    assert details2.work_progress.progress_percentage == 60
    assert "60%" in details2.work_progress.status_display
