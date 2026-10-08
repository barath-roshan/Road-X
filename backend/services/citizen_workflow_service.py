"""Citizen Workflow Service coordinating complaint reporting, tracking, evidence, and public status views."""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models.evidence import Evidence
from backend.models.government_verification import GovernmentVerification, VerificationDecision
from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.ml_analysis import MLAnalysisResult
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
from backend.schemas.citizen import (
    CitizenGrievanceCreate,
    CitizenGrievanceDetailsRead,
    CitizenMLSummaryRead,
    CitizenRejectionInfoRead,
    CitizenTimelineItemRead,
    CitizenWorkProgressRead,
)
from backend.schemas.evidence import EvidenceRead
from backend.security import UserContext, UnauthorizedError, InvalidStateTransitionError
from backend.services.state_machine import GrievanceStateMachine
from ml.common.exceptions import RoadXDataError
from ml.common.logging_config import get_logger

logger = get_logger("backend.services.citizen_workflow")


class CitizenWorkflowService:
    """Service encapsulating Citizen operations, grievance tracking, evidence, and public timelines."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.grievance_repo = GrievanceRepository(db)
        self.road_repo = RoadRepository(db)
        self.user_repo = UserRepository(db)
        self.work_order_repo = WorkOrderRepository(db)
        self.progress_repo = WorkProgressRepository(db)
        self.verification_repo = GovernmentVerificationRepository(db)
        self.event_repo = WorkflowEventRepository(db)

    def _verify_citizen_ownership(self, actor: UserContext, grievance: Grievance) -> None:
        """Verify actor has CITIZEN role and owns the specified grievance."""
        actor.require_role(UserRole.CITIZEN)
        if not actor.user_id:
            raise UnauthorizedError("Actor user_id is missing.")
        if grievance.citizen_id != actor.user_id:
            raise UnauthorizedError(
                f"Citizen '{actor.user_id}' does not own Grievance '{grievance.id}'."
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
        """Record an immutable workflow history audit log entry."""
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
        return event

    def create_grievance(
        self,
        actor: UserContext,
        payload: CitizenGrievanceCreate,
    ) -> Grievance:
        """Citizen creates and submits a new road grievance report.
        
        Strictly enforces initial status as SUBMITTED.
        """
        actor.require_role(UserRole.CITIZEN)
        if not actor.user_id:
            raise UnauthorizedError("Actor user_id is missing.")

        # Coordinate bounds validation
        if not (-90.0 <= payload.latitude <= 90.0):
            raise RoadXDataError(f"Latitude '{payload.latitude}' must be between -90.0 and +90.0.")
        if not (-180.0 <= payload.longitude <= 180.0):
            raise RoadXDataError(f"Longitude '{payload.longitude}' must be between -180.0 and +180.0.")

        # Resolve road segment ID if provided
        road_id = payload.road_id
        if not road_id and payload.road_segment_id:
            road = self.road_repo.get_by_segment_id(payload.road_segment_id)
            if road:
                road_id = road.id
            else:
                logger.warning("Road segment_id '%s' not found during grievance submission", payload.road_segment_id)

        grievance = Grievance(
            citizen_id=actor.user_id,
            road_id=road_id,
            description=payload.description.strip(),
            issue_category=payload.issue_category.strip().upper(),
            latitude=payload.latitude,
            longitude=payload.longitude,
            status=GrievanceStatus.SUBMITTED,
        )
        self.db.add(grievance)
        self.db.flush()

        # Audit Event
        self._log_workflow_event(
            grievance_id=grievance.id,
            event_type=WorkflowEventType.GRIEVANCE_SUBMITTED,
            actor=actor,
            new_status=GrievanceStatus.SUBMITTED.value,
            notes=f"Grievance submitted by citizen '{actor.user_id}'.",
        )

        # Attach initial evidence metadata if provided
        if payload.evidence_items:
            for item in payload.evidence_items:
                ev = Evidence(
                    grievance_id=grievance.id,
                    file_name=item.file_name.strip(),
                    file_type=item.file_type.strip(),
                    storage_path=item.storage_path.strip(),
                    file_size_bytes=item.file_size_bytes,
                )
                self.db.add(ev)

        try:
            self.db.commit()
            self.db.refresh(grievance)
            logger.info("Citizen '%s' created Grievance '%s'", actor.user_id, grievance.id)
            return grievance
        except Exception as e:
            self.db.rollback()
            raise e

    def attach_evidence(
        self,
        actor: UserContext,
        grievance_id: str,
        file_name: str,
        file_type: str,
        storage_path: str,
        file_size_bytes: Optional[int] = None,
    ) -> Evidence:
        """Citizen attaches additional image/evidence metadata to an existing owned grievance."""
        if not file_name or not file_name.strip() or not file_type or not file_type.strip() or not storage_path or not storage_path.strip():
            raise RoadXDataError("Evidence metadata file_name, file_type, and storage_path must be non-empty strings.")
        if file_size_bytes is not None and file_size_bytes < 0:
            raise RoadXDataError("Evidence file_size_bytes cannot be negative.")

        grievance = self.grievance_repo.get_by_id(grievance_id)
        if not grievance:
            raise RoadXDataError(f"Grievance with ID '{grievance_id}' not found.")

        self._verify_citizen_ownership(actor, grievance)

        if grievance.status in (GrievanceStatus.RESOLVED, GrievanceStatus.REJECTED):
            raise InvalidStateTransitionError(
                f"Cannot attach evidence to grievance in terminal state '{grievance.status.value}'."
            )

        evidence = Evidence(
            grievance_id=grievance.id,
            file_name=file_name.strip(),
            file_type=file_type.strip(),
            storage_path=storage_path.strip(),
            file_size_bytes=file_size_bytes,
        )
        self.db.add(evidence)

        try:
            self.db.commit()
            self.db.refresh(evidence)
            logger.info("Citizen '%s' attached evidence '%s' to Grievance '%s'", actor.user_id, evidence.id, grievance.id)
            return evidence
        except Exception as e:
            self.db.rollback()
            raise e

    def list_citizen_grievances(
        self,
        actor: UserContext,
        status_filter: Optional[GrievanceStatus] = None,
        issue_category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Grievance]:
        """Fetch grievances submitted by the requesting citizen."""
        actor.require_role(UserRole.CITIZEN)
        if not actor.user_id:
            raise UnauthorizedError("Actor user_id is missing.")

        return self.grievance_repo.filter_grievances(
            citizen_id=actor.user_id,
            status=status_filter,
            issue_category=issue_category,
            skip=skip,
            limit=limit,
        )

    def get_citizen_grievance_details(
        self,
        actor: UserContext,
        grievance_id: str,
    ) -> CitizenGrievanceDetailsRead:
        """Build complete citizen-safe view of a grievance including status, evidence, progress, timeline, and ML summary."""
        grievance = self.grievance_repo.get_by_id(grievance_id)
        if not grievance:
            raise RoadXDataError(f"Grievance with ID '{grievance_id}' not found.")

        self._verify_citizen_ownership(actor, grievance)

        # Fetch Road Name
        road = self.road_repo.get_by_id(grievance.road_id) if grievance.road_id else None
        road_name = road.road_name if road else None

        # Fetch Evidence Items
        evidence_items = (
            self.db.query(Evidence)
            .filter_by(grievance_id=grievance.id)
            .order_by(Evidence.uploaded_at.desc())
            .all()
        )
        evidence_reads = [EvidenceRead.model_validate(e) for e in evidence_items]

        # Fetch ML Analysis Summary if available
        ml_record = (
            self.db.query(MLAnalysisResult)
            .filter_by(grievance_id=grievance.id)
            .order_by(MLAnalysisResult.created_at.desc())
            .first()
        )
        ml_summary = None
        if ml_record:
            sev_out = ml_record.severity_prediction or {}
            fail_out = ml_record.failure_prediction or {}
            prio_out = ml_record.maintenance_priority or {}
            comp_out = ml_record.complaint_analysis or {}

            ml_summary = CitizenMLSummaryRead(
                detected_issue=comp_out.get("issue_category") or grievance.issue_category,
                severity_level=sev_out.get("severity_level"),
                risk_level=fail_out.get("risk_level"),
                priority_level=prio_out.get("priority_level"),
            )

        # Fetch Work Order and Contractor Progress
        work_order = (
            self.db.query(WorkOrder)
            .filter_by(grievance_id=grievance.id)
            .order_by(WorkOrder.created_at.desc())
            .first()
        )
        work_progress = None
        if work_order:
            progresses = self.progress_repo.get_by_work_order(work_order.id)
            latest_prog = progresses[-1] if progresses else None

            pct = latest_prog.progress_percentage if latest_prog else (100 if work_order.status == WorkOrderStatus.COMPLETED else 0)

            if work_order.status == WorkOrderStatus.ASSIGNED:
                status_display = "Maintenance work order assigned to contractor."
            elif work_order.status == WorkOrderStatus.IN_PROGRESS:
                status_display = f"Repair work in progress ({pct}% completed)."
            elif work_order.status == WorkOrderStatus.PENDING_VERIFICATION:
                status_display = "Repair work completed by contractor; pending final government officer verification."
            elif work_order.status == WorkOrderStatus.COMPLETED:
                status_display = "Repair work inspected and verified. Grievance resolved."
            else:
                status_display = f"Work order status: {work_order.status.value}"

            work_progress = CitizenWorkProgressRead(
                work_order_id=work_order.id,
                status=work_order.status.value,
                progress_percentage=pct,
                last_updated_at=latest_prog.created_at if latest_prog else work_order.updated_at,
                status_display=status_display,
            )

        # Fetch Rejection / Rework Info
        rejection_info = None
        if work_order and grievance.status == GrievanceStatus.IN_PROGRESS:
            verifications = self.verification_repo.get_by_work_order_id(work_order.id)
            has_rejection = any(v.decision == VerificationDecision.REJECT for v in verifications)
            if has_rejection:
                rejection_info = CitizenRejectionInfoRead(
                    is_reverted_for_rework=True,
                    public_message="Repair completion was inspected by government officer and sent back to contractor for rework.",
                )

        # Build Citizen-Friendly Timeline
        raw_events = self.event_repo.get_history_for_grievance(grievance.id)
        timeline_items = []
        for ev in raw_events:
            public_msg = self._map_event_to_public_message(ev)
            timeline_items.append(
                CitizenTimelineItemRead(
                    event_type=ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type),
                    status=ev.new_status or ev.old_status or grievance.status.value,
                    timestamp=ev.created_at,
                    public_message=public_msg,
                )
            )

        return CitizenGrievanceDetailsRead(
            id=grievance.id,
            citizen_id=grievance.citizen_id,
            road_id=grievance.road_id,
            road_name=road_name,
            issue_category=grievance.issue_category,
            description=grievance.description,
            latitude=grievance.latitude,
            longitude=grievance.longitude,
            status=grievance.status,
            created_at=grievance.created_at,
            updated_at=grievance.updated_at,
            evidence_items=evidence_reads,
            ml_summary=ml_summary,
            work_progress=work_progress,
            rejection_info=rejection_info,
            timeline=timeline_items,
        )

    def _map_event_to_public_message(self, event: WorkflowEvent) -> str:
        """Map internal event type to human-readable citizen timeline description."""
        et = event.event_type
        et_val = et.value if hasattr(et, "value") else str(et)

        if et_val == WorkflowEventType.GRIEVANCE_SUBMITTED.value:
            return "Grievance report submitted by citizen."
        elif et_val == WorkflowEventType.GRIEVANCE_ACCEPTED.value:
            return "Grievance reviewed and accepted for municipal repair."
        elif et_val == WorkflowEventType.GRIEVANCE_REJECTED.value:
            return "Grievance review rejected by government officer."
        elif et_val == WorkflowEventType.WORK_ORDER_CREATED.value:
            return "Maintenance work order created for repair."
        elif et_val == WorkflowEventType.WORK_ORDER_ASSIGNED.value:
            return "Work order assigned to maintenance contractor."
        elif et_val == WorkflowEventType.WORK_ORDER_ACKNOWLEDGED.value:
            return "Contractor acknowledged work order assignment."
        elif et_val == WorkflowEventType.WORK_STARTED.value:
            return "Contractor started repair work on site."
        elif et_val == WorkflowEventType.WORK_PROGRESS_UPDATED.value:
            return event.notes or "Contractor updated repair progress."
        elif et_val in (WorkflowEventType.WORK_COMPLETION_SUBMITTED.value, WorkflowEventType.WORK_VERIFICATION_SUBMITTED.value):
            return "Contractor submitted repair completion; pending government verification."
        elif et_val == WorkflowEventType.WORK_VERIFICATION_APPROVED.value:
            return "Government officer inspected and verified completion. Grievance resolved."
        elif et_val == WorkflowEventType.WORK_VERIFICATION_REJECTED.value:
            return "Government officer inspected repair and requested contractor rework."
        else:
            return event.notes or f"Status updated: {event.new_status or event.old_status or ''}"
