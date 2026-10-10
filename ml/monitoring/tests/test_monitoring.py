"""Comprehensive test suite for Phase 21 MLflow tracking, candidate evaluation, operational telemetry, and feature drift detection."""

import os
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from ml.monitoring.config import MonitoringConfig
from ml.monitoring.drift import (
    DriftAnalyzer,
    PredictionQualityMonitor,
    calculate_categorical_psi,
    calculate_numeric_psi,
)
from ml.monitoring.evaluator import CandidateModelEvaluator, ModelMetadata
from ml.monitoring.telemetry import InferenceTelemetry
from ml.monitoring.tracker import MLflowTracker


# ==============================================================================
# 1. MLFLOW TRACKER TESTS
# ==============================================================================


def test_mlflow_tracker_local_logging(tmp_path):
    """Test experiment logging saves summary and metadata locally."""
    tracking_dir = tmp_path / "mlruns"
    tracker = MLflowTracker(
        tracking_uri=f"file:///{tracking_dir.as_posix()}",
        experiment_name="test_experiment",
        enabled=True,
    )
    tracker.history_file = tmp_path / "history.json"

    params = {"n_estimators": 100, "learning_rate": 0.05, "api_key": "SECRET_SHOULD_BE_EXCLUDED"}
    metrics = {"f1_score": 0.88, "roc_auc": 0.94, "precision": 0.86, "recall": 0.89}
    tags = {"phase": "test_phase", "version": "v1.0"}
    artifacts = {"feature_importance": {"potholes": 0.45, "vibration": 0.35}}

    result = tracker.log_experiment(
        params=params,
        metrics=metrics,
        tags=tags,
        artifacts=artifacts,
        run_name="unit_test_run",
    )

    assert result["run_id"] is not None
    assert "api_key" not in result["params"]  # Privacy check: secret excluded
    assert result["params"]["n_estimators"] == 100
    assert result["metrics"]["f1_score"] == 0.88

    # Verify history persistence
    history = tracker.get_experiment_history()
    assert len(history) == 1
    assert history[0]["run_name"] == "unit_test_run"


def test_mlflow_tracker_disabled(tmp_path):
    """Test tracker gracefully skips MLflow calls and saves local fallback when disabled."""
    tracker = MLflowTracker(enabled=False)
    tracker.history_file = tmp_path / "disabled_history.json"

    result = tracker.log_experiment(
        params={"algo": "XGBoost"},
        metrics={"f1_score": 0.85},
        run_name="disabled_run",
    )

    assert result["run_id"] is not None
    assert result["mlflow_tracked"] is False
    assert len(tracker.get_experiment_history()) == 1


def test_mlflow_tracker_server_failure_handling(tmp_path):
    """Test that when MLflow server/backend raises an error, tracker falls back safely."""
    tracker = MLflowTracker(enabled=True)
    tracker._is_active = True
    tracker.history_file = tmp_path / "failure_history.json"

    with patch("mlflow.start_run", side_effect=RuntimeError("MLflow server unreachable")):
        # Must not raise an exception
        result = tracker.log_experiment(
            params={"algo": "LogisticRegression"},
            metrics={"f1_score": 0.77},
        )
        assert result["run_id"] is not None
        assert len(tracker.get_experiment_history()) == 1


# ==============================================================================
# 2. MODEL METADATA & CANDIDATE EVALUATION TESTS
# ==============================================================================


def test_model_metadata_serialization():
    """Verify ModelMetadata data structure contract."""
    metadata = ModelMetadata(
        model_id="spatiotemporal_xgb",
        version="v1.0",
        algorithm="XGBClassifier",
        feature_schema_version="2.0",
        target="road_failure_within_90d",
        created_at="2026-10-10T00:00:00Z",
        metrics={"f1_score": 0.85, "roc_auc": 0.91},
    )

    data = metadata.to_dict()
    assert data["model_id"] == "spatiotemporal_xgb"
    assert data["metrics"]["roc_auc"] == 0.91


def test_candidate_evaluator_promoted():
    """Candidate exceeding baseline and passing all acceptance thresholds is promoted."""
    evaluator = CandidateModelEvaluator(
        min_precision=0.75,
        min_recall=0.70,
        min_f1=0.75,
        min_roc_auc=0.85,
    )

    candidate_metrics = {"precision": 0.82, "recall": 0.78, "f1_score": 0.80, "roc_auc": 0.89}
    baseline_metrics = {"precision": 0.76, "recall": 0.72, "f1_score": 0.74, "roc_auc": 0.86}

    decision = evaluator.evaluate_candidate(
        candidate_metrics=candidate_metrics,
        baseline_metrics=baseline_metrics,
        candidate_version="v2.0",
        baseline_version="v1.0",
    )

    assert decision.recommended_for_promotion is True
    assert all(decision.criteria_evaluations.values())
    assert "Recommended for controlled promotion" in decision.decision_reason


def test_candidate_evaluator_rejected_on_threshold():
    """Candidate failing a hard threshold (F1 < 0.75) is rejected."""
    evaluator = CandidateModelEvaluator(min_f1=0.75)

    candidate_metrics = {"precision": 0.80, "recall": 0.60, "f1_score": 0.68, "roc_auc": 0.86}
    baseline_metrics = {"precision": 0.78, "recall": 0.74, "f1_score": 0.76, "roc_auc": 0.86}

    decision = evaluator.evaluate_candidate(
        candidate_metrics=candidate_metrics,
        baseline_metrics=baseline_metrics,
    )

    assert decision.recommended_for_promotion is False
    assert decision.criteria_evaluations["min_f1_passed"] is False
    assert "rejected" in decision.decision_reason.lower()


def test_candidate_evaluator_rejected_on_f1_regression():
    """Candidate with lower F1 than baseline by more than allowable margin is rejected."""
    evaluator = CandidateModelEvaluator(max_f1_drop_margin=0.01)

    candidate_metrics = {"precision": 0.78, "recall": 0.75, "f1_score": 0.76, "roc_auc": 0.87}
    baseline_metrics = {"precision": 0.86, "recall": 0.82, "f1_score": 0.84, "roc_auc": 0.90}

    decision = evaluator.evaluate_candidate(
        candidate_metrics=candidate_metrics,
        baseline_metrics=baseline_metrics,
    )

    assert decision.recommended_for_promotion is False
    assert decision.criteria_evaluations["f1_improvement_or_parity_passed"] is False


# ==============================================================================
# 3. INFERENCE OPERATIONAL TELEMETRY TESTS
# ==============================================================================


def test_inference_telemetry_counters_and_latencies():
    """Verify thread-safe operational metrics aggregation."""
    tel = InferenceTelemetry()
    tel.reset()

    tel.record_inference(latency_ms=45.2, success=True, model_id="pipeline", model_version="v1.0", prediction_label="HIGH")
    tel.record_inference(latency_ms=52.8, success=True, model_id="pipeline", model_version="v1.0", prediction_label="HIGH")
    tel.record_inference(latency_ms=61.0, success=True, model_id="pipeline", model_version="v1.0", prediction_label="LOW")
    tel.record_inference(latency_ms=10.0, success=False, model_id="pipeline", model_version="v1.0", is_validation_failure=True)

    metrics = tel.get_metrics()

    assert metrics["total_requests"] == 4
    assert metrics["successful_requests"] == 3
    assert metrics["failed_requests"] == 1
    assert metrics["validation_failures"] == 1
    assert metrics["success_rate_pct"] == 75.0

    lat = metrics["latency_metrics"]
    assert lat["sample_size"] == 4
    assert lat["min_ms"] == 10.0
    assert lat["max_ms"] == 61.0
    assert lat["avg_ms"] > 0

    assert metrics["model_inferences"]["pipeline:v1.0"] == 4
    assert metrics["prediction_distribution"]["HIGH"] == 2
    assert metrics["prediction_distribution"]["LOW"] == 1


def test_inference_telemetry_failure_isolation():
    """Verify that telemetry recording errors do not propagate exceptions."""
    tel = InferenceTelemetry()
    mock_deque = MagicMock()
    mock_deque.append.side_effect = RuntimeError("Queue overflow")
    original_deque = tel.latencies_ms
    try:
        tel.latencies_ms = mock_deque
        # Recording must not raise an exception
        tel.record_inference(latency_ms=30.0, success=True)
    finally:
        tel.latencies_ms = original_deque


# ==============================================================================
# 4. DATA & FEATURE DRIFT ANALYSIS TESTS
# ==============================================================================


def test_psi_calculation_stable_distribution():
    """Stable distribution should produce low PSI (< 0.10)."""
    np.random.seed(42)
    ref = np.random.normal(loc=50.0, scale=10.0, size=500)
    curr = np.random.normal(loc=50.2, scale=10.1, size=500)

    psi = calculate_numeric_psi(ref, curr)
    assert psi < 0.10


def test_psi_calculation_shifted_distribution():
    """Shifted distribution should produce high PSI (>= 0.25)."""
    np.random.seed(42)
    ref = np.random.normal(loc=50.0, scale=5.0, size=500)
    curr = np.random.normal(loc=75.0, scale=5.0, size=500)  # Distinct shift

    psi = calculate_numeric_psi(ref, curr)
    assert psi >= 0.25


def test_categorical_psi_stable_vs_shifted():
    """Test discrete category PSI calculation."""
    ref = pd.Series(["A", "A", "B", "B", "C"] * 50)
    curr_stable = pd.Series(["A", "A", "B", "B", "C"] * 50)
    curr_shifted = pd.Series(["A"] * 200 + ["C"] * 50)

    psi_stable = calculate_categorical_psi(ref, curr_stable)
    psi_shifted = calculate_categorical_psi(ref, curr_shifted)

    assert psi_stable < 0.05
    assert psi_shifted > 0.25


def test_drift_analyzer_full_report():
    """Test DriftAnalyzer end-to-end report generation across multiple feature types."""
    np.random.seed(42)
    n = 100

    ref_df = pd.DataFrame({
        "traffic_density": np.random.uniform(0.1, 0.9, n),
        "vibration_index": np.random.normal(5.0, 1.0, n),
        "road_type": ["asphalt", "concrete"] * (n // 2),
    })

    curr_df = pd.DataFrame({
        "traffic_density": np.random.uniform(0.1, 0.9, n),  # stable
        "vibration_index": np.random.normal(9.0, 1.0, n),   # significantly shifted
        "road_type": ["asphalt", "concrete"] * (n // 2),    # stable
    })

    analyzer = DriftAnalyzer(min_sample_size=15)
    report = analyzer.analyze(reference_data=ref_df, current_data=curr_df)

    assert report.features_analyzed == 3
    assert "vibration_index" in report.features_with_drift
    assert report.feature_results["traffic_density"]["drift_status"] == "NO_DRIFT"
    assert report.feature_results["vibration_index"]["drift_status"] in ("HIGH_DRIFT", "MODERATE_DRIFT")
    assert report.overall_drift_detected is True


def test_drift_analyzer_insufficient_data():
    """Sample sizes below threshold should return INSUFFICIENT_DATA without crashing."""
    ref_df = pd.DataFrame({"score": [1.0, 2.0, 3.0]})
    curr_df = pd.DataFrame({"score": [1.5, 2.5]})

    analyzer = DriftAnalyzer(min_sample_size=10)
    report = analyzer.analyze(reference_data=ref_df, current_data=curr_df)

    assert report.overall_status == "INSUFFICIENT_DATA"
    assert report.feature_results["score"]["drift_status"] == "INSUFFICIENT_DATA"


def test_drift_analyzer_missing_values_and_schema_mismatch():
    """Test missing value accounting and schema mismatch warnings."""
    ref_df = pd.DataFrame({
        "feature_a": [1.0, np.nan, 3.0, 4.0, 5.0] * 10,
        "feature_b": [10, 20, 30, 40, 50] * 10,
    })
    curr_df = pd.DataFrame({
        "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0] * 10,
        "feature_extra": [99] * 50,  # missing feature_b, extra feature_extra
    })

    analyzer = DriftAnalyzer(min_sample_size=10)
    report = analyzer.analyze(reference_data=ref_df, current_data=curr_df)

    assert len(report.schema_warnings) > 0
    assert report.feature_results["feature_a"]["ref_missing_pct"] > 0


# ==============================================================================
# 5. PREDICTION QUALITY MONITOR TESTS
# ==============================================================================


def test_prediction_quality_unvalidated_without_ground_truth():
    """Ground truth absence correctly marks quality monitoring as unavailable."""
    res = PredictionQualityMonitor.evaluate(predictions=[1, 0, 1], ground_truth=None)
    assert res["status"] == "UNAVAILABLE_NO_GROUND_TRUTH"
    assert res["is_validated"] is False


def test_prediction_quality_with_ground_truth():
    """Verified ground truth computes classification metrics and confusion matrix."""
    preds = [1, 1, 0, 0]
    truth = [1, 0, 0, 1]

    res = PredictionQualityMonitor.evaluate(predictions=preds, ground_truth=truth)
    assert res["status"] == "EVALUATED_WITH_GROUND_TRUTH"
    assert res["is_validated"] is True
    metrics = res["metrics"]
    assert metrics["sample_size"] == 4
    assert metrics["accuracy"] == 0.50
    assert "confusion_matrix" in metrics


# ==============================================================================
# 6. FASTAPI MONITORING HTTP ENDPOINTS TESTS
# ==============================================================================


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_api_telemetry_endpoint(client):
    """GET /api/v1/ml/monitoring/telemetry returns HTTP 200 with aggregated metrics."""
    response = client.get("/api/v1/ml/monitoring/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "latency_metrics" in data
    assert "model_inferences" in data


def test_api_experiments_endpoint(client):
    """GET /api/v1/ml/monitoring/experiments returns HTTP 200 with list."""
    response = client.get("/api/v1/ml/monitoring/experiments")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_candidate_evaluate_endpoint(client):
    """POST /api/v1/ml/monitoring/evaluate returns evaluation decision."""
    payload = {
        "candidate_metrics": {"precision": 0.85, "recall": 0.80, "f1_score": 0.82, "roc_auc": 0.90},
        "baseline_metrics": {"precision": 0.78, "recall": 0.75, "f1_score": 0.76, "roc_auc": 0.86},
        "candidate_version": "v2.0_candidate",
        "baseline_version": "v1.0_baseline",
    }
    response = client.post("/api/v1/ml/monitoring/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["recommended_for_promotion"] is True
    assert "decision_reason" in data


def test_api_drift_endpoint(client):
    """POST /api/v1/ml/monitoring/drift returns drift report."""
    np.random.seed(42)
    ref_records = [{"temp": float(x), "rain": float(y)} for x, y in zip(np.random.normal(25, 2, 30), np.random.normal(50, 5, 30))]
    curr_records = [{"temp": float(x), "rain": float(y)} for x, y in zip(np.random.normal(25, 2, 30), np.random.normal(50, 5, 30))]

    payload = {
        "reference_data": ref_records,
        "current_data": curr_records,
        "features": ["temp", "rain"],
    }
    response = client.post("/api/v1/ml/monitoring/drift", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["features_analyzed"] == 2
    assert "feature_results" in data
