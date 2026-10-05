"""Tests verifying DamageSeverityModel training, prediction, and serialization."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge

from ml.common.exceptions import ModelNotFittedError
from ml.severity.model import DamageSeverityModel


def test_severity_model_training_and_clipping():
    """Verify DamageSeverityModel fits, predicts continuous scores, and clips within [0.0, 100.0]."""
    X = pd.DataFrame({
        "feat_a": [1.0, 2.0, 5.0, 10.0],
        "feat_b": [0.1, 0.2, 0.8, 1.5],
    })
    y = pd.Series([10.0, 25.0, 60.0, 95.0])

    model = DamageSeverityModel(estimator=Ridge(), model_name="test_ridge")
    assert not model.is_fitted

    model.train(X, y)
    assert model.is_fitted

    preds = model.predict(X)
    assert len(preds) == 4
    assert np.all((preds >= 0.0) & (preds <= 100.0))


def test_severity_model_predict_before_fit_raises_error():
    """Verify calling predict on unfitted model raises ModelNotFittedError."""
    model = DamageSeverityModel(estimator=Ridge())
    with pytest.raises(ModelNotFittedError):
        model.predict([[1.0, 2.0]])


def test_severity_model_serialization(tmp_path: Path):
    """Verify saved severity model artifact reloads accurately."""
    X = pd.DataFrame({
        "feat_1": [1.0, 2.0, 3.0, 4.0],
        "feat_2": [10.0, 20.0, 30.0, 40.0],
    })
    y = pd.Series([15.0, 35.0, 65.0, 85.0])

    model = DamageSeverityModel(estimator=Ridge(), model_name="reload_test")
    model.train(X, y)

    save_path = tmp_path / "severity_test.joblib"
    model.save(save_path)

    loaded_model = DamageSeverityModel.load(save_path)
    assert loaded_model.is_fitted
    assert loaded_model.model_name == "reload_test"

    original_preds = model.predict(X)
    loaded_preds = loaded_model.predict(X)
    np.testing.assert_allclose(original_preds, loaded_preds)
