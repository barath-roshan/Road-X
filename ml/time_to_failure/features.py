"""Feature engineering utilities for Time-to-Failure Survival Analysis."""

from __future__ import annotations

from typing import Any, Dict
import pandas as pd

from ml.failure_prediction.schemas import RoadFailureInput
from ml.time_to_failure.config import BASE_FEATURE_NAMES, ENGINEERED_FEATURE_NAMES, ALL_FEATURE_NAMES


def compute_survival_features(data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute civil engineering distress features from raw road segment attributes.

    Ensures zero temporal leakage by calculating features strictly using observation time state.
    """
    traffic_vol = float(data.get("traffic_volume", 0.0))
    heavy_ratio = float(data.get("heavy_vehicle_ratio", 0.0))
    days_repair = float(data.get("days_since_repair", 0.0))
    prev_repairs = int(data.get("previous_repairs", 0))
    potholes = float(data.get("pothole_count", 0))
    cracks = float(data.get("crack_ratio", 0.0))
    rain_30d = float(data.get("rainfall_30d_mm", 0.0))
    rain_7d = float(data.get("rainfall_7d_mm", 0.0))
    floods = int(data.get("flood_events_30d", 0))
    age = float(data.get("road_age_years", 0.0))
    quality = float(data.get("road_quality_score", 0.5))
    complaints = int(data.get("citizen_complaints_30d", 0))

    # 1. Traffic stress index
    traffic_stress = traffic_vol * heavy_ratio

    # 2. Repair aging metric
    repair_aging = days_repair / (365.25 * (prev_repairs + 1))

    # 3. Composite damage indicator
    damage_indicator = (potholes * 0.70) + (cracks * 100.0 * 0.30)

    # 4. Weather saturation stress
    weather_stress = rain_30d * (1.0 + floods * 0.50) + rain_7d * 1.50

    # 5. Structural vulnerability
    structural_vulnerability = age * (1.0 - max(0.0, min(1.0, quality)))

    # 6. Grievance complaint pressure per traffic volume
    complaint_pressure = complaints / ((traffic_vol / 1000.0) + 1.0)

    features = dict(data)
    features.update(
        {
            "traffic_stress": traffic_stress,
            "repair_aging": repair_aging,
            "damage_indicator": damage_indicator,
            "weather_stress": weather_stress,
            "structural_vulnerability": structural_vulnerability,
            "complaint_pressure": complaint_pressure,
        }
    )
    return features


class SurvivalFeatureBuilder:
    """Builder for extracting feature vectors from RoadFailureInput Pydantic models or DataFrames."""

    def __init__(self) -> None:
        self.feature_names = ALL_FEATURE_NAMES

    def transform_single(self, input_schema: RoadFailureInput) -> Dict[str, Any]:
        """Transform a single RoadFailureInput into an engineered feature dictionary."""
        data_dict = input_schema.model_dump()
        return compute_survival_features(data_dict)

    def transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform a DataFrame of raw road observations into engineered survival feature DataFrame."""
        out_df = df.copy()

        out_df["traffic_stress"] = out_df["traffic_volume"] * out_df["heavy_vehicle_ratio"]
        out_df["repair_aging"] = out_df["days_since_repair"] / (
            365.25 * (out_df["previous_repairs"] + 1)
        )
        out_df["damage_indicator"] = (out_df["pothole_count"] * 0.70) + (
            out_df["crack_ratio"] * 100.0 * 0.30
        )
        out_df["weather_stress"] = (
            out_df["rainfall_30d_mm"] * (1.0 + out_df["flood_events_30d"] * 0.50)
            + out_df["rainfall_7d_mm"] * 1.50
        )
        out_df["structural_vulnerability"] = out_df["road_age_years"] * (
            1.0 - out_df["road_quality_score"]
        )
        out_df["complaint_pressure"] = out_df["citizen_complaints_30d"] / (
            (out_df["traffic_volume"] / 1000.0) + 1.0
        )

        return out_df[self.feature_names]
