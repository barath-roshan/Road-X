"""Pydantic schemas for Maintenance Work Orders."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.models.work_order import WorkOrderStatus
from backend.schemas.evidence import EvidenceRead
from backend.schemas.work_progress import WorkProgressRead


class WorkOrderCreate(BaseModel):
    """Request schema for creating a maintenance work order."""

    title: str = Field(min_length=1, max_length=255, description="Work order summary title")
    description: str = Field(min_length=1, description="Detailed repair scope & engineering instructions")
    priority: Optional[str] = Field(default="MEDIUM", description="Assigned priority: LOW, MEDIUM, HIGH, CRITICAL")
    assigned_contractor_id: Optional[str] = Field(default=None, description="Optional initial contractor assignment UUID")


class WorkOrderUpdate(BaseModel):
    """Request schema for updating a work order."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, min_length=1)
    priority: Optional[str] = Field(default=None)
    status: Optional[WorkOrderStatus] = Field(default=None)
    assigned_contractor_id: Optional[str] = Field(default=None)


class WorkOrderRead(BaseModel):
    """Response schema for WorkOrder entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Work order UUID")
    grievance_id: str = Field(description="Target grievance UUID")
    road_id: Optional[str] = Field(default=None, description="Road segment UUID")
    created_by: Optional[str] = Field(default=None, description="Creating officer UUID")
    assigned_contractor_id: Optional[str] = Field(default=None, description="Assigned contractor UUID")
    title: str = Field(description="Title")
    description: str = Field(description="Description")
    priority: str = Field(description="Priority tier")
    status: WorkOrderStatus = Field(description="Current work order status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class ContractorWorkOrderDetailsRead(WorkOrderRead):
    """Detailed response schema for contractor viewing an assigned work order."""

    grievance_description: Optional[str] = Field(default=None, description="Grievance description text")
    grievance_issue_category: Optional[str] = Field(default=None, description="Grievance category")
    grievance_latitude: Optional[float] = Field(default=None, description="Grievance latitude")
    grievance_longitude: Optional[float] = Field(default=None, description="Grievance longitude")
    road_name: Optional[str] = Field(default=None, description="Physical road name")
    road_code: Optional[str] = Field(default=None, description="Road segment code identifier")
    progress_history: list[WorkProgressRead] = Field(default_factory=list, description="Chronological progress history updates")
    evidence_items: list[EvidenceRead] = Field(default_factory=list, description="Attached evidence items")
    latest_rejection_notes: Optional[str] = Field(default=None, description="Feedback notes from latest government completion rejection, if applicable")
