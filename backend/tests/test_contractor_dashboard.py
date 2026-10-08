"""Unit tests for Contractor Dashboard Service operations, role enforcement, ownership isolation, and workload stats."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.models.government_verification import VerificationDecision
from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.user import User, UserRole
from backend.models.work_order import WorkOrder, WorkOrderStatus
from backend.models.work_progress import WorkProgress
from backend.models.evidence import Evidence
from backend.security import UserContext, UnauthorizedError
from backend.services.contractor_dashboard_service import ContractorDashboardService
from backend.services.contractor_workflow_service import ContractorWorkflowService
from backend.services.government_workflow_service import GovernmentWorkflowService
from backend.schemas.work_order import WorkOrderCreate
from backend.schemas.completion_submission import CompletionSubmissionCreate
from ml.common.exceptions import RoadXDataError


@pytest.fixture
def test_users(db_session: Session):
    """Fixture providing user accounts for testing."""
    gov_officer = User(
        name="Officer Dave",
        email="officer_dave@example.com",
        role=UserRole.GOVERNMENT_OFFICER,
    )
    contractor_a = User(
        name="Contractor Alice",
        email="alice_repairs@example.com",
        role=UserRole.CONTRACTOR,
    )
    contractor_b = User(
        name="Contractor Bob",
        email="bob_repairs@example.com",
        role=UserRole.CONTRACTOR,
    )
    citizen = User(
        name="Citizen Charlie",
        email="charlie@example.com",
        role=UserRole.CITIZEN,
    )
    db_session.add_all([gov_officer, contractor_a, contractor_b, citizen])
    db_session.commit()
    db_session.refresh(gov_officer)
    db_session.refresh(contractor_a)
    db_session.refresh(contractor_b)
    db_session.refresh(citizen)
    return {
        "gov": gov_officer,
        "contractor_a": contractor_a,
        "contractor_b": contractor_b,
        "citizen": citizen,
    }


def test_contractor_dashboard_role_enforcement(db_session: Session, test_users: dict):
    """Verify that only CONTRACTOR role can access dashboard service methods."""
    service = ContractorDashboardService(db_session)

    gov_actor = UserContext(user_id=test_users["gov"].id, role=UserRole.GOVERNMENT_OFFICER)
    citizen_actor = UserContext(user_id=test_users["citizen"].id, role=UserRole.CITIZEN)
    contractor_actor = UserContext(user_id=test_users["contractor_a"].id, role=UserRole.CONTRACTOR)

    # Overview
    with pytest.raises(UnauthorizedError):
        service.get_overview(gov_actor)
    with pytest.raises(UnauthorizedError):
        service.get_overview(citizen_actor)
    overview = service.get_overview(contractor_actor)
    assert overview.total_assigned == 0

    # Work orders list
    with pytest.raises(UnauthorizedError):
        service.list_assigned_work_orders(gov_actor)
    with pytest.raises(UnauthorizedError):
        service.list_assigned_work_orders(citizen_actor)
    wos = service.list_assigned_work_orders(contractor_actor)
    assert len(wos) == 0


def test_contractor_dashboard_ownership_isolation(db_session: Session, test_users: dict):
    """Verify that Contractor A cannot access Contractor B's work order data."""
    gov_actor = UserContext(user_id=test_users["gov"].id, role=UserRole.GOVERNMENT_OFFICER)
    contractor_a_actor = UserContext(user_id=test_users["contractor_a"].id, role=UserRole.CONTRACTOR)
    contractor_b_actor = UserContext(user_id=test_users["contractor_b"].id, role=UserRole.CONTRACTOR)

    # Create Grievances & Work Orders
    gr1 = Grievance(
        citizen_id=test_users["citizen"].id,
        issue_category="POTHOLE",
        description="Pothole for Contractor A",
        latitude=12.97,
        longitude=77.59,
        status=GrievanceStatus.UNDER_REVIEW,
    )
    gr2 = Grievance(
        citizen_id=test_users["citizen"].id,
        issue_category="CRACK",
        description="Crack for Contractor B",
        latitude=12.98,
        longitude=77.60,
        status=GrievanceStatus.UNDER_REVIEW,
    )
    db_session.add_all([gr1, gr2])
    db_session.commit()

    gov_service = GovernmentWorkflowService(db_session)
    wo1 = gov_service.create_and_assign_work_order(
        actor=gov_actor,
        grievance_id=gr1.id,
        payload=WorkOrderCreate(
            title="Fix Pothole A",
            description="Repair pothole A",
            priority="HIGH",
            assigned_contractor_id=test_users["contractor_a"].id,
        ),
    )
    wo2 = gov_service.create_and_assign_work_order(
        actor=gov_actor,
        grievance_id=gr2.id,
        payload=WorkOrderCreate(
            title="Fix Crack B",
            description="Repair crack B",
            priority="MEDIUM",
            assigned_contractor_id=test_users["contractor_b"].id,
        ),
    )

    dash_service = ContractorDashboardService(db_session)

    # Contractor A can access wo1 detail, but NOT wo2 detail
    detail_a = dash_service.get_work_order_detail(contractor_a_actor, wo1.id)
    assert detail_a.id == wo1.id
    assert detail_a.title == "Fix Pothole A"

    with pytest.raises(UnauthorizedError):
        dash_service.get_work_order_detail(contractor_a_actor, wo2.id)

    # Contractor B can access wo2 detail, but NOT wo1 detail
    detail_b = dash_service.get_work_order_detail(contractor_b_actor, wo2.id)
    assert detail_b.id == wo2.id

    with pytest.raises(UnauthorizedError):
        dash_service.get_work_order_detail(contractor_b_actor, wo1.id)

    # Contractor A's work orders list returns only wo1
    list_a = dash_service.list_assigned_work_orders(contractor_a_actor)
    assert len(list_a) == 1
    assert list_a[0].id == wo1.id

    # Contractor B's work orders list returns only wo2
    list_b = dash_service.list_assigned_work_orders(contractor_b_actor)
    assert len(list_b) == 1
    assert list_b[0].id == wo2.id


def test_contractor_dashboard_overview_statistics(db_session: Session, test_users: dict):
    """Verify deterministic statistics in contractor overview and workload summary."""
    gov_actor = UserContext(user_id=test_users["gov"].id, role=UserRole.GOVERNMENT_OFFICER)
    contractor_actor = UserContext(user_id=test_users["contractor_a"].id, role=UserRole.CONTRACTOR)

    # Create 3 Grievances
    grievances = [
        Grievance(
            citizen_id=test_users["citizen"].id,
            issue_category="POTHOLE",
            description=f"Issue {i}",
            latitude=12.9,
            longitude=77.5,
            status=GrievanceStatus.UNDER_REVIEW,
        )
        for i in range(3)
    ]
    db_session.add_all(grievances)
    db_session.commit()

    gov_service = GovernmentWorkflowService(db_session)
    contractor_service = ContractorWorkflowService(db_session)

    wo1 = gov_service.create_and_assign_work_order(
        actor=gov_actor,
        grievance_id=grievances[0].id,
        payload=WorkOrderCreate(title="WO 1", description="WO 1", priority="LOW", assigned_contractor_id=test_users["contractor_a"].id),
    )
    wo2 = gov_service.create_and_assign_work_order(
        actor=gov_actor,
        grievance_id=grievances[1].id,
        payload=WorkOrderCreate(title="WO 2", description="WO 2", priority="HIGH", assigned_contractor_id=test_users["contractor_a"].id),
    )
    wo3 = gov_service.create_and_assign_work_order(
        actor=gov_actor,
        grievance_id=grievances[2].id,
        payload=WorkOrderCreate(title="WO 3", description="WO 3", priority="CRITICAL", assigned_contractor_id=test_users["contractor_a"].id),
    )

    # Update progress for wo2 -> 50%
    contractor_service.start_work_order(contractor_actor, wo2.id)
    contractor_service.update_progress(contractor_actor, wo2.id, progress_percentage=50, note="Halfway done")

    # Submit completion for wo3 -> PENDING_VERIFICATION (100%)
    contractor_service.start_work_order(contractor_actor, wo3.id)
    contractor_service.submit_completion(contractor_actor, wo3.id, CompletionSubmissionCreate(completion_note="Finished"))

    dash_service = ContractorDashboardService(db_session)
    overview = dash_service.get_overview(contractor_actor)

    assert overview.total_assigned == 3
    assert overview.assigned == 1  # wo1
    assert overview.in_progress == 1  # wo2
    assert overview.pending_verification == 1  # wo3
    assert overview.completed == 0
    assert overview.rework == 0
    # Average progress: (0 + 50 + 100) / 3 = 50.0
    assert overview.average_progress == 50.0

    workload = dash_service.get_workload_summary(contractor_actor)
    assert workload.total_assignments == 3
    assert workload.active_assignments == 2  # ASSIGNED + IN_PROGRESS
    assert workload.pending_verification == 1
    assert workload.resolved_completed == 0
    assert workload.average_completion_percentage == 50.0


def test_contractor_dashboard_rework_and_pending_verification_queues(db_session: Session, test_users: dict):
    """Verify pending verification queue and rework queue tracking across government decision lifecycle."""
    gov_actor = UserContext(user_id=test_users["gov"].id, role=UserRole.GOVERNMENT_OFFICER)
    contractor_actor = UserContext(user_id=test_users["contractor_a"].id, role=UserRole.CONTRACTOR)

    # Create Grievance and Work Order
    gr = Grievance(
        citizen_id=test_users["citizen"].id,
        issue_category="DRAINAGE",
        description="Drainage blockage",
        latitude=13.0,
        longitude=77.6,
        status=GrievanceStatus.UNDER_REVIEW,
    )
    db_session.add(gr)
    db_session.commit()

    gov_service = GovernmentWorkflowService(db_session)
    contractor_service = ContractorWorkflowService(db_session)

    wo = gov_service.create_and_assign_work_order(
        actor=gov_actor,
        grievance_id=gr.id,
        payload=WorkOrderCreate(title="Fix Drain", description="Unblock drain", priority="HIGH", assigned_contractor_id=test_users["contractor_a"].id),
    )

    dash_service = ContractorDashboardService(db_session)

    # Initially: no pending verification, no rework
    assert len(dash_service.get_pending_verification_queue(contractor_actor)) == 0
    assert len(dash_service.get_rework_queue(contractor_actor)) == 0

    # Contractor submits completion
    contractor_service.start_work_order(contractor_actor, wo.id)
    contractor_service.submit_completion(contractor_actor, wo.id, CompletionSubmissionCreate(completion_note="Drain cleared"))

    # Now appears in pending verification queue
    pending_queue = dash_service.get_pending_verification_queue(contractor_actor)
    assert len(pending_queue) == 1
    assert pending_queue[0].work_order_id == wo.id
    assert pending_queue[0].progress_percentage == 100

    # Government REJECTS completion with feedback
    gov_service.verify_work_completion(
        actor=gov_actor,
        work_order_id=wo.id,
        decision=VerificationDecision.REJECT,
        notes="Drain still clogged near outlet. Please clear outlet completely.",
    )

    # Work order is no longer in pending verification
    assert len(dash_service.get_pending_verification_queue(contractor_actor)) == 0

    # Work order appears in rework queue with feedback
    rework_queue = dash_service.get_rework_queue(contractor_actor)
    assert len(rework_queue) == 1
    assert rework_queue[0].work_order_id == wo.id
    assert "outlet" in rework_queue[0].rejection_message
    assert rework_queue[0].current_status == WorkOrderStatus.IN_PROGRESS

    # Work order detail shows rework feedback and timeline
    detail = dash_service.get_work_order_detail(contractor_actor, wo.id)
    assert detail.rework_required is True
    assert "outlet" in detail.latest_rejection_notes
    assert detail.government_verification_status == "REJECT"
    assert len(detail.timeline) > 0

    # Contractor re-submits completion after rework
    contractor_service.update_progress(contractor_actor, wo.id, progress_percentage=90, note="Correction: cleared outlet area")
    contractor_service.submit_completion(contractor_actor, wo.id, CompletionSubmissionCreate(completion_note="Resubmitted after outlet clearing"))

    # Re-appears in pending verification queue, leaves rework queue
    assert len(dash_service.get_pending_verification_queue(contractor_actor)) == 1
    assert len(dash_service.get_rework_queue(contractor_actor)) == 0

    # Government APPROVES completion -> COMPLETED
    gov_service.verify_work_completion(
        actor=gov_actor,
        work_order_id=wo.id,
        decision=VerificationDecision.APPROVE,
        notes="Work verified satisfactory.",
    )

    # No longer in pending verification or rework queue
    assert len(dash_service.get_pending_verification_queue(contractor_actor)) == 0
    assert len(dash_service.get_rework_queue(contractor_actor)) == 0

    overview = dash_service.get_overview(contractor_actor)
    assert overview.completed == 1
    assert overview.pending_verification == 0
    assert overview.rework == 0
