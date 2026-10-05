"""Base interface and image validation for Road Damage Detectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Tuple, Union

import cv2
import numpy as np
from PIL import Image

from ml.common.exceptions import RoadXDataError
from ml.damage_detection.config import damage_detection_config
from ml.damage_detection.schemas import RoadDamageDetectionResponse


class RoadDamageDetector(ABC):
    """Abstract Base Class for all computer vision road damage detectors in RoadX.

    RoadX components interact exclusively through this interface without depending on
    the specific underlying vision framework (PyTorch, YOLO, OpenCV, ONNX, etc.).
    """

    @abstractmethod
    def detect(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        confidence_threshold: float = damage_detection_config.confidence_threshold,
    ) -> RoadDamageDetectionResponse:
        """Run object detection / segmentation on an image input and return normalized RoadX output.

        Args:
            image: Image filepath (str/Path), OpenCV numpy array (BGR/RGB), or PIL Image.
            confidence_threshold: Minimum confidence threshold filter.

        Returns:
            RoadDamageDetectionResponse schema object.
        """
        raise NotImplementedError

    def validate_image(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
    ) -> Tuple[np.ndarray, int, int]:
        """Validate input image format, existence, readability, and non-zero dimensions.

        Args:
            image: Image path or object.

        Returns:
            Tuple of (bgr_numpy_array, width_px, height_px).

        Raises:
            RoadXDataError: If image path is missing, corrupted, unsupported, or has zero dimensions.
        """
        if image is None:
            raise RoadXDataError("Image input cannot be None.")

        # 1. Path input (str or Path)
        if isinstance(image, (str, Path)):
            img_path = Path(image)
            if not img_path.exists():
                raise RoadXDataError(f"Image file does not exist at: {img_path}")
            if img_path.is_dir():
                raise RoadXDataError(f"Target path is a directory, not an image file: {img_path}")
            if img_path.suffix.lower() not in damage_detection_config.supported_extensions:
                raise RoadXDataError(
                    f"Unsupported image file extension '{img_path.suffix}'. "
                    f"Supported types: {damage_detection_config.supported_extensions}"
                )

            # Read image using OpenCV
            bgr_arr = cv2.imread(str(img_path))
            if bgr_arr is None or bgr_arr.size == 0:
                raise RoadXDataError(f"Failed to decode or corrupted image file at: {img_path}")

        # 2. PIL Image input
        elif isinstance(image, Image.Image):
            try:
                rgb_arr = np.array(image.convert("RGB"))
                bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            except Exception as e:
                raise RoadXDataError(f"Failed to process PIL Image input: {e}") from e

        # 3. NumPy array input
        elif isinstance(image, np.ndarray):
            if image.size == 0 or image.ndim not in (2, 3):
                raise RoadXDataError(f"Invalid image numpy array shape: {image.shape}")
            bgr_arr = image.copy()
            if bgr_arr.ndim == 2:  # Grayscale to BGR
                bgr_arr = cv2.cvtColor(bgr_arr, cv2.COLOR_GRAY2BGR)

        else:
            raise RoadXDataError(f"Unsupported image input type: {type(image)}")

        height, width = bgr_arr.shape[:2]
        if height <= 0 or width <= 0:
            raise RoadXDataError(f"Invalid image dimensions: {width}x{height} pixels.")

        return bgr_arr, width, height
