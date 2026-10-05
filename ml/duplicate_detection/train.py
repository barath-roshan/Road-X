"""Training script for Duplicate Complaint Detection (Phase 6)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from ml.common.exceptions import RoadXDataError
from ml.duplicate_detection.config import config
from ml.duplicate_detection.generate_synthetic_data import generate_synthetic_pairs
from ml.duplicate_detection.schemas import ComplaintRecord
from ml.duplicate_detection.similarity import SimilarityCalculator
from ml.duplicate_detection.features import GeographicTemporalFeatureBuilder
from ml.duplicate_detection.scorer import DuplicateScorer
from ml.duplicate_detection.evaluate import (
    evaluate_duplicate_detection,
    print_duplicate_evaluation_summary,
)


def load_pairs_dataset(dataset_path: Path) -> pd.DataFrame:
    """Load duplicate complaint pairs CSV dataset, ignoring comment header lines."""
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}. Generating synthetic pairs dataset...")
        generate_synthetic_pairs(dataset_path)

    df = pd.read_csv(dataset_path, comment="#")
    required = {
        "text_a",
        "text_b",
        "lat_a",
        "lon_a",
        "lat_b",
        "lon_b",
        "created_at_a",
        "created_at_b",
        "category_a",
        "category_b",
        "is_duplicate",
    }
    if not required.issubset(df.columns):
        raise RoadXDataError(f"Dataset missing required columns. Required: {required}")

    return df


def extract_pair_features(
    df: pd.DataFrame,
    similarity_calc: SimilarityCalculator,
    feature_builder: GeographicTemporalFeatureBuilder,
) -> Tuple[np.ndarray, List[int], List[float]]:
    """Extract feature matrix X, ground truth y, and heuristic scores for complaint pairs."""
    X_list = []
    y_list = []
    heuristic_scores = []

    for _, row in df.iterrows():
        rec_a = ComplaintRecord(
            grievance_id=str(row.get("complaint_id_a", "GRV-A")),
            text=str(row["text_a"]),
            latitude=float(row["lat_a"]) if pd.notna(row["lat_a"]) else None,
            longitude=float(row["lon_a"]) if pd.notna(row["lon_a"]) else None,
            created_at=str(row["created_at_a"]) if pd.notna(row["created_at_a"]) else None,
            issue_category=str(row["category_a"]) if pd.notna(row["category_a"]) else None,
        )
        rec_b = ComplaintRecord(
            grievance_id=str(row.get("complaint_id_b", "GRV-B")),
            text=str(row["text_b"]),
            latitude=float(row["lat_b"]) if pd.notna(row["lat_b"]) else None,
            longitude=float(row["lon_b"]) if pd.notna(row["lon_b"]) else None,
            created_at=str(row["created_at_b"]) if pd.notna(row["created_at_b"]) else None,
            issue_category=str(row["category_b"]) if pd.notna(row["category_b"]) else None,
        )

        text_sim = similarity_calc.calculate_similarity(rec_a.text, rec_b.text)
        evidence = feature_builder.build_evidence(rec_a, rec_b, text_sim)
        geo_score, time_score = feature_builder.compute_proximity_scores(evidence)
        cat_match = 1.0 if evidence.same_issue_category is True else 0.0

        # Feature vector: [text_similarity, geo_score, time_score, category_match]
        X_list.append(
            [
                text_sim,
                geo_score if geo_score is not None else 0.0,
                time_score if time_score is not None else 0.0,
                cat_match,
            ]
        )
        y_list.append(int(row["is_duplicate"]))

        # Compute heuristic score
        h_scorer = DuplicateScorer()
        heuristic_scores.append(h_scorer.compute_heuristic_score(evidence))

    return np.array(X_list, dtype=np.float32), y_list, heuristic_scores


def train_duplicate_detection(
    dataset_path: Path = config.raw_dataset_path,
    model_dir: Path = config.model_dir,
) -> Dict[str, Any]:
    """Train duplicate scorer model, evaluate against baselines, and save artifacts."""
    config.ensure_directories()

    print(f"Loading complaint pairs dataset from {dataset_path}...")
    df = load_pairs_dataset(dataset_path)

    similarity_calc = SimilarityCalculator()
    feature_builder = GeographicTemporalFeatureBuilder()

    print("Extracting text similarity, geographic, and temporal features...")
    X, y, h_scores = extract_pair_features(df, similarity_calc, feature_builder)

    # Stratified Train/Test Split
    X_train, X_test, y_train, y_test, h_train, h_test = train_test_split(
        X,
        y,
        h_scores,
        test_size=0.2,
        random_state=config.random_state,
        stratify=y,
    )

    print(f"Dataset split: Train={len(y_train)} pairs, Test={len(y_test)} pairs")

    # Evaluate Heuristic Baseline on Test Partition
    h_preds = [1 if s >= config.duplicate_score_threshold else 0 for s in h_test]
    heuristic_metrics = evaluate_duplicate_detection(y_test, h_preds, h_test, "Heuristic Baseline")
    print_duplicate_evaluation_summary(heuristic_metrics)

    # Train Supervised Logistic Regression Scorer
    print("Training Supervised DuplicateScorer Classifier...")
    scorer = DuplicateScorer(version=config.model_version)
    scorer.train(X_train, y_train)

    # Evaluate Supervised Scorer on Test Partition
    y_scores = list(scorer.predict_proba(X_test))
    y_preds = scorer.predict(X_test)
    supervised_metrics = evaluate_duplicate_detection(y_test, y_preds, y_scores, "Supervised Scorer")
    print_duplicate_evaluation_summary(supervised_metrics)

    # Save Model Artifacts
    scorer.save(model_dir / "model.joblib")

    # Metadata Serialization
    metadata = {
        "dataset_type": "SYNTHETIC / MANUALLY CREATED DEVELOPMENT DATA",
        "disclaimer": (
            "Current duplicate detection results are development results based on synthetic data and "
            "must not be interpreted as production performance on real citizen complaints."
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_version": config.model_version,
        "n_train_pairs": len(y_train),
        "n_test_pairs": len(y_test),
        "threshold": config.duplicate_score_threshold,
        "metrics": {
            "heuristic_baseline": {
                "precision": heuristic_metrics["precision"],
                "recall": heuristic_metrics["recall"],
                "f1_score": heuristic_metrics["f1_score"],
            },
            "supervised_scorer": {
                "precision": supervised_metrics["precision"],
                "recall": supervised_metrics["recall"],
                "f1_score": supervised_metrics["f1_score"],
                "pr_auc": supervised_metrics.get("pr_auc"),
                "roc_auc": supervised_metrics.get("roc_auc"),
            },
        },
    }

    metadata_path = model_dir / "metadata" / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nDuplicate detection model artifacts saved to: {model_dir}")
    print(f"Metadata written to: {metadata_path}")

    return {
        "heuristic_metrics": heuristic_metrics,
        "supervised_metrics": supervised_metrics,
        "metadata_path": str(metadata_path),
    }


if __name__ == "__main__":
    train_duplicate_detection()
