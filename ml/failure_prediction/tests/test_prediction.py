"""Tests verifying model training, serialization, loading, and end-to-end inference."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from ml.common.exceptions import ModelArtifactNotFoundError, RoadXDataError
from ml.failure_prediction.config import failure_config
from ml.failure_prediction.features import RoadFailureFeatureBuilder
from ml.failure_prediction.model import RoadFailureModel
from ml.failure_prediction.predict import RoadFailurePredictor, predict_failure_risk
from ml.failure_prediction.preprocessing import RoadFailurePreprocessor
from ml.failure_prediction.schemas import (
    FailurePredictionOutput,
    FailureRiskLevel,
    RoadFailureInput,
)


def test_model_training_and_probabilities():
    """Verify RoadFailureModel trains, produces class predictions and bounded probabilities."""
    X = pd.DataFrame({
        "feat_a": [1.0, 2.0, 5.0, 6.0],
        "feat_b": [0.1, 0.2, 0.8, 0.9],
    })
    y = pd.Series([0, 0, 1, 1])

    model = RoadFailureModel(estimator=LogisticRegression(), model_name="test_lr")
    assert not model.is_fitted

    model.train(X, y)
    assert model.is_fitted

    preds = model.predict(X)
    assert len(preds) == 4
    assert set(preds).issubset({0, 1})

    probs = model.predict_proba(X)
    assert probs.shape == (4, 2)
    assert np.all((probs >= 0.0) & (probs <= 1.0))
    assert np.allclose(np.sum(probs, axis=1), 1.0)


def test_end_to_end_inference_with_trained_artifact():
    """Verify RoadFailurePredictor produces valid FailurePredictionOutput from saved artifact."""
    if not failure_config.artifact_file.exists():
        pytest.skip("Model artifact not yet trained.")

    predictor = RoadFailurePredictor(failure_config.artifact_file)

    sample_input = {
        "road_age_years": 9.2,
        "road_length_m": 250.0,
        "lane_count": 2,
        "road_quality_score": 0.45,
        "traffic_volume": 28000.0,
        "heavy_vehicle_ratio": 0.32,
        "average_speed_kmph": 42.0,
        "rainfall_7d_mm": 120.0,
        "rainfall_30d_mm": 380.0,
        "temperature_avg_c": 32.0,
        "flood_events_30d": 2,
        "days_since_repair": 850.0,
        "previous_repairs": 3,
        "previous_failures": 2,
        "citizen_complaints_30d": 8,
        "pothole_count": 7,
        "crack_ratio": 0.14,
    }

    result = predictor.predict(sample_input)

    assert isinstance(result, FailurePredictionOutput)
    assert 0.0 <= result.failure_probability <= 1.0
    assert result.risk_level in [
        FailureRiskLevel.LOW,
        FailureRiskLevel.MEDIUM,
        FailureRiskLevel.HIGH,
        FailureRiskLevel.CRITICAL,
    ]
    assert result.model_version == failure_config.model_version
    assert isinstance(result.top_contributing_factors, list)


def test_predictor_risk_mapping():
    """Verify probability-to-risk threshold mapping rules."""
    predictor = RoadFailurePredictor(
        model_artifact_path=None,
        artifact_bundle={
            "model": RoadFailureModel(estimator=LogisticRegression()),
            "preprocessor": RoadFailurePreprocessor(),
            "feature_builder": RoadFailureFeatureBuilder(),
            "risk_thresholds": {"low_max": 0.30, "medium_max": 0.60, "high_max": 0.80},
            "version": "v1",
            "model_name": "test",
        },
    )

    assert predictor.map_probability_to_risk(0.15) == FailureRiskLevel.LOW
    assert predictor.map_probability_to_risk(0.45) == FailureRiskLevel.MEDIUM
    assert predictor.map_probability_to_risk(0.72) == FailureRiskLevel.HIGH
    assert predictor.map_probability_to_risk(0.88) == FailureRiskLevel.CRITICAL


def test_invalid_input_fails_clearly():
    """Verify physically impossible values trigger clear error during prediction."""
    if not failure_config.artifact_file.exists():
        pytest.skip("Model artifact not yet trained.")

    predictor = RoadFailurePredictor(failure_config.artifact_file)
    invalid_input = {
        "road_age_years": -5.0,  # Impossible negative age
        "road_length_m": 250.0,
        "lane_count": 2,
        "road_quality_score": 0.45,
        "traffic_volume": 28000.0,
        "heavy_vehicle_ratio": 0.32,
        "average_speed_kmph": 42.0,
        "rainfall_7d_mm": 120.0,
        "rainfall_30d_mm": 380.0,
        "temperature_avg_c": 32.0,
        "flood_events_30d": 2,
        "days_since_repair": 850.0,
        "previous_repairs": 3,
        "previous_failures": 2,
        "citizen_complaints_30d": 8,
        "pothole_count": 7,
        "crack_ratio": 0.14,
    }

    with pytest.raises(RoadXDataError, match="Negative road age"):
        predictor.predict(invalid_input)


def test_artifact_persistence_and_reload(tmp_path: Path):
    """Verify saved bundle preserves model state and produces identical outputs."""
    X = pd.DataFrame({
        "feat_1": [1.0, 2.0, 3.0, 4.0],
        "feat_2": [10.0, 20.0, 30.0, 40.0],
    })
    y = pd.Series([0, 0, 1, 1])

    model = RoadFailureModel(estimator=LogisticRegression(), model_name="reload_test")
    model.train(X, y)

    save_file = tmp_path / "test_model.joblib"
    model.save(save_file)

    loaded_model = RoadFailureModel.load(save_file)
    assert loaded_model.is_fitted
    assert loaded_model.model_name == "reload_test"

    original_preds = model.predict_proba(X)
    loaded_preds = loaded_model.predict_proba(X)
    np.testing.assert_allclose(original_preds, loaded_preds)
