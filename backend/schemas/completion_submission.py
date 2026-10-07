"""Pydantic schemas for Contractor Completion Submissions."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CompletionSubmissionCreate(BaseModel):
    """Request schema for submitting work order completion for government verification."""

    completion_note: str = Field(min_length=1, description="Summary of work completed by contractor")
    actual_work_summary: Optional[str] = Field(default=None, description="Detailed breakdown of repairs completed")
    evidence_ids: Optional[List[str]] = Field(default=None, description="List of evidence UUIDs attached to this submission")


class CompletionSubmissionRead(BaseModel):
    """Response schema for completion submission acknowledgment."""

    work_order_id: str = Field(description="Work order UUID")
    status: str = Field(description="Work order status after submission (PENDING_VERIFICATION)")
    grievance_status: str = Field(description="Grievance status after submission (PENDING_VERIFICATION)")
    submitted_at: datetime = Field(description="Submission timestamp")
    completion_note: str = Field(description="Completion note")
    message: str = Field(
        default="Work completion submitted successfully. Status updated to PENDING_VERIFICATION. Awaiting government verification."
    )
