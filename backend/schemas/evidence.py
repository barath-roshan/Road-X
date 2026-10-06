"""Pydantic schemas for Grievance visual evidence metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceBase(BaseModel):
    """Base fields for Evidence payload."""

    file_name: str = Field(min_length=1, max_length=255, description="Uploaded file name")
    file_type: str = Field(min_length=1, max_length=50, description="MIME content type")
    storage_path: str = Field(min_length=1, max_length=512, description="Local or object storage path reference")
    file_size_bytes: Optional[int] = Field(default=None, ge=0, description="File size in bytes")


class EvidenceCreate(EvidenceBase):
    """Request schema for attaching evidence to a grievance."""

    grievance_id: str = Field(description="Target grievance UUID")


class EvidenceRead(EvidenceBase):
    """Response schema for Evidence entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique evidence UUID identifier")
    grievance_id: str = Field(description="Target grievance UUID")
    uploaded_at: datetime = Field(description="Upload timestamp")
