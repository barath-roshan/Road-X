"""Pydantic schemas for Government Review decisions."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.models.government_review import ReviewDecision


class GovernmentReviewCreate(BaseModel):
    """Request schema for submitting a government review decision."""

    decision: ReviewDecision = Field(description="Review decision: ACCEPT or REJECT")
    reason: Optional[str] = Field(default=None, description="Required rejection reason")
    notes: Optional[str] = Field(default=None, description="Optional officer administrative notes")


class GovernmentReviewRead(BaseModel):
    """Response schema for GovernmentReview entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique review record UUID")
    grievance_id: str = Field(description="Grievance UUID")
    officer_id: Optional[str] = Field(default=None, description="Reviewing officer UUID")
    decision: ReviewDecision = Field(description="Review decision")
    reason: Optional[str] = Field(default=None, description="Rejection reason if applicable")
    notes: Optional[str] = Field(default=None, description="Officer notes")
    created_at: datetime = Field(description="Timestamp of review decision")
