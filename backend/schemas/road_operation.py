"""Pydantic schemas for Road Operations API operations."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.models.road_operation import RoadOperationStatus, RoadOperationType


class RoadOperationCreate(BaseModel):
    """Payload schema for creating a new road operation."""

    model_config = ConfigDict(from_attributes=True)

    title: str = Field(min_length=3, max_length=255, description="Short title for road operation / closure")
    description: str = Field(min_length=5, description="Detailed description of operation")
    reason: str = Field(min_length=3, description="Reason for closure/restriction")
    operation_type: RoadOperationType = Field(default=RoadOperationType.ROAD_CLOSURE, description="Type of operation")
    road_id: Optional[str] = Field(default=None, description="Affected primary road segment ID")
    grievance_id: Optional[str] = Field(default=None, description="Optional associated grievance ID")
    work_order_id: Optional[str] = Field(default=None, description="Optional associated work order ID")
    start_time: datetime = Field(description="Operation start timestamp")
    expected_end_time: datetime = Field(description="Expected completion timestamp")
    status: Optional[RoadOperationStatus] = Field(default=RoadOperationStatus.PLANNED, description="Initial status")

    # Alternative Route Information
    alternative_route_name: Optional[str] = Field(default=None, description="Name/title of alternative detour route")
    alternative_route_instructions: Optional[str] = Field(default=None, description="Detour instructions")
    alternative_road_id: Optional[str] = Field(default=None, description="Alternative road segment ID")
    alternative_distance_km: Optional[float] = Field(default=None, ge=0.0, description="Detour distance in kilometers")

    @field_validator("expected_end_time")

    @classmethod
    def validate_end_after_start(cls, expected_end_time: datetime, info) -> datetime:
        """Validate expected_end_time is after start_time."""
        start_time = info.data.get("start_time")
        if start_time and expected_end_time <= start_time:
            raise ValueError("expected_end_time must be strictly after start_time.")
        return expected_end_time


class RoadOperationUpdate(BaseModel):
    """Payload schema for updating an existing road operation."""

    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, min_length=5)
    reason: Optional[str] = Field(default=None, min_length=3)
    operation_type: Optional[RoadOperationType] = None
    road_id: Optional[str] = None
    grievance_id: Optional[str] = None
    work_order_id: Optional[str] = None
    start_time: Optional[datetime] = None
    expected_end_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None

    # Alternative Route Information
    alternative_route_name: Optional[str] = None
    alternative_route_instructions: Optional[str] = None
    alternative_road_id: Optional[str] = None
    alternative_distance_km: Optional[float] = Field(default=None, ge=0.0)


class RoadOperationEventRead(BaseModel):
    """Read DTO for road operation audit event history log."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Event UUID")
    operation_id: str = Field(description="Road operation UUID")
    actor_id: Optional[str] = Field(default=None, description="Actor UUID")
    actor_role: Optional[str] = Field(default=None, description="Actor role")
    event_type: str = Field(description="Event type identifier")
    old_status: Optional[str] = Field(default=None, description="Status before event")
    new_status: Optional[str] = Field(default=None, description="Status after event")
    notes: Optional[str] = Field(default=None, description="Audit notes or remarks")
    created_at: datetime = Field(description="Event timestamp")


class GovernmentRoadOperationRead(BaseModel):
    """Detailed government read view for road operation."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Operation UUID")
    road_id: Optional[str] = Field(default=None, description="Affected road segment ID")
    road_name: Optional[str] = Field(default=None, description="Affected road segment name")
    grievance_id: Optional[str] = Field(default=None, description="Linked grievance ID")
    work_order_id: Optional[str] = Field(default=None, description="Linked work order ID")
    created_by: Optional[str] = Field(default=None, description="Creator officer user ID")
    creator_name: Optional[str] = Field(default=None, description="Creator officer name")
    title: str = Field(description="Operation title")
    description: str = Field(description="Operation description")
    reason: str = Field(description="Closure/restriction reason")
    operation_type: RoadOperationType = Field(description="Operation category")
    status: RoadOperationStatus = Field(description="Lifecycle status")
    start_time: datetime = Field(description="Start time")
    expected_end_time: datetime = Field(description="Expected end time")
    actual_end_time: Optional[datetime] = Field(default=None, description="Actual end time")

    # Alternative Route
    alternative_route_name: Optional[str] = Field(default=None, description="Alternative route title")
    alternative_route_instructions: Optional[str] = Field(default=None, description="Detour instructions")
    alternative_road_id: Optional[str] = Field(default=None, description="Alternative road segment ID")
    alternative_road_name: Optional[str] = Field(default=None, description="Alternative road segment name")
    alternative_distance_km: Optional[float] = Field(default=None, description="Detour distance in km")

    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last updated timestamp")
    history: List[RoadOperationEventRead] = Field(default_factory=list, description="Audit event log")


class CitizenRoadOperationRead(BaseModel):
    """Citizen-safe public read view for road operation."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Operation UUID")
    road_id: Optional[str] = Field(default=None, description="Affected road segment ID")
    road_name: Optional[str] = Field(default=None, description="Affected road segment name")
    title: str = Field(description="Public operation title")
    description: str = Field(description="Public operation description")
    reason: str = Field(description="Reason for closure/restriction")
    operation_type: RoadOperationType = Field(description="Operation category")
    status: RoadOperationStatus = Field(description="Lifecycle status")
    start_time: datetime = Field(description="Start time")
    expected_end_time: datetime = Field(description="Expected end time")
    actual_end_time: Optional[datetime] = Field(default=None, description="Actual end time")

    # Alternative Route
    alternative_route_name: Optional[str] = Field(default=None, description="Alternative route title")
    alternative_route_instructions: Optional[str] = Field(default=None, description="Detour instructions")
    alternative_road_name: Optional[str] = Field(default=None, description="Alternative road segment name")
    alternative_distance_km: Optional[float] = Field(default=None, description="Detour distance in km")

    created_at: datetime = Field(description="Published timestamp")
    updated_at: datetime = Field(description="Last updated timestamp")
