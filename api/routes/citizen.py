"""API Router for Citizen Platform operations (/api/v1/citizen/...)."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.config import api_settings
from api.dependencies import get_current_actor
from backend.database import get_db
from backend.models.grievance import GrievanceStatus
from backend.models.road_operation import RoadOperationStatus, RoadOperationType
from backend.schemas.citizen import (
    CitizenGrievanceCreate,
    CitizenGrievanceDetailsRead,
)
from backend.schemas.evidence import EvidenceCreate, EvidenceRead
from backend.schemas.grievance import GrievanceRead
from backend.schemas.road_operation import CitizenRoadOperationRead
from backend.security import UserContext, UnauthorizedError, InvalidStateTransitionError
from backend.services.citizen_workflow_service import CitizenWorkflowService
from backend.services.road_operation_service import RoadOperationService
from ml.common.exceptions import RoadXDataError

router = APIRouter(prefix=f"{api_settings.api_prefix}/citizen", tags=["Citizen Platform"])

# ... existing routes ...


@router.post(
    "/grievances",
    response_model=GrievanceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Citizen Grievance Report",
    description="Creates a new citizen grievance report with initial status SUBMITTED.",
)
def create_citizen_grievance(
    payload: CitizenGrievanceCreate,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GrievanceRead:
    """Submit a citizen grievance report."""
    service = CitizenWorkflowService(db)
    try:
        grievance = service.create_grievance(actor=actor, payload=payload)
        return GrievanceRead.model_validate(grievance)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/grievances",
    response_model=List[GrievanceRead],
    summary="List Citizen's Own Grievances",
    description="Returns all grievances submitted by the requesting citizen.",
)
def list_citizen_grievances(
    status_filter: Optional[GrievanceStatus] = Query(default=None, alias="status"),
    issue_category: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> List[GrievanceRead]:
    """Retrieve grievances submitted by the current citizen."""
    service = CitizenWorkflowService(db)
    try:
        items = service.list_citizen_grievances(
            actor=actor,
            status_filter=status_filter,
            issue_category=issue_category,
            skip=skip,
            limit=limit,
        )
        return [GrievanceRead.model_validate(item) for item in items]
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/grievances/{grievance_id}",
    response_model=CitizenGrievanceDetailsRead,
    summary="Get Citizen Grievance Details & Timeline",
    description="Returns detailed citizen-safe grievance view, road info, progress history, timeline, and ML summary.",
)
def get_citizen_grievance_details(
    grievance_id: str,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CitizenGrievanceDetailsRead:
    """Retrieve citizen grievance details and progress timeline."""
    service = CitizenWorkflowService(db)
    try:
        return service.get_citizen_grievance_details(actor=actor, grievance_id=grievance_id)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/grievances/{grievance_id}/evidence",
    response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Attach Citizen Evidence Metadata",
    description="Attach additional evidence/photo metadata to an owned citizen grievance report.",
)
def attach_citizen_evidence(
    grievance_id: str,
    payload: EvidenceCreate,
    actor: UserContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> EvidenceRead:
    """Attach evidence metadata to a grievance."""
    service = CitizenWorkflowService(db)
    try:
        evidence = service.attach_evidence(
            actor=actor,
            grievance_id=grievance_id,
            file_name=payload.file_name,
            file_type=payload.file_type,
            storage_path=payload.storage_path,
            file_size_bytes=payload.file_size_bytes,
        )
        return EvidenceRead.model_validate(evidence)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (InvalidStateTransitionError, RoadXDataError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# --- Citizen Public Road Operations Endpoints ---

@router.get(
    "/road-operations",
    response_model=List[CitizenRoadOperationRead],
    summary="List Active & Planned Public Road Operations",
    description="Returns public active and planned municipal road closures, restrictions, and detour routes.",
)
def list_citizen_road_operations(
    status_filter: Optional[RoadOperationStatus] = Query(default=None, alias="status"),
    road_id: Optional[str] = Query(default=None),
    operation_type: Optional[RoadOperationType] = Query(default=None),
    active_only: bool = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[CitizenRoadOperationRead]:
    """Retrieve public active/planned road operations."""
    service = RoadOperationService(db)
    return service.list_operations_citizen(
        status_filter=status_filter,
        road_id=road_id,
        operation_type=operation_type,
        active_only=active_only,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/road-operations/{operation_id}",
    response_model=CitizenRoadOperationRead,
    summary="Get Detailed Public Road Operation & Detour Information",
    description="Returns public details for a road operation including reason, status, schedule, and alternative route detour instructions.",
)
def get_citizen_road_operation(
    operation_id: str,
    db: Session = Depends(get_db),
) -> CitizenRoadOperationRead:
    """Retrieve public road operation details."""
    service = RoadOperationService(db)
    try:
        return service.get_operation_citizen(operation_id=operation_id)
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

