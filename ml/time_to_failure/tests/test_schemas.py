"""Unit tests for Time-to-Failure Pydantic schemas and risk level assignment."""

from ml.time_to_failure.schemas import (
    ConfidenceIntervalDays,
    SurvivalProbabilities,
    TimeToFailureOutput,
    TimeToFailureRiskLevel,
)


def test_survival_probabilities_rounding():
    sp = SurvivalProbabilities(
        day_30=0.88456,
        day_90=0.45123,
        day_180=0.12345,
        day_365=0.01234,
    )

    assert sp.day_30 == 0.8846
    assert sp.day_90 == 0.4512
    assert sp.day_180 == 0.1235
    assert sp.day_365 == 0.0123


def test_confidence_interval_rounding():
    ci = ConfidenceIntervalDays(lower_bound=45.678, upper_bound=92.345)
    assert ci.lower_bound == 45.7
    assert ci.upper_bound == 92.3
