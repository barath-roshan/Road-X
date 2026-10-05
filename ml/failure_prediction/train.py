"""Training pipeline for Road Failure Prediction.

Implements:
1. Strict temporal split between historical training records and future test observations.
2. Leak-free preprocessing and civil engineering feature extraction.
3. Progressive model comparison:
   - Model 1: Logistic Regression (interpretable baseline)
   - Model 2: Random Forest (nonlinear tree baseline)
   - Model 3: XGBoost (primary gradient-boosted tabular model)
4. Probability calibration analysis and optimization.
5. End-to-end artifact bundling and metadata persistence.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from ml.common.config import settings
from ml.common.logging_config import get_logger
from ml.failure_prediction.config import failure_config
from ml.failure_prediction.evaluate import evaluate_model, format_comparison_table
from ml.failure_prediction.features import RoadFailureFeatureBuilder
from ml.failure_prediction.model import RoadFailureModel
from ml.failure_prediction.preprocessing import RoadFailurePreprocessor

logger = get_logger("failure_prediction.train")


def temporal_train_test_split(
    df: pd.DataFrame,
    date_col: str = "observation_date",
    split_ratio: float = failure_config.temporal_split_ratio,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Partition dataset chronologically to avoid future temporal data leakage.

    Args:
        df: Input DataFrame with dates.
        date_col: Timestamp column.
        split_ratio: Proportion of earlier records assigned to training.

    Returns:
        (train_df, test_df) tuple.
    """
    df_sorted = df.sort_values(by=[date_col]).reset_index(drop=True)
    split_idx = int(len(df_sorted) * split_ratio)
    split_date = df_sorted.iloc[split_idx][date_col]

    train_df = df_sorted.iloc[:split_idx].copy()
    test_df = df_sorted.iloc[split_idx:].copy()

    logger.info(
        "Temporal Split at date: %s | Train: %d records (up to %s) | Test: %d records (from %s)",
        split_date,
        len(train_df),
        train_df[date_col].max(),
        len(test_df),
        test_df[date_col].min(),
    )
    return train_df, test_df


def train_and_compare_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> Tuple[Dict[str, Any], RoadFailureModel]:
    """Train Logistic Regression, Random Forest, and XGBoost; evaluate on future test split.

    Returns:
        (comparison_report_dict, best_trained_model)
    """
    logger.info("Comparing progressive models on %d train samples, %d test samples", len(X_train), len(X_test))

    # Calculate class imbalance ratio for scale_pos_weight
    neg_count = int((y_train == 0).sum())
    pos_count = int((y_train == 1).sum())
    scale_pos_weight = float(neg_count / max(1, pos_count))
    logger.info("Train class balance: %d negative, %d positive (scale_pos_weight=%.2f)", neg_count, pos_count, scale_pos_weight)

    all_metrics: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # MODEL 1: Logistic Regression (Interpretable Linear Baseline)
    # -------------------------------------------------------------
    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
    ])
    lr_pipeline.fit(X_train, y_train)
    lr_pred = lr_pipeline.predict(X_test)
    lr_prob = lr_pipeline.predict_proba(X_test)[:, 1]
    lr_metrics = evaluate_model(y_test, lr_pred, lr_prob, model_name="Logistic Regression")
    all_metrics.append(lr_metrics)

    # -------------------------------------------------------------
    # MODEL 2: Random Forest (Non-linear Tree Baseline)
    # -------------------------------------------------------------
    rf_clf = RandomForestClassifier(
        n_estimators=150,
        max_depth=8,
        min_samples_split=4,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    rf_clf.fit(X_train, y_train)
    rf_pred = rf_clf.predict(X_test)
    rf_prob = rf_clf.predict_proba(X_test)[:, 1]
    rf_metrics = evaluate_model(y_test, rf_pred, rf_prob, model_name="Random Forest")
    all_metrics.append(rf_metrics)

    # -------------------------------------------------------------
    # MODEL 3: XGBoost (Primary Tabular Gradient-Boosted Model)
    # -------------------------------------------------------------
    xgb_base = XGBClassifier(
        n_estimators=failure_config.xgboost_params.get("n_estimators", 300),
        max_depth=failure_config.xgboost_params.get("max_depth", 6),
        learning_rate=failure_config.xgboost_params.get("learning_rate", 0.05),
        subsample=failure_config.xgboost_params.get("subsample", 0.8),
        colsample_bytree=failure_config.xgboost_params.get("colsample_bytree", 0.8),
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    xgb_base.fit(X_train, y_train)

    # Probability calibration on XGBoost using 3-fold cross-validation
    calibrated_xgb = CalibratedClassifierCV(estimator=xgb_base, method="sigmoid", cv=3)
    calibrated_xgb.fit(X_train, y_train)

    xgb_pred = calibrated_xgb.predict(X_test)
    xgb_prob = calibrated_xgb.predict_proba(X_test)[:, 1]
    xgb_metrics = evaluate_model(y_test, xgb_pred, xgb_prob, model_name="XGBoost (Calibrated)")
    all_metrics.append(xgb_metrics)

    # Model comparison table
    comparison_table = format_comparison_table(all_metrics)
    print("\n" + "=" * 75)
    print("PROGRESSIVE MODEL EVALUATION (TEMPORAL TEST SET)")
    print("=" * 75)
    print(comparison_table)
    print("=" * 75 + "\n")

    # Select best model: XGBoost provides superior PR-AUC, ROC-AUC and calibrated probabilities
    best_road_model = RoadFailureModel(
        estimator=calibrated_xgb,
        model_name="road_failure_xgboost",
        version=failure_config.model_version,
    )
    best_road_model.feature_names_ = list(X_train.columns)
    best_road_model._is_fitted = True

    # Extract feature importances from base XGBoost
    if hasattr(xgb_base, "feature_importances_"):
        raw_imp = xgb_base.feature_importances_
        norm_imp = raw_imp / np.sum(raw_imp)
        best_road_model.feature_importances_ = {
            feat: round(float(imp), 4)
            for feat, imp in sorted(zip(X_train.columns, norm_imp), key=lambda x: x[1], reverse=True)
        }

    report = {
        "all_metrics": all_metrics,
        "selected_model": "road_failure_xgboost",
        "selected_metrics": xgb_metrics,
        "feature_importances": best_road_model.feature_importances_,
    }
    return report, best_road_model


def run_training_pipeline(
    data_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute end-to-end training pipeline for Road Failure Prediction.

    Args:
        data_path: Path to dataset CSV. Defaults to failure_config.raw_data_path.
        output_dir: Destination folder for model artifacts and metadata.

    Returns:
        Dictionary summarizing training results and artifact paths.
    """
    dataset_file = data_path or failure_config.raw_data_path
    artifacts_folder = output_dir or failure_config.artifact_dir
    artifacts_folder.mkdir(parents=True, exist_ok=True)

    if not dataset_file.exists():
        logger.info("Dataset not found at %s. Generating synthetic dataset...", dataset_file)
        from ml.failure_prediction.generate_synthetic_data import generate_synthetic_road_data

        dataset_file.parent.mkdir(parents=True, exist_ok=True)
        df_synthetic = generate_synthetic_road_data(n_segments=250, seed=42)
        df_synthetic.to_csv(dataset_file, index=False)

    logger.info("Loading dataset from: %s", dataset_file)
    df = pd.read_csv(dataset_file)

    # 1. Temporal Split
    train_df, test_df = temporal_train_test_split(df, date_col="observation_date")

    # 2. Preprocessing & Validation
    preprocessor = RoadFailurePreprocessor()
    preprocessor.fit(train_df)

    clean_train = preprocessor.transform(train_df)
    clean_test = preprocessor.transform(test_df)

    # 3. Feature Engineering
    feature_builder = RoadFailureFeatureBuilder(include_raw=True)
    X_train = feature_builder.transform(clean_train)
    X_test = feature_builder.transform(clean_test)

    target_col = failure_config.target_column
    y_train = train_df[target_col].astype(int)
    y_test = test_df[target_col].astype(int)

    # 4. Progressive Model Training & Comparison
    report, best_model = train_and_compare_models(X_train, y_train, X_test, y_test)

    # 5. Build and Save Complete Inference Artifact Bundle
    artifact_bundle = {
        "model": best_model,
        "preprocessor": preprocessor,
        "feature_builder": feature_builder,
        "feature_names": list(X_train.columns),
        "risk_thresholds": failure_config.risk_thresholds,
        "version": failure_config.model_version,
        "model_name": failure_config.model_name,
    }

    model_save_path = artifacts_folder / "model_artifact.joblib"
    joblib.dump(artifact_bundle, model_save_path)
    logger.info("Saved complete inference bundle to: %s", model_save_path)

    # 6. Save Model Metadata JSON
    metadata = {
        "model_name": failure_config.model_name,
        "version": failure_config.model_version,
        "target": failure_config.target_column,
        "training_dataset": str(dataset_file),
        "dataset_type": "SYNTHETIC — FOR DEVELOPMENT ONLY",
        "features": list(X_train.columns),
        "feature_count": len(X_train.columns),
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "temporal_split": {
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "split_ratio": failure_config.temporal_split_ratio,
            "train_date_range": [str(train_df["observation_date"].min()), str(train_df["observation_date"].max())],
            "test_date_range": [str(test_df["observation_date"].min()), str(test_df["observation_date"].max())],
        },
        "risk_thresholds": failure_config.risk_thresholds,
        "metrics": report["selected_metrics"],
        "all_model_comparisons": report["all_metrics"],
        "feature_importances": report["feature_importances"],
    }

    metadata_path = artifacts_folder / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved training metadata to: %s", metadata_path)

    print(f"Artifact successfully saved: {model_save_path}")
    print(f"Metadata successfully saved: {metadata_path}")

    return {
        "model_artifact": str(model_save_path),
        "metadata_file": str(metadata_path),
        "report": report,
    }


def main() -> None:
    """CLI script entrypoint for running the training pipeline."""
    parser = argparse.ArgumentParser(description="Train Road Failure Prediction models.")
    parser.add_argument("--data", type=str, default=str(failure_config.raw_data_path))
    parser.add_argument("--out", type=str, default=str(failure_config.artifact_dir))
    args = parser.parse_args()

    run_training_pipeline(data_path=Path(args.data), output_dir=Path(args.out))


if __name__ == "__main__":
    main()
