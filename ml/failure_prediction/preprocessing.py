"""Data preprocessing and validation pipeline for Road Failure Prediction."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ml.common.exceptions import RoadXDataError
from ml.common.logging_config import get_logger
from ml.failure_prediction.config import failure_config
from ml.failure_prediction.schemas import RoadFailureInput

logger = get_logger("failure_prediction.preprocessing")


class RoadFailurePreprocessor:
    """Validates raw road records, enforces physical boundaries, and imputes missing signals."""

    def __init__(self, raw_features: Optional[List[str]] = None) -> None:
        self.raw_features = raw_features or failure_config.raw_feature_columns
        self.imputation_medians_: Dict[str, float] = {}
        self.is_fitted: bool = False

    def validate_record(self, record: Union[Dict[str, Any], RoadFailureInput, pd.Series]) -> Dict[str, Any]:
        """Validate single record against civil engineering physical domain rules.

        Raises:
            RoadXDataError: If physical domain rules are violated.
        """
        if isinstance(record, RoadFailureInput):
            data = record.model_dump()
        elif isinstance(record, pd.Series):
            data = record.to_dict()
        elif isinstance(record, dict):
            data = dict(record)
        else:
            raise RoadXDataError(f"Unsupported record type: {type(record)}")

        # Explicit numerical domain assertions
        if data.get("road_age_years", 0) is not None and data.get("road_age_years", 0) < 0:
            raise RoadXDataError(f"Negative road age detected: {data.get('road_age_years')}")
        if data.get("road_length_m", 1) is not None and data.get("road_length_m", 1) <= 0:
            raise RoadXDataError(f"Invalid non-positive road length: {data.get('road_length_m')}")
        if data.get("lane_count", 1) is not None and data.get("lane_count", 1) < 1:
            raise RoadXDataError(f"Invalid lane count: {data.get('lane_count')}")
        if data.get("road_quality_score") is not None and not (0.0 <= float(data["road_quality_score"]) <= 1.0):
            raise RoadXDataError(f"Road quality score outside [0, 1]: {data.get('road_quality_score')}")
        if data.get("traffic_volume", 0) is not None and data.get("traffic_volume", 0) < 0:
            raise RoadXDataError(f"Negative traffic volume detected: {data.get('traffic_volume')}")
        if data.get("heavy_vehicle_ratio") is not None and not (0.0 <= float(data["heavy_vehicle_ratio"]) <= 1.0):
            raise RoadXDataError(f"Heavy vehicle ratio outside [0, 1]: {data.get('heavy_vehicle_ratio')}")
        if (data.get("rainfall_7d_mm", 0) is not None and data.get("rainfall_7d_mm", 0) < 0) or (
            data.get("rainfall_30d_mm", 0) is not None and data.get("rainfall_30d_mm", 0) < 0
        ):
            raise RoadXDataError("Negative precipitation measurement detected.")
        if data.get("flood_events_30d", 0) is not None and data.get("flood_events_30d", 0) < 0:
            raise RoadXDataError("Negative flood event count detected.")
        if data.get("days_since_repair", 0) is not None and data.get("days_since_repair", 0) < 0:
            raise RoadXDataError("Negative days since repair detected.")
        if (data.get("previous_repairs", 0) is not None and data.get("previous_repairs", 0) < 0) or (
            data.get("previous_failures", 0) is not None and data.get("previous_failures", 0) < 0
        ):
            raise RoadXDataError("Negative historical counts detected.")
        if data.get("citizen_complaints_30d", 0) is not None and data.get("citizen_complaints_30d", 0) < 0:
            raise RoadXDataError("Negative citizen complaint count detected.")
        if data.get("pothole_count", 0) is not None and data.get("pothole_count", 0) < 0:
            raise RoadXDataError("Negative pothole count detected.")
        if data.get("crack_ratio") is not None and not (0.0 <= float(data["crack_ratio"]) <= 1.0):
            raise RoadXDataError(f"Crack ratio outside [0, 1]: {data.get('crack_ratio')}")

        # Check through Pydantic schema if dict
        if isinstance(record, dict):
            try:
                validated = RoadFailureInput(**data)
                data = validated.model_dump()
            except Exception as e:
                raise RoadXDataError(f"Record validation failed schema checks: {e}") from e

        return data

    def validate_dataframe(self, df: pd.DataFrame, is_training: bool = False) -> None:
        """Validate entire DataFrame columns, physical constraints, duplicates, and target validity.

        Raises:
            RoadXDataError: If DataFrame lacks required columns or contains corrupted data.
        """
        # 1. Column existence
        missing_cols = [c for c in self.raw_features if c not in df.columns]
        if missing_cols:
            raise RoadXDataError(f"DataFrame is missing required feature columns: {missing_cols}")

        if is_training:
            target_col = failure_config.target_column
            if target_col not in df.columns:
                raise RoadXDataError(f"Training DataFrame is missing target column: '{target_col}'")
            # Check target values are purely binary 0 and 1
            unique_targets = set(df[target_col].dropna().unique())
            if not unique_targets.issubset({0, 1}):
                raise RoadXDataError(f"Invalid target values found: {unique_targets}. Must be {{0, 1}}.")
            if len(unique_targets) < 2:
                raise RoadXDataError(f"Severe target imbalance: only single class present ({unique_targets}).")

        # 2. Duplicate rows check
        dup_count = df.duplicated(subset=self.raw_features).sum()
        if dup_count > 0:
            logger.warning("Detected %d duplicate feature rows in dataset.", dup_count)

        # 3. Domain constraints on full matrix
        if (df["road_age_years"] < 0).any():
            raise RoadXDataError("Dataset contains negative road age values.")
        if (df["traffic_volume"] < 0).any():
            raise RoadXDataError("Dataset contains negative traffic volume values.")
        if ((df["heavy_vehicle_ratio"] < 0.0) | (df["heavy_vehicle_ratio"] > 1.0)).any():
            raise RoadXDataError("Heavy vehicle ratio out of [0, 1] range.")
        if ((df["road_quality_score"] < 0.0) | (df["road_quality_score"] > 1.0)).any():
            raise RoadXDataError("Road quality score out of [0, 1] range.")
        if ((df["crack_ratio"] < 0.0) | (df["crack_ratio"] > 1.0)).any():
            raise RoadXDataError("Crack ratio out of [0, 1] range.")
        if (df["pothole_count"] < 0).any():
            raise RoadXDataError("Negative pothole count detected in dataset.")

    def fit(self, df: pd.DataFrame) -> RoadFailurePreprocessor:
        """Compute training statistics (e.g. feature medians) for leak-free imputation."""
        self.validate_dataframe(df, is_training=False)
        self.imputation_medians_ = {
            col: float(df[col].median(skipna=True))
            for col in self.raw_features
            if col in df.columns
        }
        self.is_fitted = True
        logger.info("Fitted RoadFailurePreprocessor across %d features", len(self.imputation_medians_))
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Impute missing values and prepare clean numerical feature DataFrame."""
        if not self.is_fitted:
            raise RoadXDataError("RoadFailurePreprocessor must be fitted before transforming data.")

        missing_cols = [c for c in self.raw_features if c not in df.columns]
        if missing_cols:
            raise RoadXDataError(f"Missing required columns during transform: {missing_cols}")

        transformed_df = df[self.raw_features].copy()

        # Fill missing values using training medians
        for col, median_val in self.imputation_medians_.items():
            if col in transformed_df.columns:
                if transformed_df[col].isnull().any():
                    transformed_df[col] = transformed_df[col].fillna(median_val)

        return transformed_df

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit preprocessor on DataFrame and transform it."""
        return self.fit(df).transform(df)


# Backward compatibility alias
FailureDataPreprocessor = RoadFailurePreprocessor
