"""Pytest suite for Phase 22 End-to-End Smoke Tests."""

from __future__ import annotations

import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from api.main import app
from ml.monitoring.telemetry import telemetry


@pytest.fixture(scope="module")
def client():
    """Module-scoped TestClient that triggers FastAPI lifespan initialization."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_smoke_health_endpoint(client: TestClient):
    """1. Health check returns 200 with service metadata."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "roadx-ml-service"


def test_smoke_readiness_probe(client: TestClient):
    """2. Readiness probe returns 200 and indicates ML pipeline is loaded."""
    res = client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["pipeline_loaded"] is True
    assert "database" in data.get("details", {})


def test_smoke_openapi_docs(client: TestClient):
    """3. OpenAPI docs specification loads successfully."""
    res = client.get("/openapi.json")
    assert res.status_code == 200
    assert "openapi" in res.json()


def test_smoke_ml_analyze_valid(client: TestClient):
    """4. ML analyze endpoint returns valid predictions and overall SUCCESS."""
    payload = {
        "road_segment_id": "SEG-SMOKE-PYTEST-1",
        "road_data": {
            "segment_id": "SEG-SMOKE-PYTEST-1",
            "road_age_years": 4.0,
            "road_length_m": 800.0,
            "lane_count": 2,
            "road_quality_score": 0.40,
            "traffic_volume": 3500.0,
            "heavy_vehicle_ratio": 0.15,
            "average_speed_kmph": 45.0,
            "rainfall_7d_mm": 50.0,
            "rainfall_30d_mm": 150.0,
            "temperature_avg_c": 28.0,
            "flood_events_30d": 0,
            "days_since_repair": 250.0,
            "previous_repairs": 1,
            "previous_failures": 0,
            "citizen_complaints_30d": 3,
            "pothole_count": 2,
            "crack_ratio": 0.20,
        },
    }
    res = client.post("/api/v1/ml/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "SUCCESS"
    assert "failure_prediction" in data


def test_smoke_validation_and_error_handling(client: TestClient):
    """5. Invalid input returns safe structured HTTP 422 error."""
    res = client.post("/api/v1/ml/analyze", json={"road_data": "invalid_type"})
    assert res.status_code in (400, 422)
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_smoke_damage_image_validation(client: TestClient):
    """6. Invalid non-image upload is rejected with HTTP 400."""
    files = {"file": ("script.sh", b"echo hello", "text/x-sh")}
    res = client.post("/api/v1/ml/damage/analyze", files=files)
    assert res.status_code == 400
    assert "INVALID_FILE_TYPE" in str(res.json())


def test_smoke_database_backed_route(client: TestClient):
    """7. Database-backed routes query and return metrics successfully."""
    headers = {"X-Actor-Role": "GOVERNMENT_OFFICER", "X-Actor-User-ID": "officer-smoke-1"}
    res = client.get("/api/v1/government/dashboard/overview", headers=headers)
    assert res.status_code == 200
    assert "total_grievances" in res.json()


def test_smoke_ml_artifact_loading(client: TestClient):
    """8. ML pipeline singleton is ready in memory."""
    assert hasattr(app.state, "ml_service")
    assert app.state.ml_service.is_ready is True


def test_smoke_chatbot_offline_fallback(client: TestClient):
    """9. Chatbot operates offline without external LLM keys."""
    headers = {"X-Actor-Role": "CITIZEN", "X-Actor-User-ID": "citizen-smoke-1"}
    conv_res = client.post("/api/v1/citizen/chat/conversations", json={"title": "Pytest Smoke"}, headers=headers)
    assert conv_res.status_code in (200, 201)
    conv_id = conv_res.json()["id"]

    msg_res = client.post(
        f"/api/v1/citizen/chat/conversations/{conv_id}/messages",
        json={"content": "What is RoadX?"},
        headers=headers,
    )
    assert msg_res.status_code == 200
    assert "assistant_message" in msg_res.json()
    assert len(msg_res.json()["assistant_message"]["content"]) > 0


def test_smoke_notifications_with_fallback(client: TestClient):
    """10. Notification endpoint retrieves list with optional Twilio disabled."""
    headers = {"X-Actor-Role": "CITIZEN", "X-Actor-User-ID": "citizen-smoke-1"}
    res = client.get("/api/v1/notifications", headers=headers)
    assert res.status_code == 200
    assert "items" in res.json()


def test_smoke_monitoring_telemetry(client: TestClient):
    """11. Operational telemetry endpoint returns statistics."""
    res = client.get("/api/v1/ml/monitoring/telemetry")
    assert res.status_code == 200
    assert "total_requests" in res.json()


def test_smoke_telemetry_failure_isolation():
    """12. Telemetry failures do not disrupt execution."""
    telemetry.record_inference(latency_ms=-1.0, success=True)
