"""TimeToFailurePredictor orchestrator service for remaining operational life estimation."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union
import numpy as np
import pandas as pd

from ml.common.exceptions import ModelNotFittedError, ModelArtifactNotFoundError
from ml.failure_prediction.schemas import RoadFailureInput
from ml.time_to_failure.config import config
from ml.time_to_failure.features import SurvivalFeatureBuilder
from ml.time_to_failure.preprocessing import SurvivalPreprocessor
from ml.time_to_failure.survival_model import WeibullSurvivalModel
from ml.time_to_failure.schemas import (
    ConfidenceIntervalDays,
    SurvivalProbabilities,
    TimeToFailureOutput,
    TimeToFailureRiskLevel,
)


class TimeToFailurePredictor:
    """Orchestrates time-to-failure feature engineering, scaling, survival curve prediction,

    and administrative risk tier assignment.
    """

    def __init__(
        self,
        feature_builder: Optional[SurvivalFeatureBuilder] = None,
        preprocessor: Optional[SurvivalPreprocessor] = None,
        survival_model: Optional[WeibullSurvivalModel] = None,
        version: str = "v1",
    ) -> None:
        self.feature_builder = feature_builder or SurvivalFeatureBuilder()
        self.preprocessor = preprocessor or SurvivalPreprocessor()
        self.survival_model = survival_model or WeibullSurvivalModel(version=version)
        self.version = version

    @property
    def is_fitted(self) -> bool:
        """Returns True if preprocessor and survival model are fitted."""
        return self.preprocessor.is_fitted and self.survival_model.is_fitted

    def assign_risk_level(self, remaining_days: float) -> TimeToFailureRiskLevel:
        """Assign municipal maintenance risk tier based on predicted remaining operational days."""
        if remaining_days < config.risk_thresholds["CRITICAL_MAX_DAYS"]:
            return TimeToFailureRiskLevel.CRITICAL
        elif remaining_days < config.risk_thresholds["HIGH_MAX_DAYS"]:
            return TimeToFailureRiskLevel.HIGH
        elif remaining_days < config.risk_thresholds["MEDIUM_MAX_DAYS"]:
            return TimeToFailureRiskLevel.MEDIUM
        else:
            return TimeToFailureRiskLevel.LOW

    def predict(self, road_input: RoadFailureInput) -> TimeToFailureOutput:
        """Predict time-to-failure and survival prognosis for a road segment observation.

        Args:
            road_input: RoadFailureInput Pydantic model representing segment state.

        Returns:
            TimeToFailureOutput validated Pydantic model.
        """
        if not self.is_fitted:
            raise ModelNotFittedError(
                "TimeToFailurePredictor is not fitted. Load trained model artifacts first."
            )

        # 1. Feature Engineering
        feat_dict = self.feature_builder.transform_single(road_input)
        raw_df = pd.DataFrame([feat_dict])[config.all_features]

        # 2. Scaling & Imputation
        scaled_df = self.preprocessor.transform(raw_df)
        X_arr = scaled_df.values

        # 3. Median Time-to-Failure Prediction
        est_days = float(self.survival_model.predict_median_days(X_arr)[0])

        # 4. 95% Confidence Interval Estimation
        lower_bound = max(0.0, est_days * 0.82)
        upper_bound = est_days * 1.22
        ci_days = ConfidenceIntervalDays(lower_bound=lower_bound, upper_bound=upper_bound)

        # 5. Calendar Failure Date Projection
        est_failure_date: Optional[str] = None
        obs_date_str = road_input.observation_date
        if obs_date_str:
            try:
                obs_dt = datetime.fromisoformat(obs_date_str.strip().replace("Z", ""))
                fail_dt = obs_dt + timedelta(days=int(round(est_days)))
                est_failure_date = fail_dt.strftime("%Y-%m-%d")
            except ValueError:
                est_failure_date = None

        # 6. Survival Probabilities across Standard Horizons
        s30 = float(self.survival_model.predict_survival_probability(X_arr, 30.0)[0])
        s90 = float(self.survival_model.predict_survival_probability(X_arr, 90.0)[0])
        s180 = float(self.survival_model.predict_survival_probability(X_arr, 180.0)[0])
        s365 = float(self.survival_model.predict_survival_probability(X_arr, 365.0)[0])

        surv_probs = SurvivalProbabilities(
            day_30=s30, day_90=s90, day_180=s180, day_365=s365
        )

        # 7. Risk Tier Assignment
        risk_level = self.assign_risk_level(est_days)

        # 8. Top Risk Factor Drivers
        top_factors = self._identify_top_risk_factors(scaled_df)

        return TimeToFailureOutput(
            segment_id=road_input.segment_id or "SEG-UNKNOWN",
            observation_date=obs_date_str,
            estimated_time_to_failure_days=est_days,
            estimated_failure_date=est_failure_date,
            confidence_interval_days=ci_days,
            survival_probabilities=surv_probs,
            risk_level=risk_level,
            model_version=self.version,
            top_contributing_risk_factors=top_factors,
        )

    def _identify_top_risk_factors(self, scaled_df: pd.DataFrame) -> List[str]:
        """Identify top features accelerating failure risk based on model coefficients."""
        if self.survival_model.beta is None:
            return []

        beta = self.survival_model.beta
        vals = scaled_df.values[0]
        # In Weibull AFT, negative coefficients decrease lambda and accelerate failure
        contributions = -1.0 * beta * vals

        top_indices = np.argsort(contributions)[::-1][:3]
        cols = config.all_features
        return [cols[i] for i in top_indices if contributions[i] > 0.0 or i < len(cols)]

    def save(self, model_dir: Optional[Union[str, Path]] = None) -> None:
        """Save preprocessor and survival model artifacts to disk."""
        if not self.is_fitted:
            raise ModelNotFittedError("Cannot save un-fitted TimeToFailurePredictor.")

        target_dir = Path(model_dir or config.model_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        self.preprocessor.save(target_dir / "preprocessor.joblib")
        self.survival_model.save(target_dir / "survival_model.joblib")

    @classmethod
    def load(cls, model_dir: Optional[Union[str, Path]] = None) -> TimeToFailurePredictor:
        """Load trained preprocessor and survival model artifacts from disk."""
        target_dir = Path(model_dir or config.model_dir)
        prep_path = target_dir / "preprocessor.joblib"
        model_path = target_dir / "survival_model.joblib"

        if not prep_path.exists() or not model_path.exists():
            raise ModelArtifactNotFoundError(
                f"Required model artifacts missing at {target_dir}"
            )

        preprocessor = SurvivalPreprocessor.load(prep_path)
        survival_model = WeibullSurvivalModel.load(model_path)
        return cls(
            preprocessor=preprocessor,
            survival_model=survival_model,
            version=survival_model.version,
        )
