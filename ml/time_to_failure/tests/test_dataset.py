"""Unit tests for survival dataset generation and censoring validation."""

import pandas as pd
from ml.time_to_failure.config import config
from ml.time_to_failure.generate_synthetic_data import generate_synthetic_survival_dataset


def test_survival_dataset_generation(tmp_path):
    dataset_path = tmp_path / "survival_test.csv"
    generate_synthetic_survival_dataset(dataset_path, num_samples=50)

    assert dataset_path.exists()
    df = pd.read_csv(dataset_path, comment="#")

    assert len(df) == 50
    assert "time_to_event_days" in df.columns
    assert "event_observed" in df.columns

    # Verify time to event is strictly positive
    assert (df["time_to_event_days"] > 0).all()

    # Verify binary censoring flags (0 or 1)
    assert set(df["event_observed"].unique()).issubset({0, 1})
