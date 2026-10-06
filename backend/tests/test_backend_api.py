"""Integration tests for backend HTTP API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.services.ml_analysis_service import MLAnalysisService
from ml.pipeline.orchestrator import RoadXPipeline
from ml.pipeline.schemas import UnifiedPipelineResult


def test_api_create_and_get_grievance(api_client: TestClient):
    """Test POST /api/v1/grievances and GET /api/v1/grievances/{id}."""
    payload = {
        "issue_category": "POTHOLE",
        "description": "Large dangerous pothole near school zone.",
        "latitude": 19.0760,
        "longitude": 72.8777,
    }

    # 1. Create grievance
    response = api_client.post("/api/v1/grievances", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["status"] == "SUBMITTED"
    assert data["description"] == "Large dangerous pothole near school zone."
    grievance_id = data["id"]

    # 2. Retrieve grievance
    get_res = api_client.get(f"/api/v1/grievances/{grievance_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == grievance_id


def test_api_list_and_filter_grievances(api_client: TestClient):
    """Test GET /api/v1/grievances with status filtering."""
    # Create two grievances
    api_client.post(
        "/api/v1/grievances",
        json={"issue_category": "POTHOLE", "description": "Pothole A"},
    )
    api_client.post(
        "/api/v1/grievances",
        json={"issue_category": "CRACK", "description": "Crack B"},
    )

    response = api_client.get("/api/v1/grievances?status=SUBMITTED")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 2
    for item in items:
        assert item["status"] == "SUBMITTED"


def test_api_patch_grievance_status(api_client: TestClient):
    """Test PATCH /api/v1/grievances/{id} status update."""
    res = api_client.post(
        "/api/v1/grievances",
        json={"issue_category": "WATERLOGGING", "description": "Water accumulated on road."},
    )
    grievance_id = res.json()["id"]

    patch_res = api_client.patch(
        f"/api/v1/grievances/{grievance_id}",
        json={"status": "UNDER_REVIEW"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "UNDER_REVIEW"


def test_api_trigger_and_get_ml_analysis(api_client: TestClient, monkeypatch):
    """Test POST /api/v1/grievances/{id}/analysis and GET /api/v1/grievances/{id}/analysis."""
    res = api_client.post(
        "/api/v1/grievances",
        json={"issue_category": "POTHOLE", "description": "Pothole near hospital entrance."},
    )
    grievance_id = res.json()["id"]

    # Mock ML pipeline inside MLAnalysisService
    mock_pipeline = MagicMock(spec=RoadXPipeline)
    mock_pipeline.run.return_value = UnifiedPipelineResult(
        pipeline_version="v1",
        timestamp_utc="2026-10-06T12:00:00Z",
        overall_status="SUCCESS",
        complaint_id=grievance_id,
        total_duration_ms=18.5,
    )

    orig_init = MLAnalysisService.__init__

    def mock_service_init(self, db, pipeline=None):
        orig_init(self, db, pipeline=mock_pipeline)

    monkeypatch.setattr(MLAnalysisService, "__init__", mock_service_init)

    # 1. Trigger ML Analysis
    analysis_res = api_client.post(f"/api/v1/grievances/{grievance_id}/analysis")
    assert analysis_res.status_code == 201
    analysis_data = analysis_res.json()
    assert analysis_data["grievance_id"] == grievance_id
    assert analysis_data["pipeline_version"] == "v1"

    # 2. Get Stored Analyses
    get_analysis_res = api_client.get(f"/api/v1/grievances/{grievance_id}/analysis")
    assert get_analysis_res.status_code == 200
    history = get_analysis_res.json()
    assert len(history) == 1
    assert history[0]["grievance_id"] == grievance_id
