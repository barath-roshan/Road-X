"""Unit tests for FastAPI health and readiness endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.dependencies import get_ml_service
from api.service import MLInferenceService
from ml.pipeline.orchestrator import RoadXPipeline


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_endpoint(client: TestClient):
    """Test 1 — GET /health returns 200 with service metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "roadx-ml-service"
    assert data["version"] == "1.0.0"


def test_readiness_endpoint_ready(client: TestClient):
    """Test 2a — GET /ready returns 200 when ML pipeline is initialized."""
    service = MLInferenceService(pipeline=MagicMock(spec=RoadXPipeline))
    service._is_ready = True
    app.dependency_overrides[get_ml_service] = lambda: service

    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["pipeline_loaded"] is True


def test_readiness_endpoint_not_ready(client: TestClient):
    """Test 2b — GET /ready returns 503 when ML pipeline failed to load."""
    service = MLInferenceService(pipeline=None)
    service._is_ready = False
    service._init_error = "Failed to load model checkpoint"
    app.dependency_overrides[get_ml_service] = lambda: service

    response = client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["pipeline_loaded"] is False
    assert "error" in data["details"]
