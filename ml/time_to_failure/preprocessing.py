"""Preprocessing and input validation pipeline for Time-to-Failure Analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler

from ml.common.exceptions import RoadXDataError, ModelNotFittedError, ModelArtifactNotFoundError
from ml.time_to_failure.config import config


class SurvivalPreprocessor:
    """Preprocesses road observation feature data for survival analysis modeling.

    Handles median imputation, standard scaling, and schema validation.
    """

    def __init__(self, feature_names: Optional[List[str]] = None) -> None:
        self.feature_names = feature_names or config.all_features
        self.scaler = StandardScaler()
        self.medians: Dict[str, float] = {}
        self._is_fitted: bool = False

    @property
    def is_fitted(self) -> bool:
        """Returns True if preprocessor has been fitted on training data."""
        return self._is_fitted

    def fit(self, df: pd.DataFrame) -> SurvivalPreprocessor:
        """Fit median imputers and StandardScaler on training feature DataFrame."""
        if df.empty:
            raise RoadXDataError("Cannot fit preprocessor on empty DataFrame.")

        # Compute medians for imputation
        for col in self.feature_names:
            if col in df.columns:
                self.medians[col] = float(df[col].median(skipna=True))
            else:
                self.medians[col] = 0.0

        # Impute missing values before fitting scaler
        df_imputed = df[self.feature_names].fillna(self.medians)
        self.scaler.fit(df_imputed)
        self._is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Impute missing values and apply StandardScaler to feature DataFrame."""
        if not self._is_fitted:
            raise ModelNotFittedError("SurvivalPreprocessor must be fitted before transform().")

        df_imputed = df.copy()
        for col in self.feature_names:
            if col not in df_imputed.columns:
                df_imputed[col] = self.medians.get(col, 0.0)
            else:
                df_imputed[col] = df_imputed[col].fillna(self.medians.get(col, 0.0))

        scaled_arr = self.scaler.transform(df_imputed[self.feature_names])
        return pd.DataFrame(scaled_arr, columns=self.feature_names, index=df.index)

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit preprocessor parameters and return transformed scaled DataFrame."""
        self.fit(df)
        return self.transform(df)

    def save(self, path: Union[str, Path]) -> None:
        """Persist fitted preprocessor to disk."""
        if not self._is_fitted:
            raise ModelNotFittedError("Cannot save un-fitted preprocessor.")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "feature_names": self.feature_names,
                "scaler": self.scaler,
                "medians": self.medians,
                "is_fitted": self._is_fitted,
            },
            path,
        )

    @classmethod
    def load(cls, path: Union[str, Path]) -> SurvivalPreprocessor:
        """Load fitted preprocessor artifact from disk."""
        path = Path(path)
        if not path.exists():
            raise ModelArtifactNotFoundError(f"Preprocessor artifact not found at: {path}")

        data = joblib.load(path)
        instance = cls(feature_names=data.get("feature_names"))
        instance.scaler = data["scaler"]
        instance.medians = data.get("medians", {})
        instance._is_fitted = data.get("is_fitted", True)
        return instance
