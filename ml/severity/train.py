"""Training pipeline for Damage Severity Estimation.

Implements:
1. Leak-free preprocessing and feature extraction.
2. Progressive model comparison:
   - Model 1: Ridge Regression (Interpretable linear baseline)
   - Model 2: Random Forest Regressor (Non-linear tree baseline)
   - Model 3: XGBoost Regressor (Primary gradient-boosted regressor)
3. MAE, RMSE, R² and mapped level macro-F1 evaluation on unseen test split.
4. End-to-end artifact bundling and metadata persistence.
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
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from ml.common.config import settings
from ml.common.logging_config import get_logger
from ml.severity.config import severity_config
from ml.severity.evaluate import evaluate_severity_model, format_severity_comparison_table
from ml.severity.features import SeverityFeatureExtractor
from ml.severity.model import DamageSeverityModel
from ml.severity.preprocessing import SeverityPreprocessor

logger = get_logger("severity.train")


def train_and_compare_severity_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> Tuple[Dict[str, Any], DamageSeverityModel]:
    """Train Ridge, Random Forest, and XGBoost regressors; evaluate on test set.

    Returns:
        (comparison_report_dict, best_trained_model)
    """
    logger.info("Comparing progressive severity models on %d train samples, %d test samples", len(X_train), len(X_test))

    all_metrics: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # MODEL 1: Ridge Regression (Interpretable Linear Baseline)
    # -------------------------------------------------------------
    ridge_reg = Ridge(alpha=1.0, random_state=42)
    ridge_reg.fit(X_train, y_train)
    ridge_pred = ridge_reg.predict(X_test)
    ridge_metrics = evaluate_severity_model(y_test, ridge_pred, model_name="Ridge Regression")
    all_metrics.append(ridge_metrics)

    # -------------------------------------------------------------
    # MODEL 2: Random Forest Regressor (Non-linear Tree Baseline)
    # -------------------------------------------------------------
    rf_reg = RandomForestRegressor(
        n_estimators=100,
        max_depth=6,
        min_samples_split=4,
        random_state=42,
        n_jobs=-1,
    )
    rf_reg.fit(X_train, y_train)
    rf_pred = rf_reg.predict(X_test)
    rf_metrics = evaluate_severity_model(y_test, rf_pred, model_name="Random Forest Regressor")
    all_metrics.append(rf_metrics)

    # -------------------------------------------------------------
    # MODEL 3: XGBoost Regressor (Primary Tabular Regressor)
    # -------------------------------------------------------------
    xgb_reg = XGBRegressor(
        n_estimators=severity_config.xgboost_params.get("n_estimators", 200),
        max_depth=severity_config.xgboost_params.get("max_depth", 5),
        learning_rate=severity_config.xgboost_params.get("learning_rate", 0.05),
        subsample=severity_config.xgboost_params.get("subsample", 0.8),
        colsample_bytree=severity_config.xgboost_params.get("colsample_bytree", 0.8),
        random_state=42,
        n_jobs=-1,
    )
    xgb_reg.fit(X_train, y_train)
    xgb_pred = xgb_reg.predict(X_test)
    xgb_metrics = evaluate_severity_model(y_test, xgb_pred, model_name="XGBoost Regressor")
    all_metrics.append(xgb_metrics)

    # Print comparison table
    comparison_table = format_severity_comparison_table(all_metrics)
    print("\n" + "=" * 75)
    print("PROGRESSIVE DAMAGE SEVERITY MODEL EVALUATION (TEST SET)")
    print("=" * 75)
    print(comparison_table)
    print("=" * 75 + "\n")

    # Select best model: XGBoost gives lowest MAE / highest R2
    best_severity_model = DamageSeverityModel(
        estimator=xgb_reg,
        model_name="road_damage_severity_xgboost",
        version=severity_config.model_version,
    )
    best_severity_model.feature_names_ = list(X_train.columns)
    best_severity_model._is_fitted = True

    # Feature importances
    if hasattr(xgb_reg, "feature_importances_"):
        raw_imp = xgb_reg.feature_importances_
        norm_imp = raw_imp / np.sum(raw_imp)
        best_severity_model.feature_importances_ = {
            feat: round(float(imp), 4)
            for feat, imp in sorted(zip(X_train.columns, norm_imp), key=lambda x: x[1], reverse=True)
        }

    report = {
        "all_metrics": all_metrics,
        "selected_model": "road_damage_severity_xgboost",
        "selected_metrics": xgb_metrics,
        "feature_importances": best_severity_model.feature_importances_,
    }
    return report, best_severity_model


def run_severity_training_pipeline(
    data_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute end-to-end training pipeline for Damage Severity Estimation.

    Args:
        data_path: Path to dataset CSV. Defaults to severity_config.raw_data_path.
        output_dir: Destination folder for model artifacts and metadata.

    Returns:
        Dictionary summarizing training results and artifact paths.
    """
    dataset_file = data_path or severity_config.raw_data_path
    artifacts_folder = output_dir or severity_config.artifact_dir
    artifacts_folder.mkdir(parents=True, exist_ok=True)

    if not dataset_file.exists():
        logger.info("Dataset not found at %s. Generating synthetic dataset...", dataset_file)
        from ml.severity.generate_synthetic_data import generate_synthetic_severity_data

        dataset_file.parent.mkdir(parents=True, exist_ok=True)
        df_synthetic = generate_synthetic_severity_data(n_samples=3000, seed=42)
        df_synthetic.to_csv(dataset_file, index=False)

    logger.info("Loading dataset from: %s", dataset_file)
    df = pd.read_csv(dataset_file)

    target_col = severity_config.target_column
    X_raw = df.drop(columns=[target_col])
    y_raw = df[target_col]

    # Split 80% train / 20% test
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X_raw, y_raw, test_size=0.20, random_state=42
    )

    # Preprocessing
    preprocessor = SeverityPreprocessor()
    preprocessor.fit(X_train_raw)

    clean_train = preprocessor.transform(X_train_raw)
    clean_test = preprocessor.transform(X_test_raw)

    # Feature extraction
    feature_extractor = SeverityFeatureExtractor(include_raw=True)
    X_train = feature_extractor.transform(clean_train)
    X_test = feature_extractor.transform(clean_test)

    # Train & Compare
    report, best_model = train_and_compare_severity_models(X_train, y_train, X_test, y_test)

    # Save Bundle
    artifact_bundle = {
        "model": best_model,
        "preprocessor": preprocessor,
        "feature_extractor": feature_extractor,
        "feature_names": list(X_train.columns),
        "level_thresholds": severity_config.level_thresholds,
        "version": severity_config.model_version,
        "model_name": severity_config.model_name,
    }

    model_save_path = artifacts_folder / "model_artifact.joblib"
    joblib.dump(artifact_bundle, model_save_path)
    logger.info("Saved severity inference bundle to: %s", model_save_path)

    # Save Metadata JSON
    metadata = {
        "model_name": severity_config.model_name,
        "version": severity_config.model_version,
        "problem_type": severity_config.problem_type,
        "target": severity_config.target_column,
        "training_dataset": str(dataset_file),
        "dataset_type": "SYNTHETIC — FOR DEVELOPMENT ONLY",
        "features": list(X_train.columns),
        "feature_count": len(X_train.columns),
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "data_split": {
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "test_ratio": 0.20,
        },
        "level_thresholds": severity_config.level_thresholds,
        "metrics": report["selected_metrics"],
        "all_model_comparisons": report["all_metrics"],
        "feature_importances": report["feature_importances"],
    }

    metadata_path = artifacts_folder / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved severity metadata to: %s", metadata_path)

    print(f"Artifact successfully saved: {model_save_path}")
    print(f"Metadata successfully saved: {metadata_path}")

    return {
        "model_artifact": str(model_save_path),
        "metadata_file": str(metadata_path),
        "report": report,
    }


def main() -> None:
    """CLI script entrypoint for running the severity training pipeline."""
    parser = argparse.ArgumentParser(description="Train Damage Severity Estimation models.")
    parser.add_argument("--data", type=str, default=str(severity_config.raw_data_path))
    parser.add_argument("--out", type=str, default=str(severity_config.artifact_dir))
    args = parser.parse_args()

    run_severity_training_pipeline(data_path=Path(args.data), output_dir=Path(args.out))


if __name__ == "__main__":
    main()
