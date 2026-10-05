"""Test suite verifying all RoadX ML modules import cleanly."""

import importlib
import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "ml",
        "ml.common",
        "ml.common.base",
        "ml.common.config",
        "ml.common.exceptions",
        "ml.common.logging_config",
        "ml.failure_prediction",
        "ml.failure_prediction.config",
        "ml.failure_prediction.schemas",
        "ml.failure_prediction.preprocessing",
        "ml.failure_prediction.features",
        "ml.failure_prediction.model",
        "ml.failure_prediction.train",
        "ml.failure_prediction.evaluate",
        "ml.failure_prediction.predict",
        "ml.damage_detection",
        "ml.severity",
        "ml.complaint_intelligence",
        "ml.duplicate_detection",
        "ml.time_to_failure",
        "ml.priority_engine",
    ],
)
def test_module_imports(module_name: str):
    """Ensure every declared package and submodule can be imported without syntax or runtime error."""
    mod = importlib.import_module(module_name)
    assert mod is not None
