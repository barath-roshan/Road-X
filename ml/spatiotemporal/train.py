"""Training and Model Evaluation pipeline for Phase 20 Spatiotemporal ML vs Phase 2 Baseline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier

from ml.common.logging_config import get_logger
from ml.failure_prediction.config import failure_config
from ml.failure_prediction.features import RoadFailureFeatureBuilder
from ml.failure_prediction.preprocessing import RoadFailurePreprocessor
from ml.spatiotemporal.config import spatiotemporal_config
from ml.spatiotemporal.dataset import SpatiotemporalDatasetBuilder
from ml.spatiotemporal.model import SpatiotemporalFailureModel
from ml.spatiotemporal.spatial import SpatialFeatureBuilder
from ml.spatiotemporal.temporal import TemporalFeatureBuilder

logger = get_logger("spatiotemporal.train")


def evaluate_binary_metrics(
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    model_name: str,
) -> Dict[str, Any]:
    """Calculate comprehensive classification and regression metrics for model comparison."""
    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    try:
        roc_auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        roc_auc = 0.5

    try:
        pr_auc = float(average_precision_score(y_true, y_prob))
    except Exception:
        pr_auc = 0.5

    mae = float(mean_absolute_error(y_true, y_prob))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_prob)))
    r2 = float(r2_score(y_true, y_prob))

    return {
        "model_name": model_name,
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2_score": round(r2, 4),
    }


def run_spatiotemporal_training(
    data_path: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Execute training pipeline comparing Phase 2 Baseline vs Phase 20 Spatiotemporal Model.

    Returns:
        Dictionary summarizing evaluation comparison and artifact paths.
    """
    artifacts_folder = Path(output_dir or spatiotemporal_config.artifact_dir)
    artifacts_folder.mkdir(parents=True, exist_ok=True)

    dataset_builder = SpatiotemporalDatasetBuilder()
    raw_df = dataset_builder.load_or_generate_dataset(data_path=data_path)

    # 1. Chronological Split (80% Train, 20% Test)
    train_df, test_df = dataset_builder.chronological_split(raw_df, date_col="observation_date")

    # Preprocessing
    preprocessor = RoadFailurePreprocessor()
    preprocessor.fit(train_df)

    clean_train = preprocessor.transform(train_df)
    clean_test = preprocessor.transform(test_df)

    target_col = spatiotemporal_config.target_column
    y_train = train_df[target_col].astype(int)
    y_test = test_df[target_col].astype(int)

    # Calculate class weight balance
    pos_count = int((y_train == 1).sum())
    neg_count = int((y_train == 0).sum())
    scale_pos_weight = float(neg_count / max(1, pos_count))

    # -------------------------------------------------------------
    # MODEL 1: Phase 2 Baseline Model (Raw + Phase 2 Features)
    # -------------------------------------------------------------
    phase2_builder = RoadFailureFeatureBuilder(include_raw=True)
    X_train_p2 = phase2_builder.transform(clean_train)
    X_test_p2 = phase2_builder.transform(clean_test)

    p2_xgb = XGBClassifier(
        n_estimators=failure_config.xgboost_params.get("n_estimators", 300),
        max_depth=failure_config.xgboost_params.get("max_depth", 6),
        learning_rate=failure_config.xgboost_params.get("learning_rate", 0.05),
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    p2_calibrated = CalibratedClassifierCV(estimator=p2_xgb, method="sigmoid", cv=3)
    p2_calibrated.fit(X_train_p2, y_train)

    p2_pred = p2_calibrated.predict(X_test_p2)
    p2_prob = p2_calibrated.predict_proba(X_test_p2)[:, 1]
    p2_metrics = evaluate_binary_metrics(y_test, p2_pred, p2_prob, model_name="Phase 2 Baseline (XGBoost)")

    # -------------------------------------------------------------
    # MODEL 2: Phase 20 Spatiotemporal Model (Raw + Phase 2 + Spatial + Temporal)
    # -------------------------------------------------------------
    X_train_p20, feature_names = dataset_builder.build_feature_matrix(clean_train)
    X_test_p20, _ = dataset_builder.build_feature_matrix(clean_test)

    # Align columns
    for col in feature_names:
        if col not in X_test_p20.columns:
            X_test_p20[col] = 0.0
    X_test_p20 = X_test_p20[feature_names]

    p20_xgb = XGBClassifier(
        n_estimators=spatiotemporal_config.xgboost_params.get("n_estimators", 350),
        max_depth=spatiotemporal_config.xgboost_params.get("max_depth", 6),
        learning_rate=spatiotemporal_config.xgboost_params.get("learning_rate", 0.04),
        subsample=spatiotemporal_config.xgboost_params.get("subsample", 0.85),
        colsample_bytree=spatiotemporal_config.xgboost_params.get("colsample_bytree", 0.85),
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    p20_calibrated = CalibratedClassifierCV(estimator=p20_xgb, method="sigmoid", cv=3)
    p20_calibrated.fit(X_train_p20, y_train)

    p20_pred = p20_calibrated.predict(X_test_p20)
    p20_prob = p20_calibrated.predict_proba(X_test_p20)[:, 1]
    p20_metrics = evaluate_binary_metrics(y_test, p20_pred, p20_prob, model_name="Phase 20 Spatiotemporal Model")

    # Print comparison table
    logger.info("Phase 2 Baseline Metrics: %s", p2_metrics)
    logger.info("Phase 20 Spatiotemporal Metrics: %s", p20_metrics)

    print("\n" + "=" * 80)
    print("PHASE 20 SPATIOTEMPORAL ML VS PHASE 2 BASELINE (CHRONOLOGICAL TEST SET)")
    print("=" * 80)
    print(f"{'Metric':<20} | {'Phase 2 Baseline':<20} | {'Phase 20 Spatiotemporal':<25}")
    print("-" * 80)
    for k in ["accuracy", "precision", "recall", "f1_score", "roc_auc", "pr_auc", "mae", "rmse", "r2_score"]:
        print(f"{k:<20} | {p2_metrics[k]:<20} | {p20_metrics[k]:<25}")
    print("=" * 80 + "\n")

    # 5. Build Spatiotemporal Failure Model
    spatiotemporal_model = SpatiotemporalFailureModel(
        estimator=p20_calibrated,
        model_name=spatiotemporal_config.model_name,
        version=spatiotemporal_config.model_version,
    )
    spatiotemporal_model.feature_names_ = feature_names
    spatiotemporal_model._is_fitted = True

    # Save Bundle
    bundle = {
        "model": spatiotemporal_model,
        "preprocessor": preprocessor,
        "dataset_builder": dataset_builder,
        "feature_names": feature_names,
        "risk_thresholds": spatiotemporal_config.risk_thresholds,
        "version": spatiotemporal_config.model_version,
        "model_name": spatiotemporal_config.model_name,
        "metrics_p2_baseline": p2_metrics,
        "metrics_p20_spatiotemporal": p20_metrics,
    }

    model_save_path = artifacts_folder / "spatiotemporal_model_artifact.joblib"
    joblib.dump(bundle, model_save_path)
    logger.info("Saved spatiotemporal model artifact bundle to: %s", model_save_path)

    # Save Metadata JSON
    metadata = {
        "model_name": spatiotemporal_config.model_name,
        "version": spatiotemporal_config.model_version,
        "target": spatiotemporal_config.target_column,
        "feature_count": len(feature_names),
        "features": feature_names,
        "spatial_features": spatiotemporal_config.spatial_feature_columns,
        "temporal_features": spatiotemporal_config.temporal_feature_columns,
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "temporal_split": {
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "split_ratio": spatiotemporal_config.temporal_split_ratio,
        },
        "metrics_p2_baseline": p2_metrics,
        "metrics_p20_spatiotemporal": p20_metrics,
    }

    metadata_path = artifacts_folder / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved spatiotemporal training metadata to: %s", metadata_path)

    return {
        "model_artifact": str(model_save_path),
        "metadata_file": str(metadata_path),
        "p2_metrics": p2_metrics,
        "p20_metrics": p20_metrics,
    }


def main() -> None:
    """CLI script entrypoint for running Phase 20 spatiotemporal training."""
    parser = argparse.ArgumentParser(description="Train Phase 20 Spatiotemporal Road Failure Model.")
    parser.add_argument("--data", type=str, default=str(failure_config.raw_data_path))
    parser.add_argument("--out", type=str, default=str(spatiotemporal_config.artifact_dir))
    args = parser.parse_args()

    run_spatiotemporal_training(data_path=Path(args.data), output_dir=Path(args.out))


if __name__ == "__main__":
    main()
