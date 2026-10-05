"""Test suite verifying foundational module structure, OOP abstractions, and interfaces."""

import inspect
import pytest
from ml.common.base import BaseModel
from ml.common.exceptions import (
    ModelArtifactNotFoundError,
    ModelNotFittedError,
    RoadXConfigError,
    RoadXDataError,
    RoadXError,
    RoadXModelError,
)
from ml.failure_prediction.model import RoadFailurePredictionModel


def test_base_model_abstraction():
    """Verify that BaseModel cannot be directly instantiated without implementing abstract methods."""
    with pytest.raises(TypeError):
        BaseModel(model_name="test_model")  # type: ignore


def test_failure_prediction_model_subclasses_base_model():
    """Verify RoadFailurePredictionModel implements BaseModel interface."""
    assert issubclass(RoadFailurePredictionModel, BaseModel)
    model = RoadFailurePredictionModel()
    assert model.model_name == "road_failure_classifier"
    assert model.is_fitted is False

    # Calling predict before fitting must raise ModelNotFittedError
    with pytest.raises(ModelNotFittedError):
        model.predict([[1, 2, 3]])

    with pytest.raises(ModelNotFittedError):
        model.predict_proba([[1, 2, 3]])


def test_exception_hierarchy():
    """Verify RoadX custom exceptions inherit properly from RoadXError."""
    assert issubclass(RoadXConfigError, RoadXError)
    assert issubclass(RoadXDataError, RoadXError)
    assert issubclass(RoadXModelError, RoadXError)
    assert issubclass(ModelNotFittedError, RoadXModelError)
    assert issubclass(ModelArtifactNotFoundError, RoadXModelError)


def test_model_interface_methods():
    """Verify that required lifecycle methods exist on BaseModel."""
    for method_name in ["train", "predict", "predict_proba", "save", "load"]:
        assert hasattr(BaseModel, method_name)
        assert callable(getattr(BaseModel, method_name))
