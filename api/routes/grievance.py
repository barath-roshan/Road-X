"""API Router for Grievances, Roads, Users, and Database ML Integration."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.config import api_settings
from backend.database import get_db
from backend.models.grievance import GrievanceStatus
from backend.schemas.grievance import GrievanceCreate, GrievanceRead, GrievanceUpdate
from backend.schemas.road import RoadCreate, RoadRead
from backend.schemas.user import UserCreate, UserRead
from backend.schemas.ml_analysis import MLAnalysisRead
from backend.services.grievance_service import GrievanceService
from backend.services.user_service import UserService
from backend.repositories.road_repository import RoadRepository
from backend.services.ml_analysis_service import MLAnalysisService
from ml.common.exceptions import RoadXDataError

HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY)

router = APIRouter(prefix=api_settings.api_prefix, tags=["Backend & Grievances"])


# --- User Endpoints ---

@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Platform User",
    description="Registers a new citizen, officer, or contractor actor user.",
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> UserRead:
    """Register user in backend database."""
    service = UserService(db)
    try:
        user = service.create_user(payload)
        return UserRead.model_validate(user)
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/users/{user_id}",
    response_model=UserRead,
    summary="Get User by ID",
)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
) -> UserRead:
    """Retrieve user entity by ID."""
    service = UserService(db)
    try:
        user = service.get_user(user_id)
        return UserRead.model_validate(user)
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# --- Road Endpoints ---

@router.post(
    "/roads",
    response_model=RoadRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Road Segment",
    description="Registers a new physical road segment.",
)
def create_road_segment(
    payload: RoadCreate,
    db: Session = Depends(get_db),
) -> RoadRead:
    """Create road segment in backend database."""
    repo = RoadRepository(db)
    existing = repo.get_by_segment_id(payload.segment_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Road segment with segment_id '{payload.segment_id}' already exists.",
        )
    from backend.models.road import RoadSegment
    segment = RoadSegment(
        segment_id=payload.segment_id.strip(),
        road_name=payload.road_name.strip(),
        area=payload.area.strip() if payload.area else None,
        latitude=payload.latitude,
        longitude=payload.longitude,
        road_type=payload.road_type,
    )
    saved = repo.add(segment)
    return RoadRead.model_validate(saved)


@router.get(
    "/roads/{road_id}",
    response_model=RoadRead,
    summary="Get Road Segment by ID",
)
def get_road_segment(
    road_id: str,
    db: Session = Depends(get_db),
) -> RoadRead:
    """Retrieve road segment by database ID or string segment_id."""
    repo = RoadRepository(db)
    road = repo.get_by_id(road_id) or repo.get_by_segment_id(road_id)
    if not road:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Road segment '{road_id}' not found.",
        )
    return RoadRead.model_validate(road)


# --- Grievance Endpoints ---

@router.post(
    "/grievances",
    response_model=GrievanceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Citizen Grievance",
    description="Creates and persists a new citizen complaint report.",
)
def create_grievance(
    payload: GrievanceCreate,
    db: Session = Depends(get_db),
) -> GrievanceRead:
    """Persist citizen grievance in backend database."""
    service = GrievanceService(db)
    try:
        grievance = service.create_grievance(payload)
        return GrievanceRead.model_validate(grievance)
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/grievances/{grievance_id}",
    response_model=GrievanceRead,
    summary="Get Grievance by ID",
)
def get_grievance(
    grievance_id: str,
    db: Session = Depends(get_db),
) -> GrievanceRead:
    """Fetch stored grievance report by ID."""
    service = GrievanceService(db)
    try:
        grievance = service.get_grievance(grievance_id)
        return GrievanceRead.model_validate(grievance)
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/grievances",
    response_model=List[GrievanceRead],
    summary="List and Filter Grievances",
)
def list_grievances(
    status_filter: Optional[GrievanceStatus] = Query(default=None, alias="status"),
    issue_category: Optional[str] = Query(default=None),
    road_id: Optional[str] = Query(default=None),
    citizen_id: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[GrievanceRead]:
    """Query stored grievances with filtering and pagination."""
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


@router.patch(
    "/grievances/{grievance_id}",
    response_model=GrievanceRead,
    summary="Update Grievance Attributes",
)
def update_grievance(
    grievance_id: str,
    payload: GrievanceUpdate,
    db: Session = Depends(get_db),
) -> GrievanceRead:
    """Update grievance record details or status."""
    service = GrievanceService(db)
    try:
        updated = service.update_grievance(grievance_id, payload)
        return GrievanceRead.model_validate(updated)
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# --- ML Analysis Integration Endpoints ---

@router.post(
    "/grievances/{grievance_id}/analysis",
    response_model=MLAnalysisRead,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger and Persist ML Analysis for Grievance",
    description="Explicitly executes the Phase 9/10 ML pipeline for a grievance and stores the result in database.",
)
def analyze_and_store_grievance(
    grievance_id: str,
    db: Session = Depends(get_db),
) -> MLAnalysisRead:
    """Run ML pipeline for grievance and save analysis result."""
    service = MLAnalysisService(db)
    try:
        record = service.analyze_and_store_grievance(grievance_id)
        return MLAnalysisRead.model_validate(record)
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML Analysis execution or persistence failed: {e}",
        ) from e


@router.get(
    "/grievances/{grievance_id}/analysis",
    response_model=List[MLAnalysisRead],
    summary="Get Stored ML Analyses for Grievance",
)
def get_grievance_analyses(
    grievance_id: str,
    db: Session = Depends(get_db),
) -> List[MLAnalysisRead]:
    """Retrieve all historical ML analysis records for a grievance."""
    service = MLAnalysisService(db)
    try:
        records = service.get_analyses_for_grievance(grievance_id)
        return [MLAnalysisRead.model_validate(r) for r in records]
    except RoadXDataError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
