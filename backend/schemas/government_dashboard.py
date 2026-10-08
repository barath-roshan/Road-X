"""Pydantic schemas for Government Dashboard API operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.models.grievance import GrievanceStatus
from backend.models.work_order import WorkOrderStatus
from backend.schemas.evidence import EvidenceRead
from backend.schemas.government_review import GovernmentReviewRead
from backend.schemas.government_verification import GovernmentVerificationRead
from backend.schemas.user import UserRead
from backend.schemas.work_order import WorkOrderRead
from backend.schemas.work_progress import WorkProgressRead
from backend.schemas.workflow_event import WorkflowEventRead


class GovernmentDashboardOverviewRead(BaseModel):
    """Aggregate dashboard metrics summary for government officers."""

    model_config = ConfigDict(from_attributes=True)

    total_grievances: int = Field(description="Total count of recorded grievances")
    status_counts: Dict[str, int] = Field(description="Breakdown of grievances by lifecycle status")
    priority_counts: Dict[str, int] = Field(description="Breakdown of grievances by ML priority level")
    severity_counts: Dict[str, int] = Field(description="Breakdown of grievances by ML damage severity level")
    work_order_counts: Dict[str, int] = Field(description="Breakdown of work orders by lifecycle status")
    active_contractors_count: int = Field(description="Count of active contractors in system")
    pending_verifications_count: int = Field(description="Count of work orders awaiting government verification")


class GovernmentDashboardGrievanceItemRead(BaseModel):
    """Dashboard-oriented grievance summary item."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Grievance UUID")
    citizen_id: str = Field(description="Citizen user ID")
    citizen_name: Optional[str] = Field(default=None, description="Citizen user name")
    road_id: Optional[str] = Field(default=None, description="Road segment ID")
    road_name: Optional[str] = Field(default=None, description="Road segment name")
    issue_category: str = Field(description="Issue category classification")
    description: str = Field(description="Citizen issue description")
    latitude: float = Field(description="Latitude coordinate")
    longitude: float = Field(description="Longitude coordinate")
    status: GrievanceStatus = Field(description="Current grievance lifecycle status")
    created_at: datetime = Field(description="Submission timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    priority: Optional[str] = Field(default=None, description="ML priority level")
    severity: Optional[str] = Field(default=None, description="ML severity level")
    risk_level: Optional[str] = Field(default=None, description="ML risk level")
    work_order_status: Optional[str] = Field(default=None, description="Associated work order status")
    assigned_contractor_name: Optional[str] = Field(default=None, description="Assigned contractor name")


class GovernmentDashboardGrievanceDetailRead(BaseModel):
    """Comprehensive government-side detailed view of a grievance case."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Grievance UUID")
    citizen_id: str = Field(description="Citizen user ID")
    citizen_name: Optional[str] = Field(default=None, description="Citizen name")
    citizen_email: Optional[str] = Field(default=None, description="Citizen email")
    road_id: Optional[str] = Field(default=None, description="Road segment ID")
    road_name: Optional[str] = Field(default=None, description="Road segment name")
    road_code: Optional[str] = Field(default=None, description="Road segment string ID")
    issue_category: str = Field(description="Issue category")
    description: str = Field(description="Description text")
    latitude: float = Field(description="Latitude")
    longitude: float = Field(description="Longitude")
    status: GrievanceStatus = Field(description="Grievance status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last updated timestamp")

    evidence_items: List[EvidenceRead] = Field(default_factory=list, description="Attached evidence items")
    ml_analysis: Optional[Dict[str, Any]] = Field(default=None, description="High-level ML decision support dict")
    work_order: Optional[WorkOrderRead] = Field(default=None, description="Associated work order details")
    assigned_contractor: Optional[UserRead] = Field(default=None, description="Assigned contractor details")
    progress_history: List[WorkProgressRead] = Field(default_factory=list, description="Progress update logs")
    verifications: List[GovernmentVerificationRead] = Field(default_factory=list, description="Verification records")
    reviews: List[GovernmentReviewRead] = Field(default_factory=list, description="Review records")
    timeline: List[WorkflowEventRead] = Field(default_factory=list, description="Chronological audit history")


class GovernmentDashboardPriorityItemRead(BaseModel):
    """Prioritized maintenance queue item using Phase 8 priority results."""

    model_config = ConfigDict(from_attributes=True)

    grievance_id: str = Field(description="Grievance UUID")
    road_name: Optional[str] = Field(default=None, description="Road segment name")
    issue_category: str = Field(description="Issue category")
    description: str = Field(description="Grievance description")
    status: GrievanceStatus = Field(description="Grievance status")
    priority_score: Optional[float] = Field(default=None, description="Priority score (0-100)")
    priority_level: str = Field(description="Priority level (LOW, MEDIUM, HIGH, CRITICAL)")
    severity_level: Optional[str] = Field(default=None, description="Damage severity level")
    risk_level: Optional[str] = Field(default=None, description="Failure risk level")
    estimated_time_to_failure_days: Optional[float] = Field(default=None, description="Estimated remaining lifespan in days")
    reasons: List[str] = Field(default_factory=list, description="Evidence reasons generated by ML priority engine")
    created_at: datetime = Field(description="Submission timestamp")


class GovernmentDashboardVerificationItemRead(BaseModel):
    """Work order item pending government completion verification."""

    model_config = ConfigDict(from_attributes=True)

    work_order_id: str = Field(description="Work order UUID")
    grievance_id: str = Field(description="Grievance UUID")
    grievance_description: str = Field(description="Grievance description")
    road_name: Optional[str] = Field(default=None, description="Road segment name")
    contractor_id: str = Field(description="Assigned contractor ID")
    contractor_name: Optional[str] = Field(default=None, description="Assigned contractor name")
    work_order_title: str = Field(description="Work order title")
    priority: str = Field(description="Work order priority")
    submitted_at: datetime = Field(description="Completion submission timestamp")
    latest_progress_note: Optional[str] = Field(default=None, description="Latest progress note")
    evidence_items: List[EvidenceRead] = Field(default_factory=list, description="Completion evidence files")


class GovernmentDashboardWorkOrderItemRead(BaseModel):
    """Government work-order monitoring item."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Work order UUID")
    grievance_id: str = Field(description="Grievance UUID")
    road_name: Optional[str] = Field(default=None, description="Road segment name")
    assigned_contractor_id: Optional[str] = Field(default=None, description="Assigned contractor ID")
    contractor_name: Optional[str] = Field(default=None, description="Assigned contractor name")
    title: str = Field(description="Work order title")
    description: str = Field(description="Work order description")
    priority: str = Field(description="Work order priority")
    status: WorkOrderStatus = Field(description="Work order status")
    current_progress_percentage: int = Field(default=0, ge=0, le=100, description="Current progress percentage")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last updated timestamp")


class GovernmentDashboardContractorSummaryRead(BaseModel):
    """Summary metrics of contractor workload and progress performance."""

    model_config = ConfigDict(from_attributes=True)

    contractor_id: str = Field(description="Contractor user UUID")
    contractor_name: str = Field(description="Contractor name")
    contractor_email: str = Field(description="Contractor email")
    assigned_work_orders_count: int = Field(description="Total work orders assigned to contractor")
    in_progress_count: int = Field(description="Work orders currently in progress")
    pending_verification_count: int = Field(description="Work orders awaiting verification")
    completed_count: int = Field(description="Work orders completed and verified")
    average_progress_percentage: float = Field(description="Average progress percentage across active work orders")
