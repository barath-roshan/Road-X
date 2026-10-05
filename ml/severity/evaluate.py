"""Model evaluation metrics for Damage Severity Estimation."""

from __future__ import annotations

from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)

from ml.common.logging_config import get_logger
from ml.severity.config import severity_config
from ml.severity.schemas import DamageSeverityLevel

logger = get_logger("severity.evaluate")


def score_to_level(score: float, thresholds: Optional[Dict[str, float]] = None) -> DamageSeverityLevel:
    """Map continuous severity score (0.0 - 100.0) into categorical presentation level.

    Thresholds:
        LOW: < low_max (default < 30.0)
        MEDIUM: low_max <= score < medium_max (default 30.0 - 59.9)
        HIGH: medium_max <= score < high_max (default 60.0 - 79.9)
        CRITICAL: >= high_max (default >= 80.0)
    """
    thresh = thresholds or severity_config.level_thresholds
    low_max = thresh.get("low_max", 30.0)
    med_max = thresh.get("medium_max", 60.0)
    high_max = thresh.get("high_max", 80.0)

    if score < low_max:
        return DamageSeverityLevel.LOW
    if score < med_max:
        return DamageSeverityLevel.MEDIUM
    if score < high_max:
        return DamageSeverityLevel.HIGH
    return DamageSeverityLevel.CRITICAL


def evaluate_severity_model(
    y_true: Union[pd.Series, np.ndarray],
    y_pred: Union[pd.Series, np.ndarray],
    model_name: str = "model",
) -> Dict[str, Any]:
    """Compute regression metrics (MAE, RMSE, R2) and mapped categorical level metrics.

    Args:
        y_true: Continuous ground truth severity scores.
        y_pred: Continuous predicted severity scores.
        model_name: Identifying model name.

    Returns:
        Dictionary of formatted evaluation metrics.
    """
    y_true_arr = np.asarray(y_true).astype(float)
    y_pred_arr = np.clip(np.asarray(y_pred).astype(float), 0.0, 100.0)

    # 1. Regression Metrics
    mae = float(mean_absolute_error(y_true_arr, y_pred_arr))
    rmse = float(np.sqrt(mean_squared_error(y_true_arr, y_pred_arr)))
    r2 = float(r2_score(y_true_arr, y_pred_arr))

    # 2. Mapped Classification Level Metrics
    levels_true = [score_to_level(s).value for s in y_true_arr]
    levels_pred = [score_to_level(s).value for s in y_pred_arr]

    unique_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    level_prec = float(precision_score(levels_true, levels_pred, labels=unique_levels, average="macro", zero_division=0))
    level_rec = float(recall_score(levels_true, levels_pred, labels=unique_levels, average="macro", zero_division=0))
    level_f1 = float(f1_score(levels_true, levels_pred, labels=unique_levels, average="macro", zero_division=0))

    cm = confusion_matrix(levels_true, levels_pred, labels=unique_levels).tolist()

    metrics = {
        "model_name": model_name,
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2_score": round(r2, 4),
        "level_macro_precision": round(level_prec, 4),
        "level_macro_recall": round(level_rec, 4),
        "level_macro_f1": round(level_f1, 4),
        "level_confusion_matrix": {
            "labels": unique_levels,
            "matrix": cm,
        },
    }

    logger.info(
        "Evaluated Severity [%s] -> MAE: %.4f, RMSE: %.4f, R2: %.4f, Level Macro-F1: %.4f",
        model_name,
        mae,
        rmse,
        r2,
        level_f1,
    )
    return metrics


def format_severity_comparison_table(metrics_list: List[Dict[str, Any]]) -> str:
    """Format multiple regression model metrics into an ASCII markdown comparison table."""
    headers = ["Model", "MAE", "RMSE", "R² Score", "Level Precision", "Level Recall", "Level F1"]
    rows = []
    for m in metrics_list:
        rows.append([
            m["model_name"],
            f"{m['mae']:.4f}",
            f"{m['rmse']:.4f}",
            f"{m['r2_score']:.4f}",
            f"{m['level_macro_precision']:.4f}",
            f"{m['level_macro_recall']:.4f}",
            f"{m['level_macro_f1']:.4f}",
        ])

    col_widths = [max(len(str(val)) for val in col) for col in zip(headers, *rows)]
    header_str = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    sep_str = "-|-".join("-" * w for w in col_widths)
    body_str = "\n".join(" | ".join(val.ljust(w) for val, w in zip(row, col_widths)) for row in rows)

    return f"{header_str}\n{sep_str}\n{body_str}"
