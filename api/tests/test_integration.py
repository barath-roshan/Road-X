"""Integration test for RoadX FastAPI ML Service.

Exercises full request lifecycle: HTTP Request -> FastAPI Route -> MLInferenceService -> RoadXPipeline -> API Response.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def integration_client():
    """TestClient that triggers app lifespan (initializing real RoadXPipeline)."""
    with TestClient(app) as client:
        yield client


def test_full_pipeline_http_integration(integration_client: TestClient):
    """Integration Test — Send real HTTP request through FastAPI app to real RoadXPipeline."""
    payload = {
        "road_segment_id": "SEG-INTEG-001",
        "complaint_id": "CMP-INTEG-001",
        "complaint_text": "Severe potholes and cracking near central crossroads.",
        "road_data": {
            "segment_id": "SEG-INTEG-001",
            "road_age_years": 5.0,
            "road_length_m": 800.0,
            "lane_count": 2,
            "road_quality_score": 0.35,
            "traffic_volume": 6000.0,
            "heavy_vehicle_ratio": 0.20,
            "average_speed_kmph": 40.0,
            "rainfall_7d_mm": 120.0,
            "rainfall_30d_mm": 280.0,
            "temperature_avg_c": 30.0,
            "flood_events_30d": 2,
            "days_since_repair": 500.0,
            "previous_repairs": 4,
            "previous_failures": 2,
            "citizen_complaints_30d": 12,
            "pothole_count": 8,
            "crack_ratio": 0.45,
        },
    }

    response = integration_client.post("/api/v1/ml/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["pipeline_version"] == "v1"
    assert data["road_segment_id"] == "SEG-INTEG-001"
    assert data["complaint_id"] == "CMP-INTEG-001"
    assert data["overall_status"] in ("SUCCESS", "PARTIAL_SUCCESS")

    # Check that individual ML module outputs are populated in structured response
    assert "failure_prediction" in data
    assert "complaint_analysis" in data
    assert "stage_summaries" in data
    assert "total_duration_ms" in data
    assert data["total_duration_ms"] > 0.0
