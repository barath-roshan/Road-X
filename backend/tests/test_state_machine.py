"""Unit tests for GrievanceStateMachine and WorkOrderStateMachine rules."""

from __future__ import annotations

import pytest
from backend.models.grievance import GrievanceStatus
from backend.models.work_order import WorkOrderStatus
from backend.security import InvalidStateTransitionError
from backend.services.state_machine import GrievanceStateMachine, WorkOrderStateMachine


def test_valid_grievance_transitions():
    """Test valid grievance state transitions."""
    # SUBMITTED -> UNDER_REVIEW -> IN_PROGRESS -> PENDING_VERIFICATION -> RESOLVED
    GrievanceStateMachine.validate_transition(GrievanceStatus.SUBMITTED, GrievanceStatus.UNDER_REVIEW)
    GrievanceStateMachine.validate_transition(GrievanceStatus.UNDER_REVIEW, GrievanceStatus.IN_PROGRESS)
    GrievanceStateMachine.validate_transition(GrievanceStatus.IN_PROGRESS, GrievanceStatus.PENDING_VERIFICATION)
    GrievanceStateMachine.validate_transition(GrievanceStatus.PENDING_VERIFICATION, GrievanceStatus.RESOLVED)


def test_invalid_grievance_transitions():
    """Test illegal grievance state transitions raise InvalidStateTransitionError."""
    # SUBMITTED -> RESOLVED (Bypassing review & verification is illegal)
    with pytest.raises(InvalidStateTransitionError, match="prohibited"):
        GrievanceStateMachine.validate_transition(GrievanceStatus.SUBMITTED, GrievanceStatus.RESOLVED)

    # REJECTED -> RESOLVED
    with pytest.raises(InvalidStateTransitionError, match="prohibited"):
        GrievanceStateMachine.validate_transition(GrievanceStatus.REJECTED, GrievanceStatus.RESOLVED)

    # IN_PROGRESS -> RESOLVED (Directly resolving without pending verification is illegal)
    with pytest.raises(InvalidStateTransitionError, match="prohibited"):
        GrievanceStateMachine.validate_transition(GrievanceStatus.IN_PROGRESS, GrievanceStatus.RESOLVED)


def test_work_order_state_transitions():
    """Test valid and invalid work order status transitions."""
    WorkOrderStateMachine.validate_transition(WorkOrderStatus.OPEN, WorkOrderStatus.ASSIGNED)
    WorkOrderStateMachine.validate_transition(WorkOrderStatus.ASSIGNED, WorkOrderStatus.IN_PROGRESS)
    WorkOrderStateMachine.validate_transition(WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.PENDING_VERIFICATION)
    WorkOrderStateMachine.validate_transition(WorkOrderStatus.PENDING_VERIFICATION, WorkOrderStatus.COMPLETED)

    # OPEN -> COMPLETED (Illegal shortcut)
    with pytest.raises(InvalidStateTransitionError):
        WorkOrderStateMachine.validate_transition(WorkOrderStatus.OPEN, WorkOrderStatus.COMPLETED)
