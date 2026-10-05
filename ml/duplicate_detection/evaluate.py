"""Evaluation metrics and reporting utilities for Duplicate Complaint Detection (Phase 6)."""

from __future__ import annotations

from typing import Dict, List, Any
import numpy as np
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    precision_recall_curve,
    auc,
    roc_auc_score,
)


def evaluate_duplicate_detection(
    y_true: List[int], y_pred: List[int], y_scores: List[float], name: str = "DuplicateDetector"
) -> Dict[str, Any]:
    """Calculate evaluation metrics for duplicate complaint detection with emphasis on Precision.

    Args:
        y_true: True binary duplicate labels (1 = duplicate, 0 = distinct).
        y_pred: Predicted binary duplicate labels.
        y_scores: Predicted duplicate probability / composite likelihood scores.
        name: Identifier for model/pipeline evaluated.

    Returns:
        Dict containing precision, recall, F1, PR-AUC, ROC-AUC, and confusion matrix.
    """
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    # Calculate PR-AUC and ROC-AUC if non-trivial score distribution
    pr_auc = None
    roc_auc = None
    if len(set(y_true)) > 1:
        p_curve, r_curve, _ = precision_recall_curve(y_true, y_scores)
        pr_auc = float(auc(r_curve, p_curve))
        roc_auc = float(roc_auc_score(y_true, y_scores))

    cm = confusion_matrix(y_true, y_pred).tolist()

    metrics = {
        "model_name": name,
        "n_samples": len(y_true),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "pr_auc": round(pr_auc, 4) if pr_auc is not None else None,
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "confusion_matrix": cm,
    }

    return metrics


def print_duplicate_evaluation_summary(metrics: Dict[str, Any]) -> None:
    """Print formatted evaluation summary table."""
    print("\n==========================================")
    print(f" EVALUATION METRICS: {metrics['model_name']}")
    print("==========================================")
    print(f" Samples Evaluated  : {metrics['n_samples']}")
    print(f" Precision          : {metrics['precision']:.4f}")
    print(f" Recall             : {metrics['recall']:.4f}")
    print(f" F1 Score           : {metrics['f1_score']:.4f}")
    if metrics.get("pr_auc") is not None:
        print(f" PR-AUC             : {metrics['pr_auc']:.4f}")
    if metrics.get("roc_auc") is not None:
        print(f" ROC-AUC            : {metrics['roc_auc']:.4f}")
    print("-" * 42)
