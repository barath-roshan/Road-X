"""API Router for Government Officer Workflow operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.config import api_settings
from api.dependencies import get_current_actor
from backend.database import get_db
from backend.models.grievance import GrievanceStatus
from backend.models.work_order import WorkOrderStatus
from backend.models.road_operation import RoadOperationStatus, RoadOperationType
from backend.schemas.government_dashboard import (
    GovernmentDashboardOverviewRead,
    GovernmentDashboardGrievanceItemRead,
    GovernmentDashboardGrievanceDetailRead,
    GovernmentDashboardPriorityItemRead,
    GovernmentDashboardVerificationItemRead,
    GovernmentDashboardWorkOrderItemRead,
    GovernmentDashboardContractorSummaryRead,
)
from backend.schemas.government_review import GovernmentReviewCreate, GovernmentReviewRead
from backend.schemas.government_verification import GovernmentVerificationCreate, GovernmentVerificationRead
from backend.schemas.grievance import GrievanceRead
from backend.schemas.work_order import WorkOrderCreate, WorkOrderRead
from backend.schemas.workflow_event import WorkflowEventRead
from backend.schemas.road_operation import (
    RoadOperationCreate,
    RoadOperationUpdate,
    GovernmentRoadOperationRead,
    RoadOperationEventRead,
)
from backend.security import UserContext, UnauthorizedError, InvalidStateTransitionError
from backend.services.government_dashboard_service import GovernmentDashboardService
from backend.services.government_workflow_service import GovernmentWorkflowService
from backend.services.grievance_service import GrievanceService
from backend.services.road_operation_service import RoadOperationService
from backend.repositories.work_order_repository import WorkOrderRepository
from ml.common.exceptions import RoadXDataError

router = APIRouter(prefix=f"{api_settings.api_prefix}/government", tags=["Government Workflow"])


@router.get(
    "/grievances",
    response_model=List[GrievanceRead],
    summary="List Grievances for Government Review",
    description="Returns grievances for municipal review with status, priority, and category filtering.",
)
def list_government_grievances(
    status_filter: Optional[GrievanceStatus] = Query(default=None, alias="status"),
    issue_category: Optional[str] = Query(default=None),
    road_id: Optional[str] = Query(default=None),
    citizen_id: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[GrievanceRead]:
    """Retrieve grievances for officer inspection."""
    if not actor.is_government_officer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Actor role '{actor.role.value}' is not authorized to access government queue.",
        )
    service = GrievanceService(db)
    items = service.list_grievances(
        status=status_filter,
        issue_category=issue_category,
        road_id=road_id,
        citizen_id=citizen_id,
        skip=skip,
        limit=limit,
    )
    return [GrievanceRead.model_validate(item) for item in items]


@router.get(
    "/grievances/{grievance_id}",
    response_model=GrievanceRead,
    summary="Get Detailed Grievance Case for Government Review",
)
def get_government_grievance_details(
    grievance_id: str,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GrievanceRead:
    """Retrieve complete grievance case detail for government review."""
    if not actor.is_government_officer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Actor role '{actor.role.value}' is not authorized.",
        )
    service = GrievanceService(db)
    try:
        grievance = service.get_grievance(grievance_id)
        return GrievanceRead.model_validate(grievance)
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/grievances/{grievance_id}/review",
    response_model=GovernmentReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Government Review Decision",
    description="Submits an official ACCEPT or REJECT review decision for a citizen grievance.",
)
def review_grievance(
    grievance_id: str,
    payload: GovernmentReviewCreate,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GovernmentReviewRead:
    """Process officer review decision."""
    service = GovernmentWorkflowService(db)
    try:
        review = service.review_grievance(
            actor=actor,
            grievance_id=grievance_id,
            decision=payload.decision,
            reason=payload.reason,
            notes=payload.notes,
        )
        return GovernmentReviewRead.model_validate(review)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (InvalidStateTransitionError, RoadXDataError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/grievances/{grievance_id}/work-orders",
    response_model=WorkOrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create & Assign Work Order",
    description="Creates a government-approved work order and assigns it to a contractor.",
)
def create_work_order(
    grievance_id: str,
    payload: WorkOrderCreate,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> WorkOrderRead:
    """Create maintenance work order."""
    service = GovernmentWorkflowService(db)
    try:
        work_order = service.create_and_assign_work_order(
            actor=actor,
            grievance_id=grievance_id,
            payload=payload,
        )
        return WorkOrderRead.model_validate(work_order)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (InvalidStateTransitionError, RoadXDataError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/work-orders",
    response_model=List[WorkOrderRead],
    summary="List Work Orders",
)
def list_work_orders(
    status_filter: Optional[WorkOrderStatus] = Query(default=None, alias="status"),
    priority: Optional[str] = Query(default=None),
    assigned_contractor_id: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[WorkOrderRead]:
    """List maintenance work orders."""
    if not actor.is_government_officer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Actor role '{actor.role.value}' is not authorized.",
        )
    repo = WorkOrderRepository(db)
    items = repo.filter_work_orders(
        status=status_filter,
        priority=priority,
        assigned_contractor_id=assigned_contractor_id,
        skip=skip,
        limit=limit,
    )
    return [WorkOrderRead.model_validate(item) for item in items]


@router.get(
    "/work-orders/{work_order_id}",
    response_model=WorkOrderRead,
    summary="Get Work Order by ID",
)
def get_work_order(
    work_order_id: str,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> WorkOrderRead:
    """Retrieve work order details."""
    if not actor.is_government_officer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Actor role '{actor.role.value}' is not authorized.",
        )
    repo = WorkOrderRepository(db)
    wo = repo.get_by_id(work_order_id)
    if not wo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work order with ID '{work_order_id}' not found.",
        )
    return WorkOrderRead.model_validate(wo)


@router.post(
    "/work-orders/{work_order_id}/verify",
    response_model=GovernmentVerificationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Verify Work Completion",
    description=(
        "Officer completion verification. Only an APPROVE decision transitions the "
        "associated grievance to RESOLVED."
    ),
)
def verify_work_completion(
    work_order_id: str,
    payload: GovernmentVerificationCreate,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GovernmentVerificationRead:
    """Verify work order completion."""
    service = GovernmentWorkflowService(db)
    try:
        verification = service.verify_work_completion(
            actor=actor,
            work_order_id=work_order_id,
            decision=payload.decision,
            notes=payload.notes,
        )
        return GovernmentVerificationRead.model_validate(verification)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (InvalidStateTransitionError, RoadXDataError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/grievances/{grievance_id}/history",
    response_model=List[WorkflowEventRead],
    summary="Get Grievance Workflow Audit History",
)
def get_grievance_history(
    grievance_id: str,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[WorkflowEventRead]:
    """Retrieve full chronological workflow event history for a grievance."""
    service = GovernmentWorkflowService(db)
    try:
        history = service.get_workflow_history(grievance_id)
        return [WorkflowEventRead.model_validate(ev) for ev in history]
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# --- Government Dashboard Endpoints ---

@router.get(
    "/dashboard/overview",
    response_model=GovernmentDashboardOverviewRead,
    summary="Get Government Dashboard Overview Metrics",
    description="Returns aggregate counts of grievances, work orders, priorities, severities, active contractors, and pending verifications.",
)
def get_dashboard_overview(
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GovernmentDashboardOverviewRead:
    """Retrieve overview metrics for government dashboard."""
    service = GovernmentDashboardService(db)
    try:
        return service.get_overview(actor=actor)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/dashboard/grievances",
    response_model=List[GovernmentDashboardGrievanceItemRead],
    summary="Dashboard Grievances List & Search",
    description="Returns filtered and searched grievances list for government dashboard.",
)
def list_dashboard_grievances(
    status_filter: Optional[GrievanceStatus] = Query(default=None, alias="status"),
    issue_category: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[GovernmentDashboardGrievanceItemRead]:
    """Retrieve grievances list with dashboard filters and search."""
    service = GovernmentDashboardService(db)
    try:
        return service.list_dashboard_grievances(
            actor=actor,
            status_filter=status_filter,
            issue_category=issue_category,
            priority=priority,
            severity=severity,
            risk_level=risk_level,
            search=search,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
        )
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/dashboard/grievances/{grievance_id}",
    response_model=GovernmentDashboardGrievanceDetailRead,
    summary="Get Detailed Government Grievance Case View",
    description="Returns full government grievance details including citizen ref, road info, ML outputs, work orders, progress, reviews, and timeline.",
)
def get_dashboard_grievance_detail(
    grievance_id: str,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GovernmentDashboardGrievanceDetailRead:
    """Retrieve detailed government grievance case view."""
    service = GovernmentDashboardService(db)
    try:
        return service.get_dashboard_grievance_detail(actor=actor, grievance_id=grievance_id)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/dashboard/priority-queue",
    response_model=List[GovernmentDashboardPriorityItemRead],
    summary="Get Prioritized Maintenance Queue",
    description="Returns grievances ordered by Phase 8 Maintenance Priority score.",
)
def get_priority_queue(
    min_priority: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[GovernmentDashboardPriorityItemRead]:
    """Retrieve prioritized maintenance queue."""
    service = GovernmentDashboardService(db)
    try:
        return service.get_priority_queue(actor=actor, min_priority=min_priority, skip=skip, limit=limit)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/dashboard/verification-queue",
    response_model=List[GovernmentDashboardVerificationItemRead],
    summary="Get Pending Verification Queue",
    description="Returns work orders awaiting government officer completion verification.",
)
def get_verification_queue(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[GovernmentDashboardVerificationItemRead]:
    """Retrieve pending verification queue."""
    service = GovernmentDashboardService(db)
    try:
        return service.get_verification_queue(actor=actor, skip=skip, limit=limit)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/dashboard/work-orders",
    response_model=List[GovernmentDashboardWorkOrderItemRead],
    summary="Government Work Orders Monitoring",
    description="Returns work order monitoring queue with contractor progress percentages.",
)
def get_dashboard_work_orders(
    status_filter: Optional[WorkOrderStatus] = Query(default=None, alias="status"),
    priority: Optional[str] = Query(default=None),
    assigned_contractor_id: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[GovernmentDashboardWorkOrderItemRead]:
    """Retrieve work orders monitoring queue."""
    service = GovernmentDashboardService(db)
    try:
        return service.get_work_orders_monitoring(
            actor=actor,
            status_filter=status_filter,
            priority=priority,
            assigned_contractor_id=assigned_contractor_id,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/dashboard/contractors",
    response_model=List[GovernmentDashboardContractorSummaryRead],
    summary="Get Contractor Workload & Performance Summary",
    description="Returns read-only summary of contractor workload, active jobs, and average progress.",
)
def get_dashboard_contractors_summary(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[GovernmentDashboardContractorSummaryRead]:
    """Retrieve contractor workload summary metrics."""
    service = GovernmentDashboardService(db)
    try:
        return service.get_contractors_summary(actor=actor, skip=skip, limit=limit)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


# --- Government Road Operations Endpoints ---

@router.post(
    "/road-operations",
    response_model=GovernmentRoadOperationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Municipal Road Operation / Closure",
    description="Publishes a government road operation, closure, or detour restriction.",
)
def create_road_operation(
    payload: RoadOperationCreate,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GovernmentRoadOperationRead:
    """Create road operation."""
    service = RoadOperationService(db)
    try:
        return service.create_operation(actor=actor, payload=payload)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/road-operations",
    response_model=List[GovernmentRoadOperationRead],
    summary="List Government Road Operations",
    description="Returns municipal road operations with status, type, road segment, and date range filtering.",
)
def list_government_road_operations(
    status_filter: Optional[RoadOperationStatus] = Query(default=None, alias="status"),
    operation_type: Optional[RoadOperationType] = Query(default=None),
    road_id: Optional[str] = Query(default=None),
    grievance_id: Optional[str] = Query(default=None),
    work_order_id: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[GovernmentRoadOperationRead]:
    """List road operations for government inspection."""
    service = RoadOperationService(db)
    try:
        return service.list_operations_government(
            actor=actor,
            status_filter=status_filter,
            operation_type=operation_type,
            road_id=road_id,
            grievance_id=grievance_id,
            work_order_id=work_order_id,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/road-operations/{operation_id}",
    response_model=GovernmentRoadOperationRead,
    summary="Get Detailed Government Road Operation",
)
def get_government_road_operation(
    operation_id: str,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GovernmentRoadOperationRead:
    """Retrieve road operation details for government officer."""
    service = RoadOperationService(db)
    try:
        return service.get_operation_government(actor=actor, operation_id=operation_id)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.patch(
    "/road-operations/{operation_id}",
    response_model=GovernmentRoadOperationRead,
    summary="Update Road Operation Details",
)
def update_road_operation(
    operation_id: str,
    payload: RoadOperationUpdate,
    notes: Optional[str] = Query(default=None),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GovernmentRoadOperationRead:
    """Update road operation."""
    service = RoadOperationService(db)
    try:
        return service.update_operation(actor=actor, operation_id=operation_id, payload=payload, notes=notes)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (InvalidStateTransitionError, RoadXDataError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/road-operations/{operation_id}/activate",
    response_model=GovernmentRoadOperationRead,
    summary="Activate Road Operation",
)
def activate_road_operation(
    operation_id: str,
    notes: Optional[str] = Query(default=None),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GovernmentRoadOperationRead:
    """Activate road operation (PLANNED -> ACTIVE)."""
    service = RoadOperationService(db)
    try:
        return service.activate_operation(actor=actor, operation_id=operation_id, notes=notes)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (InvalidStateTransitionError, RoadXDataError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/road-operations/{operation_id}/complete",
    response_model=GovernmentRoadOperationRead,
    summary="Complete Road Operation",
)
def complete_road_operation(
    operation_id: str,
    notes: Optional[str] = Query(default=None),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GovernmentRoadOperationRead:
    """Complete road operation (ACTIVE -> COMPLETED)."""
    service = RoadOperationService(db)
    try:
        return service.complete_operation(actor=actor, operation_id=operation_id, notes=notes)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (InvalidStateTransitionError, RoadXDataError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/road-operations/{operation_id}/cancel",
    response_model=GovernmentRoadOperationRead,
    summary="Cancel Road Operation",
)
def cancel_road_operation(
    operation_id: str,
    notes: Optional[str] = Query(default=None),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GovernmentRoadOperationRead:
    """Cancel road operation."""
    service = RoadOperationService(db)
    try:
        return service.cancel_operation(actor=actor, operation_id=operation_id, notes=notes)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (InvalidStateTransitionError, RoadXDataError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

