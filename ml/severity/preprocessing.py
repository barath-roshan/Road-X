"""Data preprocessing and validation pipeline for Damage Severity Estimation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from ml.common.exceptions import RoadXDataError
from ml.common.logging_config import get_logger
from ml.severity.config import severity_config

logger = get_logger("severity.preprocessing")


class SeverityPreprocessor:
    """Validates raw severity feature inputs and imputes missing signals using training statistics."""

    def __init__(self, raw_features: Optional[List[str]] = None) -> None:
        self.raw_features = raw_features or severity_config.raw_feature_columns
        self.imputation_medians_: Dict[str, float] = {}
        self.is_fitted: bool = False

    def validate_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate single feature dictionary against domain rules.

        Raises:
            RoadXDataError: If physical bounds are violated.
        """
        if data.get("detection_count", 0) < 0:
            raise RoadXDataError("Negative detection count detected.")
        if data.get("total_area_ratio") is not None and not (0.0 <= float(data["total_area_ratio"]) <= 1.0):
            raise RoadXDataError(f"Total area ratio outside [0, 1]: {data.get('total_area_ratio')}")
        if data.get("max_area_ratio") is not None and not (0.0 <= float(data["max_area_ratio"]) <= 1.0):
            raise RoadXDataError(f"Max area ratio outside [0, 1]: {data.get('max_area_ratio')}")
        if data.get("max_confidence") is not None and not (0.0 <= float(data["max_confidence"]) <= 1.0):
            raise RoadXDataError(f"Max confidence score outside [0, 1]: {data.get('max_confidence')}")
        if data.get("total_bbox_area", 0) < 0:
            raise RoadXDataError("Negative bounding box area detected.")
        if data.get("traffic_volume", 0) < 0:
            raise RoadXDataError("Negative traffic volume detected.")

        return data

    def validate_dataframe(self, df: pd.DataFrame, is_training: bool = False) -> None:
        """Validate feature matrix columns and target range if training."""
        if is_training:
            target_col = severity_config.target_column
            if target_col not in df.columns:
                raise RoadXDataError(f"Training DataFrame missing target column: '{target_col}'")
            if ((df[target_col] < 0.0) | (df[target_col] > 100.0)).any():
                raise RoadXDataError("Severity target values outside [0.0, 100.0] range.")

    def fit(self, df: pd.DataFrame) -> SeverityPreprocessor:
        """Compute training statistics (medians) for leak-free imputation."""
        self.validate_dataframe(df, is_training=False)
        self.imputation_medians_ = {
            col: float(df[col].median(skipna=True))
            for col in self.raw_features
            if col in df.columns and not df[col].isnull().all()
        }
        # Provide default fallback for any unobserved column
        for col in self.raw_features:
            if col not in self.imputation_medians_:
                self.imputation_medians_[col] = 0.0
        self.is_fitted = True
        logger.info("Fitted SeverityPreprocessor across %d features", len(self.imputation_medians_))
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Impute missing values using training medians."""
        if not self.is_fitted:
            raise RoadXDataError("SeverityPreprocessor must be fitted before transforming data.")

        transformed_df = pd.DataFrame(index=df.index)
        for col in self.raw_features:
            if col in df.columns:
                transformed_df[col] = df[col].fillna(self.imputation_medians_.get(col, 0.0))
            else:
                transformed_df[col] = self.imputation_medians_.get(col, 0.0)

        return transformed_df

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit preprocessor on DataFrame and transform it."""
        return self.fit(df).transform(df)
