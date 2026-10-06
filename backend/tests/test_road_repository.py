"""Unit tests for RoadRepository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models.road import RoadSegment
from backend.repositories.road_repository import RoadRepository


def test_create_and_query_road_segment(db_session: Session):
    """Test creating road segment and querying by segment_id string."""
    repo = RoadRepository(db_session)
    segment = RoadSegment(
        segment_id="SEG-MH-4001",
        road_name="MG Road Expressway",
        area="Central District",
        latitude=18.9220,
        longitude=72.8347,
        road_type="URBAN_ARTERIAL",
    )
    saved = repo.add(segment)

    assert saved.id is not None
    assert saved.segment_id == "SEG-MH-4001"

    found = repo.get_by_segment_id("SEG-MH-4001")
    assert found is not None
    assert found.id == saved.id
    assert found.road_name == "MG Road Expressway"
