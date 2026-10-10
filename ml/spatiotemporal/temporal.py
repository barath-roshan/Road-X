"""Temporal Feature Engineering for RoadX Spatiotemporal ML (Phase 20)."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from ml.common.logging_config import get_logger
from ml.spatiotemporal.config import spatiotemporal_config

logger = get_logger("spatiotemporal.temporal")


class TemporalFeatureBuilder:
    """Constructs seasonal/calendar cyclical features and historical rolling degradation trends."""

    def build_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Derive cyclical time features and historical segment rolling statistics.

        Args:
            df: DataFrame containing observation_date, segment_id, road_quality_score, etc.

        Returns:
            DataFrame containing engineered temporal features.
        """
        temporal_df = pd.DataFrame(index=df.index)

        # 1. Parse observation dates
        if "observation_date" in df.columns:
            dates = pd.to_datetime(df["observation_date"], errors="coerce")
        else:
            dates = pd.Series([pd.Timestamp.now()] * len(df), index=df.index)

        dates = dates.fillna(pd.Timestamp.now())

        months = dates.dt.month
        day_of_week = dates.dt.dayofweek
        day_of_year = dates.dt.dayofyear

        temporal_df["month"] = months
        temporal_df["day_of_week"] = day_of_week
        temporal_df["is_monsoon"] = months.isin([6, 7, 8, 9]).astype(int)

        # Season: 1 = Winter (12, 1, 2), 2 = Summer (3, 4, 5), 3 = Monsoon (6, 7, 8, 9), 4 = Autumn (10, 11)
        seasons = []
        for m in months:
            if m in [12, 1, 2]:
                seasons.append(1)
            elif m in [3, 4, 5]:
                seasons.append(2)
            elif m in [6, 7, 8, 9]:
                seasons.append(3)
            else:
                seasons.append(4)
        temporal_df["season"] = seasons

        # Cyclical Sine/Cosine transformations
        temporal_df["day_of_year_sin"] = np.round(np.sin(2.0 * np.pi * day_of_year / 365.25), 4)
        temporal_df["day_of_year_cos"] = np.round(np.cos(2.0 * np.pi * day_of_year / 365.25), 4)

        # 2. Historical Rolling Statistics (Segment-aware, strictly leak-free)
        if "segment_id" in df.columns and "road_quality_score" in df.columns:
            df_temp = df.copy()
            df_temp["_date"] = dates
            df_temp["_orig_idx"] = df.index

            # Ensure chronological order within segment
            df_temp = df_temp.sort_values(by=["segment_id", "_date"]).reset_index(drop=True)

            # Rolling 3-observation mean of road quality
            df_temp["quality_rolling_3obs_mean"] = (
                df_temp.groupby("segment_id")["road_quality_score"]
                .transform(lambda s: s.rolling(window=3, min_periods=1).mean())
            )

            # Quality decay rate: diff from previous observation for segment
            df_temp["quality_decay_rate"] = (
                df_temp.groupby("segment_id")["road_quality_score"]
                .transform(lambda s: s.diff().fillna(0.0))
            )

            # Pothole trend: 3-observation rolling change in pothole count
            if "pothole_count" in df_temp.columns:
                df_temp["pothole_trend_3obs"] = (
                    df_temp.groupby("segment_id")["pothole_count"]
                    .transform(lambda s: s.diff().rolling(window=3, min_periods=1).mean().fillna(0.0))
                )
            else:
                df_temp["pothole_trend_3obs"] = 0.0

            # Restore original index order
            df_restored = df_temp.sort_values(by="_orig_idx")
            temporal_df["quality_rolling_3obs_mean"] = df_restored["quality_rolling_3obs_mean"].values
            temporal_df["quality_decay_rate"] = df_restored["quality_decay_rate"].values
            temporal_df["pothole_trend_3obs"] = df_restored["pothole_trend_3obs"].values
        else:
            # Fallback for single inference records without history
            temporal_df["quality_rolling_3obs_mean"] = df.get("road_quality_score", 0.5)
            temporal_df["quality_decay_rate"] = 0.0
            temporal_df["pothole_trend_3obs"] = 0.0

        return temporal_df
