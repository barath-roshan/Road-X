"""Tests verifying image validation and base detector interface constraints."""

from pathlib import Path
import numpy as np
from PIL import Image
import pytest

from ml.common.exceptions import RoadXDataError
from ml.damage_detection.detector import RoadDamageDetector
from ml.damage_detection.schemas import RoadDamageDetectionResponse


class DummyDetector(RoadDamageDetector):
    """Concrete dummy subclass for testing base detector validation logic."""

    def detect(self, image, confidence_threshold=0.25):
        bgr, w, h = self.validate_image(image)
        return RoadDamageDetectionResponse(
            detections=[],
            image_width=w,
            image_height=h,
            detection_count=0,
            model_version="v1",
        )


def test_validate_image_none_raises_error():
    """Verify passing None raises descriptive RoadXDataError."""
    detector = DummyDetector()
    with pytest.raises(RoadXDataError, match="cannot be None"):
        detector.validate_image(None)


def test_validate_nonexistent_filepath_raises_error(tmp_path: Path):
    """Verify non-existent filepath raises RoadXDataError."""
    detector = DummyDetector()
    missing_file = tmp_path / "non_existent_road.jpg"
    with pytest.raises(RoadXDataError, match="does not exist"):
        detector.validate_image(missing_file)


def test_validate_directory_path_raises_error(tmp_path: Path):
    """Verify providing a directory instead of an image file raises RoadXDataError."""
    detector = DummyDetector()
    with pytest.raises(RoadXDataError, match="is a directory"):
        detector.validate_image(tmp_path)


def test_validate_unsupported_extension_raises_error(tmp_path: Path):
    """Verify unsupported extension (e.g. .txt, .pdf) raises RoadXDataError."""
    detector = DummyDetector()
    invalid_ext_file = tmp_path / "road.txt"
    invalid_ext_file.write_text("not an image")
    with pytest.raises(RoadXDataError, match="Unsupported image file extension"):
        detector.validate_image(invalid_ext_file)


def test_validate_corrupted_image_file_raises_error(tmp_path: Path):
    """Verify corrupted image file raises RoadXDataError."""
    detector = DummyDetector()
    corrupted_file = tmp_path / "corrupted.jpg"
    corrupted_file.write_bytes(b"corrupted raw data binary noise")
    with pytest.raises(RoadXDataError, match="Failed to decode or corrupted"):
        detector.validate_image(corrupted_file)


def test_validate_numpy_array_input():
    """Verify valid numpy array (BGR/RGB) extracts correct width and height."""
    detector = DummyDetector()
    dummy_arr = np.zeros((480, 640, 3), dtype=np.uint8)
    bgr, w, h = detector.validate_image(dummy_arr)
    assert w == 640
    assert h == 480
    assert bgr.shape == (480, 640, 3)


def test_validate_pil_image_input():
    """Verify PIL Image input converts cleanly to BGR numpy array."""
    detector = DummyDetector()
    pil_img = Image.new("RGB", (320, 240), color="blue")
    bgr, w, h = detector.validate_image(pil_img)
    assert w == 320
    assert h == 240
