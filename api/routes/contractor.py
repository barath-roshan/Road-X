"""API Router for Contractor Workflow operations."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.config import api_settings
from api.dependencies import get_current_actor
from backend.database import get_db
from backend.models.work_order import WorkOrderStatus
from backend.repositories.work_order_repository import WorkOrderRepository
from backend.schemas.completion_submission import CompletionSubmissionCreate, CompletionSubmissionRead
from backend.schemas.evidence import EvidenceCreate, EvidenceRead
from backend.schemas.work_order import ContractorWorkOrderDetailsRead, WorkOrderRead
from backend.schemas.work_progress import WorkProgressCreate, WorkProgressRead
from backend.schemas.contractor_dashboard import (
    ContractorDashboardOverviewRead,
    ContractorDashboardWorkOrderItemRead,
    ContractorDashboardWorkOrderDetailRead,
    ContractorDashboardPendingVerificationItemRead,
    ContractorDashboardReworkItemRead,
    ContractorDashboardWorkloadSummaryRead,
)
from backend.security import UserContext, UnauthorizedError, InvalidStateTransitionError
from backend.services.contractor_dashboard_service import ContractorDashboardService
from backend.services.contractor_workflow_service import ContractorWorkflowService
from ml.common.exceptions import RoadXDataError

router = APIRouter(prefix=f"{api_settings.api_prefix}/contractor", tags=["Contractor Workflow"])


@router.get(
    "/work-orders",
    response_model=List[WorkOrderRead],
    summary="List Assigned Work Orders for Contractor",
    description="Returns work orders assigned to the authenticated contractor.",
)
def list_assigned_work_orders(
    status_filter: Optional[WorkOrderStatus] = Query(default=None, alias="status"),
    priority: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[WorkOrderRead]:
    """Retrieve work orders assigned to the current contractor."""
    service = ContractorWorkflowService(db)
    try:
        work_orders = service.get_assigned_work_orders(
            actor=actor,
            status_filter=status_filter,
            priority_filter=priority,
            skip=skip,
            limit=limit,
        )
        return [WorkOrderRead.model_validate(wo) for wo in work_orders]
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/work-orders/{work_order_id}",
    response_model=ContractorWorkOrderDetailsRead,
    summary="Get Assigned Work Order Details",
    description="Returns detailed work order, grievance description, road info, progress history, and rejection feedback.",
)
def get_assigned_work_order_details(
    work_order_id: str,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> ContractorWorkOrderDetailsRead:
    """Retrieve work order details for assigned contractor."""
    service = ContractorWorkflowService(db)
    try:
        return service.get_work_order_details(actor=actor, work_order_id=work_order_id)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/work-orders/{work_order_id}/accept",
    response_model=WorkOrderRead,
    summary="Acknowledge Work Order Assignment",
    description="Contractor acknowledges receipt of an assigned work order.",
)
def acknowledge_work_order(
    work_order_id: str,
    notes: Optional[str] = Query(default=None),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> WorkOrderRead:
    """Acknowledge assigned work order."""
    service = ContractorWorkflowService(db)
    try:
        wo = service.acknowledge_work_order(actor=actor, work_order_id=work_order_id, notes=notes)
        return WorkOrderRead.model_validate(wo)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/work-orders/{work_order_id}/start",
    response_model=WorkOrderRead,
    summary="Start Work Order Repairs",
    description="Transitions work order status from ASSIGNED to IN_PROGRESS.",
)
def start_work_order(
    work_order_id: str,
    notes: Optional[str] = Query(default=None),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> WorkOrderRead:
    """Start maintenance work."""
    service = ContractorWorkflowService(db)
    try:
        wo = service.start_work_order(actor=actor, work_order_id=work_order_id, notes=notes)
        return WorkOrderRead.model_validate(wo)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (InvalidStateTransitionError, RoadXDataError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/work-orders/{work_order_id}/progress",
    response_model=WorkProgressRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log Work Progress Update",
    description="Log percentage completion update (0-100%). Does not resolve or complete work order.",
)
def update_work_progress(
    work_order_id: str,
    payload: WorkProgressCreate,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> WorkProgressRead:
    """Record a work progress update."""
    service = ContractorWorkflowService(db)
    try:
        progress = service.update_progress(
            actor=actor,
            work_order_id=work_order_id,
            progress_percentage=payload.progress_percentage,
            note=payload.note,
        )
        return WorkProgressRead.model_validate(progress)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (InvalidStateTransitionError, RoadXDataError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/work-orders/{work_order_id}/evidence",
    response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Attach Completion Evidence Metadata",
    description="Attach repair photo or proof document metadata to the work order.",
)
def attach_work_order_evidence(
    work_order_id: str,
    payload: EvidenceCreate,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> EvidenceRead:
    """Attach evidence metadata to a work order."""
    service = ContractorWorkflowService(db)
    try:
        evidence = service.attach_evidence(
            actor=actor,
            work_order_id=work_order_id,
            file_name=payload.file_name,
            file_type=payload.file_type,
            storage_path=payload.storage_path,
            file_size_bytes=payload.file_size_bytes,
        )
        return EvidenceRead.model_validate(evidence)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/work-orders/{work_order_id}/submit",
    response_model=CompletionSubmissionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Work Completion for Government Verification",
    description="Transitions WorkOrder and Grievance to PENDING_VERIFICATION. Requires government officer verification to resolve.",
)
def submit_work_completion(
    work_order_id: str,
    payload: CompletionSubmissionCreate,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CompletionSubmissionRead:
    """Submit completed work order for government verification."""
    service = ContractorWorkflowService(db)
    try:
        return service.submit_completion(actor=actor, work_order_id=work_order_id, payload=payload)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (InvalidStateTransitionError, RoadXDataError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# --- Contractor Dashboard Endpoints ---

@router.get(
    "/dashboard/overview",
    response_model=ContractorDashboardOverviewRead,
    summary="Get Contractor Dashboard Overview Statistics",
    description="Returns aggregate workload metrics for the authenticated contractor.",
)
def get_contractor_dashboard_overview(
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> ContractorDashboardOverviewRead:
    """Retrieve overview metrics for current contractor dashboard."""
    service = ContractorDashboardService(db)
    try:
        return service.get_overview(actor=actor)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/dashboard/work-orders",
    response_model=List[ContractorDashboardWorkOrderItemRead],
    summary="List Assigned Work Orders for Contractor Dashboard",
    description="Returns assigned work orders with status, priority, date filtering, sorting, and pagination.",
)
def list_contractor_dashboard_work_orders(
    status_filter: Optional[WorkOrderStatus] = Query(default=None, alias="status"),
    priority: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[ContractorDashboardWorkOrderItemRead]:
    """Retrieve work orders for current contractor dashboard."""
    service = ContractorDashboardService(db)
    try:
        return service.list_assigned_work_orders(
            actor=actor,
            status_filter=status_filter,
            priority=priority,
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
    "/dashboard/work-orders/{work_order_id}",
    response_model=ContractorDashboardWorkOrderDetailRead,
    summary="Get Detailed Contractor Work Order View",
    description="Returns detailed contractor-safe work order information, road details, grievance reference, progress history, completion evidence, rejection feedback, and workflow timeline.",
)
def get_contractor_dashboard_work_order_detail(
    work_order_id: str,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> ContractorDashboardWorkOrderDetailRead:
    """Retrieve detailed work order view for current contractor."""
    service = ContractorDashboardService(db)
    try:
        return service.get_work_order_detail(actor=actor, work_order_id=work_order_id)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/dashboard/pending-verification",
    response_model=List[ContractorDashboardPendingVerificationItemRead],
    summary="Get Work Orders Pending Government Verification",
    description="Returns assigned work orders awaiting government officer completion verification.",
)
def get_contractor_dashboard_pending_verification(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[ContractorDashboardPendingVerificationItemRead]:
    """Retrieve pending verification work orders for current contractor."""
    service = ContractorDashboardService(db)
    try:
        return service.get_pending_verification_queue(actor=actor, skip=skip, limit=limit)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/dashboard/rework",
    response_model=List[ContractorDashboardReworkItemRead],
    summary="Get Contractor Rework Queue",
    description="Returns work orders rejected by government officer requiring contractor rework and action.",
)
def get_contractor_dashboard_rework(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[ContractorDashboardReworkItemRead]:
    """Retrieve rework queue for current contractor."""
    service = ContractorDashboardService(db)
    try:
        return service.get_rework_queue(actor=actor, skip=skip, limit=limit)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/dashboard/workload",
    response_model=ContractorDashboardWorkloadSummaryRead,
    summary="Get Contractor Personal Workload Statistics",
    description="Returns summary metrics of assigned, active, pending verification, rework, resolved, and average progress for current contractor.",
)
def get_contractor_dashboard_workload(
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> ContractorDashboardWorkloadSummaryRead:
    """Retrieve personal workload metrics for current contractor."""
    service = ContractorDashboardService(db)
    try:
        return service.get_workload_summary(actor=actor)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e

