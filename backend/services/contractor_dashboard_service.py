"""Contractor Dashboard Service handling read-oriented workload analytics, filtering, progress, rework queues, and evidence visibility."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.models.evidence import Evidence
from backend.models.government_verification import GovernmentVerification, VerificationDecision
from backend.models.grievance import Grievance
from backend.models.ml_analysis import MLAnalysisResult
from backend.models.road import RoadSegment
from backend.models.user import User, UserRole
from backend.models.work_order import WorkOrder, WorkOrderStatus
from backend.models.work_progress import WorkProgress
from backend.models.workflow_event import WorkflowEvent
from backend.repositories.government_verification_repository import GovernmentVerificationRepository
from backend.repositories.grievance_repository import GrievanceRepository
from backend.repositories.road_repository import RoadRepository
from backend.repositories.user_repository import UserRepository
from backend.repositories.work_order_repository import WorkOrderRepository
from backend.repositories.work_progress_repository import WorkProgressRepository
from backend.repositories.workflow_event_repository import WorkflowEventRepository
from backend.schemas.contractor_dashboard import (
    ContractorDashboardOverviewRead,
    ContractorDashboardPendingVerificationItemRead,
    ContractorDashboardReworkItemRead,
    ContractorDashboardWorkOrderDetailRead,
    ContractorDashboardWorkOrderItemRead,
    ContractorDashboardWorkloadSummaryRead,
)
from backend.schemas.evidence import EvidenceRead
from backend.schemas.work_progress import WorkProgressRead
from backend.schemas.workflow_event import WorkflowEventRead
from backend.security import UserContext, UnauthorizedError
from ml.common.exceptions import RoadXDataError
from ml.common.logging_config import get_logger

logger = get_logger("backend.services.contractor_dashboard")


class ContractorDashboardService:
    """Service handling read-only Contractor Dashboard aggregations, filtering, progress, and workload metrics."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.grievance_repo = GrievanceRepository(db)
        self.road_repo = RoadRepository(db)
        self.user_repo = UserRepository(db)
        self.work_order_repo = WorkOrderRepository(db)
        self.progress_repo = WorkProgressRepository(db)
        self.verification_repo = GovernmentVerificationRepository(db)
        self.event_repo = WorkflowEventRepository(db)

    def _verify_contractor_actor(self, actor: UserContext) -> str:
        """Enforce CONTRACTOR role and return non-null user_id."""
        actor.require_role(UserRole.CONTRACTOR)
        if not actor.user_id:
            raise UnauthorizedError("Actor user_id is missing.")
        return actor.user_id

    def _verify_work_order_ownership(self, actor: UserContext, work_order: WorkOrder) -> None:
        """Verify contractor ownership of a work order."""
        contractor_id = self._verify_contractor_actor(actor)
        if work_order.assigned_contractor_id != contractor_id:
            raise UnauthorizedError(
                f"Contractor '{contractor_id}' is not authorized to access work order '{work_order.id}'."
            )

    def _get_latest_progress_percentage(self, work_order_id: str, wo_status: WorkOrderStatus) -> int:
        """Get latest recorded progress percentage or default based on status."""
        progresses = self.progress_repo.get_by_work_order(work_order_id)
        if progresses:
            return progresses[-1].progress_percentage
        if wo_status == WorkOrderStatus.COMPLETED:
            return 100
        return 0

    def _get_latest_rejection_info(self, work_order_id: str) -> Tuple[Optional[str], Optional[datetime]]:
        """Fetch latest rejection notes and timestamp for a work order if present."""
        verifications = self.verification_repo.get_by_work_order_id(work_order_id)
        for ver in verifications:
            if ver.decision == VerificationDecision.REJECT:
                return ver.notes, ver.created_at
        return None, None

    def get_overview(self, actor: UserContext) -> ContractorDashboardOverviewRead:
        """Calculate dashboard statistics for the authenticated contractor."""
        contractor_id = self._verify_contractor_actor(actor)

        work_orders = (
            self.db.query(WorkOrder)
            .filter(WorkOrder.assigned_contractor_id == contractor_id)
            .all()
        )

        total_assigned = len(work_orders)
        assigned_count = sum(1 for w in work_orders if w.status == WorkOrderStatus.ASSIGNED)
        in_progress_count = sum(1 for w in work_orders if w.status == WorkOrderStatus.IN_PROGRESS)
        pending_verification_count = sum(1 for w in work_orders if w.status == WorkOrderStatus.PENDING_VERIFICATION)
        completed_count = sum(1 for w in work_orders if w.status == WorkOrderStatus.COMPLETED)

        rework_count = 0
        progress_values = []
        for w in work_orders:
            rejection_notes, _ = self._get_latest_rejection_info(w.id)
            if w.status == WorkOrderStatus.IN_PROGRESS and rejection_notes is not None:
                rework_count += 1

            pct = self._get_latest_progress_percentage(w.id, w.status)
            progress_values.append(pct)

        avg_progress = (sum(progress_values) / len(progress_values)) if progress_values else 0.0

        return ContractorDashboardOverviewRead(
            total_assigned=total_assigned,
            assigned=assigned_count,
            in_progress=in_progress_count,
            pending_verification=pending_verification_count,
            completed=completed_count,
            rework=rework_count,
            average_progress=round(avg_progress, 2),
        )

    def list_assigned_work_orders(
        self,
        actor: UserContext,
        status_filter: Optional[WorkOrderStatus] = None,
        priority: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 100,
    ) -> List[ContractorDashboardWorkOrderItemRead]:
        """List work orders assigned to the authenticated contractor with filtering, sorting, and pagination."""
        contractor_id = self._verify_contractor_actor(actor)

        query = self.db.query(WorkOrder).filter(WorkOrder.assigned_contractor_id == contractor_id)

        if status_filter:
            query = query.filter(WorkOrder.status == status_filter)
        if priority:
            query = query.filter(WorkOrder.priority == priority.upper())
        if date_from:
            query = query.filter(WorkOrder.created_at >= date_from)
        if date_to:
            query = query.filter(WorkOrder.created_at <= date_to)

        # Sorting
        if hasattr(WorkOrder, sort_by):
            col = getattr(WorkOrder, sort_by)
            order_col = col.desc() if sort_order.lower() == "desc" else col.asc()
            query = query.order_by(order_col)
        else:
            query = query.order_by(WorkOrder.created_at.desc())

        work_orders = query.offset(skip).limit(limit).all()

        items: List[ContractorDashboardWorkOrderItemRead] = []
        for wo in work_orders:
            road = self.road_repo.get_by_id(wo.road_id) if wo.road_id else None
            rejection_notes, _ = self._get_latest_rejection_info(wo.id)
            rework_req = (wo.status == WorkOrderStatus.IN_PROGRESS and rejection_notes is not None)
            pct = self._get_latest_progress_percentage(wo.id, wo.status)

            items.append(
                ContractorDashboardWorkOrderItemRead(
                    id=wo.id,
                    grievance_id=wo.grievance_id,
                    road_id=wo.road_id,
                    road_name=road.road_name if road else None,
                    title=wo.title,
                    description=wo.description,
                    priority=wo.priority,
                    status=wo.status,
                    progress_percentage=pct,
                    rework_required=rework_req,
                    created_at=wo.created_at,
                    updated_at=wo.updated_at,
                )
            )

        return items

    def get_work_order_detail(
        self,
        actor: UserContext,
        work_order_id: str,
    ) -> ContractorDashboardWorkOrderDetailRead:
        """Retrieve contractor-safe detailed view of an assigned work order."""
        wo = self.work_order_repo.get_by_id(work_order_id)
        if not wo:
            raise RoadXDataError(f"Work order with ID '{work_order_id}' not found.")

        self._verify_work_order_ownership(actor, wo)

        grievance = self.grievance_repo.get_by_id(wo.grievance_id)
        road = self.road_repo.get_by_id(wo.road_id) if wo.road_id else None

        # Progress history in chronological order
        progresses = self.progress_repo.get_by_work_order(wo.id)
        progress_reads = [WorkProgressRead.model_validate(p) for p in progresses]
        current_pct = progresses[-1].progress_percentage if progresses else (100 if wo.status == WorkOrderStatus.COMPLETED else 0)

        # Completion evidence metadata
        evidence_items = (
            self.db.query(Evidence)
            .filter((Evidence.work_order_id == wo.id) | (Evidence.grievance_id == wo.grievance_id))
            .order_by(Evidence.uploaded_at.desc())
            .all()
        )
        evidence_reads = [EvidenceRead.model_validate(e) for e in evidence_items]

        # Government verification feedback
        verifications = self.verification_repo.get_by_work_order_id(wo.id)
        latest_ver = verifications[0] if verifications else None
        latest_verification_status = latest_ver.decision.value if latest_ver else None

        latest_rejection_notes, rejection_ts = self._get_latest_rejection_info(wo.id)
        rework_req = (wo.status == WorkOrderStatus.IN_PROGRESS and latest_rejection_notes is not None)

        # High-level ML results associated with grievance (if any)
        ml_rec = (
            self.db.query(MLAnalysisResult)
            .filter_by(grievance_id=wo.grievance_id)
            .order_by(MLAnalysisResult.created_at.desc())
            .first()
        )
        grievance_severity = None
        grievance_risk = None
        grievance_priority = None
        if ml_rec:
            sev_out = ml_rec.severity_prediction or {}
            fail_out = ml_rec.failure_prediction or {}
            prio_out = ml_rec.maintenance_priority or {}
            grievance_severity = sev_out.get("severity_level")
            grievance_risk = fail_out.get("risk_level")
            grievance_priority = prio_out.get("priority_level")

        # Timeline
        timeline_events = self.event_repo.get_history_for_grievance(wo.grievance_id)
        timeline_reads = [WorkflowEventRead.model_validate(e) for e in timeline_events]

        return ContractorDashboardWorkOrderDetailRead(
            id=wo.id,
            grievance_id=wo.grievance_id,
            road_id=wo.road_id,
            title=wo.title,
            description=wo.description,
            priority=wo.priority,
            status=wo.status,
            created_at=wo.created_at,
            updated_at=wo.updated_at,
            road_name=road.road_name if road else None,
            road_code=road.segment_id if road else None,
            latitude=grievance.latitude if grievance else None,
            longitude=grievance.longitude if grievance else None,
            grievance_description=grievance.description if grievance else None,
            grievance_issue_category=grievance.issue_category if grievance else None,
            grievance_severity=grievance_severity,
            grievance_risk_level=grievance_risk,
            grievance_priority=grievance_priority,
            current_progress=current_pct,
            progress_history=progress_reads,
            completion_evidence=evidence_reads,
            government_verification_status=latest_verification_status,
            rework_required=rework_req,
            latest_rejection_notes=latest_rejection_notes,
            rejection_timestamp=rejection_ts,
            timeline=timeline_reads,
        )

    def get_pending_verification_queue(
        self,
        actor: UserContext,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ContractorDashboardPendingVerificationItemRead]:
        """Fetch current contractor's work orders in PENDING_VERIFICATION status."""
        contractor_id = self._verify_contractor_actor(actor)

        pending_wos = (
            self.db.query(WorkOrder)
            .filter(
                WorkOrder.assigned_contractor_id == contractor_id,
                WorkOrder.status == WorkOrderStatus.PENDING_VERIFICATION,
            )
            .order_by(WorkOrder.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        results: List[ContractorDashboardPendingVerificationItemRead] = []
        for wo in pending_wos:
            evidence_items = (
                self.db.query(Evidence)
                .filter((Evidence.work_order_id == wo.id) | (Evidence.grievance_id == wo.grievance_id))
                .order_by(Evidence.uploaded_at.desc())
                .all()
            )
            evidence_reads = [EvidenceRead.model_validate(e) for e in evidence_items]

            results.append(
                ContractorDashboardPendingVerificationItemRead(
                    work_order_id=wo.id,
                    grievance_id=wo.grievance_id,
                    title=wo.title,
                    priority=wo.priority,
                    progress_percentage=100,
                    completion_submitted_at=wo.updated_at,
                    evidence=evidence_reads,
                )
            )

        return results

    def get_rework_queue(
        self,
        actor: UserContext,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ContractorDashboardReworkItemRead]:
        """Fetch work orders assigned to current contractor that were rejected by government and require rework."""
        contractor_id = self._verify_contractor_actor(actor)

        assigned_wos = (
            self.db.query(WorkOrder)
            .filter(
                WorkOrder.assigned_contractor_id == contractor_id,
                WorkOrder.status == WorkOrderStatus.IN_PROGRESS,
            )
            .order_by(WorkOrder.updated_at.desc())
            .all()
        )

        rework_items: List[ContractorDashboardReworkItemRead] = []
        for wo in assigned_wos:
            rejection_notes, rejection_ts = self._get_latest_rejection_info(wo.id)
            if rejection_notes is not None:
                current_pct = self._get_latest_progress_percentage(wo.id, wo.status)
                rework_items.append(
                    ContractorDashboardReworkItemRead(
                        work_order_id=wo.id,
                        grievance_id=wo.grievance_id,
                        title=wo.title,
                        priority=wo.priority,
                        current_status=wo.status,
                        rejection_message=rejection_notes,
                        rejection_timestamp=rejection_ts,
                        current_progress=current_pct,
                    )
                )

        return rework_items[skip : skip + limit]

    def get_workload_summary(self, actor: UserContext) -> ContractorDashboardWorkloadSummaryRead:
        """Fetch personal workload summary metrics for current contractor."""
        contractor_id = self._verify_contractor_actor(actor)

        work_orders = (
            self.db.query(WorkOrder)
            .filter(WorkOrder.assigned_contractor_id == contractor_id)
            .all()
        )

        total_assignments = len(work_orders)
        active_assignments = sum(1 for w in work_orders if w.status in (WorkOrderStatus.ASSIGNED, WorkOrderStatus.IN_PROGRESS))
        pending_ver = sum(1 for w in work_orders if w.status == WorkOrderStatus.PENDING_VERIFICATION)
        resolved_comp = sum(1 for w in work_orders if w.status == WorkOrderStatus.COMPLETED)

        rework_count = 0
        progress_values = []
        for w in work_orders:
            rejection_notes, _ = self._get_latest_rejection_info(w.id)
            if w.status == WorkOrderStatus.IN_PROGRESS and rejection_notes is not None:
                rework_count += 1

            pct = self._get_latest_progress_percentage(w.id, w.status)
            progress_values.append(pct)

        avg_comp = (sum(progress_values) / len(progress_values)) if progress_values else 0.0

        return ContractorDashboardWorkloadSummaryRead(
            total_assignments=total_assignments,
            active_assignments=active_assignments,
            pending_verification=pending_ver,
            rework_required=rework_count,
            resolved_completed=resolved_comp,
            average_completion_percentage=round(avg_comp, 2),
        )
