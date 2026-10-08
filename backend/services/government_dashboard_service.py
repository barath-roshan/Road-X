"""Government Dashboard Service coordinating executive analytics, queue management, and contractor monitoring."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from backend.models.evidence import Evidence
from backend.models.government_review import GovernmentReview
from backend.models.government_verification import GovernmentVerification, VerificationDecision
from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.ml_analysis import MLAnalysisResult
from backend.models.road import RoadSegment
from backend.models.user import User, UserRole
from backend.models.work_order import WorkOrder, WorkOrderStatus
from backend.models.work_progress import WorkProgress
from backend.models.workflow_event import WorkflowEvent
from backend.repositories.government_review_repository import GovernmentReviewRepository
from backend.repositories.government_verification_repository import GovernmentVerificationRepository
from backend.repositories.grievance_repository import GrievanceRepository
from backend.repositories.road_repository import RoadRepository
from backend.repositories.user_repository import UserRepository
from backend.repositories.work_order_repository import WorkOrderRepository
from backend.repositories.work_progress_repository import WorkProgressRepository
from backend.repositories.workflow_event_repository import WorkflowEventRepository
from backend.schemas.evidence import EvidenceRead
from backend.schemas.government_dashboard import (
    GovernmentDashboardContractorSummaryRead,
    GovernmentDashboardGrievanceDetailRead,
    GovernmentDashboardGrievanceItemRead,
    GovernmentDashboardOverviewRead,
    GovernmentDashboardPriorityItemRead,
    GovernmentDashboardVerificationItemRead,
    GovernmentDashboardWorkOrderItemRead,
)
from backend.schemas.government_review import GovernmentReviewRead
from backend.schemas.government_verification import GovernmentVerificationRead
from backend.schemas.user import UserRead
from backend.schemas.work_order import WorkOrderRead
from backend.schemas.work_progress import WorkProgressRead
from backend.schemas.workflow_event import WorkflowEventRead
from backend.security import UserContext, UnauthorizedError
from ml.common.exceptions import RoadXDataError
from ml.common.logging_config import get_logger

logger = get_logger("backend.services.government_dashboard")


class GovernmentDashboardService:
    """Service handling Government Dashboard aggregations, search, monitoring, and analytics."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.grievance_repo = GrievanceRepository(db)
        self.road_repo = RoadRepository(db)
        self.user_repo = UserRepository(db)
        self.work_order_repo = WorkOrderRepository(db)
        self.progress_repo = WorkProgressRepository(db)
        self.verification_repo = GovernmentVerificationRepository(db)
        self.event_repo = WorkflowEventRepository(db)
        self.review_repo = GovernmentReviewRepository(db)

    def get_overview(self, actor: UserContext) -> GovernmentDashboardOverviewRead:
        """Fetch aggregate dashboard summary stats for government officers."""
        actor.require_role(UserRole.GOVERNMENT_OFFICER)

        # 1. Total Grievances
        total_grievances = self.db.query(func.count(Grievance.id)).scalar() or 0

        # 2. Grievances Status Breakdown
        grievance_status_query = (
            self.db.query(Grievance.status, func.count(Grievance.id))
            .group_by(Grievance.status)
            .all()
        )
        status_counts = {st.value: 0 for st in GrievanceStatus}
        for st_val, count in grievance_status_query:
            key = st_val.value if hasattr(st_val, "value") else str(st_val)
            status_counts[key] = count

        # 3. Work Order Status Breakdown
        wo_status_query = (
            self.db.query(WorkOrder.status, func.count(WorkOrder.id))
            .group_by(WorkOrder.status)
            .all()
        )
        work_order_counts = {st.value: 0 for st in WorkOrderStatus}
        for st_val, count in wo_status_query:
            key = st_val.value if hasattr(st_val, "value") else str(st_val)
            work_order_counts[key] = count

        # 4. Contractor & Verification Counts
        active_contractors_count = (
            self.db.query(func.count(User.id))
            .filter(User.role == UserRole.CONTRACTOR)
            .scalar() or 0
        )
        pending_verifications_count = work_order_counts.get(WorkOrderStatus.PENDING_VERIFICATION.value, 0)

        # 5. Priority & Severity Counts from ML Analysis Results
        priority_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

        ml_records = self.db.query(MLAnalysisResult).all()
        for rec in ml_records:
            prio_out = rec.maintenance_priority or {}
            sev_out = rec.severity_prediction or {}

            prio_lvl = prio_out.get("priority_level", "").upper()
            if prio_lvl in priority_counts:
                priority_counts[prio_lvl] += 1

            sev_lvl = sev_out.get("severity_level", "").upper()
            if sev_lvl in severity_counts:
                severity_counts[sev_lvl] += 1

        return GovernmentDashboardOverviewRead(
            total_grievances=total_grievances,
            status_counts=status_counts,
            priority_counts=priority_counts,
            severity_counts=severity_counts,
            work_order_counts=work_order_counts,
            active_contractors_count=active_contractors_count,
            pending_verifications_count=pending_verifications_count,
        )

    def list_dashboard_grievances(
        self,
        actor: UserContext,
        status_filter: Optional[GrievanceStatus] = None,
        issue_category: Optional[str] = None,
        priority: Optional[str] = None,
        severity: Optional[str] = None,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 100,
    ) -> List[GovernmentDashboardGrievanceItemRead]:
        """Search and filter grievances for government dashboard listing."""
        actor.require_role(UserRole.GOVERNMENT_OFFICER)

        query = self.db.query(Grievance)

        if status_filter:
            query = query.filter(Grievance.status == status_filter)
        if issue_category:
            query = query.filter(Grievance.issue_category.ilike(f"%{issue_category.strip()}%"))
        if date_from:
            query = query.filter(Grievance.created_at >= date_from)
        if date_to:
            query = query.filter(Grievance.created_at <= date_to)

        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Grievance.id.ilike(s),
                    Grievance.description.ilike(s),
                    Grievance.issue_category.ilike(s),
                )
            )

        # Sorting
        if sort_by == "created_at":
            order_col = Grievance.created_at.desc() if sort_order == "desc" else Grievance.created_at.asc()
            query = query.order_by(order_col)

        grievances = query.offset(skip).limit(limit).all()

        results: List[GovernmentDashboardGrievanceItemRead] = []
        for gr in grievances:
            citizen = self.user_repo.get_by_id(gr.citizen_id) if gr.citizen_id else None
            road = self.road_repo.get_by_id(gr.road_id) if gr.road_id else None

            # Fetch ML analysis
            ml_rec = (
                self.db.query(MLAnalysisResult)
                .filter_by(grievance_id=gr.id)
                .order_by(MLAnalysisResult.created_at.desc())
                .first()
            )
            prio_lvl = None
            sev_lvl = None
            r_lvl = None
            if ml_rec:
                prio_out = ml_rec.maintenance_priority or {}
                sev_out = ml_rec.severity_prediction or {}
                fail_out = ml_rec.failure_prediction or {}
                prio_lvl = prio_out.get("priority_level")
                sev_lvl = sev_out.get("severity_level")
                r_lvl = fail_out.get("risk_level")

            # Post-filter ML attributes if requested
            if priority and prio_lvl and prio_lvl.upper() != priority.upper():
                continue
            if severity and sev_lvl and sev_lvl.upper() != severity.upper():
                continue
            if risk_level and r_lvl and r_lvl.upper() != risk_level.upper():
                continue

            # Fetch associated work order
            wo = (
                self.db.query(WorkOrder)
                .filter_by(grievance_id=gr.id)
                .order_by(WorkOrder.created_at.desc())
                .first()
            )
            contractor_name = None
            wo_status_str = None
            if wo:
                wo_status_str = wo.status.value
                if wo.assigned_contractor_id:
                    c_user = self.user_repo.get_by_id(wo.assigned_contractor_id)
                    contractor_name = c_user.name if c_user else None

            results.append(
                GovernmentDashboardGrievanceItemRead(
                    id=gr.id,
                    citizen_id=gr.citizen_id,
                    citizen_name=citizen.name if citizen else None,
                    road_id=gr.road_id,
                    road_name=road.road_name if road else None,
                    issue_category=gr.issue_category,
                    description=gr.description,
                    latitude=gr.latitude,
                    longitude=gr.longitude,
                    status=gr.status,
                    created_at=gr.created_at,
                    updated_at=gr.updated_at,
                    priority=prio_lvl,
                    severity=sev_lvl,
                    risk_level=r_lvl,
                    work_order_status=wo_status_str,
                    assigned_contractor_name=contractor_name,
                )
            )

        return results

    def get_dashboard_grievance_detail(
        self,
        actor: UserContext,
        grievance_id: str,
    ) -> GovernmentDashboardGrievanceDetailRead:
        """Fetch complete government detailed view of a grievance case."""
        actor.require_role(UserRole.GOVERNMENT_OFFICER)

        gr = self.grievance_repo.get_by_id(grievance_id)
        if not gr:
            raise RoadXDataError(f"Grievance with ID '{grievance_id}' not found.")

        citizen = self.user_repo.get_by_id(gr.citizen_id) if gr.citizen_id else None
        road = self.road_repo.get_by_id(gr.road_id) if gr.road_id else None

        # Evidence
        evidence_items = (
            self.db.query(Evidence)
            .filter_by(grievance_id=gr.id)
            .order_by(Evidence.uploaded_at.desc())
            .all()
        )
        evidence_reads = [EvidenceRead.model_validate(e) for e in evidence_items]

        # ML Analysis
        ml_rec = (
            self.db.query(MLAnalysisResult)
            .filter_by(grievance_id=gr.id)
            .order_by(MLAnalysisResult.created_at.desc())
            .first()
        )
        ml_dict = None
        if ml_rec:
            ml_dict = {
                "id": ml_rec.id,
                "pipeline_version": ml_rec.pipeline_version,
                "overall_status": ml_rec.overall_status,
                "failure_prediction": ml_rec.failure_prediction,
                "damage_detection": ml_rec.damage_detection,
                "severity_prediction": ml_rec.severity_prediction,
                "complaint_analysis": ml_rec.complaint_analysis,
                "duplicate_detection": ml_rec.duplicate_detection,
                "time_to_failure": ml_rec.time_to_failure,
                "maintenance_priority": ml_rec.maintenance_priority,
                "created_at": ml_rec.created_at.isoformat(),
            }

        # Work Order & Contractor
        wo = (
            self.db.query(WorkOrder)
            .filter_by(grievance_id=gr.id)
            .order_by(WorkOrder.created_at.desc())
            .first()
        )
        wo_read = WorkOrderRead.model_validate(wo) if wo else None

        contractor = None
        if wo and wo.assigned_contractor_id:
            c_user = self.user_repo.get_by_id(wo.assigned_contractor_id)
            contractor = UserRead.model_validate(c_user) if c_user else None

        # Progress history
        progress_entries = self.progress_repo.get_by_work_order(wo.id) if wo else []
        progress_reads = [WorkProgressRead.model_validate(p) for p in progress_entries]

        # Reviews & Verifications
        reviews = (
            self.db.query(GovernmentReview)
            .filter_by(grievance_id=gr.id)
            .order_by(GovernmentReview.created_at.desc())
            .all()
        )
        review_reads = [GovernmentReviewRead.model_validate(r) for r in reviews]

        verifications = (
            self.db.query(GovernmentVerification)
            .filter_by(grievance_id=gr.id)
            .order_by(GovernmentVerification.created_at.desc())
            .all()
        )
        verification_reads = [GovernmentVerificationRead.model_validate(v) for v in verifications]

        # Timeline
        timeline_events = self.event_repo.get_history_for_grievance(gr.id)
        timeline_reads = [WorkflowEventRead.model_validate(e) for e in timeline_events]

        return GovernmentDashboardGrievanceDetailRead(
            id=gr.id,
            citizen_id=gr.citizen_id,
            citizen_name=citizen.name if citizen else None,
            citizen_email=citizen.email if citizen else None,
            road_id=gr.road_id,
            road_name=road.road_name if road else None,
            road_code=road.segment_id if road else None,
            issue_category=gr.issue_category,
            description=gr.description,
            latitude=gr.latitude,
            longitude=gr.longitude,
            status=gr.status,
            created_at=gr.created_at,
            updated_at=gr.updated_at,
            evidence_items=evidence_reads,
            ml_analysis=ml_dict,
            work_order=wo_read,
            assigned_contractor=contractor,
            progress_history=progress_reads,
            verifications=verification_reads,
            reviews=review_reads,
            timeline=timeline_reads,
        )

    def get_priority_queue(
        self,
        actor: UserContext,
        min_priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GovernmentDashboardPriorityItemRead]:
        """Fetch prioritized maintenance queue based strictly on stored Phase 8 Maintenance Priority ML outputs."""
        actor.require_role(UserRole.GOVERNMENT_OFFICER)

        ml_records = (
            self.db.query(MLAnalysisResult)
            .order_by(MLAnalysisResult.created_at.desc())
            .all()
        )

        # Map latest ML record per grievance
        latest_by_grievance: Dict[str, MLAnalysisResult] = {}
        for rec in ml_records:
            if rec.grievance_id not in latest_by_grievance:
                latest_by_grievance[rec.grievance_id] = rec

        priority_items: List[GovernmentDashboardPriorityItemRead] = []
        for grievance_id, ml_rec in latest_by_grievance.items():
            gr = self.grievance_repo.get_by_id(grievance_id)
            if not gr or gr.status in (GrievanceStatus.RESOLVED, GrievanceStatus.REJECTED):
                continue

            prio_out = ml_rec.maintenance_priority or {}
            sev_out = ml_rec.severity_prediction or {}
            fail_out = ml_rec.failure_prediction or {}
            ttf_out = ml_rec.time_to_failure or {}

            prio_score = prio_out.get("priority_score", 0.0)
            prio_level = prio_out.get("priority_level", "MEDIUM")
            reasons = prio_out.get("reasons", [])

            if min_priority:
                allowed_priorities = []
                if min_priority.upper() == "CRITICAL":
                    allowed_priorities = ["CRITICAL"]
                elif min_priority.upper() == "HIGH":
                    allowed_priorities = ["HIGH", "CRITICAL"]
                if prio_level.upper() not in allowed_priorities:
                    continue

            road = self.road_repo.get_by_id(gr.road_id) if gr.road_id else None

            priority_items.append(
                GovernmentDashboardPriorityItemRead(
                    grievance_id=gr.id,
                    road_name=road.road_name if road else None,
                    issue_category=gr.issue_category,
                    description=gr.description,
                    status=gr.status,
                    priority_score=prio_score,
                    priority_level=prio_level,
                    severity_level=sev_out.get("severity_level"),
                    risk_level=fail_out.get("risk_level"),
                    estimated_time_to_failure_days=ttf_out.get("estimated_time_to_failure_days"),
                    reasons=reasons,
                    created_at=gr.created_at,
                )
            )

        # Sort strictly descending by priority_score
        priority_items.sort(key=lambda x: x.priority_score or 0.0, reverse=True)
        return priority_items[skip : skip + limit]

    def get_verification_queue(
        self,
        actor: UserContext,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GovernmentDashboardVerificationItemRead]:
        """Fetch work orders currently waiting for government completion verification."""
        actor.require_role(UserRole.GOVERNMENT_OFFICER)

        pending_work_orders = (
            self.db.query(WorkOrder)
            .filter(WorkOrder.status == WorkOrderStatus.PENDING_VERIFICATION)
            .order_by(WorkOrder.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        results: List[GovernmentDashboardVerificationItemRead] = []
        for wo in pending_work_orders:
            gr = self.grievance_repo.get_by_id(wo.grievance_id)
            road = self.road_repo.get_by_id(wo.road_id) if wo.road_id else None
            contractor = self.user_repo.get_by_id(wo.assigned_contractor_id) if wo.assigned_contractor_id else None

            progresses = self.progress_repo.get_by_work_order(wo.id)
            latest_prog = progresses[-1] if progresses else None

            evidence_items = (
                self.db.query(Evidence)
                .filter((Evidence.work_order_id == wo.id) | (Evidence.grievance_id == wo.grievance_id))
                .order_by(Evidence.uploaded_at.desc())
                .all()
            )
            evidence_reads = [EvidenceRead.model_validate(e) for e in evidence_items]

            results.append(
                GovernmentDashboardVerificationItemRead(
                    work_order_id=wo.id,
                    grievance_id=wo.grievance_id,
                    grievance_description=gr.description if gr else "",
                    road_name=road.road_name if road else None,
                    contractor_id=wo.assigned_contractor_id or "",
                    contractor_name=contractor.name if contractor else None,
                    work_order_title=wo.title,
                    priority=wo.priority,
                    submitted_at=wo.updated_at,
                    latest_progress_note=latest_prog.note if latest_prog else None,
                    evidence_items=evidence_reads,
                )
            )

        return results

    def get_work_orders_monitoring(
        self,
        actor: UserContext,
        status_filter: Optional[WorkOrderStatus] = None,
        priority: Optional[str] = None,
        assigned_contractor_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GovernmentDashboardWorkOrderItemRead]:
        """Fetch work order monitoring entries with contractor assignment and progress status."""
        actor.require_role(UserRole.GOVERNMENT_OFFICER)

        query = self.db.query(WorkOrder)
        if status_filter:
            query = query.filter(WorkOrder.status == status_filter)
        if priority:
            query = query.filter(WorkOrder.priority == priority.upper())
        if assigned_contractor_id:
            query = query.filter(WorkOrder.assigned_contractor_id == assigned_contractor_id)
        if date_from:
            query = query.filter(WorkOrder.created_at >= date_from)
        if date_to:
            query = query.filter(WorkOrder.created_at <= date_to)

        work_orders = query.order_by(WorkOrder.updated_at.desc()).offset(skip).limit(limit).all()

        results: List[GovernmentDashboardWorkOrderItemRead] = []
        for wo in work_orders:
            road = self.road_repo.get_by_id(wo.road_id) if wo.road_id else None
            contractor = self.user_repo.get_by_id(wo.assigned_contractor_id) if wo.assigned_contractor_id else None

            progresses = self.progress_repo.get_by_work_order(wo.id)
            latest_prog = progresses[-1] if progresses else None
            pct = latest_prog.progress_percentage if latest_prog else (100 if wo.status == WorkOrderStatus.COMPLETED else 0)

            results.append(
                GovernmentDashboardWorkOrderItemRead(
                    id=wo.id,
                    grievance_id=wo.grievance_id,
                    road_name=road.road_name if road else None,
                    assigned_contractor_id=wo.assigned_contractor_id,
                    contractor_name=contractor.name if contractor else None,
                    title=wo.title,
                    description=wo.description,
                    priority=wo.priority,
                    status=wo.status,
                    current_progress_percentage=pct,
                    created_at=wo.created_at,
                    updated_at=wo.updated_at,
                )
            )

        return results

    def get_contractors_summary(
        self,
        actor: UserContext,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GovernmentDashboardContractorSummaryRead]:
        """Fetch workload and progress performance metrics for all contractors."""
        actor.require_role(UserRole.GOVERNMENT_OFFICER)

        contractors = (
            self.db.query(User)
            .filter(User.role == UserRole.CONTRACTOR)
            .offset(skip)
            .limit(limit)
            .all()
        )

        summaries: List[GovernmentDashboardContractorSummaryRead] = []
        for c in contractors:
            wo_list = (
                self.db.query(WorkOrder)
                .filter(WorkOrder.assigned_contractor_id == c.id)
                .all()
            )

            assigned_count = len(wo_list)
            in_prog_count = sum(1 for w in wo_list if w.status == WorkOrderStatus.IN_PROGRESS)
            pending_ver_count = sum(1 for w in wo_list if w.status == WorkOrderStatus.PENDING_VERIFICATION)
            completed_count = sum(1 for w in wo_list if w.status == WorkOrderStatus.COMPLETED)

            # Calculate average progress
            progress_values = []
            for w in wo_list:
                progs = self.progress_repo.get_by_work_order(w.id)
                if progs:
                    progress_values.append(progs[-1].progress_percentage)
                elif w.status == WorkOrderStatus.COMPLETED:
                    progress_values.append(100)
                else:
                    progress_values.append(0)

            avg_progress = (sum(progress_values) / len(progress_values)) if progress_values else 0.0

            summaries.append(
                GovernmentDashboardContractorSummaryRead(
                    contractor_id=c.id,
                    contractor_name=c.name,
                    contractor_email=c.email,
                    assigned_work_orders_count=assigned_count,
                    in_progress_count=in_prog_count,
                    pending_verification_count=pending_ver_count,
                    completed_count=completed_count,
                    average_progress_percentage=round(avg_progress, 2),
                )
            )

        return summaries
