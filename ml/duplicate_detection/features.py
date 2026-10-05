"""Geographic (Haversine) and temporal distance feature calculation utilities."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional, Tuple, Union

from ml.duplicate_detection.schemas import ComplaintRecord, DuplicateEvidence
from ml.duplicate_detection.config import config


def calculate_haversine_distance(
    lat1: Optional[float],
    lon1: Optional[float],
    lat2: Optional[float],
    lon2: Optional[float],
) -> Optional[float]:
    """Calculate geographic distance in meters between two lat/lon coordinate pairs using the Haversine formula.

    Args:
        lat1, lon1: Coordinates of point A in degrees.
        lat2, lon2: Coordinates of point B in degrees.

    Returns:
        Distance in meters (float >= 0.0), or None if any coordinate is missing.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None

    # Mean Earth radius in meters
    R = 6371000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )

    # Bounded for numerical precision safety
    a = max(0.0, min(1.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    distance_m = R * c
    return float(max(0.0, distance_m))


def parse_datetime(dt_input: Optional[Union[datetime, str]]) -> Optional[datetime]:
    """Parse datetime object or ISO format string into UTC/naive datetime."""
    if dt_input is None:
        return None

    if isinstance(dt_input, datetime):
        return dt_input

    if isinstance(dt_input, str):
        cleaned = dt_input.strip()
        if not cleaned:
            return None
        try:
            # Parse standard ISO format string (e.g. 2026-09-01T10:00:00 or 2026-09-01 10:00:00)
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        except ValueError:
            return None

    return None


def calculate_time_difference_hours(
    dt1_input: Optional[Union[datetime, str]],
    dt2_input: Optional[Union[datetime, str]],
) -> Optional[float]:
    """Calculate temporal difference in hours between two complaint timestamps.

    Args:
        dt1_input: Timestamp A (datetime or ISO string).
        dt2_input: Timestamp B (datetime or ISO string).

    Returns:
        Time difference in hours (float >= 0.0), or None if any timestamp is missing or unparseable.
    """
    dt1 = parse_datetime(dt1_input)
    dt2 = parse_datetime(dt2_input)

    if dt1 is None or dt2 is None:
        return None

    # Handle timezone awareness mismatch by normalizing timezone if present
    if dt1.tzinfo is not None and dt2.tzinfo is None:
        dt2 = dt2.replace(tzinfo=dt1.tzinfo)
    elif dt2.tzinfo is not None and dt1.tzinfo is None:
        dt1 = dt1.replace(tzinfo=dt2.tzinfo)

    diff_seconds = abs((dt1 - dt2).total_seconds())
    diff_hours = diff_seconds / 3600.0
    return float(max(0.0, diff_hours))


class GeographicTemporalFeatureBuilder:
    """Extracts geographic, temporal, and metadata evidence between two complaint records."""

    def __init__(
        self,
        geo_decay_m: float = config.geo_decay_distance_m,
        time_decay_h: float = config.time_decay_hours,
    ) -> None:
        self.geo_decay_m = geo_decay_m
        self.time_decay_h = time_decay_h

    def build_evidence(
        self,
        complaint_a: ComplaintRecord,
        complaint_b: ComplaintRecord,
        text_similarity: float,
    ) -> DuplicateEvidence:
        """Compute geographic distance, temporal difference, and issue category match evidence.

        Args:
            complaint_a: Target complaint record.
            complaint_b: Candidate complaint record.
            text_similarity: Cosine similarity score between complaint text embeddings.

        Returns:
            DuplicateEvidence Pydantic object.
        """
        distance_m = calculate_haversine_distance(
            complaint_a.latitude,
            complaint_a.longitude,
            complaint_b.latitude,
            complaint_b.longitude,
        )

        time_difference_hours = calculate_time_difference_hours(
            complaint_a.created_at,
            complaint_b.created_at,
        )

        same_issue_category: Optional[bool] = None
        if complaint_a.issue_category and complaint_b.issue_category:
            cat_a = str(complaint_a.issue_category).upper()
            cat_b = str(complaint_b.issue_category).upper()
            same_issue_category = cat_a == cat_b

        return DuplicateEvidence(
            text_similarity=text_similarity,
            distance_m=distance_m,
            time_difference_hours=time_difference_hours,
            same_issue_category=same_issue_category,
        )

    def compute_proximity_scores(
        self, evidence: DuplicateEvidence
    ) -> Tuple[Optional[float], Optional[float]]:
        """Compute exponential decay proximity scores for geographic and temporal features.

        Returns:
            Tuple of (geo_score, time_score) where each score is in [0.0, 1.0] if feature exists, else None.
        """
        geo_score: Optional[float] = None
        if evidence.distance_m is not None:
            # Exponential decay: score = exp(-distance / d0)
            geo_score = math.exp(-evidence.distance_m / max(1.0, self.geo_decay_m))
            geo_score = max(0.0, min(1.0, geo_score))

        time_score: Optional[float] = None
        if evidence.time_difference_hours is not None:
            # Exponential decay: score = exp(-time_hours / t0)
            time_score = math.exp(-evidence.time_difference_hours / max(0.1, self.time_decay_h))
            time_score = max(0.0, min(1.0, time_score))

        return geo_score, time_score
