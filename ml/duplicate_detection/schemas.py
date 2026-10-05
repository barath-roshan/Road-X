"""Pydantic schemas and data structures for Duplicate Complaint Detection (Phase 6)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator

from ml.complaint_intelligence.schemas import IssueCategory


class ComplaintRecord(BaseModel):
    """Normalized citizen complaint representation for candidate retrieval and duplicate detection."""

    grievance_id: str = Field(min_length=1, description="Unique identifier for the grievance report")
    text: str = Field(min_length=1, description="Raw or cleaned citizen complaint text description")
    latitude: Optional[float] = Field(
        default=None, ge=-90.0, le=90.0, description="Geographic latitude coordinate"
    )
    longitude: Optional[float] = Field(
        default=None, ge=-180.0, le=180.0, description="Geographic longitude coordinate"
    )
    created_at: Optional[Union[datetime, str]] = Field(
        default=None, description="Timestamp when complaint was logged (ISO string or datetime)"
    )
    issue_category: Optional[Union[IssueCategory, str]] = Field(
        default=None, description="Categorical grievance issue category"
    )
    image_path: Optional[str] = Field(
        default=None, description="Optional path to attached grievance visual image"
    )

    @field_validator("text", "grievance_id")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Ensure string fields are non-empty after stripping whitespace."""
        stripped = str(v).strip()
        if not stripped:
            raise ValueError("Field cannot be empty or whitespace only.")
        return stripped


class DuplicateEvidence(BaseModel):
    """Granular evidence breakdown supporting duplicate detection decision."""

    text_similarity: float = Field(
        ge=0.0, le=1.0, description="Semantic text similarity cosine score from Phase 5 embeddings"
    )
    distance_m: Optional[float] = Field(
        default=None, ge=0.0, description="Geographic Haversine distance in meters"
    )
    time_difference_hours: Optional[float] = Field(
        default=None, ge=0.0, description="Temporal separation in hours"
    )
    same_issue_category: Optional[bool] = Field(
        default=None, description="Flag indicating matching issue categories"
    )

    @field_validator("text_similarity")
    @classmethod
    def round_similarity(cls, v: float) -> float:
        """Round similarity score to 4 decimal places bounded in [0.0, 1.0]."""
        return round(float(max(0.0, min(1.0, v))), 4)

    @field_validator("distance_m", "time_difference_hours")
    @classmethod
    def round_evidence_values(cls, v: Optional[float]) -> Optional[float]:
        """Round float evidence values to 2 decimal places if present."""
        if v is None:
            return None
        return round(float(max(0.0, v)), 2)


class DuplicateCandidate(BaseModel):
    """Ranked candidate grievance entry with similarity score and evidence."""

    grievance_id: str = Field(description="Grievance ID of existing candidate complaint")
    duplicate_score: float = Field(
        ge=0.0, le=1.0, description="Composite likelihood score indicating duplicate relationship"
    )
    is_candidate: bool = Field(description="Flag indicating if score exceeds candidate threshold")
    evidence: DuplicateEvidence = Field(description="Evidence breakdown for government review")

    @field_validator("duplicate_score")
    @classmethod
    def round_score(cls, v: float) -> float:
        """Round score to 4 decimal places bounded in [0.0, 1.0]."""
        return round(float(max(0.0, min(1.0, v))), 4)


class DuplicateDetectionRequest(BaseModel):
    """Request payload to query for potential duplicate grievances."""

    new_complaint: ComplaintRecord = Field(description="Newly submitted citizen complaint record")
    existing_complaints: List[ComplaintRecord] = Field(
        default_factory=list, description="Pool of historical existing complaints to query against"
    )


class DuplicateDetectionResponse(BaseModel):
    """Structured response object containing ranked duplicate candidates for government review."""

    grievance_id: str = Field(description="Grievance ID of the queried new complaint")
    duplicate_score: float = Field(
        ge=0.0, le=1.0, description="Top overall duplicate candidate likelihood score"
    )
    is_duplicate_candidate: bool = Field(
        description="True if top candidate exceeds duplicate score threshold"
    )
    possible_duplicate_grievance_ids: List[str] = Field(
        default_factory=list, description="List of candidate grievance IDs exceeding threshold"
    )
    candidates: List[DuplicateCandidate] = Field(
        default_factory=list, description="Ranked list of duplicate candidates sorted by score"
    )
    model_version: str = Field(default="v1", description="Duplicate detection model version identifier")
    disclaimer: str = Field(
        default=(
            "AI identifies duplicate candidates for assisted government review. "
            "Automatic complaint merging is strictly prohibited."
        ),
        description="Government human-in-the-loop governance safeguard notice",
    )

    @field_validator("duplicate_score")
    @classmethod
    def round_score(cls, v: float) -> float:
        """Round top score to 4 decimal places bounded in [0.0, 1.0]."""
        return round(float(max(0.0, min(1.0, v))), 4)
