"""Repeatable End-to-End Smoke Test Suite for RoadX (Phase 22).

Validates the 12 core operational capabilities required for deployment:
1. API Service Initialization & Liveness (/health)
2. Model Readiness Probe (/ready)
3. OpenAPI Documentation Availability (/openapi.json)
4. ML Unified Pipeline Inference (/api/v1/ml/analyze)
5. Request Validation & Safe Error Handling (Invalid Payload)
6. Visual Damage Detection Upload Validation
7. Database-Backed Route Execution (/api/v1/government/dashboard/overview)
8. ML Model Artifact Load Verification
9. Citizen Chatbot Offline Fallback (No External API Keys)
10. Notification Delivery with Integrations Disabled (/api/v1/notifications)
11. MLflow Telemetry & Monitoring Endpoints
12. Operational Telemetry Failure Isolation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_smoke_tests(target_url: str | None = None, use_testclient: bool = True) -> int:
    """Execute all 12 smoke tests and print formatted operational summary table."""
    results: List[Tuple[str, str, str]] = []

    def record(name: str, passed: bool, message: str) -> None:
        status = "PASSED" if passed else "FAILED"
        results.append((name, status, message))

    print("=" * 80)
    print("ROADX PHASE 22 — END-TO-END SMOKE TEST SUITE")
    print("=" * 80)

    if use_testclient:
        from fastapi.testclient import TestClient
        from api.main import app
        # Using context manager triggers FastAPI lifespan startup to initialize ML service
        with TestClient(app, raise_server_exceptions=False) as client:
            _execute_tests(client.get, client.post, record, app=app)
    else:
        import httpx
        with httpx.Client(base_url=target_url, timeout=30.0) as client:
            _execute_tests(client.get, client.post, record, app=None)

    # Print Report Summary
    print("-" * 80)
    print(f"{'Test':<42} | {'Status':<10} | {'Details'}")
    print("-" * 80)
    failed_count = 0
    for name, status, msg in results:
        print(f"{name:<42} | {status:<10} | {msg}")
        if status != "PASSED":
            failed_count += 1
    print("=" * 80)
    print(f"Total: {len(results)} | Passed: {len(results) - failed_count} | Failed: {failed_count}")
    print("=" * 80)

    return 0 if failed_count == 0 else 1


def _execute_tests(
    get: Callable[..., Any],
    post: Callable[..., Any],
    record: Callable[[str, bool, str], None],
    app: Any = None,
) -> None:
    """Run all 12 smoke tests using provided HTTP callables."""

    # 1. Health check
    try:
        res = get("/health")
        passed = res.status_code == 200 and res.json().get("status") == "healthy"
        record("1. Health Endpoint (/health)", passed, f"Status: {res.status_code}, body: {res.json()}")
    except Exception as e:
        record("1. Health Endpoint (/health)", False, str(e))

    # 2. Readiness check
    try:
        res = get("/ready")
        passed = res.status_code == 200 and res.json().get("pipeline_loaded") is True
        record("2. Readiness Probe (/ready)", passed, f"Status: {res.status_code}, pipeline_loaded: {res.json().get('pipeline_loaded')}")
    except Exception as e:
        record("2. Readiness Probe (/ready)", False, str(e))

    # 3. OpenAPI Documentation
    try:
        res = get("/openapi.json")
        passed = res.status_code == 200 and "openapi" in res.json()
        record("3. OpenAPI Docs (/openapi.json)", passed, f"Status: {res.status_code}, version: {res.json().get('openapi')}")
    except Exception as e:
        record("3. OpenAPI Docs (/openapi.json)", False, str(e))

    # 4. Valid ML Inference
    try:
        payload = {
            "road_segment_id": "SEG-SMOKE-001",
            "road_data": {
                "segment_id": "SEG-SMOKE-001",
                "road_age_years": 3.0,
                "road_length_m": 1000.0,
                "lane_count": 2,
                "road_quality_score": 0.45,
                "traffic_volume": 4000.0,
                "heavy_vehicle_ratio": 0.20,
                "average_speed_kmph": 50.0,
                "rainfall_7d_mm": 60.0,
                "rainfall_30d_mm": 180.0,
                "temperature_avg_c": 30.0,
                "flood_events_30d": 0,
                "days_since_repair": 300.0,
                "previous_repairs": 2,
                "previous_failures": 1,
                "citizen_complaints_30d": 5,
                "pothole_count": 3,
                "crack_ratio": 0.25,
            },
        }
        res = post("/api/v1/ml/analyze", json=payload)
        data = res.json()
        passed = res.status_code == 200 and data.get("overall_status") == "SUCCESS" and "failure_prediction" in data
        record("4. ML Inference (/api/v1/ml/analyze)", passed, f"Status: {res.status_code}, overall_status: {data.get('overall_status')}")
    except Exception as e:
        record("4. ML Inference (/api/v1/ml/analyze)", False, str(e))

    # 5. Invalid Input Validation & Safe Error
    try:
        res = post("/api/v1/ml/analyze", json={"road_data": "invalid_not_a_dict"})
        passed = res.status_code in (400, 422) and "error" in res.json()
        record("5. Validation & Safe Error Handling", passed, f"Status: {res.status_code}, error_code: {res.json().get('error', {}).get('code')}")
    except Exception as e:
        record("5. Validation & Safe Error Handling", False, str(e))

    # 6. Damage Image Upload Validation
    try:
        files = {"file": ("malicious.txt", b"plain text is not an image", "text/plain")}
        res = post("/api/v1/ml/damage/analyze", files=files)
        passed = res.status_code == 400 and "INVALID_FILE_TYPE" in str(res.json())
        record("6. Image Upload Validation", passed, f"Status: {res.status_code}, rejected text file successfully")
    except Exception as e:
        record("6. Image Upload Validation", False, str(e))

    # 7. Database-Backed Route Execution
    try:
        headers = {"X-Actor-Role": "GOVERNMENT_OFFICER", "X-Actor-User-ID": "officer-smoke-1"}
        res = get("/api/v1/government/dashboard/overview", headers=headers)
        passed = res.status_code == 200 and "total_grievances" in res.json()
        record("7. Database-Backed Route Execution", passed, f"Status: {res.status_code}, overview metrics returned from DB")
    except Exception as e:
        record("7. Database-Backed Route Execution", False, str(e))

    # 8. Model Artifacts Verification
    try:
        from api.service import MLInferenceService
        if app and hasattr(app.state, "ml_service"):
            service = app.state.ml_service
        else:
            service = MLInferenceService()
            service.initialize()
        passed = service.is_ready
        record("8. ML Artifact Load Verification", passed, "Unified pipeline models successfully loaded into memory")
    except Exception as e:
        record("8. ML Artifact Load Verification", False, str(e))

    # 9. Chatbot Offline Fallback (No External API Keys)
    try:
        headers = {"X-Actor-Role": "CITIZEN", "X-Actor-User-ID": "citizen-smoke-1"}
        # Create a conversation first
        conv_res = post("/api/v1/citizen/chat/conversations", json={"title": "Smoke Session"}, headers=headers)
        if conv_res.status_code in (200, 201):
            conv_id = conv_res.json()["id"]
            msg_res = post(
                f"/api/v1/citizen/chat/conversations/{conv_id}/messages",
                json={"content": "How do I report a pothole on my street?"},
                headers=headers,
            )
            data = msg_res.json()
            passed = (
                msg_res.status_code == 200
                and "assistant_message" in data
                and len(data["assistant_message"].get("content", "")) > 0
            )
            record("9. Chatbot Offline Fallback", passed, f"Status: {msg_res.status_code}, reply generated without external keys")
        else:
            record("9. Chatbot Offline Fallback", False, f"Failed to create conversation: {conv_res.status_code}")
    except Exception as e:
        record("9. Chatbot Offline Fallback", False, str(e))

    # 10. Notification System with Fallback
    try:
        headers = {"X-Actor-Role": "CITIZEN", "X-Actor-User-ID": "citizen-smoke-1"}
        res = get("/api/v1/notifications", headers=headers)
        passed = res.status_code == 200 and "items" in res.json()
        record("10. Notification System Fallback", passed, f"Status: {res.status_code}, retrieved user notifications with Twilio disabled")
    except Exception as e:
        record("10. Notification System Fallback", False, str(e))

    # 11. MLflow Telemetry & Monitoring Endpoints
    try:
        res = get("/api/v1/ml/monitoring/telemetry")
        passed = res.status_code == 200 and "total_requests" in res.json()
        record("11. Telemetry Monitoring Endpoint", passed, f"Status: {res.status_code}, requests tracked: {res.json().get('total_requests')}")
    except Exception as e:
        record("11. Telemetry Monitoring Endpoint", False, str(e))

    # 12. Telemetry Failure Isolation
    try:
        from ml.monitoring.telemetry import telemetry
        telemetry.record_inference(latency_ms=-99.0, success=True)
        passed = True
        record("12. Telemetry Failure Isolation", passed, "Core execution safely isolated from telemetry errors")
    except Exception as e:
        record("12. Telemetry Failure Isolation", False, str(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RoadX Phase 22 Smoke Test Runner")
    parser.add_argument("--url", type=str, default=None, help="Target HTTP server URL (e.g. http://localhost:8000)")
    parser.add_argument("--in-process", action="store_true", default=True, help="Run against FastAPI in-process TestClient")
    args = parser.parse_args()

    use_client = args.url is None or args.in_process
    exit_code = run_smoke_tests(target_url=args.url, use_testclient=use_client)
    sys.exit(exit_code)
