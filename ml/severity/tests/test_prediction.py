"""Tests verifying DamageSeverityPredictor inference and configurable level conversion."""

from pathlib import Path
import pytest

from ml.common.exceptions import RoadXDataError
from ml.damage_detection.schemas import DetectedDamageItem, RoadDamageDetectionResponse
from ml.severity.config import severity_config
from ml.severity.evaluate import score_to_level
from ml.severity.predict import DamageSeverityPredictor
from ml.severity.schemas import DamageSeverityLevel, RoadContextInput, SeverityPredictionOutput


def test_score_to_level_mapping():
    """Verify configurable continuous score-to-level mapping thresholds."""
    assert score_to_level(15.0) == DamageSeverityLevel.LOW
    assert score_to_level(45.0) == DamageSeverityLevel.MEDIUM
    assert score_to_level(72.0) == DamageSeverityLevel.HIGH
    assert score_to_level(88.0) == DamageSeverityLevel.CRITICAL


def test_end_to_end_severity_prediction():
    """Verify DamageSeverityPredictor produces valid SeverityPredictionOutput from trained artifact."""
    if not severity_config.artifact_file.exists():
        pytest.skip("Severity model artifact not yet trained.")

    predictor = DamageSeverityPredictor(severity_config.artifact_file)

    det_resp = RoadDamageDetectionResponse(
        detections=[
            DetectedDamageItem(
                class_name="pothole",
                confidence=0.91,
                bbox=(120.0, 80.0, 420.0, 350.0),
                area_ratio=0.18,
                segmentation_polygon=None,
            )
        ],
        image_width=640,
        image_height=480,
        detection_count=1,
        model_version="v1",
    )

    road_ctx = RoadContextInput(
        road_quality_score=0.40,
        traffic_volume=25000.0,
        heavy_vehicle_ratio=0.30,
        road_age_years=9.0,
        citizen_complaints_30d=7,
    )

    output = predictor.predict(det_resp, road_ctx)

    assert isinstance(output, SeverityPredictionOutput)
    assert 0.0 <= output.severity_score <= 100.0
    assert output.severity_level in [
        DamageSeverityLevel.LOW,
        DamageSeverityLevel.MEDIUM,
        DamageSeverityLevel.HIGH,
        DamageSeverityLevel.CRITICAL,
    ]
    assert isinstance(output.contributing_factors, list)
    assert output.model_version == severity_config.model_version
