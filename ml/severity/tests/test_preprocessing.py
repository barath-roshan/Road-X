"""Tests verifying severity data preprocessing, bounds validation, and imputation."""

import pandas as pd
import pytest

from ml.common.exceptions import RoadXDataError
from ml.severity.preprocessing import SeverityPreprocessor


def test_valid_record_passes_validation():
    """Verify valid feature dictionary passes validate_record."""
    preprocessor = SeverityPreprocessor()
    valid_record = {
        "detection_count": 2,
        "total_area_ratio": 0.15,
        "max_area_ratio": 0.10,
        "max_confidence": 0.92,
        "total_bbox_area": 40000.0,
        "traffic_volume": 15000.0,
    }
    validated = preprocessor.validate_record(valid_record)
    assert validated["detection_count"] == 2


@pytest.mark.parametrize(
    "invalid_patch, error_pattern",
    [
        ({"detection_count": -1}, "Negative detection count"),
        ({"total_area_ratio": 1.5}, r"Total area ratio outside \[0, 1\]"),
        ({"max_confidence": -0.2}, r"Max confidence score outside \[0, 1\]"),
        ({"total_bbox_area": -100.0}, "Negative bounding box area"),
        ({"traffic_volume": -50.0}, "Negative traffic volume"),
    ],
)
def test_invalid_values_raise_data_error(invalid_patch, error_pattern):
    """Verify physical bounds violations raise RoadXDataError."""
    preprocessor = SeverityPreprocessor()
    base_record = {
        "detection_count": 1,
        "total_area_ratio": 0.05,
        "max_area_ratio": 0.05,
        "max_confidence": 0.88,
        "total_bbox_area": 10000.0,
        "traffic_volume": 10000.0,
    }
    base_record.update(invalid_patch)
    with pytest.raises(RoadXDataError, match=error_pattern):
        preprocessor.validate_record(base_record)


def test_preprocessor_imputation_without_leakage():
    """Verify preprocessor fits training medians for leak-free imputation."""
    preprocessor = SeverityPreprocessor()
    train_df = pd.DataFrame([
        {"detection_count": 1, "total_area_ratio": 0.05, "traffic_volume": 10000.0},
        {"detection_count": 3, "total_area_ratio": 0.25, "traffic_volume": 30000.0},
    ])
    preprocessor.fit(train_df)
    assert preprocessor.is_fitted
    assert preprocessor.imputation_medians_["traffic_volume"] == 20000.0

    test_df = train_df.copy()
    test_df.loc[0, "traffic_volume"] = None
    transformed = preprocessor.transform(test_df)
    assert transformed.loc[0, "traffic_volume"] == 20000.0
