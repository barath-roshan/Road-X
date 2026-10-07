"""Unit tests for Contractor Workflow Service, ownership rules, and state machine transitions."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.road import RoadSegment
from backend.models.user import User, UserRole
from backend.models.work_order import WorkOrder, WorkOrderStatus
from backend.models.government_verification import VerificationDecision
from backend.schemas.completion_submission import CompletionSubmissionCreate
from backend.security import UserContext, UnauthorizedError, InvalidStateTransitionError
from backend.services.contractor_workflow_service import ContractorWorkflowService
from backend.services.government_workflow_service import GovernmentWorkflowService
from ml.common.exceptions import RoadXDataError


@pytest.fixture
def setup_data(db_session: Session):
    """Seed test database with users, road segment, grievance, and assigned work order."""
    gov_user = User(
        name="Officer Bob",
        email="officer.bob@city.gov.in",
        role=UserRole.GOVERNMENT_OFFICER,
    )
    contractor_a = User(
        name="Contractor Alice (BuildCorp)",
        email="alice@buildcorp.com",
        role=UserRole.CONTRACTOR,
    )
    contractor_b = User(
        name="Contractor Charlie (RoadFix)",
        email="charlie@roadfix.com",
        role=UserRole.CONTRACTOR,
    )
    citizen_user = User(
        name="Dave Citizen",
        email="dave@example.com",
        role=UserRole.CITIZEN,
    )
    db_session.add_all([gov_user, contractor_a, contractor_b, citizen_user])
    db_session.flush()

    road = RoadSegment(
        segment_id="SEG-BLR-101",
        road_name="Outer Ring Road Sec 2",
        area="Bellandur",
        latitude=12.9260,
        longitude=77.6762,
        road_type="ASPHALT",
    )
    db_session.add(road)
    db_session.flush()

    grievance = Grievance(
        citizen_id=citizen_user.id,
        road_id=road.id,
        description="Deep pothole causing traffic slowdowns",
        issue_category="POTHOLE",
        latitude=12.9265,
        longitude=77.6765,
        status=GrievanceStatus.UNDER_REVIEW,
    )
    db_session.add(grievance)
    db_session.flush()

    work_order = WorkOrder(
        grievance_id=grievance.id,
        road_id=road.id,
        created_by=gov_user.id,
        assigned_contractor_id=contractor_a.id,
        title="Repair Pothole on Outer Ring Road",
        description="Asphalt patch and roller compaction required",
        priority="HIGH",
        status=WorkOrderStatus.ASSIGNED,
    )
    db_session.add(work_order)
    db_session.commit()

    return {
        "gov_user": gov_user,
        "contractor_a": contractor_a,
        "contractor_b": contractor_b,
        "citizen_user": citizen_user,
        "road": road,
        "grievance": grievance,
        "work_order": work_order,
    }


def test_contractor_ownership_enforcement(db_session: Session, setup_data):
    """Verify that Contractor A can access their work order, but Contractor B and Citizen are rejected."""
    service = ContractorWorkflowService(db_session)
    wo = setup_data["work_order"]

    actor_a = UserContext(user_id=setup_data["contractor_a"].id, role=UserRole.CONTRACTOR)
    actor_b = UserContext(user_id=setup_data["contractor_b"].id, role=UserRole.CONTRACTOR)
    actor_citizen = UserContext(user_id=setup_data["citizen_user"].id, role=UserRole.CITIZEN)

    # Contractor A can access details
    details = service.get_work_order_details(actor=actor_a, work_order_id=wo.id)
    assert details.id == wo.id

    # Contractor B accessing Contractor A's work order raises UnauthorizedError
    with pytest.raises(UnauthorizedError) as exc_b:
        service.get_work_order_details(actor=actor_b, work_order_id=wo.id)
    assert "not assigned" in str(exc_b.value)

    # Citizen accessing contractor service raises UnauthorizedError
    with pytest.raises(UnauthorizedError):
        service.get_work_order_details(actor=actor_citizen, work_order_id=wo.id)


def test_start_work_order_transition(db_session: Session, setup_data):
    """Verify starting work order transitions status to IN_PROGRESS."""
    service = ContractorWorkflowService(db_session)
    wo = setup_data["work_order"]
    actor_a = UserContext(user_id=setup_data["contractor_a"].id, role=UserRole.CONTRACTOR)

    updated_wo = service.start_work_order(actor=actor_a, work_order_id=wo.id, notes="Mobilizing crew on site")
    assert updated_wo.status == WorkOrderStatus.IN_PROGRESS

    # Grievance status should also be updated to IN_PROGRESS
    gr = db_session.query(Grievance).filter_by(id=wo.grievance_id).first()
    assert gr.status == GrievanceStatus.IN_PROGRESS


def test_progress_percentage_validation_and_non_resolution(db_session: Session, setup_data):
    """Verify progress percentage must be 0-100, and 100% progress does NOT set status to COMPLETED or RESOLVED."""
    service = ContractorWorkflowService(db_session)
    wo = setup_data["work_order"]
    actor_a = UserContext(user_id=setup_data["contractor_a"].id, role=UserRole.CONTRACTOR)

    # Invalid progress < 0
    with pytest.raises(RoadXDataError):
        service.update_progress(actor=actor_a, work_order_id=wo.id, progress_percentage=-10)

    # Invalid progress > 100
    with pytest.raises(RoadXDataError):
        service.update_progress(actor=actor_a, work_order_id=wo.id, progress_percentage=150)

    # Valid progress 50%
    p50 = service.update_progress(actor=actor_a, work_order_id=wo.id, progress_percentage=50, note="Half done")
    assert p50.progress_percentage == 50

    # Valid progress 100%
    p100 = service.update_progress(actor=actor_a, work_order_id=wo.id, progress_percentage=100, note="Layer finished")
    assert p100.progress_percentage == 100

    # Crucial rule: status remains IN_PROGRESS, NOT COMPLETED or RESOLVED!
    wo_db = db_session.query(WorkOrder).filter_by(id=wo.id).first()
    gr_db = db_session.query(Grievance).filter_by(id=wo.grievance_id).first()
    assert wo_db.status == WorkOrderStatus.IN_PROGRESS
    assert gr_db.status != GrievanceStatus.RESOLVED


def test_completion_submission_and_government_verification_lifecycle(db_session: Session, setup_data):
    """Test full completion submission lifecycle:
    Contractor submits completion -> PENDING_VERIFICATION (NOT RESOLVED).
    Government REJECTS -> reverts to IN_PROGRESS.
    Contractor re-submits completion -> PENDING_VERIFICATION.
    Government APPROVES -> RESOLVED & COMPLETED.
    """
    contractor_service = ContractorWorkflowService(db_session)
    gov_service = GovernmentWorkflowService(db_session)

    wo = setup_data["work_order"]
    contractor_actor = UserContext(user_id=setup_data["contractor_a"].id, role=UserRole.CONTRACTOR)
    gov_actor = UserContext(user_id=setup_data["gov_user"].id, role=UserRole.GOVERNMENT_OFFICER)

    # 1. Start work
    contractor_service.start_work_order(actor=contractor_actor, work_order_id=wo.id)

    # 2. Attach evidence
    ev = contractor_service.attach_evidence(
        actor=contractor_actor,
        work_order_id=wo.id,
        file_name="repaired_patch.jpg",
        file_type="image/jpeg",
        storage_path="/uploads/repaired_patch.jpg",
        file_size_bytes=204850,
    )
    assert ev.id is not None

    # 3. Contractor submits completion
    sub_res = contractor_service.submit_completion(
        actor=contractor_actor,
        work_order_id=wo.id,
        payload=CompletionSubmissionCreate(
            completion_note="Asphalt repair completed according to municipal specification.",
            actual_work_summary="1.5 sq meter patch laid and compacted",
            evidence_ids=[ev.id],
        ),
    )
    assert sub_res.status == "PENDING_VERIFICATION"
    assert sub_res.grievance_status == "PENDING_VERIFICATION"

    # Verify status in database
    wo_db = db_session.query(WorkOrder).filter_by(id=wo.id).first()
    gr_db = db_session.query(Grievance).filter_by(id=wo.grievance_id).first()
    assert wo_db.status == WorkOrderStatus.PENDING_VERIFICATION
    assert gr_db.status == GrievanceStatus.PENDING_VERIFICATION
    assert gr_db.status != GrievanceStatus.RESOLVED  # STRICT RULE CHECK

    # 4. Government officer rejects completion due to poor compaction
    gov_service.verify_work_completion(
        actor=gov_actor,
        work_order_id=wo.id,
        decision=VerificationDecision.REJECT,
        notes="Edge seal incomplete. Please re-roll edges and re-submit.",
    )

    # Verify status reverted to IN_PROGRESS
    assert wo_db.status == WorkOrderStatus.IN_PROGRESS
    assert gr_db.status == GrievanceStatus.IN_PROGRESS

    # Contractor views details and checks latest rejection notes
    details = contractor_service.get_work_order_details(actor=contractor_actor, work_order_id=wo.id)
    assert details.latest_rejection_notes == "Edge seal incomplete. Please re-roll edges and re-submit."

    # 5. Contractor performs rework and re-submits completion
    sub_res_2 = contractor_service.submit_completion(
        actor=contractor_actor,
        work_order_id=wo.id,
        payload=CompletionSubmissionCreate(completion_note="Edges re-rolled and sealed."),
    )
    assert sub_res_2.status == "PENDING_VERIFICATION"

    # 6. Government officer approves verification
    gov_service.verify_work_completion(
        actor=gov_actor,
        work_order_id=wo.id,
        decision=VerificationDecision.APPROVE,
        notes="Audit passed. Perfect repair.",
    )

    # 7. Final status verification
    assert wo_db.status == WorkOrderStatus.COMPLETED
    assert gr_db.status == GrievanceStatus.RESOLVED
