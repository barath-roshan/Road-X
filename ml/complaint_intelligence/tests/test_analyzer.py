"""Unit tests for ComplaintAnalyzer end-to-end service and pipeline save/load."""

import pytest
from ml.common.config import settings
from ml.complaint_intelligence.analyzer import ComplaintAnalyzer
from ml.complaint_intelligence.schemas import (
    ComplaintAnalysisResponse,
    IssueCategory,
    UrgencyLevel,
    SafetyRiskLevel,
)


@pytest.fixture
def loaded_analyzer():
    model_dir = settings.models_dir / "complaint_intelligence"
    return ComplaintAnalyzer.load(model_dir)


def test_analyzer_end_to_end_prediction(loaded_analyzer):
    complaint = "There is a large pothole near the railway station. It is dangerous for bikes at night."

    response = loaded_analyzer.analyze(complaint)

    assert isinstance(response, ComplaintAnalysisResponse)
    assert isinstance(response.issue_category, IssueCategory)
    assert isinstance(response.urgency, UrgencyLevel)
    assert isinstance(response.safety_risk, SafetyRiskLevel)

    assert 0.0 <= response.issue_confidence <= 1.0
    assert 0.0 <= response.urgency_confidence <= 1.0
    assert 0.0 <= response.safety_confidence <= 1.0

    assert response.embedding_available is True
    assert isinstance(response.location_mentions, list)


def test_analyzer_embed_forwarding(loaded_analyzer):
    vec = loaded_analyzer.embed("Pothole near Anna Salai road")
    assert vec.shape == (300,)
    assert vec.dtype == "float32"


def test_analyzer_save_and_load(loaded_analyzer, tmp_path):
    target_dir = tmp_path / "complaint_models"
    loaded_analyzer.save(target_dir)

    reloaded = ComplaintAnalyzer.load(target_dir)
    assert reloaded.is_fitted

    res1 = loaded_analyzer.analyze("Deep crack on road")
    res2 = reloaded.analyze("Deep crack on road")

    assert res1.issue_category == res2.issue_category
    assert res1.urgency == res2.urgency
    assert res1.safety_risk == res2.safety_risk
