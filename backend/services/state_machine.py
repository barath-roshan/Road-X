"""Grievance and WorkOrder Lifecycle State Machine logic."""

from __future__ import annotations

from backend.models.grievance import GrievanceStatus
from backend.models.work_order import WorkOrderStatus
from backend.security import InvalidStateTransitionError


class GrievanceStateMachine:
    """Enforces strict state transitions for Grievance entities."""

    ALLOWED_TRANSITIONS = {
        GrievanceStatus.SUBMITTED: {
            GrievanceStatus.UNDER_REVIEW,
            GrievanceStatus.REJECTED,
            GrievanceStatus.IN_PROGRESS,
        },
        GrievanceStatus.UNDER_REVIEW: {
            GrievanceStatus.REJECTED,
            GrievanceStatus.IN_PROGRESS,
        },
        GrievanceStatus.IN_PROGRESS: {
            GrievanceStatus.PENDING_VERIFICATION,
        },
        GrievanceStatus.PENDING_VERIFICATION: {
            GrievanceStatus.RESOLVED,
            GrievanceStatus.IN_PROGRESS,
        },
        GrievanceStatus.RESOLVED: set(),  # Terminal state
        GrievanceStatus.REJECTED: set(),  # Terminal state
    }

    @classmethod
    def validate_transition(cls, current_status: GrievanceStatus, target_status: GrievanceStatus) -> None:
        """Validate whether transition from current_status to target_status is permitted.

        Args:
            current_status: Current GrievanceStatus enum.
            target_status: Target GrievanceStatus enum.

        Raises:
            InvalidStateTransitionError if transition is illegal.
        """
        if current_status == target_status:
            return  # Idempotent

        allowed = cls.ALLOWED_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal grievance status transition: '{current_status.value}' → '{target_status.value}' is prohibited."
            )


class WorkOrderStateMachine:
    """Enforces strict state transitions for WorkOrder entities."""

    ALLOWED_TRANSITIONS = {
        WorkOrderStatus.OPEN: {WorkOrderStatus.ASSIGNED, WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.CANCELLED},
        WorkOrderStatus.ASSIGNED: {WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.CANCELLED},
        WorkOrderStatus.IN_PROGRESS: {WorkOrderStatus.PENDING_VERIFICATION, WorkOrderStatus.CANCELLED},
        WorkOrderStatus.PENDING_VERIFICATION: {WorkOrderStatus.COMPLETED, WorkOrderStatus.IN_PROGRESS},
        WorkOrderStatus.COMPLETED: set(),  # Terminal state
        WorkOrderStatus.CANCELLED: set(),  # Terminal state
    }

    @classmethod
    def validate_transition(cls, current_status: WorkOrderStatus, target_status: WorkOrderStatus) -> None:
        """Validate work order status transition."""
        if current_status == target_status:
            return

        allowed = cls.ALLOWED_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal work order status transition: '{current_status.value}' → '{target_status.value}' is prohibited."
            )
