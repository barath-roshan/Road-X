"""Unit tests for SurvivalPreprocessor scaling and median imputation."""

import pandas as pd
import pytest
from ml.common.exceptions import ModelNotFittedError
from ml.time_to_failure.preprocessing import SurvivalPreprocessor
from ml.time_to_failure.config import config


def test_preprocessor_fit_transform():
    df = pd.DataFrame(
        [
            {col: 10.0 for col in config.all_features},
            {col: 20.0 for col in config.all_features},
        ]
    )

    preprocessor = SurvivalPreprocessor()
    assert preprocessor.is_fitted is False

    scaled_df = preprocessor.fit_transform(df)
    assert preprocessor.is_fitted is True
    assert scaled_df.shape == (2, len(config.all_features))


def test_preprocessor_unfitted_raises_error():
    preprocessor = SurvivalPreprocessor()
    df = pd.DataFrame([{col: 10.0 for col in config.all_features}])
    with pytest.raises(ModelNotFittedError):
        preprocessor.transform(df)


def test_preprocessor_missing_value_imputation():
    df_train = pd.DataFrame(
        [
            {col: 10.0 for col in config.all_features},
            {col: 30.0 for col in config.all_features},
        ]
    )
    preprocessor = SurvivalPreprocessor()
    preprocessor.fit(df_train)

    # Test sample with missing column values (None / NaN)
    df_missing = pd.DataFrame([{"road_age_years": None}])
    scaled_df = preprocessor.transform(df_missing)

    assert not scaled_df.isna().any().any()
