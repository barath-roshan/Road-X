"""Unit tests for Complaint Intelligence schemas and validation."""

import pytest
from pydantic import ValidationError
from ml.complaint_intelligence.schemas import (
    ComplaintAnalysisRequest,
    ComplaintAnalysisResponse,
    IssueCategory,
    UrgencyLevel,
    SafetyRiskLevel,
    LocationMention,
    LocationEntityType,
)


def test_request_validation():
    req = ComplaintAnalysisRequest(text="Large pothole near school")
    assert req.text == "Large pothole near school"

    with pytest.raises(ValidationError):
        ComplaintAnalysisRequest(text="")

    with pytest.raises(ValidationError):
        ComplaintAnalysisRequest(text="    ")


def test_response_schema_fields():
    resp = ComplaintAnalysisResponse(
        issue_category=IssueCategory.POTHOLE,
        issue_confidence=0.91234,
        urgency=UrgencyLevel.HIGH,
        urgency_confidence=0.8411,
        safety_risk=SafetyRiskLevel.HIGH,
        safety_confidence=0.8800,
        location_mentions=[
            LocationMention(text="railway station", type=LocationEntityType.LANDMARK)
        ],
        embedding_available=True,
        model_version="v1",
    )

    assert resp.issue_category == IssueCategory.POTHOLE
    assert resp.issue_confidence == 0.9123
    assert resp.urgency == UrgencyLevel.HIGH
    assert resp.safety_risk == SafetyRiskLevel.HIGH
    assert len(resp.location_mentions) == 1
    assert resp.location_mentions[0].text == "railway station"
    assert resp.embedding_available is True
    assert resp.model_version == "v1"
