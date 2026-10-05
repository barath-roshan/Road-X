"""Adapter wrapping the existing pre-trained pothole YOLO segmentation model for RoadX."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Union

import numpy as np
from PIL import Image

from ml.common.exceptions import ModelArtifactNotFoundError, RoadXModelError
from ml.common.logging_config import get_logger
from ml.damage_detection.config import damage_detection_config
from ml.damage_detection.detector import RoadDamageDetector
from ml.damage_detection.schemas import DetectedDamageItem, RoadDamageDetectionResponse

logger = get_logger("damage_detection.adapter")


class ExistingPotholeModelAdapter(RoadDamageDetector):
    """Adapter wrapping the pre-existing trained PyTorch/YOLO pothole detection & segmentation model.

    Translates raw framework model outputs into standardized RoadX schemas.
    The model is loaded once upon instantiation and reused across inference requests.
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        confidence_threshold: float = damage_detection_config.confidence_threshold,
    ) -> None:
        self.model_path = Path(model_path or damage_detection_config.model_path)
        self.confidence_threshold = confidence_threshold
        self.version = damage_detection_config.model_version
        self._yolo_model: Optional[Any] = None
        self._is_loaded = False

        # Load the existing pre-trained model checkpoint on initialization
        self.load_model()

    def load_model(self) -> None:
        """Load the pre-trained Ultralytics YOLO checkpoint into memory."""
        if not self.model_path.exists():
            raise ModelArtifactNotFoundError(
                f"Existing pothole detection model checkpoint not found at: {self.model_path}"
            )

        try:
            from ultralytics import YOLO

            logger.info("Loading pre-trained pothole model checkpoint from: %s", self.model_path)
            self._yolo_model = YOLO(str(self.model_path))
            self._is_loaded = True
            logger.info(
                "Successfully loaded pre-trained YOLO model (task=%s, classes=%s)",
                getattr(self._yolo_model, "task", "segment"),
                getattr(self._yolo_model, "names", {}),
            )
        except Exception as e:
            raise RoadXModelError(f"Failed to load existing pothole YOLO model: {e}") from e

    def detect(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        confidence_threshold: Optional[float] = None,
    ) -> RoadDamageDetectionResponse:
        """Execute pothole/road damage detection on input image and return normalized schema.

        Args:
            image: Image path, OpenCV numpy BGR array, or PIL Image.
            confidence_threshold: Optional threshold override.

        Returns:
            Normalized RoadDamageDetectionResponse object.
        """
        if not self._is_loaded or self._yolo_model is None:
            raise RoadXModelError("ExistingPotholeModelAdapter is not loaded.")

        # 1. Validate input image and extract dimensions
        bgr_image, width, height = self.validate_image(image)
        thresh = confidence_threshold if confidence_threshold is not None else self.confidence_threshold
        image_surface_area = float(width * height)

        # 2. Run inference through existing pre-trained model
        try:
            results = self._yolo_model.predict(
                source=bgr_image,
                conf=thresh,
                iou=damage_detection_config.iou_threshold,
                verbose=False,
            )
        except Exception as e:
            raise RoadXModelError(f"YOLO model inference failed: {e}") from e

        normalized_detections: List[DetectedDamageItem] = []

        if results and len(results) > 0:
            result = results[0]
            boxes = getattr(result, "boxes", None)
            masks = getattr(result, "masks", None)
            class_names_dict = getattr(result, "names", {0: "Pothole"})

            if boxes is not None and len(boxes) > 0:
                xyxy_coords = boxes.xyxy.cpu().numpy()  # [N, 4] -> [x1, y1, x2, y2]
                confidences = boxes.conf.cpu().numpy()  # [N]
                class_indices = boxes.cls.cpu().numpy().astype(int)  # [N]

                polygon_xy_list = masks.xy if masks is not None else [None] * len(boxes)

                for idx in range(len(boxes)):
                    x1, y1, x2, y2 = xyxy_coords[idx]
                    conf = float(confidences[idx])
                    cls_idx = int(class_indices[idx])

                    # Translate raw class string to canonical RoadX name
                    raw_cls_name = str(class_names_dict.get(cls_idx, "pothole")).lower()
                    canonical_name = damage_detection_config.canonical_class_map.get(
                        raw_cls_name, raw_cls_name
                    )

                    # Bounding box normalization [x1, y1, x2, y2]
                    box_x1 = max(0.0, min(float(x1), float(width)))
                    box_y1 = max(0.0, min(float(y1), float(height)))
                    box_x2 = max(box_x1, min(float(x2), float(width)))
                    box_y2 = max(box_y1, min(float(y2), float(height)))

                    # Calculate area ratio = bbox_area / image_surface_area
                    box_area = (box_x2 - box_x1) * (box_y2 - box_y1)
                    area_ratio = float(np.clip(box_area / image_surface_area, 0.0, 1.0))

                    # Format optional segmentation polygon
                    poly_pts = polygon_xy_list[idx]
                    poly_tuple_list: Optional[List[tuple[float, float]]] = None
                    if poly_pts is not None and len(poly_pts) > 0:
                        poly_tuple_list = [(round(float(pt[0]), 2), round(float(pt[1]), 2)) for pt in poly_pts]

                    item = DetectedDamageItem(
                        class_name=canonical_name,
                        confidence=round(conf, 4),
                        bbox=(round(box_x1, 2), round(box_y1, 2), round(box_x2, 2), round(box_y2, 2)),
                        area_ratio=round(area_ratio, 4),
                        segmentation_polygon=poly_tuple_list,
                    )
                    normalized_detections.append(item)

        return RoadDamageDetectionResponse(
            detections=normalized_detections,
            image_width=width,
            image_height=height,
            detection_count=len(normalized_detections),
            model_version=self.version,
        )
