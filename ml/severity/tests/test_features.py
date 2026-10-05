"""Tests verifying feature extraction for Damage Severity Estimation."""

import pytest
from ml.damage_detection.schemas import DetectedDamageItem, RoadDamageDetectionResponse
from ml.severity.features import SeverityFeatureExtractor
from ml.severity.schemas import RoadContextInput


def test_feature_extraction_from_detections_and_context():
    """Verify feature extractor handles multiple detections and road context attributes."""
    extractor = SeverityFeatureExtractor(include_raw=True)

    detection_resp = RoadDamageDetectionResponse(
        detections=[
            DetectedDamageItem(
                class_name="pothole",
                confidence=0.90,
                bbox=(100.0, 50.0, 300.0, 250.0),  # Area = 200 * 200 = 40,000 px^2
                area_ratio=0.1302,
                segmentation_polygon=None,
            ),
            DetectedDamageItem(
                class_name="pothole",
                confidence=0.85,
                bbox=(350.0, 100.0, 450.0, 200.0),  # Area = 100 * 100 = 10,000 px^2
                area_ratio=0.0326,
                segmentation_polygon=None,
            ),
        ],
        image_width=640,
        image_height=480,
        detection_count=2,
        model_version="v1",
    )

    road_ctx = RoadContextInput(
        road_quality_score=0.45,
        traffic_volume=20000.0,
        heavy_vehicle_ratio=0.25,
        road_age_years=8.0,
        citizen_complaints_30d=5,
    )

    feat_dict = extractor.extract_from_detection_response(detection_resp, road_ctx)

    assert feat_dict["detection_count"] == 2.0
    assert feat_dict["total_area_ratio"] == pytest.approx(0.1628, abs=1e-3)
    assert feat_dict["max_area_ratio"] == pytest.approx(0.1302, abs=1e-3)
    assert feat_dict["max_confidence"] == 0.90
    assert feat_dict["total_bbox_area"] == 50000.0
    assert feat_dict["road_quality_score"] == 0.45
    assert feat_dict["traffic_damage_interaction"] > 0.0


def test_feature_extraction_empty_detections():
    """Verify zero detections produce clean zero-padded defect metrics without crash."""
    extractor = SeverityFeatureExtractor(include_raw=True)

    empty_resp = RoadDamageDetectionResponse(
        detections=[],
        image_width=640,
        image_height=480,
        detection_count=0,
        model_version="v1",
    )

    feat_dict = extractor.extract_from_detection_response(empty_resp, None)

    assert feat_dict["detection_count"] == 0.0
    assert feat_dict["total_area_ratio"] == 0.0
    assert feat_dict["max_area_ratio"] == 0.0
    assert feat_dict["total_bbox_area"] == 0.0
    assert feat_dict["road_quality_score"] == 0.50  # Imputed context default
