"""Training script for Time-to-Failure Prediction (Phase 7)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from ml.common.exceptions import RoadXDataError
from ml.time_to_failure.config import config
from ml.time_to_failure.generate_synthetic_data import generate_synthetic_survival_dataset
from ml.time_to_failure.features import SurvivalFeatureBuilder
from ml.time_to_failure.preprocessing import SurvivalPreprocessor
from ml.time_to_failure.survival_model import WeibullSurvivalModel
from ml.time_to_failure.predictor import TimeToFailurePredictor
from ml.time_to_failure.evaluate import (
    evaluate_survival_model,
    print_survival_evaluation_summary,
)


def load_survival_dataset(dataset_path: Path) -> pd.DataFrame:
    """Load road segment survival dataset, ignoring comment header lines."""
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}. Generating synthetic survival dataset...")
        generate_synthetic_survival_dataset(dataset_path)

    df = pd.read_csv(dataset_path, comment="#")
    required = {"time_to_event_days", "event_observed"}
    if not required.issubset(df.columns):
        raise RoadXDataError(f"Survival dataset missing required target columns: {required}")

    return df


def train_time_to_failure(
    dataset_path: Path = config.raw_dataset_path,
    model_dir: Path = config.model_dir,
) -> Dict[str, Any]:
    """Train preprocessor and Weibull survival regression model, evaluate, and save artifacts."""
    config.ensure_directories()

    print(f"Loading road segment survival dataset from {dataset_path}...")
    df = load_survival_dataset(dataset_path)

    # 1. Feature Engineering
    feature_builder = SurvivalFeatureBuilder()
    df_features = feature_builder.transform_dataframe(df)

    t_arr = df["time_to_event_days"].values.astype(np.float64)
    delta_arr = df["event_observed"].values.astype(np.int32)

    # 2. Train / Test Split
    (
        df_train,
        df_test,
        t_train,
        t_test,
        delta_train,
        delta_test,
    ) = train_test_split(
        df_features,
        t_arr,
        delta_arr,
        test_size=config.test_size,
        random_state=config.random_state,
    )

    print(f"Dataset split: Train={len(df_train)} observations, Test={len(df_test)} observations")

    # 3. Fit Preprocessor on Training Split
    preprocessor = SurvivalPreprocessor(feature_names=config.all_features)
    X_train_scaled = preprocessor.fit_transform(df_train)
    X_test_scaled = preprocessor.transform(df_test)

    # 4. Train Weibull AFT Survival Regression Model
    print("Training Weibull Parametric Survival Model...")
    survival_model = WeibullSurvivalModel(version=config.model_version)
    survival_model.train(X_train_scaled.values, t_train, delta_train)

    # 5. Evaluate on Test Split
    pred_test_days = list(survival_model.predict_median_days(X_test_scaled.values))
    metrics = evaluate_survival_model(
        t_test.tolist(), delta_test.tolist(), pred_test_days, "Weibull Survival Model"
    )
    print_survival_evaluation_summary(metrics)

    # 6. Save Artifacts & Orchestrator
    predictor = TimeToFailurePredictor(
        feature_builder=feature_builder,
        preprocessor=preprocessor,
        survival_model=survival_model,
        version=config.model_version,
    )
    predictor.save(model_dir)

    # 7. Metadata Serialization
    metadata = {
        "dataset_type": "SYNTHETIC DEVELOPMENT DATA",
        "disclaimer": (
            "Current time-to-failure results are development results based on synthetic data and "
            "must not be interpreted as production performance on real road segments."
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_version": config.model_version,
        "n_train_samples": len(df_train),
        "n_test_samples": len(df_test),
        "metrics": {
            "c_index": metrics["c_index"],
            "mae_uncensored_days": metrics["mae_uncensored_days"],
            "rmse_uncensored_days": metrics["rmse_uncensored_days"],
        },
    }

    metadata_path = model_dir / "metadata" / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nTime-to-failure model artifacts saved to: {model_dir}")
    print(f"Metadata written to: {metadata_path}")

    return {
        "metrics": metrics,
        "metadata_path": str(metadata_path),
    }


if __name__ == "__main__":
    train_time_to_failure()
