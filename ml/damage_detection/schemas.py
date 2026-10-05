"""Pydantic schemas for normalized RoadX damage detection outputs."""

from __future__ import annotations

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator


class DetectedDamageItem(BaseModel):
    """Normalized schema for an individual detected road damage instance."""

    class_name: str = Field(description="Canonical damage class (e.g. 'pothole', 'crack')")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from vision model")
    bbox: Tuple[float, float, float, float] = Field(
        description="Bounding box in normalized format [x1, y1, x2, y2] (top-left to bottom-right)"
    )
    area_ratio: float = Field(
        ge=0.0, le=1.0, description="Ratio of bounding box area relative to total image surface area"
    )
    segmentation_polygon: Optional[List[Tuple[float, float]]] = Field(
        default=None, description="Optional segmentation polygon vertices [(x, y), ...]"
    )

    @field_validator("bbox")
    @classmethod
    def validate_bbox_coordinates(cls, v: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        """Verify x1 <= x2 and y1 <= y2."""
        x1, y1, x2, y2 = v
        if x2 < x1:
            raise ValueError(f"Invalid bounding box width: x1 ({x1}) > x2 ({x2})")
        if y2 < y1:
            raise ValueError(f"Invalid bounding box height: y1 ({y1}) > y2 ({y2})")
        return (round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2))


class RoadDamageDetectionResponse(BaseModel):
    """Normalized response schema for a complete image damage detection request."""

    detections: List[DetectedDamageItem] = Field(
        default_factory=list, description="List of detected defect instances"
    )
    image_width: int = Field(gt=0, description="Original image width in pixels")
    image_height: int = Field(gt=0, description="Original image height in pixels")
    detection_count: int = Field(ge=0, description="Total count of defects detected")
    model_version: str = Field(default="v1", description="Vision model version identifier")


# Backward compatibility alias
DamageDetection = DetectedDamageItem
