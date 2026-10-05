"""Unit tests for Haversine distance, temporal difference, and feature building."""

from datetime import datetime, timezone
from ml.duplicate_detection.features import (
    calculate_haversine_distance,
    calculate_time_difference_hours,
    GeographicTemporalFeatureBuilder,
)
from ml.duplicate_detection.schemas import ComplaintRecord


def test_haversine_distance_same_location():
    dist = calculate_haversine_distance(13.0827, 80.2707, 13.0827, 80.2707)
    assert dist == 0.0


def test_haversine_distance_known_points():
    # Chennai (13.0827, 80.2707) to Coimbatore (11.0168, 76.9558) is approx ~420km = ~420,000 meters
    dist = calculate_haversine_distance(13.0827, 80.2707, 11.0168, 76.9558)
    assert dist is not None
    assert 400000.0 < dist < 450000.0


def test_haversine_distance_missing_coordinates():
    assert calculate_haversine_distance(None, 80.2707, 13.0827, 80.2707) is None
    assert calculate_haversine_distance(13.0827, None, 13.0827, 80.2707) is None


def test_time_difference_hours():
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 1, 14, 30, 0, tzinfo=timezone.utc)
    diff = calculate_time_difference_hours(t1, t2)
    assert diff == 4.5


def test_time_difference_iso_string():
    s1 = "2026-09-01T10:00:00Z"
    s2 = "2026-09-01T16:00:00Z"
    diff = calculate_time_difference_hours(s1, s2)
    assert diff == 6.0


def test_time_difference_missing_timestamps():
    assert calculate_time_difference_hours(None, "2026-09-01T10:00:00") is None
    assert calculate_time_difference_hours("2026-09-01T10:00:00", None) is None


def test_feature_builder_missing_data_graceful_handling():
    builder = GeographicTemporalFeatureBuilder()
    c1 = ComplaintRecord(grievance_id="GRV-1", text="Pothole near bus stand")
    c2 = ComplaintRecord(grievance_id="GRV-2", text="Crack on road")

    evidence = builder.build_evidence(c1, c2, text_similarity=0.5)
    assert evidence.text_similarity == 0.5
    assert evidence.distance_m is None
    assert evidence.time_difference_hours is None

    geo_score, time_score = builder.compute_proximity_scores(evidence)
    assert geo_score is None
    assert time_score is None
