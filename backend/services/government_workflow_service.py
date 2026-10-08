"""Government Workflow Service coordinating review, work orders, verification, and audit logging."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.models.government_review import GovernmentReview, ReviewDecision
from backend.models.government_verification import GovernmentVerification, VerificationDecision
from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.user import UserRole
from backend.models.work_order import WorkOrder, WorkOrderStatus
from backend.models.workflow_event import WorkflowEvent, WorkflowEventType
from backend.repositories.government_review_repository import GovernmentReviewRepository
from backend.repositories.government_verification_repository import GovernmentVerificationRepository
from backend.repositories.grievance_repository import GrievanceRepository
from backend.repositories.user_repository import UserRepository
from backend.repositories.work_order_repository import WorkOrderRepository
from backend.repositories.workflow_event_repository import WorkflowEventRepository
from backend.schemas.work_order import WorkOrderCreate
from backend.security import UserContext, UnauthorizedError
from backend.services.notification_service import NotificationService
from backend.services.state_machine import GrievanceStateMachine, WorkOrderStateMachine
from ml.common.exceptions import RoadXDataError
from ml.common.logging_config import get_logger

logger = get_logger("backend.services.government_workflow")


class GovernmentWorkflowService:
    """Service encapsulating Government Officer workflows and governance state transitions."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.grievance_repo = GrievanceRepository(db)
        self.user_repo = UserRepository(db)
        self.review_repo = GovernmentReviewRepository(db)
        self.work_order_repo = WorkOrderRepository(db)
        self.verification_repo = GovernmentVerificationRepository(db)
        self.event_repo = WorkflowEventRepository(db)

    def _log_workflow_event(
        self,
        grievance_id: str,
        event_type: WorkflowEventType,
        actor: UserContext,
        work_order_id: Optional[str] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> WorkflowEvent:
        """Create and append an immutable workflow history audit event."""
        event = WorkflowEvent(
            grievance_id=grievance_id,
            work_order_id=work_order_id,
            actor_id=actor.user_id,
            actor_role=actor.role.value if actor.role else None,
            event_type=event_type,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
        )
        self.db.add(event)
        self.db.flush()

        # Dispatch event-driven notifications
        try:
            grievance = self.grievance_repo.get_by_id(grievance_id)
            work_order = self.work_order_repo.get_by_id(work_order_id) if work_order_id else None
            if grievance:
                notif_service = NotificationService(self.db)
                notif_service.process_workflow_event(event, grievance, work_order)
        except Exception as exc:
            logger.warning("Failed to dispatch government workflow notification: %s", exc)

        return event

    def review_grievance(
        self,
        actor: UserContext,
        grievance_id: str,
        decision: ReviewDecision,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> GovernmentReview:
        """Process official government officer grievance review decision (ACCEPT or REJECT)."""
        actor.require_role(UserRole.GOVERNMENT_OFFICER)

        grievance = self.grievance_repo.get_by_id(grievance_id)
        if not grievance:
            raise RoadXDataError(f"Grievance with ID '{grievance_id}' not found.")

        old_status = grievance.status

        if decision == ReviewDecision.REJECT:
            if not reason or not reason.strip():
                raise RoadXDataError("A descriptive reason is required when rejecting a grievance.")
            
            target_status = GrievanceStatus.REJECTED
            GrievanceStateMachine.validate_transition(grievance.status, target_status)
            grievance.status = target_status
            event_type = WorkflowEventType.GRIEVANCE_REJECTED

        elif decision == ReviewDecision.ACCEPT:
            target_status = GrievanceStatus.UNDER_REVIEW
            GrievanceStateMachine.validate_transition(grievance.status, target_status)
            grievance.status = target_status
            event_type = WorkflowEventType.GRIEVANCE_ACCEPTED

        # Persist review record
        review = GovernmentReview(
            grievance_id=grievance.id,
            officer_id=actor.user_id,
            decision=decision,
            reason=reason.strip() if reason else None,
            notes=notes.strip() if notes else None,
        )
        self.db.add(review)

        # Audit Event
        self._log_workflow_event(
            grievance_id=grievance.id,
            event_type=event_type,
            actor=actor,
            old_status=old_status.value,
            new_status=grievance.status.value,
            notes=notes or reason,
        )

        try:
            self.db.commit()
            self.db.refresh(review)
            self.db.refresh(grievance)
            logger.info(
                "Officer '%s' reviewed grievance '%s': %s (Status → %s)",
                actor.user_id,
                grievance_id,
                decision.value,
                grievance.status.value,
            )
            return review
        except Exception as e:
            self.db.rollback()
            raise e

    def create_and_assign_work_order(
        self,
        actor: UserContext,
        grievance_id: str,
        payload: WorkOrderCreate,
    ) -> WorkOrder:
        """Create a maintenance work order and transition grievance status to IN_PROGRESS."""
        actor.require_role(UserRole.GOVERNMENT_OFFICER)

        grievance = self.grievance_repo.get_by_id(grievance_id)
        if not grievance:
            raise RoadXDataError(f"Grievance with ID '{grievance_id}' not found.")

        if grievance.status in (GrievanceStatus.RESOLVED, GrievanceStatus.REJECTED):
            raise RoadXDataError(
                f"Cannot create work order for grievance in terminal state '{grievance.status.value}'."
            )

        # Validate contractor user reference if provided
        contractor_id = payload.assigned_contractor_id
        if contractor_id:
            contractor_user = self.user_repo.get_by_id(contractor_id)
            if not contractor_user:
                raise RoadXDataError(f"Assigned contractor user ID '{contractor_id}' not found.")
            if contractor_user.role != UserRole.CONTRACTOR:
                raise RoadXDataError(f"User '{contractor_id}' is a {contractor_user.role.value}, not a CONTRACTOR.")

        # Determine WorkOrder initial status
        wo_status = WorkOrderStatus.ASSIGNED if contractor_id else WorkOrderStatus.OPEN

        work_order = WorkOrder(
            grievance_id=grievance.id,
            road_id=grievance.road_id,
            created_by=actor.user_id,
            assigned_contractor_id=contractor_id,
            title=payload.title.strip(),
            description=payload.description.strip(),
            priority=(payload.priority or "MEDIUM").upper(),
            status=wo_status,
        )
        self.db.add(work_order)

        # Transition Grievance status to IN_PROGRESS
        old_status = grievance.status
        if grievance.status != GrievanceStatus.IN_PROGRESS:
            GrievanceStateMachine.validate_transition(grievance.status, GrievanceStatus.IN_PROGRESS)
            grievance.status = GrievanceStatus.IN_PROGRESS

        # Audit Event
        self._log_workflow_event(
            grievance_id=grievance.id,
            work_order_id=work_order.id,
            event_type=WorkflowEventType.WORK_ORDER_CREATED,
            actor=actor,
            old_status=old_status.value,
            new_status=grievance.status.value,
            notes=f"Work order created: '{payload.title}'",
        )

        if contractor_id:
            self._log_workflow_event(
                grievance_id=grievance.id,
                work_order_id=work_order.id,
                event_type=WorkflowEventType.WORK_ORDER_ASSIGNED,
                actor=actor,
                notes=f"Work order assigned to contractor '{contractor_id}'",
            )

        try:
            self.db.commit()
            self.db.refresh(work_order)
            self.db.refresh(grievance)
            logger.info("Created WorkOrder '%s' for grievance '%s'", work_order.id, grievance_id)
            return work_order
        except Exception as e:
            self.db.rollback()
            raise e

    def verify_work_completion(
        self,
        actor: UserContext,
        work_order_id: str,
        decision: VerificationDecision,
        notes: Optional[str] = None,
    ) -> GovernmentVerification:
        """Verify contractor repair completion and transition grievance status.

        CRITICAL BUSINESS RULE: Only a government officer APPROVE decision can transition
        a grievance to RESOLVED.
        """
        actor.require_role(UserRole.GOVERNMENT_OFFICER)

        work_order = self.work_order_repo.get_by_id(work_order_id)
        if not work_order:
            raise RoadXDataError(f"Work order with ID '{work_order_id}' not found.")

        grievance = self.grievance_repo.get_by_id(work_order.grievance_id)
        if not grievance:
            raise RoadXDataError(f"Grievance with ID '{work_order.grievance_id}' not found.")

        old_grievance_status = grievance.status
        old_wo_status = work_order.status

        if decision == VerificationDecision.APPROVE:
            # 1. Transition WorkOrder to COMPLETED
            WorkOrderStateMachine.validate_transition(work_order.status, WorkOrderStatus.COMPLETED)
            work_order.status = WorkOrderStatus.COMPLETED

            # 2. Transition Grievance to RESOLVED (Only government verification can set RESOLVED!)
            GrievanceStateMachine.validate_transition(grievance.status, GrievanceStatus.RESOLVED)
            grievance.status = GrievanceStatus.RESOLVED
            event_type = WorkflowEventType.WORK_VERIFICATION_APPROVED

        elif decision == VerificationDecision.REJECT:
            # Revert WorkOrder and Grievance to IN_PROGRESS for rework
            work_order.status = WorkOrderStatus.IN_PROGRESS
            grievance.status = GrievanceStatus.IN_PROGRESS
            event_type = WorkflowEventType.WORK_VERIFICATION_REJECTED

        # Record Verification Entity
        verification = GovernmentVerification(
            work_order_id=work_order.id,
            grievance_id=grievance.id,
            officer_id=actor.user_id,
            decision=decision,
            notes=notes.strip() if notes else None,
        )
        self.db.add(verification)

        # Audit Event
        self._log_workflow_event(
            grievance_id=grievance.id,
            work_order_id=work_order.id,
            event_type=event_type,
            actor=actor,
            old_status=old_grievance_status.value,
            new_status=grievance.status.value,
            notes=notes,
        )

        try:
            self.db.commit()
            self.db.refresh(verification)
            self.db.refresh(work_order)
            self.db.refresh(grievance)
            logger.info(
                "Officer '%s' verified work order '%s': %s (Grievance Status → %s)",
                actor.user_id,
                work_order_id,
                decision.value,
                grievance.status.value,
            )
            return verification
        except Exception as e:
            self.db.rollback()
            raise e

    def get_workflow_history(self, grievance_id: str) -> List[WorkflowEvent]:
        """Fetch complete chronological audit history for a grievance."""
        grievance = self.grievance_repo.get_by_id(grievance_id)
        if not grievance:
            raise RoadXDataError(f"Grievance with ID '{grievance_id}' not found.")
        return self.event_repo.get_history_for_grievance(grievance_id)
