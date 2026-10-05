"""Parametric Weibull AFT Survival Model and Kaplan-Meier Baseline Estimator."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import joblib
import numpy as np
from scipy.optimize import minimize

from ml.common.base import BaseModel
from ml.common.exceptions import ModelNotFittedError, ModelArtifactNotFoundError, RoadXModelError
from ml.time_to_failure.config import config


class KaplanMeierEstimator:
    """Non-parametric Kaplan-Meier empirical survival function estimator."""

    def __init__(self) -> None:
        self.timeline: np.ndarray = np.array([])
        self.survival_table: np.ndarray = np.array([])
        self._is_fitted: bool = False

    def fit(self, time_to_event: np.ndarray, event_observed: np.ndarray) -> KaplanMeierEstimator:
        """Fit Kaplan-Meier survival curve on survival times and censoring flags."""
        time_to_event = np.asarray(time_to_event, dtype=np.float64)
        event_observed = np.asarray(event_observed, dtype=np.int32)

        # Sort observations by time
        sorted_indices = np.argsort(time_to_event)
        times = time_to_event[sorted_indices]
        events = event_observed[sorted_indices]

        unique_times = np.unique(times[events == 1])
        if len(unique_times) == 0:
            unique_times = np.unique(times)

        survival_probs = []
        current_surv = 1.0
        n_at_risk = len(times)

        for t in unique_times:
            n_events = int(np.sum((times == t) & (events == 1)))
            n_censored = int(np.sum((times == t) & (events == 0)))
            n_current_at_risk = int(np.sum(times >= t))

            if n_current_at_risk > 0:
                current_surv *= (1.0 - (n_events / n_current_at_risk))

            survival_probs.append(current_surv)

        self.timeline = unique_times
        self.survival_table = np.array(survival_probs, dtype=np.float64)
        self._is_fitted = True
        return self

    def predict_survival_at(self, days: float) -> float:
        """Predict empirical survival probability S(days) at specified day horizon."""
        if not self._is_fitted or len(self.timeline) == 0:
            return 1.0

        if days <= 0:
            return 1.0

        idx = np.searchsorted(self.timeline, days, side="right") - 1
        if idx < 0:
            return 1.0
        return float(self.survival_table[min(idx, len(self.survival_table) - 1)])


class WeibullSurvivalModel(BaseModel):
    """Weibull Accelerated Failure Time (AFT) Parametric Survival Model.

    Models log-survival time as a linear function of road pavement features,
    correctly incorporating right-censored observation events.
    """

    def __init__(self, version: str = "v1") -> None:
        super().__init__(model_name="WeibullSurvivalModel", version=version)
        self.beta: Optional[np.ndarray] = None
        self.beta_0: float = 0.0
        self.gamma: float = 1.0  # Shape parameter
        self.km_baseline = KaplanMeierEstimator()

    def _negative_log_likelihood(
        self, params: np.ndarray, X: np.ndarray, t: np.ndarray, delta: np.ndarray
    ) -> float:
        """Compute negative log-likelihood for Weibull AFT survival regression."""
        beta = params[:-2]
        beta_0 = params[-2]
        log_gamma = float(np.clip(params[-1], -5.0, 5.0))
        gamma = math.exp(log_gamma)

        # Scale parameter lambda_i = exp(X * beta + beta_0)
        linear_pred = np.dot(X, beta) + beta_0
        # Prevent float overflow/underflow
        linear_pred = np.clip(linear_pred, -20.0, 20.0)
        lambda_i = np.exp(linear_pred)

        # Non-negative time safety
        t_safe = np.maximum(t, 1e-3)
        t_scaled = t_safe / np.maximum(lambda_i, 1e-6)

        # Log likelihood contributions:
        # For uncensored (delta=1): log(gamma/lambda) + (gamma-1)*log(t/lambda) - (t/lambda)^gamma
        # For censored (delta=0): - (t/lambda)^gamma
        log_h = np.log(np.maximum(gamma, 1e-6)) - np.log(np.maximum(lambda_i, 1e-6)) + (gamma - 1.0) * np.log(np.maximum(t_scaled, 1e-6))
        t_scaled_clipped = np.clip(t_scaled, 1e-6, 1e4)
        cum_hazard = np.power(t_scaled_clipped, np.clip(gamma, 0.01, 20.0))
        cum_hazard = np.clip(cum_hazard, 0.0, 700.0)

        log_lik = np.sum(delta * log_h - cum_hazard)
        if not np.isfinite(log_lik):
            return 1e10

        return -float(log_lik)

    def train(
        self,
        X: np.ndarray,
        time_to_event: np.ndarray,
        event_observed: np.ndarray,
        *args: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Train Weibull AFT survival regression model on feature matrix X, times, and censoring flags."""
        X_arr = np.asarray(X, dtype=np.float64)
        t_arr = np.asarray(time_to_event, dtype=np.float64)
        delta_arr = np.asarray(event_observed, dtype=np.int32)

        if len(X_arr) == 0:
            raise RoadXModelError("Cannot train survival model on empty feature matrix.")

        # Fit Kaplan-Meier empirical baseline
        self.km_baseline.fit(t_arr, delta_arr)

        n_features = X_arr.shape[1]
        # Initial parameters: beta=0, beta_0=log(median_time), log_gamma=0
        init_beta = np.zeros(n_features)
        init_beta_0 = float(np.log(max(1.0, float(np.median(t_arr)))))
        init_params = np.append(init_beta, [init_beta_0, 0.0])

        bounds = [(-10.0, 10.0)] * n_features + [(-20.0, 20.0), (-5.0, 5.0)]
        res = minimize(
            self._negative_log_likelihood,
            init_params,
            args=(X_arr, t_arr, delta_arr),
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 1000},
        )

        self.beta = res.x[:-2]
        self.beta_0 = float(res.x[-2])
        self.gamma = math.exp(float(res.x[-1]))
        self._is_fitted = True

        self.metadata = {
            "model_name": self.model_name,
            "version": self.version,
            "n_samples": len(t_arr),
            "n_events": int(np.sum(delta_arr)),
            "gamma_shape": self.gamma,
            "beta_0": self.beta_0,
        }
        return self.metadata

    def predict_median_days(self, X: np.ndarray) -> np.ndarray:
        """Predict median remaining time-to-failure (in days) for input feature matrix X."""
        if not self._is_fitted or self.beta is None:
            raise ModelNotFittedError("Survival model must be trained before predicting.")

        X_arr = np.asarray(X, dtype=np.float64)
        linear_pred = np.dot(X_arr, self.beta) + self.beta_0
        linear_pred = np.clip(linear_pred, -20.0, 20.0)
        lambda_i = np.exp(linear_pred)

        # Median time for Weibull AFT: median = lambda * (ln 2)^(1/gamma)
        median_days = lambda_i * math.pow(math.log(2.0), 1.0 / max(0.1, self.gamma))
        return np.maximum(0.0, median_days)

    def predict_survival_probability(self, X: np.ndarray, days: float) -> np.ndarray:
        """Predict survival probability S(days | X) for input feature matrix X."""
        if not self._is_fitted or self.beta is None:
            raise ModelNotFittedError("Survival model must be trained before predicting.")

        X_arr = np.asarray(X, dtype=np.float64)
        linear_pred = np.dot(X_arr, self.beta) + self.beta_0
        linear_pred = np.clip(linear_pred, -20.0, 20.0)
        lambda_i = np.exp(linear_pred)

        # Weibull survival function: S(t) = exp( - (t / lambda)^gamma )
        t_scaled = np.maximum(0.0, days) / np.maximum(1e-6, lambda_i)
        t_scaled_clipped = np.clip(t_scaled, 0.0, 1e4)
        cum_hazard = np.power(t_scaled_clipped, np.clip(self.gamma, 0.01, 20.0))
        cum_hazard = np.clip(cum_hazard, 0.0, 700.0)
        surv_prob = np.exp(-cum_hazard)

        return np.clip(surv_prob, 0.0, 1.0)

    def predict(self, X: Any, *args: Any, **kwargs: Any) -> np.ndarray:
        """Forward predict median remaining operational days."""
        return self.predict_median_days(X)

    def predict_proba(self, X: Any, *args: Any, **kwargs: Any) -> np.ndarray:
        """Forward predict 30-day survival probability."""
        return self.predict_survival_probability(X, days=30.0)

    def save(self, path: Union[str, Path]) -> None:
        """Save WeibullSurvivalModel artifact to disk."""
        if not self._is_fitted:
            raise ModelNotFittedError("Cannot save un-fitted survival model.")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        artifact = {
            "model_name": self.model_name,
            "version": self.version,
            "beta": self.beta,
            "beta_0": self.beta_0,
            "gamma": self.gamma,
            "km_baseline": self.km_baseline,
            "is_fitted": self._is_fitted,
            "metadata": self.metadata,
        }
        joblib.dump(artifact, path)

    @classmethod
    def load(cls, path: Union[str, Path]) -> WeibullSurvivalModel:
        """Load trained WeibullSurvivalModel artifact from disk."""
        path = Path(path)
        if not path.exists():
            raise ModelArtifactNotFoundError(f"Survival model artifact not found at: {path}")

        data = joblib.load(path)
        instance = cls(version=data.get("version", "v1"))
        instance.beta = data.get("beta")
        instance.beta_0 = data.get("beta_0", 0.0)
        instance.gamma = data.get("gamma", 1.0)
        instance.km_baseline = data.get("km_baseline", KaplanMeierEstimator())
        instance._is_fitted = data.get("is_fitted", True)
        instance.metadata = data.get("metadata", {})
        return instance
