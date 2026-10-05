"""Training script for RoadX Complaint Intelligence (Phase 5)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from sklearn.model_selection import train_test_split

from ml.common.exceptions import RoadXDataError
from ml.complaint_intelligence.config import config
from ml.complaint_intelligence.generate_synthetic_data import generate_synthetic_dataset
from ml.complaint_intelligence.preprocessing import ComplaintPreprocessor
from ml.complaint_intelligence.features import ComplaintFeatureExtractor
from ml.complaint_intelligence.classifiers import IssueClassifier, UrgencyClassifier, SafetyRiskClassifier
from ml.complaint_intelligence.evaluate import evaluate_classifier, print_evaluation_summary
from ml.complaint_intelligence.analyzer import ComplaintAnalyzer


def load_dataset(dataset_path: Path) -> pd.DataFrame:
    """Load citizen complaint CSV dataset, ignoring comment header lines."""
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}. Generating synthetic dataset...")
        generate_synthetic_dataset(dataset_path)

    df = pd.read_csv(dataset_path, comment="#")

    required_cols = {"complaint_text", "issue_category", "urgency", "safety_risk"}
    if not required_cols.issubset(df.columns):
        raise RoadXDataError(
            f"Dataset at {dataset_path} missing required columns. Required: {required_cols}"
        )

    return df


def train_complaint_intelligence(
    dataset_path: Path = config.raw_dataset_path,
    model_dir: Path = config.model_dir,
) -> Dict[str, Any]:
    """Train complaint intelligence feature extractors, classifiers, and save model artifacts."""
    config.ensure_directories()

    print(f"Loading dataset from {dataset_path}...")
    df = load_dataset(dataset_path)

    # 1. Text Preprocessing
    preprocessor = ComplaintPreprocessor()
    df["clean_text"] = df["complaint_text"].apply(lambda t: preprocessor.clean_text(str(t)))

    # 2. Stratified Data Split
    train_df, test_df = train_test_split(
        df,
        test_size=config.test_size,
        random_state=config.random_state,
        stratify=df["issue_category"],
    )

    print(f"Dataset split: Train={len(train_df)} samples, Test={len(test_df)} samples")

    # 3. Fit TF-IDF Feature Extractor on Training Text
    feature_extractor = ComplaintFeatureExtractor(
        max_features=config.max_features,
        ngram_range=config.ngram_range,
        sublinear_tf=config.sublinear_tf,
    )
    X_train = feature_extractor.fit_transform(train_df["clean_text"].tolist())
    X_test = feature_extractor.transform(test_df["clean_text"].tolist())

    # 4. Train Issue Classifier
    print("Training Issue Category Classifier...")
    issue_clf = IssueClassifier(version=config.model_version)
    issue_clf.train(X_train, train_df["issue_category"].tolist())
    y_pred_issue = issue_clf.predict(X_test)
    issue_metrics = evaluate_classifier(test_df["issue_category"].tolist(), y_pred_issue, "Issue Category")
    print_evaluation_summary(issue_metrics)

    # 5. Train Urgency Classifier
    print("Training Urgency Classifier...")
    urgency_clf = UrgencyClassifier(version=config.model_version)
    urgency_clf.train(X_train, train_df["urgency"].tolist())
    y_pred_urgency = urgency_clf.predict(X_test)
    urgency_metrics = evaluate_classifier(test_df["urgency"].tolist(), y_pred_urgency, "Urgency Level")
    print_evaluation_summary(urgency_metrics)

    # 6. Train Safety Risk Classifier
    print("Training Safety Risk Classifier...")
    safety_clf = SafetyRiskClassifier(version=config.model_version)
    safety_clf.train(X_train, train_df["safety_risk"].tolist())
    y_pred_safety = safety_clf.predict(X_test)
    safety_metrics = evaluate_classifier(test_df["safety_risk"].tolist(), y_pred_safety, "Safety Risk Level")
    print_evaluation_summary(safety_metrics)

    # 7. Save Component Artifacts & Orchestrator
    analyzer = ComplaintAnalyzer(
        preprocessor=preprocessor,
        feature_extractor=feature_extractor,
        issue_classifier=issue_clf,
        urgency_classifier=urgency_clf,
        safety_classifier=safety_clf,
        version=config.model_version,
    )
    analyzer.save(model_dir)

    # 8. Save Metadata JSON
    metadata = {
        "dataset_type": "SYNTHETIC / MANUALLY CREATED DEVELOPMENT DATA",
        "disclaimer": (
            "Current NLP results are development results and must not be interpreted as "
            "production performance on real citizen complaints."
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_version": config.model_version,
        "n_train_samples": len(train_df),
        "n_test_samples": len(test_df),
        "metrics": {
            "issue_category": {
                "macro_f1": issue_metrics["macro_f1"],
                "weighted_f1": issue_metrics["weighted_f1"],
            },
            "urgency": {
                "macro_f1": urgency_metrics["macro_f1"],
                "critical_recall": urgency_metrics.get("critical_recall"),
            },
            "safety_risk": {
                "macro_f1": safety_metrics["macro_f1"],
                "high_recall": safety_metrics.get("high_recall"),
            },
        },
    }

    metadata_path = model_dir / "metadata" / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nModel artifacts successfully saved to: {model_dir}")
    print(f"Metadata written to: {metadata_path}")

    return {
        "issue_metrics": issue_metrics,
        "urgency_metrics": urgency_metrics,
        "safety_metrics": safety_metrics,
        "metadata_path": str(metadata_path),
    }


if __name__ == "__main__":
    train_complaint_intelligence()
