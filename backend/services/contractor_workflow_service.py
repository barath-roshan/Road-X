"""Contractor Workflow Service coordinating work orders, progress tracking, evidence, and completion submissions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.models.evidence import Evidence
from backend.models.government_verification import GovernmentVerification, VerificationDecision
from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.road import RoadSegment
from backend.models.user import UserRole
from backend.models.work_order import WorkOrder, WorkOrderStatus
from backend.models.work_progress import WorkProgress
from backend.models.workflow_event import WorkflowEvent, WorkflowEventType
from backend.repositories.government_verification_repository import GovernmentVerificationRepository
from backend.repositories.grievance_repository import GrievanceRepository
from backend.repositories.road_repository import RoadRepository
from backend.repositories.user_repository import UserRepository
from backend.repositories.work_order_repository import WorkOrderRepository
from backend.repositories.work_progress_repository import WorkProgressRepository
from backend.repositories.workflow_event_repository import WorkflowEventRepository
from backend.schemas.completion_submission import CompletionSubmissionCreate, CompletionSubmissionRead
from backend.schemas.evidence import EvidenceRead
from backend.schemas.work_order import ContractorWorkOrderDetailsRead
from backend.schemas.work_progress import WorkProgressRead
from backend.security import UserContext, UnauthorizedError, InvalidStateTransitionError
from backend.services.notification_service import NotificationService
from backend.services.state_machine import GrievanceStateMachine, WorkOrderStateMachine
from ml.common.exceptions import RoadXDataError
from ml.common.logging_config import get_logger

logger = get_logger("backend.services.contractor_workflow")


class ContractorWorkflowService:
    """Service handling contractor operations, work order execution, progress updates, and completion submissions."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.work_order_repo = WorkOrderRepository(db)
        self.grievance_repo = GrievanceRepository(db)
        self.road_repo = RoadRepository(db)
        self.user_repo = UserRepository(db)
        self.progress_repo = WorkProgressRepository(db)
        self.verification_repo = GovernmentVerificationRepository(db)
        self.event_repo = WorkflowEventRepository(db)

    def _verify_contractor_ownership(self, actor: UserContext, work_order: WorkOrder) -> None:
        """Verify actor has CONTRACTOR role and is assigned to the specified work order."""
        actor.require_role(UserRole.CONTRACTOR)
        if not actor.user_id:
            raise UnauthorizedError("Actor user_id is missing.")
        if work_order.assigned_contractor_id != actor.user_id:
            raise UnauthorizedError(
                f"Contractor '{actor.user_id}' is not assigned to WorkOrder '{work_order.id}'."
            )

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
        """Create and record an immutable workflow audit log entry."""
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
            logger.warning("Failed to dispatch contractor workflow notification: %s", exc)

        return event

    def get_assigned_work_orders(
        self,
        actor: UserContext,
        status_filter: Optional[WorkOrderStatus] = None,
        priority_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WorkOrder]:
        """Fetch all work orders assigned to the requesting contractor.
        
        Strictly scopes results to actor.user_id.
        """
        actor.require_role(UserRole.CONTRACTOR)
        if not actor.user_id:
            raise UnauthorizedError("Actor user_id is missing.")

        return self.work_order_repo.filter_work_orders(
            status=status_filter,
            priority=priority_filter,
            assigned_contractor_id=actor.user_id,
            skip=skip,
            limit=limit,
        )

    def get_work_order_details(
        self,
        actor: UserContext,
        work_order_id: str,
    ) -> ContractorWorkOrderDetailsRead:
        """Retrieve detailed view of an assigned work order including grievance, road, progress history, evidence, and rejection feedback."""
        wo = self.work_order_repo.get_by_id(work_order_id)
        if not wo:
            raise RoadXDataError(f"Work order with ID '{work_order_id}' not found.")

        self._verify_contractor_ownership(actor, wo)

        # Retrieve related entities
        grievance = self.grievance_repo.get_by_id(wo.grievance_id)
        road = self.road_repo.get_by_id(wo.road_id) if wo.road_id else None

        # Fetch progress entries
        progress_entries = self.progress_repo.get_by_work_order(wo.id)
        progress_reads = [WorkProgressRead.model_validate(p) for p in progress_entries]

        # Fetch evidence attached to work order or grievance
        evidence_items = (
            self.db.query(Evidence)
            .filter((Evidence.work_order_id == wo.id) | (Evidence.grievance_id == wo.grievance_id))
            .order_by(Evidence.uploaded_at.desc())
            .all()
        )
        evidence_reads = [EvidenceRead.model_validate(e) for e in evidence_items]

        # Fetch latest government rejection notes if work order is in IN_PROGRESS after a prior rejection
        verifications = self.verification_repo.get_by_work_order_id(wo.id)
        latest_rejection_notes = None
        for ver in verifications:
            if ver.decision == VerificationDecision.REJECT:
                latest_rejection_notes = ver.notes
                break

        return ContractorWorkOrderDetailsRead(
            id=wo.id,
            grievance_id=wo.grievance_id,
            road_id=wo.road_id,
            created_by=wo.created_by,
            assigned_contractor_id=wo.assigned_contractor_id,
            title=wo.title,
            description=wo.description,
            priority=wo.priority,
            status=wo.status,
            created_at=wo.created_at,
            updated_at=wo.updated_at,
            grievance_description=grievance.description if grievance else None,
            grievance_issue_category=grievance.issue_category if grievance else None,
            grievance_latitude=grievance.latitude if grievance else None,
            grievance_longitude=grievance.longitude if grievance else None,
            road_name=road.road_name if road else None,
            road_code=road.segment_id if road else None,
            progress_history=progress_reads,
            evidence_items=evidence_reads,
            latest_rejection_notes=latest_rejection_notes,
        )

    def acknowledge_work_order(
        self,
        actor: UserContext,
        work_order_id: str,
        notes: Optional[str] = None,
    ) -> WorkOrder:
        """Contractor acknowledges receipt of an assigned work order."""
        wo = self.work_order_repo.get_by_id(work_order_id)
        if not wo:
            raise RoadXDataError(f"Work order with ID '{work_order_id}' not found.")

        self._verify_contractor_ownership(actor, wo)

        if wo.status in (WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED):
            raise InvalidStateTransitionError(
                f"Cannot acknowledge work order in state '{wo.status.value}'."
            )

        self._log_workflow_event(
            grievance_id=wo.grievance_id,
            work_order_id=wo.id,
            event_type=WorkflowEventType.WORK_ORDER_ACKNOWLEDGED,
            actor=actor,
            old_status=wo.status.value,
            new_status=wo.status.value,
            notes=notes or f"Contractor '{actor.user_id}' acknowledged work order '{wo.title}'.",
        )

        self.db.commit()
        self.db.refresh(wo)
        logger.info("Contractor '%s' acknowledged WorkOrder '%s'", actor.user_id, wo.id)
        return wo

    def start_work_order(
        self,
        actor: UserContext,
        work_order_id: str,
        notes: Optional[str] = None,
    ) -> WorkOrder:
        """Contractor marks maintenance work as actively started (ASSIGNED → IN_PROGRESS)."""
        wo = self.work_order_repo.get_by_id(work_order_id)
        if not wo:
            raise RoadXDataError(f"Work order with ID '{work_order_id}' not found.")

        self._verify_contractor_ownership(actor, wo)

        old_wo_status = wo.status
        WorkOrderStateMachine.validate_transition(wo.status, WorkOrderStatus.IN_PROGRESS)
        wo.status = WorkOrderStatus.IN_PROGRESS

        # Update grievance status to IN_PROGRESS if not already
        grievance = self.grievance_repo.get_by_id(wo.grievance_id)
        if grievance and grievance.status != GrievanceStatus.IN_PROGRESS:
            GrievanceStateMachine.validate_transition(grievance.status, GrievanceStatus.IN_PROGRESS)
            grievance.status = GrievanceStatus.IN_PROGRESS

        self._log_workflow_event(
            grievance_id=wo.grievance_id,
            work_order_id=wo.id,
            event_type=WorkflowEventType.WORK_STARTED,
            actor=actor,
            old_status=old_wo_status.value,
            new_status=wo.status.value,
            notes=notes or f"Contractor started work on '{wo.title}'.",
        )

        try:
            self.db.commit()
            self.db.refresh(wo)
            logger.info("WorkOrder '%s' status updated to IN_PROGRESS by contractor '%s'", wo.id, actor.user_id)
            return wo
        except Exception as e:
            self.db.rollback()
            raise e

    def update_progress(
        self,
        actor: UserContext,
        work_order_id: str,
        progress_percentage: int,
        note: Optional[str] = None,
    ) -> WorkProgress:
        """Contractor submits a progress update entry (0-100%).
        
        CRITICAL RULE: Progress updates NEVER resolve or complete a work order/grievance, even at 100%.
        """
        if not (0 <= progress_percentage <= 100):
            raise RoadXDataError("Progress percentage must be between 0 and 100 inclusive.")

        wo = self.work_order_repo.get_by_id(work_order_id)
        if not wo:
            raise RoadXDataError(f"Work order with ID '{work_order_id}' not found.")

        self._verify_contractor_ownership(actor, wo)

        if wo.status in (WorkOrderStatus.PENDING_VERIFICATION, WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED):
            raise InvalidStateTransitionError(
                f"Cannot update progress when work order is in state '{wo.status.value}'."
            )

        # Monotonicity check against previous progress entries
        existing_progresses = self.progress_repo.get_by_work_order(wo.id)
        if existing_progresses:
            latest_pct = existing_progresses[-1].progress_percentage
            if progress_percentage < latest_pct:
                note_lower = (note or "").lower()
                correction_keywords = ["correction", "rework", "revised", "reset", "rollback", "adjustment"]
                if not any(kw in note_lower for kw in correction_keywords):
                    raise RoadXDataError(
                        f"Progress percentage cannot decrease from {latest_pct}% to {progress_percentage}% "
                        f"without an explicit correction or rework note."
                    )

        # Auto-start work if work order is currently ASSIGNED
        if wo.status == WorkOrderStatus.ASSIGNED:
            wo.status = WorkOrderStatus.IN_PROGRESS

        progress_entry = WorkProgress(
            work_order_id=wo.id,
            contractor_id=actor.user_id,
            progress_percentage=progress_percentage,
            note=note,
        )
        self.db.add(progress_entry)

        self._log_workflow_event(
            grievance_id=wo.grievance_id,
            work_order_id=wo.id,
            event_type=WorkflowEventType.WORK_PROGRESS_UPDATED,
            actor=actor,
            old_status=wo.status.value,
            new_status=wo.status.value,
            notes=f"Progress updated to {progress_percentage}%. {note or ''}".strip(),
        )

        try:
            self.db.commit()
            self.db.refresh(progress_entry)
            logger.info(
                "Logged %d%% progress for WorkOrder '%s' by contractor '%s'",
                progress_percentage,
                wo.id,
                actor.user_id,
            )
            return progress_entry
        except Exception as e:
            self.db.rollback()
            raise e

    def attach_evidence(
        self,
        actor: UserContext,
        work_order_id: str,
        file_name: str,
        file_type: str,
        storage_path: str,
        file_size_bytes: Optional[int] = None,
    ) -> Evidence:
        """Attach completion or progress evidence metadata to a work order."""
        if not file_name or not file_name.strip() or not file_type or not file_type.strip() or not storage_path or not storage_path.strip():
            raise RoadXDataError("Evidence metadata file_name, file_type, and storage_path must be non-empty strings.")
        if file_size_bytes is not None and file_size_bytes < 0:
            raise RoadXDataError("Evidence file_size_bytes cannot be negative.")

        wo = self.work_order_repo.get_by_id(work_order_id)
        if not wo:
            raise RoadXDataError(f"Work order with ID '{work_order_id}' not found.")

        self._verify_contractor_ownership(actor, wo)

        if wo.status in (WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED):
            raise InvalidStateTransitionError(
                f"Cannot attach evidence to work order in state '{wo.status.value}'."
            )

        evidence = Evidence(
            grievance_id=wo.grievance_id,
            work_order_id=wo.id,
            file_name=file_name.strip(),
            file_type=file_type.strip(),
            storage_path=storage_path.strip(),
            file_size_bytes=file_size_bytes,
        )
        self.db.add(evidence)

        try:
            self.db.commit()
            self.db.refresh(evidence)
            logger.info("Attached evidence '%s' to WorkOrder '%s'", evidence.id, wo.id)
            return evidence
        except Exception as e:
            self.db.rollback()
            raise e

    def submit_completion(
        self,
        actor: UserContext,
        work_order_id: str,
        payload: CompletionSubmissionCreate,
    ) -> CompletionSubmissionRead:
        """Contractor submits work order repair completion for government officer verification.
        
        CRITICAL BUSINESS RULE: This action transitions WorkOrder and Grievance to PENDING_VERIFICATION.
        It does NOT transition either to RESOLVED or COMPLETED. Only Phase 12 government verification can resolve.
        """
        wo = self.work_order_repo.get_by_id(work_order_id)
        if not wo:
            raise RoadXDataError(f"Work order with ID '{work_order_id}' not found.")

        self._verify_contractor_ownership(actor, wo)

        if wo.status == WorkOrderStatus.PENDING_VERIFICATION:
            raise InvalidStateTransitionError("Work order is already pending government verification.")
        if wo.status in (WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED):
            raise InvalidStateTransitionError(
                f"Cannot submit completion for work order in state '{wo.status.value}'."
            )

        # Validate current status: must be IN_PROGRESS or ASSIGNED
        if wo.status == WorkOrderStatus.ASSIGNED:
            wo.status = WorkOrderStatus.IN_PROGRESS

        old_wo_status = wo.status
        WorkOrderStateMachine.validate_transition(wo.status, WorkOrderStatus.PENDING_VERIFICATION)
        wo.status = WorkOrderStatus.PENDING_VERIFICATION

        # Transition grievance to PENDING_VERIFICATION
        grievance = self.grievance_repo.get_by_id(wo.grievance_id)
        if not grievance:
            raise RoadXDataError(f"Grievance with ID '{wo.grievance_id}' not found.")

        old_grievance_status = grievance.status
        GrievanceStateMachine.validate_transition(grievance.status, GrievanceStatus.PENDING_VERIFICATION)
        grievance.status = GrievanceStatus.PENDING_VERIFICATION

        # Record 100% progress entry
        progress_note = f"Completion Submitted: {payload.completion_note}"
        if payload.actual_work_summary:
            progress_note += f" | Details: {payload.actual_work_summary}"

        progress_entry = WorkProgress(
            work_order_id=wo.id,
            contractor_id=actor.user_id,
            progress_percentage=100,
            note=progress_note,
        )
        self.db.add(progress_entry)

        # Link evidence IDs if provided
        if payload.evidence_ids:
            for ev_id in payload.evidence_ids:
                ev = self.db.query(Evidence).filter_by(id=ev_id).first()
                if ev and ev.grievance_id == wo.grievance_id:
                    ev.work_order_id = wo.id

        # Log completion submission workflow audit event
        self._log_workflow_event(
            grievance_id=wo.grievance_id,
            work_order_id=wo.id,
            event_type=WorkflowEventType.WORK_COMPLETION_SUBMITTED,
            actor=actor,
            old_status=old_wo_status.value,
            new_status=wo.status.value,
            notes=f"Completion submitted by contractor '{actor.user_id}'. Note: '{payload.completion_note}'",
        )

        try:
            self.db.commit()
            self.db.refresh(wo)
            self.db.refresh(grievance)

            logger.info(
                "Contractor '%s' submitted completion for WorkOrder '%s'. Status set to PENDING_VERIFICATION.",
                actor.user_id,
                wo.id,
            )

            return CompletionSubmissionRead(
                work_order_id=wo.id,
                status=wo.status.value,
                grievance_status=grievance.status.value,
                submitted_at=wo.updated_at,
                completion_note=payload.completion_note,
            )
        except Exception as e:
            self.db.rollback()
            raise e
