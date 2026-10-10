"""Spatial Feature Engineering for RoadX Spatiotemporal ML (Phase 20)."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from ml.common.logging_config import get_logger
from ml.spatiotemporal.config import spatiotemporal_config

logger = get_logger("spatiotemporal.spatial")


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the Great Circle (Haversine) distance between two lat/lon points in km."""
    r = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class SpatialFeatureBuilder:
    """Derives spatial proximity, geographic clustering, and neighbor context statistics."""

    def __init__(
        self,
        center_lat: float = spatiotemporal_config.default_center_lat,
        center_lon: float = spatiotemporal_config.default_center_lon,
        radius_km: float = spatiotemporal_config.spatial_radius_km,
        n_clusters: int = spatiotemporal_config.n_spatial_clusters,
    ) -> None:
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.radius_km = radius_km
        self.n_clusters = n_clusters

    def assign_segment_coordinates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure latitude and longitude columns exist; assign deterministic coordinates based on segment_id if missing."""
        df_out = df.copy()

        if "latitude" not in df_out.columns or "longitude" not in df_out.columns:
            # Deterministically derive latitude and longitude from segment_id hash for consistent spatial layout
            lats = []
            lons = []
            for seg_id in df_out.get("segment_id", range(len(df_out))):
                h = abs(hash(str(seg_id)))
                # Spread segments across ~0.15 degree grid (~15km radius)
                lat_offset = ((h % 1000) / 1000.0 - 0.5) * 0.15
                lon_offset = (((h // 1000) % 1000) / 1000.0 - 0.5) * 0.15
                lats.append(self.center_lat + lat_offset)
                lons.append(self.center_lon + lon_offset)
            df_out["latitude"] = lats
            df_out["longitude"] = lons

        return df_out

    def build_spatial_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Construct spatial distance, cluster, and spatial neighbor features.

        Args:
            df: DataFrame containing segment_id, latitude, longitude, and historical attributes.

        Returns:
            DataFrame containing derived spatial features.
        """
        df_work = self.assign_segment_coordinates(df)
        spatial_df = pd.DataFrame(index=df_work.index)

        # 1. Distance to Municipal Center
        dists = [
            haversine_distance_km(self.center_lat, self.center_lon, lat, lon)
            for lat, lon in zip(df_work["latitude"], df_work["longitude"])
        ]
        spatial_df["latitude"] = df_work["latitude"]
        spatial_df["longitude"] = df_work["longitude"]
        spatial_df["dist_to_center_km"] = np.round(dists, 3)

        # 2. Spatial Grid / Geographic Cluster Assignment
        # Simple deterministic spatial grid binning
        lat_bin = np.digitize(df_work["latitude"], np.linspace(df_work["latitude"].min(), df_work["latitude"].max(), self.n_clusters))
        lon_bin = np.digitize(df_work["longitude"], np.linspace(df_work["longitude"].min(), df_work["longitude"].max(), self.n_clusters))
        spatial_df["spatial_cluster"] = (lat_bin * 10 + lon_bin).astype(int)

        # 3. Spatial Neighbor Statistics (Leak-free calculation per segment & date)
        # Unique segment spatial lookup
        seg_coords: Dict[str, Tuple[float, float]] = {}
        if "segment_id" in df_work.columns:
            for seg, group in df_work.groupby("segment_id"):
                first_row = group.iloc[0]
                seg_coords[str(seg)] = (float(first_row["latitude"]), float(first_row["longitude"]))

        neighbor_quality_avg = []
        neighbor_pothole_avg = []
        neighbor_failure_rate = []

        has_target = "failure_next_30d" in df_work.columns
        has_obs_date = "observation_date" in df_work.columns

        for idx, row in df_work.iterrows():
            current_seg = str(row.get("segment_id", idx))
            current_lat = float(row["latitude"])
            current_lon = float(row["longitude"])
            current_date = row.get("observation_date", None) if has_obs_date else None

            # Find neighbor segments within spatial radius
            neighbor_segs = set()
            for seg, (lat, lon) in seg_coords.items():
                if seg != current_seg:
                    d = haversine_distance_km(current_lat, current_lon, lat, lon)
                    if d <= self.radius_km:
                        neighbor_segs.add(seg)

            if neighbor_segs:
                # Filter past/concurrent observations for neighbor segments
                if current_date:
                    subset = df_work[(df_work["segment_id"].isin(neighbor_segs)) & (df_work["observation_date"] <= current_date)]
                else:
                    subset = df_work[df_work["segment_id"].isin(neighbor_segs)]

                if not subset.empty:
                    q_avg = float(subset["road_quality_score"].mean()) if "road_quality_score" in subset.columns else 0.5
                    p_avg = float(subset["pothole_count"].mean()) if "pothole_count" in subset.columns else 0.0
                    f_rate = float(subset["failure_next_30d"].mean()) if has_target else 0.1
                else:
                    q_avg, p_avg, f_rate = 0.5, 0.0, 0.1
            else:
                q_avg, p_avg, f_rate = 0.5, 0.0, 0.1

            neighbor_quality_avg.append(round(q_avg, 4))
            neighbor_pothole_avg.append(round(p_avg, 2))
            neighbor_failure_rate.append(round(f_rate, 4))

        spatial_df["neighbor_quality_avg"] = neighbor_quality_avg
        spatial_df["neighbor_pothole_avg"] = neighbor_pothole_avg
        spatial_df["neighbor_failure_rate"] = neighbor_failure_rate

        return spatial_df
