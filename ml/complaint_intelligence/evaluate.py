"""Evaluation utilities for Complaint Intelligence text classification models (Phase 5)."""

from __future__ import annotations

from typing import Dict, List, Any
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


def evaluate_classifier(
    y_true: List[str], y_pred: List[str], target_name: str = "Classifier"
) -> Dict[str, Any]:
    """Calculate comprehensive classification metrics including macro and weighted precision/recall/F1.

    Args:
        y_true: True ground truth class labels.
        y_pred: Predicted class labels.
        target_name: Name of target target classifier (e.g. 'IssueCategory').

    Returns:
        Dict containing scalar metrics, per-class metrics, and confusion matrix.
    """
    labels = sorted(list(set(y_true) | set(y_pred)))

    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    macro_precision = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_precision = float(precision_score(y_true, y_pred, average="weighted", zero_division=0))

    macro_recall = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_recall = float(recall_score(y_true, y_pred, average="weighted", zero_division=0))

    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)

    # Specific recall for critical/high risk classes if present
    critical_recall = report.get("CRITICAL", {}).get("recall", None)
    high_recall = report.get("HIGH", {}).get("recall", None)

    metrics = {
        "target_name": target_name,
        "n_samples": len(y_true),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "macro_precision": round(macro_precision, 4),
        "weighted_precision": round(weighted_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "weighted_recall": round(weighted_recall, 4),
        "critical_recall": round(critical_recall, 4) if critical_recall is not None else None,
        "high_recall": round(high_recall, 4) if high_recall is not None else None,
        "labels": labels,
        "confusion_matrix": cm,
        "per_class_report": report,
    }

    return metrics


def print_evaluation_summary(metrics: Dict[str, Any]) -> None:
    """Print formatted evaluation report to stdout."""
    name = metrics["target_name"]
    print(f"\n==========================================")
    print(f" EVALUATION METRICS: {name}")
    print(f"==========================================")
    print(f" Samples Evaluated  : {metrics['n_samples']}")
    print(f" Macro F1 Score     : {metrics['macro_f1']:.4f}")
    print(f" Weighted F1 Score  : {metrics['weighted_f1']:.4f}")
    print(f" Macro Precision    : {metrics['macro_precision']:.4f}")
    print(f" Macro Recall       : {metrics['macro_recall']:.4f}")

    if metrics.get("critical_recall") is not None:
        print(f" CRITICAL Class Recall: {metrics['critical_recall']:.4f}")
    if metrics.get("high_recall") is not None:
        print(f" HIGH Class Recall    : {metrics['high_recall']:.4f}")

    print("-" * 42)
