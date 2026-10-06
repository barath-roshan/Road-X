"""Unit tests for actor role-based authorization enforcement."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.models.government_review import ReviewDecision
from backend.models.government_verification import VerificationDecision
from backend.models.user import UserRole
from backend.schemas.grievance import GrievanceCreate
from backend.schemas.work_order import WorkOrderCreate
from backend.security import UserContext, UnauthorizedError
from backend.services.government_workflow_service import GovernmentWorkflowService
from backend.services.grievance_service import GrievanceService


def test_citizen_cannot_review_or_verify(db_session: Session):
    """Test that a Citizen actor is forbidden from reviewing or verifying grievances."""
    grievance_service = GrievanceService(db_session)
    govt_service = GovernmentWorkflowService(db_session)

    grievance = grievance_service.create_grievance(
        GrievanceCreate(issue_category="POTHOLE", description="Deep hole on road.")
    )

    citizen_actor = UserContext(user_id="citizen-123", role=UserRole.CITIZEN)

    # Citizen review attempt -> UnauthorizedError
    with pytest.raises(UnauthorizedError, match="not authorized"):
        govt_service.review_grievance(
            actor=citizen_actor,
            grievance_id=grievance.id,
            decision=ReviewDecision.ACCEPT,
        )

    # Citizen work order creation attempt -> UnauthorizedError
    with pytest.raises(UnauthorizedError, match="not authorized"):
        govt_service.create_and_assign_work_order(
            actor=citizen_actor,
            grievance_id=grievance.id,
            payload=WorkOrderCreate(title="Test", description="Test WO"),
        )


def test_contractor_cannot_verify_completion(db_session: Session):
    """Test that a Contractor actor is forbidden from government verification."""
    govt_service = GovernmentWorkflowService(db_session)
    contractor_actor = UserContext(user_id="contractor-456", role=UserRole.CONTRACTOR)

    with pytest.raises(UnauthorizedError, match="not authorized"):
        govt_service.verify_work_completion(
            actor=contractor_actor,
            work_order_id="wo-fake-id",
            decision=VerificationDecision.APPROVE,
        )


def test_officer_can_perform_government_actions(db_session: Session):
    """Test that a Government Officer actor is authorized to perform review and work orders."""
    grievance_service = GrievanceService(db_session)
    govt_service = GovernmentWorkflowService(db_session)

    grievance = grievance_service.create_grievance(
        GrievanceCreate(issue_category="POTHOLE", description="Dangerous pothole.")
    )

    officer_actor = UserContext(user_id="officer-789", role=UserRole.GOVERNMENT_OFFICER)

    # Officer ACCEPT review
    review = govt_service.review_grievance(
        actor=officer_actor,
        grievance_id=grievance.id,
        decision=ReviewDecision.ACCEPT,
        notes="Approved for priority repair dispatch.",
    )
    assert review.id is not None
    assert review.decision == ReviewDecision.ACCEPT
