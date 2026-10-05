"""Feature engineering builder for Road Failure Prediction."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ml.common.logging_config import get_logger
from ml.failure_prediction.config import failure_config

logger = get_logger("failure_prediction.features")


class RoadFailureFeatureBuilder:
    """Builds derived civil engineering features capturing pavement stress, degradation, and environmental load."""

    def __init__(self, include_raw: bool = True) -> None:
        self.include_raw = include_raw
        self.engineered_features = failure_config.engineered_feature_columns
        self.feature_names_: List[str] = []

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Derive analytical road degradation features from preprocessed base features.

        Args:
            df: Preprocessed DataFrame containing clean base features.

        Returns:
            DataFrame containing engineered features (and raw features if include_raw=True).
        """
        features_df = pd.DataFrame(index=df.index)

        # 1. Traffic Stress: Heavy vehicle volume represents exponential equivalent single axle load (ESAL)
        features_df["traffic_stress"] = df["traffic_volume"] * df["heavy_vehicle_ratio"]

        # 2. Repair Aging: Days since repair normalized by historical maintenance cadence
        features_df["repair_aging"] = df["days_since_repair"] / (365.25 * (df["previous_repairs"] + 1.0))

        # 3. Damage Indicator: Weighted composite index combining pothole severity and surface crack proportion
        features_df["damage_indicator"] = (df["pothole_count"] * 0.70) + (df["crack_ratio"] * 100.0 * 0.30)

        # 4. Weather Stress: Acute 7d deluge coupled with chronic 30d sub-grade waterlogging and flood surcharge
        features_df["weather_stress"] = (
            df["rainfall_30d_mm"] * (1.0 + (df["flood_events_30d"] * 0.50))
            + (df["rainfall_7d_mm"] * 1.50)
        )

        # 5. Structural Vulnerability: Pavement age multiplied by loss of structural quality
        features_df["structural_vulnerability"] = df["road_age_years"] * (1.0 - df["road_quality_score"])

        # 6. Complaint Pressure: Grievance density normalized by vehicular traffic exposure
        features_df["complaint_pressure"] = df["citizen_complaints_30d"] / ((df["traffic_volume"] / 1000.0) + 1.0)

        if self.include_raw:
            final_df = pd.concat([df[failure_config.raw_feature_columns], features_df], axis=1)
        else:
            final_df = features_df

        self.feature_names_ = list(final_df.columns)
        return final_df

    def extract_features(self, record_or_df: Union[Dict[str, Any], pd.DataFrame]) -> Union[Dict[str, float], pd.DataFrame]:
        """Extract features from either a dictionary or a DataFrame."""
        if isinstance(record_or_df, dict):
            df_temp = pd.DataFrame([record_or_df])
            # Fill missing keys if needed
            for col in failure_config.raw_feature_columns:
                if col not in df_temp.columns:
                    df_temp[col] = 0.0
            feat_df = self.build_features(df_temp)
            return {col: float(feat_df.iloc[0][col]) for col in self.engineered_features}
        return self.build_features(record_or_df)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform input DataFrame into final feature matrix."""
        return self.build_features(df)


# Backward compatibility alias
FailureFeatureExtractor = RoadFailureFeatureBuilder
