"""Pydantic schemas for persistent ML analysis execution results."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class MLAnalysisCreate(BaseModel):
    """Request schema for persisting Phase 9/10 Unified ML Pipeline result."""

    grievance_id: str = Field(description="Target grievance UUID")
    pipeline_version: str = Field(default="v1", description="Unified pipeline model version")
    overall_status: str = Field(default="SUCCESS", description="Overall pipeline status")
    total_duration_ms: Optional[float] = Field(default=None, ge=0.0, description="Pipeline latency in ms")

    # Module specific prediction dictionaries
    failure_prediction: Optional[Dict[str, Any]] = Field(default=None)
    damage_detection: Optional[Dict[str, Any]] = Field(default=None)
    severity_prediction: Optional[Dict[str, Any]] = Field(default=None)
    complaint_analysis: Optional[Dict[str, Any]] = Field(default=None)
    duplicate_detection: Optional[Dict[str, Any]] = Field(default=None)
    time_to_failure: Optional[Dict[str, Any]] = Field(default=None)
    maintenance_priority: Optional[Dict[str, Any]] = Field(default=None)
    stage_summaries: Optional[Dict[str, Any]] = Field(default=None)


class MLAnalysisRead(MLAnalysisCreate):
    """Response schema for MLAnalysisResult entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique ML analysis result UUID identifier")
    created_at: datetime = Field(description="Analysis creation timestamp")
