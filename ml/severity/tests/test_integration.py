"""Integration test verifying end-to-end flow: Image -> Phase 3 Detector -> Phase 4 Severity Estimator."""

from pathlib import Path
import pytest

from ml.damage_detection.adapter import ExistingPotholeModelAdapter
from ml.damage_detection.config import damage_detection_config
from ml.severity.config import severity_config
from ml.severity.predict import DamageSeverityPredictor
from ml.severity.schemas import RoadContextInput, SeverityPredictionOutput


def test_end_to_end_detector_to_severity_pipeline():
    """Verify complete pipeline integration from raw image to normalized detection and severity prediction."""
    if not damage_detection_config.model_path.exists():
        pytest.skip(f"Phase 3 detection model checkpoint missing at: {damage_detection_config.model_path}")
    if not severity_config.artifact_file.exists():
        pytest.skip(f"Phase 4 severity model artifact missing at: {severity_config.artifact_file}")

    sample_img_path = Path("data/raw/sample_road_test.jpg")
    if not sample_img_path.exists():
        pytest.skip("Sample road test image missing.")

    # 1. Instantiate Phase 3 existing pothole detector
    detector = ExistingPotholeModelAdapter()

    # 2. Run vision detection on sample image
    det_response = detector.detect(sample_img_path, confidence_threshold=0.10)
    assert det_response.image_width > 0
    assert det_response.image_height > 0

    # 3. Instantiate Phase 4 severity predictor
    severity_predictor = DamageSeverityPredictor()

    # 4. Optional road infrastructure context
    road_context = RoadContextInput(
        road_quality_score=0.45,
        traffic_volume=22000.0,
        heavy_vehicle_ratio=0.25,
        road_age_years=7.5,
        citizen_complaints_30d=4,
    )

    # 5. Predict severity score and level from normalized detection response + context
    severity_output = severity_predictor.predict(
        detections=det_response,
        road_context=road_context,
    )

    # 6. Assertions on final output
    assert isinstance(severity_output, SeverityPredictionOutput)
    assert 0.0 <= severity_output.severity_score <= 100.0
    assert severity_output.severity_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert severity_output.model_version == severity_config.model_version
