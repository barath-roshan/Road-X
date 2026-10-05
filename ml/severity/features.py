"""Feature extraction component for Damage Severity Estimation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from ml.common.logging_config import get_logger
from ml.damage_detection.schemas import RoadDamageDetectionResponse
from ml.severity.config import severity_config
from ml.severity.schemas import RoadContextInput

logger = get_logger("severity.features")


class SeverityFeatureExtractor:
    """Extracts analytical defect severity and road-context interaction features."""

    def __init__(self, include_raw: bool = True) -> None:
        self.include_raw = include_raw
        self.raw_features = severity_config.raw_feature_columns
        self.engineered_features = severity_config.engineered_feature_columns
        self.feature_names_: List[str] = []

    def extract_from_detection_response(
        self,
        detection_response: Union[RoadDamageDetectionResponse, Dict[str, Any]],
        road_context: Optional[Union[RoadContextInput, Dict[str, Any]]] = None,
    ) -> Dict[str, float]:
        """Extract a single feature vector dictionary from a Phase 3 vision detection output and optional road context.

        Args:
            detection_response: Normalized vision output from Phase 3 detector.
            road_context: Optional road infrastructure context.

        Returns:
            Dictionary of numerical features ready for preprocessor / model.
        """
        # Parse vision response
        if isinstance(detection_response, RoadDamageDetectionResponse):
            det_dict = detection_response.model_dump()
        elif isinstance(detection_response, dict):
            det_dict = detection_response
        else:
            det_dict = {"detections": [], "image_width": 640, "image_height": 480}

        detections = det_dict.get("detections", [])
        width = float(det_dict.get("image_width", 640) or 640)
        height = float(det_dict.get("image_height", 480) or 480)
        img_surface_area = width * height

        detection_count = len(detections)

        if detection_count > 0:
            area_ratios = [float(d.get("area_ratio", 0.0)) for d in detections]
            confidences = [float(d.get("confidence", 0.0)) for d in detections]

            # Calculate bounding box areas in px^2
            bbox_areas = []
            for d in detections:
                bbox = d.get("bbox", (0, 0, 0, 0))
                if bbox and len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    area = (x2 - x1) * (y2 - y1)
                    bbox_areas.append(float(max(0.0, area)))
                else:
                    bbox_areas.append(0.0)

            total_area_ratio = float(np.clip(sum(area_ratios), 0.0, 1.0))
            max_area_ratio = float(max(area_ratios))
            avg_area_ratio = float(np.mean(area_ratios))
            max_confidence = float(max(confidences))
            avg_confidence = float(np.mean(confidences))
            total_bbox_area = float(sum(bbox_areas))
            max_bbox_area = float(max(bbox_areas))
        else:
            total_area_ratio = 0.0
            max_area_ratio = 0.0
            avg_area_ratio = 0.0
            max_confidence = 0.0
            avg_confidence = 0.0
            total_bbox_area = 0.0
            max_bbox_area = 0.0

        # Parse road context
        if isinstance(road_context, RoadContextInput):
            ctx_dict = road_context.model_dump()
        elif isinstance(road_context, dict):
            ctx_dict = road_context
        else:
            ctx_dict = {}

        road_quality = float(ctx_dict.get("road_quality_score") if ctx_dict.get("road_quality_score") is not None else 0.50)
        traffic_vol = float(ctx_dict.get("traffic_volume") if ctx_dict.get("traffic_volume") is not None else 15000.0)
        heavy_ratio = float(ctx_dict.get("heavy_vehicle_ratio") if ctx_dict.get("heavy_vehicle_ratio") is not None else 0.15)
        road_age = float(ctx_dict.get("road_age_years") if ctx_dict.get("road_age_years") is not None else 5.0)
        complaints = float(ctx_dict.get("citizen_complaints_30d") if ctx_dict.get("citizen_complaints_30d") is not None else 2.0)

        # Base features
        base_features = {
            "detection_count": float(detection_count),
            "total_area_ratio": round(total_area_ratio, 4),
            "max_area_ratio": round(max_area_ratio, 4),
            "avg_area_ratio": round(avg_area_ratio, 4),
            "max_confidence": round(max_confidence, 4),
            "avg_confidence": round(avg_confidence, 4),
            "total_bbox_area": round(total_bbox_area, 2),
            "max_bbox_area": round(max_bbox_area, 2),
            "road_quality_score": round(road_quality, 4),
            "traffic_volume": round(traffic_vol, 1),
            "heavy_vehicle_ratio": round(heavy_ratio, 4),
            "road_age_years": round(road_age, 2),
            "citizen_complaints_30d": round(complaints, 1),
        }

        # Derived engineered interaction features
        traffic_damage_interaction = traffic_vol * heavy_ratio * total_area_ratio
        quality_defect_ratio = total_area_ratio / (road_quality + 0.05)
        complaint_defect_interaction = complaints * float(detection_count)

        engineered_features = {
            "traffic_damage_interaction": round(float(traffic_damage_interaction), 4),
            "quality_defect_ratio": round(float(quality_defect_ratio), 4),
            "complaint_defect_interaction": round(float(complaint_defect_interaction), 4),
        }

        if self.include_raw:
            all_feat = {**base_features, **engineered_features}
        else:
            all_feat = engineered_features

        self.feature_names_ = list(all_feat.keys())
        return all_feat

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Derive analytical features across a pandas DataFrame of raw observation records.

        Args:
            df: DataFrame containing base numerical features.

        Returns:
            DataFrame containing raw and engineered features.
        """
        features_df = pd.DataFrame(index=df.index)

        total_area = df.get("total_area_ratio", pd.Series(0.0, index=df.index))
        quality = df.get("road_quality_score", pd.Series(0.5, index=df.index))
        traffic = df.get("traffic_volume", pd.Series(15000.0, index=df.index))
        heavy = df.get("heavy_vehicle_ratio", pd.Series(0.15, index=df.index))
        complaints = df.get("citizen_complaints_30d", pd.Series(2.0, index=df.index))
        det_count = df.get("detection_count", pd.Series(0.0, index=df.index))

        features_df["traffic_damage_interaction"] = traffic * heavy * total_area
        features_df["quality_defect_ratio"] = total_area / (quality + 0.05)
        features_df["complaint_defect_interaction"] = complaints * det_count

        if self.include_raw:
            raw_cols = [c for c in self.raw_features if c in df.columns]
            final_df = pd.concat([df[raw_cols], features_df], axis=1)
        else:
            final_df = features_df

        self.feature_names_ = list(final_df.columns)
        return final_df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform DataFrame into final feature matrix."""
        return self.build_features(df)
