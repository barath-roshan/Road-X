"""Unit tests for FastAPI ML routes (analyze, damage image, validation, error handling)."""

from __future__ import annotations

import io
from unittest.mock import MagicMock
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from api.main import app
from api.dependencies import get_ml_service
from api.service import MLInferenceService
from ml.pipeline.orchestrator import RoadXPipeline
from ml.pipeline.schemas import UnifiedPipelineResult


@pytest.fixture
def mock_service():
    """Fixture providing a mocked MLInferenceService."""
    service = MagicMock(spec=MLInferenceService)
    service.is_ready = True
    service.init_error = None
    return service


@pytest.fixture
def client(mock_service):
    """TestClient with mocked MLInferenceService injected via dependency_overrides."""
    app.dependency_overrides[get_ml_service] = lambda: mock_service
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_dummy_jpeg_bytes(width: int = 100, height: int = 100) -> bytes:
    """Helper creating valid JPEG image bytes in memory."""
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_analyze_valid_payload(client: TestClient, mock_service: MagicMock):
    """Test 3 & 7 — POST /api/v1/ml/analyze with valid payload returns 200 and schema."""
    mock_service.analyze.return_value = UnifiedPipelineResult(
        pipeline_version="v1",
        timestamp_utc="2026-10-06T00:00:00Z",
        overall_status="SUCCESS",
        road_segment_id="SEG-MH-4001",
        complaint_id="CMP-1234",
    )

    payload = {
        "road_segment_id": "SEG-MH-4001",
        "complaint_id": "CMP-1234",
        "complaint_text": "Deep pothole near market area causing hazard.",
    }

    response = client.post("/api/v1/ml/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "SUCCESS"
    assert data["road_segment_id"] == "SEG-MH-4001"
    assert "X-Request-ID" in response.headers


def test_analyze_invalid_payload(client: TestClient):
    """Test 4 — POST /api/v1/ml/analyze with invalid payload type returns 422 validation error."""
    payload = {
        "road_data": "invalid_string_instead_of_dict",  # Should trigger 422 schema validation error
    }

    response = client.post("/api/v1/ml/analyze", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_analyze_service_not_ready(client: TestClient):
    """Test 6 — POST /api/v1/ml/analyze when pipeline is not ready returns 503."""
    unready_service = MLInferenceService(pipeline=None)
    unready_service._is_ready = False
    app.dependency_overrides[get_ml_service] = lambda: unready_service

    payload = {"complaint_text": "Pothole on road."}
    response = client.post("/api/v1/ml/analyze", json=payload)
    assert response.status_code == 503
    data = response.json()
    assert data["error"]["code"] == "MODEL_NOT_READY"


def test_analyze_pipeline_failure(client: TestClient, mock_service: MagicMock):
    """Test 5 — POST /api/v1/ml/analyze handles pipeline runtime error with 500 response."""
    from api.service import InferenceFailedError
    mock_service.analyze.side_effect = InferenceFailedError("Internal computation error")

    payload = {"complaint_text": "Pothole issue."}
    response = client.post("/api/v1/ml/analyze", json=payload)
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "INFERENCE_FAILED"


def test_request_id_traceability(client: TestClient, mock_service: MagicMock):
    """Test 8 — Verify custom X-Request-ID header propagation and response correlation."""
    mock_service.analyze.return_value = UnifiedPipelineResult(
        pipeline_version="v1",
        timestamp_utc="2026-10-06T00:00:00Z",
        overall_status="SUCCESS",
    )

    custom_id = "req-test-trace-999"
    headers = {"X-Request-ID": custom_id}
    response = client.post("/api/v1/ml/analyze", json={}, headers=headers)
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


def test_damage_image_valid_upload(client: TestClient, mock_service: MagicMock):
    """Test 9a — POST /api/v1/ml/damage/analyze with valid JPEG file returns 200."""
    mock_service.analyze_image.return_value = UnifiedPipelineResult(
        pipeline_version="v1",
        timestamp_utc="2026-10-06T00:00:00Z",
        overall_status="SUCCESS",
    )

    img_bytes = create_dummy_jpeg_bytes()
    files = {"file": ("road.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/ml/damage/analyze", files=files)
    assert response.status_code == 200
    assert response.json()["overall_status"] == "SUCCESS"


def test_damage_image_unsupported_type(client: TestClient):
    """Test 9b — POST /api/v1/ml/damage/analyze with text file returns 400."""
    files = {"file": ("document.txt", b"Hello world text file content", "text/plain")}
    response = client.post("/api/v1/ml/damage/analyze", files=files)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_damage_image_corrupt_file(client: TestClient):
    """Test 9c — POST /api/v1/ml/damage/analyze with corrupt image bytes returns 400."""
    service = MLInferenceService(pipeline=MagicMock(spec=RoadXPipeline))
    service._is_ready = True
    app.dependency_overrides[get_ml_service] = lambda: service

    files = {"file": ("corrupt.jpg", b"NOT_AN_IMAGE_HEADER_BYTES_12345", "image/jpeg")}
    response = client.post("/api/v1/ml/damage/analyze", files=files)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_INPUT"


def test_damage_image_oversized_file(client: TestClient):
    """Test 9d — POST /api/v1/ml/damage/analyze with oversized file returns 400."""
    from api.config import api_settings
    oversized_bytes = b"0" * (api_settings.max_image_size_bytes + 1024)
    files = {"file": ("large.jpg", oversized_bytes, "image/jpeg")}
    response = client.post("/api/v1/ml/damage/analyze", files=files)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
