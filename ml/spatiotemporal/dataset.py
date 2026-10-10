"""Spatiotemporal Dataset Builder & Chronological Split utility for Phase 20."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from ml.common.config import settings
from ml.common.logging_config import get_logger
from ml.failure_prediction.config import failure_config
from ml.failure_prediction.features import RoadFailureFeatureBuilder
from ml.failure_prediction.generate_synthetic_data import generate_synthetic_road_data
from ml.spatiotemporal.config import spatiotemporal_config
from ml.spatiotemporal.spatial import SpatialFeatureBuilder
from ml.spatiotemporal.temporal import TemporalFeatureBuilder

logger = get_logger("spatiotemporal.dataset")


class SpatiotemporalDatasetBuilder:
    """Assembles spatiotemporal feature matrices and chronologically partitioned datasets."""

    def __init__(
        self,
        spatial_builder: Optional[SpatialFeatureBuilder] = None,
        temporal_builder: Optional[TemporalFeatureBuilder] = None,
        phase2_feature_builder: Optional[RoadFailureFeatureBuilder] = None,
    ) -> None:
        self.spatial_builder = spatial_builder or SpatialFeatureBuilder()
        self.temporal_builder = temporal_builder or TemporalFeatureBuilder()
        self.phase2_feature_builder = phase2_feature_builder or RoadFailureFeatureBuilder(include_raw=True)

    def load_or_generate_dataset(
        self,
        data_path: Optional[Path | str] = None,
        n_segments: int = 250,
        seed: int = 42,
    ) -> pd.DataFrame:
        """Load raw CSV dataset or generate synthetic panel dataset with spatial coordinates."""
        csv_path = Path(data_path or failure_config.raw_data_path)

        if csv_path.exists():
            logger.info("Loading existing dataset from %s", csv_path)
            df = pd.read_csv(csv_path)
        else:
            logger.info("Generating new synthetic spatiotemporal dataset (%d segments, seed=%d)...", n_segments, seed)
            df = generate_synthetic_road_data(n_segments=n_segments, seed=seed)
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(csv_path, index=False)

        # Ensure spatial coordinates exist
        df = self.spatial_builder.assign_segment_coordinates(df)
        return df

    def build_feature_matrix(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Combine raw features, Phase 2 engineered features, spatial features, and temporal features.

        Returns:
            (feature_matrix_df, list_of_all_feature_names)
        """
        df_work = df.copy()
        for col in failure_config.raw_feature_columns:
            if col not in df_work.columns:
                df_work[col] = 0.0

        # 1. Base + Phase 2 Features
        phase2_df = self.phase2_feature_builder.transform(df_work)

        # 2. Spatial Features
        spatial_df = self.spatial_builder.build_spatial_features(df_work)

        # 3. Temporal Features
        temporal_df = self.temporal_builder.build_temporal_features(df_work)


        # Combine all features into single DataFrame
        full_df = pd.concat([phase2_df, spatial_df, temporal_df], axis=1)

        # Deduplicate column names if any overlap
        full_df = full_df.loc[:, ~full_df.columns.duplicated()].copy()
        feature_names = list(full_df.columns)

        return full_df, feature_names

    def chronological_split(
        self,
        df: pd.DataFrame,
        date_col: str = "observation_date",
        split_ratio: float = spatiotemporal_config.temporal_split_ratio,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Chronologically split dataset into train and test partitions to prevent temporal leakage.

        Args:
            df: Input DataFrame.
            date_col: Timestamp column.
            split_ratio: Ratio of earlier observations for training (e.g. 0.80).

        Returns:
            (train_df, test_df) tuple.
        """
        df_sorted = df.sort_values(by=[date_col, "segment_id"]).reset_index(drop=True)
        split_idx = int(len(df_sorted) * split_ratio)

        train_df = df_sorted.iloc[:split_idx].copy()
        test_df = df_sorted.iloc[split_idx:].copy()

        logger.info(
            "Chronological Split: Train=%d samples (up to %s) | Test=%d samples (from %s)",
            len(train_df),
            train_df[date_col].max(),
            len(test_df),
            test_df[date_col].min(),
        )
        return train_df, test_df
