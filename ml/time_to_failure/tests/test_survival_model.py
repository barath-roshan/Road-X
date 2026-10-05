"""Unit tests for WeibullSurvivalModel and KaplanMeierEstimator."""

import numpy as np
import pytest
from ml.common.exceptions import ModelNotFittedError
from ml.time_to_failure.survival_model import WeibullSurvivalModel, KaplanMeierEstimator


def test_kaplan_meier_fit_and_predict():
    km = KaplanMeierEstimator()
    times = np.array([30, 60, 90, 120, 150])
    events = np.array([1, 1, 0, 1, 0])

    km.fit(times, events)
    assert km._is_fitted is True

    s_10 = km.predict_survival_at(10.0)
    s_50 = km.predict_survival_at(50.0)
    s_200 = km.predict_survival_at(200.0)

    assert s_10 == 1.0
    assert 0.0 <= s_50 <= 1.0
    assert 0.0 <= s_200 <= 1.0
    assert s_50 >= s_200


def test_weibull_survival_model_fit_and_predict():
    X = np.array([[1.0, 2.0], [2.0, 1.0], [3.0, 4.0], [4.0, 3.0]])
    times = np.array([50.0, 120.0, 200.0, 350.0])
    events = np.array([1, 1, 0, 1])

    model = WeibullSurvivalModel()
    model.train(X, times, events)

    assert model.is_fitted is True

    # Predict median days
    pred_days = model.predict_median_days(X)
    assert len(pred_days) == 4
    assert (pred_days >= 0.0).all()

    # Predict survival probabilities across horizons
    s_30 = model.predict_survival_probability(X, 30.0)
    s_365 = model.predict_survival_probability(X, 365.0)

    assert (0.0 <= s_30).all() and (s_30 <= 1.0).all()
    assert (0.0 <= s_365).all() and (s_365 <= 1.0).all()
    # P(S(30)) >= P(S(365))
    assert (s_30 >= s_365).all()
