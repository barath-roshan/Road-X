"""Pydantic schemas for Contractor Dashboard API operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.models.work_order import WorkOrderStatus
from backend.schemas.evidence import EvidenceRead
from backend.schemas.work_progress import WorkProgressRead
from backend.schemas.workflow_event import WorkflowEventRead


class ContractorDashboardOverviewRead(BaseModel):
    """Overview statistics summary for the authenticated contractor."""

    model_config = ConfigDict(from_attributes=True)

    total_assigned: int = Field(description="Total work orders assigned to current contractor")
    assigned: int = Field(description="Count of work orders in ASSIGNED status")
    in_progress: int = Field(description="Count of work orders in IN_PROGRESS status")
    pending_verification: int = Field(description="Count of work orders in PENDING_VERIFICATION status")
    completed: int = Field(description="Count of work orders in COMPLETED status")
    rework: int = Field(description="Count of work orders requiring rework after government rejection")
    average_progress: float = Field(description="Average progress percentage across contractor's work orders")


class ContractorDashboardWorkOrderItemRead(BaseModel):
    """Summary item for work orders assigned to contractor."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Work order UUID")
    grievance_id: str = Field(description="Associated grievance UUID")
    road_id: Optional[str] = Field(default=None, description="Road segment UUID")
    road_name: Optional[str] = Field(default=None, description="Road segment name")
    title: str = Field(description="Work order title")
    description: str = Field(description="Work order description")
    priority: str = Field(description="Priority level (LOW, MEDIUM, HIGH, CRITICAL)")
    status: WorkOrderStatus = Field(description="Current work order status")
    progress_percentage: int = Field(default=0, ge=0, le=100, description="Current latest progress percentage")
    rework_required: bool = Field(default=False, description="True if rejected by government and back in IN_PROGRESS")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class ContractorDashboardWorkOrderDetailRead(BaseModel):
    """Contractor-safe detailed view of an assigned work order."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Work order UUID")
    grievance_id: str = Field(description="Associated grievance UUID")
    road_id: Optional[str] = Field(default=None, description="Road segment UUID")
    title: str = Field(description="Work order title")
    description: str = Field(description="Work order description")
    priority: str = Field(description="Priority level")
    status: WorkOrderStatus = Field(description="Current work order status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    # Location & Road info
    road_name: Optional[str] = Field(default=None, description="Road segment name")
    road_code: Optional[str] = Field(default=None, description="Road segment code/identifier")
    latitude: Optional[float] = Field(default=None, description="Grievance latitude")
    longitude: Optional[float] = Field(default=None, description="Grievance longitude")

    # Grievance reference (contractor-safe)
    grievance_description: Optional[str] = Field(default=None, description="Citizen grievance description")
    grievance_issue_category: Optional[str] = Field(default=None, description="Issue category")
    grievance_severity: Optional[str] = Field(default=None, description="ML severity level")
    grievance_risk_level: Optional[str] = Field(default=None, description="ML failure risk level")
    grievance_priority: Optional[str] = Field(default=None, description="ML priority level")

    # Progress & Evidence
    current_progress: int = Field(default=0, ge=0, le=100, description="Latest progress percentage")
    progress_history: List[WorkProgressRead] = Field(default_factory=list, description="Chronological progress updates")
    completion_evidence: List[EvidenceRead] = Field(default_factory=list, description="Attached evidence metadata")

    # Government Feedback & Verification
    government_verification_status: Optional[str] = Field(default=None, description="Latest verification decision (APPROVE/REJECT)")
    rework_required: bool = Field(default=False, description="True if latest verification decision was REJECT")
    latest_rejection_notes: Optional[str] = Field(default=None, description="Government officer rejection feedback notes")
    rejection_timestamp: Optional[datetime] = Field(default=None, description="Timestamp of rejection")

    # Workflow Audit Timeline
    timeline: List[WorkflowEventRead] = Field(default_factory=list, description="Contractor-safe workflow timeline")


class ContractorDashboardPendingVerificationItemRead(BaseModel):
    """Work order awaiting government completion verification."""

    model_config = ConfigDict(from_attributes=True)

    work_order_id: str = Field(description="Work order UUID")
    grievance_id: str = Field(description="Grievance UUID")
    title: str = Field(description="Work order title")
    priority: str = Field(description="Priority level")
    progress_percentage: int = Field(default=100, description="Progress percentage (100%)")
    completion_submitted_at: datetime = Field(description="Completion submission timestamp")
    evidence: List[EvidenceRead] = Field(default_factory=list, description="Attached completion evidence files")


class ContractorDashboardReworkItemRead(BaseModel):
    """Work order rejected by government requiring contractor rework."""

    model_config = ConfigDict(from_attributes=True)

    work_order_id: str = Field(description="Work order UUID")
    grievance_id: str = Field(description="Grievance UUID")
    title: str = Field(description="Work order title")
    priority: str = Field(description="Priority level")
    current_status: WorkOrderStatus = Field(description="Current work order status (IN_PROGRESS)")
    rejection_message: str = Field(description="Government officer rejection feedback message")
    rejection_timestamp: Optional[datetime] = Field(default=None, description="Rejection timestamp")
    current_progress: int = Field(description="Current progress percentage")


class ContractorDashboardWorkloadSummaryRead(BaseModel):
    """Personal workload summary for the requesting contractor."""

    model_config = ConfigDict(from_attributes=True)

    total_assignments: int = Field(description="Total work orders assigned to contractor")
    active_assignments: int = Field(description="Work orders actively assigned or in progress")
    pending_verification: int = Field(description="Work orders awaiting government verification")
    rework_required: int = Field(description="Work orders requiring rework")
    resolved_completed: int = Field(description="Work orders completed and verified")
    average_completion_percentage: float = Field(description="Average progress percentage across contractor's work orders")
