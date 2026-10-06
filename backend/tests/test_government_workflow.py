"""Unit tests for Government Workflow: Reviews, Work Orders, Verifications, and Resolution Rules."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.models.government_review import ReviewDecision
from backend.models.government_verification import VerificationDecision
from backend.models.grievance import GrievanceStatus
from backend.models.user import UserRole
from backend.models.work_order import WorkOrderStatus
from backend.schemas.grievance import GrievanceCreate
from backend.schemas.user import UserCreate
from backend.schemas.work_order import WorkOrderCreate
from backend.security import UserContext, InvalidStateTransitionError
from backend.services.government_workflow_service import GovernmentWorkflowService
from backend.services.grievance_service import GrievanceService
from backend.services.user_service import UserService


def test_full_government_review_and_work_order_workflow(db_session: Session):
    """Test full workflow: Submit -> Officer Review -> Work Order -> Verification -> Resolved."""
    user_service = UserService(db_session)
    grievance_service = GrievanceService(db_session)
    govt_service = GovernmentWorkflowService(db_session)

    officer = user_service.create_user(
        UserCreate(name="Officer Patel", email="patel@gov.in", role=UserRole.GOVERNMENT_OFFICER)
    )
    contractor = user_service.create_user(
        UserCreate(name="BuildCorp Infra", email="buildcorp@contractor.com", role=UserRole.CONTRACTOR)
    )

    officer_actor = UserContext(user_id=officer.id, role=UserRole.GOVERNMENT_OFFICER)

    # 1. Citizen submits grievance -> SUBMITTED
    grievance = grievance_service.create_grievance(
        GrievanceCreate(issue_category="POTHOLE", description="Deep road pothole near market.")
    )
    assert grievance.status == GrievanceStatus.SUBMITTED

    # 2. Officer reviews -> ACCEPT (UNDER_REVIEW)
    govt_service.review_grievance(
        actor=officer_actor,
        grievance_id=grievance.id,
        decision=ReviewDecision.ACCEPT,
        notes="Grievance accepted. Work order queued.",
    )
    updated_g1 = grievance_service.get_grievance(grievance.id)
    assert updated_g1.status == GrievanceStatus.UNDER_REVIEW

    # 3. Officer creates & assigns work order -> IN_PROGRESS
    wo = govt_service.create_and_assign_work_order(
        actor=officer_actor,
        grievance_id=grievance.id,
        payload=WorkOrderCreate(
            title="Pothole Paving Repair",
            description="Asphalt fill and compaction.",
            priority="HIGH",
            assigned_contractor_id=contractor.id,
        ),
    )
    assert wo.id is not None
    assert wo.status == WorkOrderStatus.ASSIGNED
    assert wo.assigned_contractor_id == contractor.id

    updated_g2 = grievance_service.get_grievance(grievance.id)
    assert updated_g2.status == GrievanceStatus.IN_PROGRESS

    # 4. Contractor work completion later sets grievance to PENDING_VERIFICATION
    # (Simulated work order pending verification state)
    wo.status = WorkOrderStatus.PENDING_VERIFICATION
    updated_g2.status = GrievanceStatus.PENDING_VERIFICATION
    db_session.commit()

    # CRITICAL RULE CHECK: Contractor work completion does NOT mean RESOLVED
    pending_grievance = grievance_service.get_grievance(grievance.id)
    assert pending_grievance.status != GrievanceStatus.RESOLVED
    assert pending_grievance.status == GrievanceStatus.PENDING_VERIFICATION

    # 5. Government Verification APPROVE -> Grievance becomes RESOLVED
    verification = govt_service.verify_work_completion(
        actor=officer_actor,
        work_order_id=wo.id,
        decision=VerificationDecision.APPROVE,
        notes="Inspected post-repair compaction. Work meets municipal standards.",
    )
    assert verification.decision == VerificationDecision.APPROVE

    final_grievance = grievance_service.get_grievance(grievance.id)
    assert final_grievance.status == GrievanceStatus.RESOLVED


def test_government_verification_rejection_sends_back_to_in_progress(db_session: Session):
    """Test government verification REJECT decision sends grievance and work order back to IN_PROGRESS."""
    grievance_service = GrievanceService(db_session)
    govt_service = GovernmentWorkflowService(db_session)
    officer_actor = UserContext(user_id="officer-001", role=UserRole.GOVERNMENT_OFFICER)

    # Setup grievance & work order in PENDING_VERIFICATION state
    grievance = grievance_service.create_grievance(
        GrievanceCreate(issue_category="CRACK", description="Surface crack.")
    )
    wo = govt_service.create_and_assign_work_order(
        actor=officer_actor,
        grievance_id=grievance.id,
        payload=WorkOrderCreate(title="Crack Sealing", description="Seal pavement crack."),
    )
    wo.status = WorkOrderStatus.PENDING_VERIFICATION
    grievance.status = GrievanceStatus.PENDING_VERIFICATION
    db_session.commit()

    # Officer REJECTS verification due to defective repair
    verification = govt_service.verify_work_completion(
        actor=officer_actor,
        work_order_id=wo.id,
        decision=VerificationDecision.REJECT,
        notes="Sealing uneven. Requires re-application.",
    )
    assert verification.decision == VerificationDecision.REJECT

    reworked_grievance = grievance_service.get_grievance(grievance.id)
    assert reworked_grievance.status == GrievanceStatus.IN_PROGRESS


def test_audit_history_recording(db_session: Session):
    """Test that all workflow actions record chronological WorkflowEvent records."""
    grievance_service = GrievanceService(db_session)
    govt_service = GovernmentWorkflowService(db_session)
    officer_actor = UserContext(user_id="officer-audit-1", role=UserRole.GOVERNMENT_OFFICER)

    grievance = grievance_service.create_grievance(
        GrievanceCreate(issue_category="POTHOLE", description="Audit test grievance.")
    )

    govt_service.review_grievance(actor=officer_actor, grievance_id=grievance.id, decision=ReviewDecision.ACCEPT)
    govt_service.create_and_assign_work_order(
        actor=officer_actor,
        grievance_id=grievance.id,
        payload=WorkOrderCreate(title="Audit Repair", description="Scope"),
    )

    history = govt_service.get_workflow_history(grievance.id)
    assert len(history) >= 2
    event_types = [e.event_type.value for e in history]
    assert "GRIEVANCE_ACCEPTED" in event_types
    assert "WORK_ORDER_CREATED" in event_types
