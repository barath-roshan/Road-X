"""Model evaluation metrics and comparative reporting for Road Failure Prediction."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from ml.common.logging_config import get_logger

logger = get_logger("failure_prediction.evaluate")


def evaluate_model(
    y_true: Union[pd.Series, np.ndarray],
    y_pred: Union[pd.Series, np.ndarray],
    y_prob: Union[pd.Series, np.ndarray],
    model_name: str = "model",
) -> Dict[str, Any]:
    """Compute comprehensive performance metrics emphasizing safety-critical recall, precision, and probability calibration.

    Args:
        y_true: Ground truth binary target (0=Stable, 1=Failure Next 30d).
        y_pred: Hard binary predictions at threshold.
        y_prob: Predicted failure probabilities for positive class.
        model_name: Identifying name of evaluated model.

    Returns:
        Dictionary of formatted evaluation metrics.
    """
    y_true_arr = np.asarray(y_true).astype(int)
    y_pred_arr = np.asarray(y_pred).astype(int)
    y_prob_arr = np.asarray(y_prob).astype(float)

    # If y_prob is 2D (shape [N, 2]), extract positive class column
    if y_prob_arr.ndim == 2:
        y_prob_arr = y_prob_arr[:, 1]

    # Confusion matrix
    cm = confusion_matrix(y_true_arr, y_pred_arr)
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)

    # Core classification metrics
    precision = float(precision_score(y_true_arr, y_pred_arr, zero_division=0))
    recall = float(recall_score(y_true_arr, y_pred_arr, zero_division=0))
    f1 = float(f1_score(y_true_arr, y_pred_arr, zero_division=0))

    # Ranking and discriminative metrics
    try:
        roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr))
    except Exception:
        roc_auc = 0.0

    try:
        pr_auc = float(average_precision_score(y_true_arr, y_prob_arr))
    except Exception:
        pr_auc = 0.0

    # Probability calibration metric
    brier = float(brier_score_loss(y_true_arr, y_prob_arr))

    metrics = {
        "model_name": model_name,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "brier_score": round(brier, 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
    }

    logger.info(
        "Evaluated [%s] -> Precision: %.4f, Recall: %.4f, F1: %.4f, ROC-AUC: %.4f, PR-AUC: %.4f, Brier: %.4f",
        model_name,
        precision,
        recall,
        f1,
        roc_auc,
        pr_auc,
        brier,
    )
    return metrics


def format_comparison_table(metrics_list: List[Dict[str, Any]]) -> str:
    """Format multiple model evaluation dictionaries into an ASCII markdown comparison table."""
    headers = ["Model", "Precision", "Recall", "F1-Score", "ROC-AUC", "PR-AUC", "Brier Score"]
    rows = []
    for m in metrics_list:
        rows.append([
            m["model_name"],
            f"{m['precision']:.4f}",
            f"{m['recall']:.4f}",
            f"{m['f1_score']:.4f}",
            f"{m['roc_auc']:.4f}",
            f"{m['pr_auc']:.4f}",
            f"{m['brier_score']:.4f}",
        ])

    col_widths = [max(len(str(val)) for val in col) for col in zip(headers, *rows)]
    header_str = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    sep_str = "-|-".join("-" * w for w in col_widths)
    body_str = "\n".join(" | ".join(val.ljust(w) for val, w in zip(row, col_widths)) for row in rows)

    return f"{header_str}\n{sep_str}\n{body_str}"
