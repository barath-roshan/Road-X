"""Feature engineering transformers for road failure risk estimation."""

from __future__ import annotations

from typing import Any, Dict
from ml.common.logging_config import get_logger

logger = get_logger("failure_prediction.features")


class FailureFeatureExtractor:
    """Extracts analytical features capturing road distress, environmental pressure, and vulnerability."""

    def __init__(self) -> None:
        self.feature_names = [
            "severity_index",
            "water_damage_risk",
            "traffic_stress_factor",
        ]

    def extract_features(self, record_dict: Dict[str, Any]) -> Dict[str, float]:
        """Compute distress indices from raw grievance attributes.

        Args:
            record_dict: Cleaned dictionary representation of road grievance.

        Returns:
            Dictionary of computed analytical features.
        """
        depth = float(record_dict.get("estimated_depth_cm") or 0.0)
        area = float(record_dict.get("estimated_area_sqm") or 0.0)
        rainfall = float(record_dict.get("rainfall_recent_mm") or 0.0)
        traffic = str(record_dict.get("traffic_volume_estimate", "medium")).lower()

        traffic_multiplier = {"low": 1.0, "medium": 1.5, "high": 2.0}.get(traffic, 1.2)

        # Baseline heuristic features serving as inputs for the upcoming ML model
        severity_index = (depth * 0.6) + (area * 0.4)
        water_damage_risk = rainfall * (1.5 if depth > 5.0 else 1.0)
        traffic_stress_factor = severity_index * traffic_multiplier

        return {
            "severity_index": round(severity_index, 4),
            "water_damage_risk": round(water_damage_risk, 4),
            "traffic_stress_factor": round(traffic_stress_factor, 4),
        }
