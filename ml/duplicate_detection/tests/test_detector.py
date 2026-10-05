"""Unit tests for full DuplicateDetector pipeline and end-to-end scenarios."""

import pytest
from ml.duplicate_detection.detector import DuplicateDetector
from ml.duplicate_detection.schemas import ComplaintRecord, DuplicateDetectionResponse


def test_detector_exact_duplicate():
    detector = DuplicateDetector()

    c_new = ComplaintRecord(
        grievance_id="GRV-NEW",
        text="There is a large pothole near the railway station. Dangerous for bikes at night.",
        latitude=13.0827,
        longitude=80.2707,
        created_at="2026-09-01T10:00:00Z",
        issue_category="POTHOLE",
    )
    c_existing = ComplaintRecord(
        grievance_id="GRV-EXISTING",
        text="There is a large pothole near the railway station. Dangerous for bikes at night.",
        latitude=13.0827,
        longitude=80.2707,
        created_at="2026-09-01T10:00:00Z",
        issue_category="POTHOLE",
    )

    response = detector.detect_duplicates(new_complaint=c_new, existing_complaints=[c_existing])

    assert isinstance(response, DuplicateDetectionResponse)
    assert response.grievance_id == "GRV-NEW"
    assert response.is_duplicate_candidate is True
    assert "GRV-EXISTING" in response.possible_duplicate_grievance_ids
    assert len(response.candidates) == 1
    assert response.candidates[0].evidence.text_similarity == 1.0
    assert response.candidates[0].evidence.distance_m == 0.0
    assert response.candidates[0].evidence.time_difference_hours == 0.0
    assert "AI identifies duplicate candidates for assisted government review" in response.disclaimer


def test_detector_geographically_far_same_text():
    detector = DuplicateDetector()

    c_new = ComplaintRecord(
        grievance_id="GRV-NEW",
        text="There is a large pothole near the railway station.",
        latitude=13.0827,  # Chennai
        longitude=80.2707,
    )
    c_existing = ComplaintRecord(
        grievance_id="GRV-EXISTING",
        text="There is a large pothole near the railway station.",
        latitude=11.0168,  # Coimbatore (~420km away)
        longitude=76.9558,
    )

    response = detector.detect_duplicates(new_complaint=c_new, existing_complaints=[c_existing])

    assert len(response.candidates) == 1
    evidence = response.candidates[0].evidence
    assert evidence.text_similarity == 1.0
    assert evidence.distance_m > 400000.0  # Geographically far (>400km)
    # Score is lower than exact match due to spatial distance decay
    assert response.candidates[0].duplicate_score < 0.90


test_different_issue_same_location_time_data = [
    ("POTHOLE", "STREETLIGHT", "There is a large pothole near bus stand", "Streetlight not working near park")
]


@pytest.mark.parametrize("cat1,cat2,text1,text2", test_different_issue_same_location_time_data)
def test_detector_different_issue_same_location(cat1, cat2, text1, text2):
    detector = DuplicateDetector()

    c_new = ComplaintRecord(
        grievance_id="GRV-NEW",
        text=text1,
        latitude=13.0827,
        longitude=80.2707,
        created_at="2026-09-01T10:00:00Z",
        issue_category=cat1,
    )
    c_existing = ComplaintRecord(
        grievance_id="GRV-EXISTING",
        text=text2,
        latitude=13.0827,
        longitude=80.2707,
        created_at="2026-09-01T10:00:00Z",
        issue_category=cat2,
    )

    response = detector.detect_duplicates(new_complaint=c_new, existing_complaints=[c_existing])

    # System does not blindly mark as duplicate when text and issue differ
    assert len(response.candidates) == 1
    assert response.candidates[0].evidence.same_issue_category is False


def test_detector_candidate_ranking_determinism():
    detector = DuplicateDetector()

    c_new = ComplaintRecord(
        grievance_id="GRV-NEW", text="Deep pothole near Anna Salai road"
    )
    c1 = ComplaintRecord(grievance_id="GRV-1", text="Minor surface crack")
    c2 = ComplaintRecord(
        grievance_id="GRV-2", text="Deep pothole near Anna Salai road"
    )

    resp1 = detector.detect_duplicates(c_new, [c1, c2])
    resp2 = detector.detect_duplicates(c_new, [c1, c2])

    assert [c.grievance_id for c in resp1.candidates] == [c.grievance_id for c in resp2.candidates]
    assert resp1.candidates[0].grievance_id == "GRV-2"  # Highest match ranked first
