"""Pydantic schemas for workflow event history tracing."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.models.workflow_event import WorkflowEventType


class WorkflowEventRead(BaseModel):
    """Response schema for WorkflowEvent entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Event UUID")
    grievance_id: str = Field(description="Grievance UUID")
    work_order_id: Optional[str] = Field(default=None, description="Work order UUID")
    actor_id: Optional[str] = Field(default=None, description="Actor UUID")
    actor_role: Optional[str] = Field(default=None, description="Actor role")
    event_type: WorkflowEventType = Field(description="Event classification type")
    old_status: Optional[str] = Field(default=None, description="Previous status")
    new_status: Optional[str] = Field(default=None, description="New status")
    notes: Optional[str] = Field(default=None, description="Event notes")
    created_at: datetime = Field(description="Event creation timestamp")
