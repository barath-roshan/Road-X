"""Pydantic schemas for Government Verification decisions."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.models.government_verification import VerificationDecision


class GovernmentVerificationCreate(BaseModel):
    """Request schema for officer completion verification."""

    decision: VerificationDecision = Field(description="Verification decision: APPROVE or REJECT")
    notes: Optional[str] = Field(default=None, description="Officer verification remarks or rejection reason")


class GovernmentVerificationRead(BaseModel):
    """Response schema for GovernmentVerification entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Verification UUID")
    work_order_id: str = Field(description="Work order UUID")
    grievance_id: str = Field(description="Grievance UUID")
    officer_id: Optional[str] = Field(default=None, description="Verifying officer UUID")
    decision: VerificationDecision = Field(description="Verification decision")
    notes: Optional[str] = Field(default=None, description="Officer notes")
    created_at: datetime = Field(description="Timestamp of verification decision")
