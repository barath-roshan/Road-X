"""Tests verifying ExistingPotholeModelAdapter loading, inference, and output normalization."""

from pathlib import Path
import numpy as np
import pytest

from ml.common.exceptions import ModelArtifactNotFoundError, RoadXDataError
from ml.damage_detection.adapter import ExistingPotholeModelAdapter
from ml.damage_detection.config import damage_detection_config
from ml.damage_detection.schemas import DetectedDamageItem, RoadDamageDetectionResponse


def test_missing_model_checkpoint_raises_error(tmp_path: Path):
    """Verify loading from a missing checkpoint path raises ModelArtifactNotFoundError."""
    missing_ckpt = tmp_path / "non_existent_yolo.pt"
    with pytest.raises(ModelArtifactNotFoundError, match="model checkpoint not found"):
        ExistingPotholeModelAdapter(model_path=missing_ckpt)


def test_adapter_loads_existing_pothole_model():
    """Verify ExistingPotholeModelAdapter loads the pre-trained weights successfully."""
    if not damage_detection_config.model_path.exists():
        pytest.skip(f"Model checkpoint not found at: {damage_detection_config.model_path}")

    adapter = ExistingPotholeModelAdapter()
    assert adapter._is_loaded
    assert adapter._yolo_model is not None


def test_adapter_inference_on_valid_image(tmp_path: Path):
    """Verify running inference on a valid image produces a normalized RoadDamageDetectionResponse."""
    if not damage_detection_config.model_path.exists():
        pytest.skip(f"Model checkpoint not found at: {damage_detection_config.model_path}")

    adapter = ExistingPotholeModelAdapter()

    # Create dummy road image array (640x480 pixels)
    img_arr = np.zeros((480, 640, 3), dtype=np.uint8)

    response = adapter.detect(img_arr, confidence_threshold=0.10)

    assert isinstance(response, RoadDamageDetectionResponse)
    assert response.image_width == 640
    assert response.image_height == 480
    assert response.detection_count == len(response.detections)
    assert response.model_version == damage_detection_config.model_version

    # Validate detection items if any defects were detected
    for item in response.detections:
        assert isinstance(item, DetectedDamageItem)
        assert isinstance(item.class_name, str)
        assert 0.0 <= item.confidence <= 1.0
        assert 0.0 <= item.area_ratio <= 1.0
        x1, y1, x2, y2 = item.bbox
        assert x1 <= x2
        assert y1 <= y2
        assert 0.0 <= x1 <= 640.0
        assert 0.0 <= y1 <= 480.0


def test_adapter_inference_on_invalid_image_raises_error():
    """Verify invalid image input (e.g. non-existent file) raises RoadXDataError."""
    if not damage_detection_config.model_path.exists():
        pytest.skip(f"Model checkpoint not found at: {damage_detection_config.model_path}")

    adapter = ExistingPotholeModelAdapter()
    with pytest.raises(RoadXDataError):
        adapter.detect("invalid_non_existent_file_12345.jpg")


def test_schema_bounding_box_normalization():
    """Verify DetectedDamageItem enforces [x1, y1, x2, y2] bbox constraints and area_ratio."""
    item = DetectedDamageItem(
        class_name="pothole",
        confidence=0.92,
        bbox=(100.0, 50.0, 300.0, 250.0),
        area_ratio=0.15,
        segmentation_polygon=[(100.0, 50.0), (300.0, 50.0), (300.0, 250.0)],
    )

    assert item.class_name == "pothole"
    assert item.confidence == 0.92
    assert item.bbox == (100.0, 50.0, 300.0, 250.0)
    assert item.area_ratio == 0.15
