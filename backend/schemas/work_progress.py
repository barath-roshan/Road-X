"""Pydantic schemas for Contractor Work Progress updates."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class WorkProgressCreate(BaseModel):
    """Request schema for logging progress on a work order."""

    progress_percentage: int = Field(ge=0, le=100, description="Work progress percentage (0-100)")
    note: Optional[str] = Field(default=None, description="Detailed progress or status note")


class WorkProgressRead(BaseModel):
    """Response schema for WorkProgress entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Progress entry UUID")
    work_order_id: str = Field(description="Associated work order UUID")
    contractor_id: str = Field(description="Contractor user UUID")
    progress_percentage: int = Field(description="Progress percentage (0-100)")
    note: Optional[str] = Field(default=None, description="Progress note")
    created_at: datetime = Field(description="Creation timestamp")
