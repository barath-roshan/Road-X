"""Pydantic schemas for physical road segments."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoadBase(BaseModel):
    """Base fields for RoadSegment payload."""

    segment_id: str = Field(
        min_length=1, max_length=100, description="Unique road segment identifier (e.g. SEG-MH-4001)"
    )
    road_name: str = Field(min_length=1, max_length=255, description="Street or highway name")
    area: Optional[str] = Field(default=None, max_length=100, description="Locality / municipal zone")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Centroid latitude")
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Centroid longitude")
    road_type: Optional[str] = Field(
        default=None, max_length=50, description="Road classification (e.g. URBAN_ARTERIAL)"
    )

    @field_validator("segment_id", "road_name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace from identifier and name strings."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or whitespace only.")
        return stripped


class RoadCreate(RoadBase):
    """Request schema for creating a road segment."""

    pass


class RoadUpdate(BaseModel):
    """Request schema for updating road segment attributes."""

    road_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    area: Optional[str] = Field(default=None, max_length=100)
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    road_type: Optional[str] = Field(default=None, max_length=50)


class RoadRead(RoadBase):
    """Response schema for RoadSegment entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique UUID string identifier")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
