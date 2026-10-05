"""Evaluation metrics for Time-to-Failure Survival Analysis (Concordance Index, MAE, RMSE)."""

from __future__ import annotations

from typing import Dict, Any, List
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error


def calculate_concordance_index(
    time_to_event: np.ndarray, event_observed: np.ndarray, predicted_times: np.ndarray
) -> float:
    """Calculate Harrell's Concordance Index (C-Index) for right-censored survival observations.

    Args:
        time_to_event: True survival / censoring times.
        event_observed: Binary event flags (1 = failed, 0 = censored).
        predicted_times: Model predicted median survival times.

    Returns:
        C-Index float in range [0.0, 1.0]. 0.5 indicates random guessing, 1.0 indicates perfect ranking.
    """
    times = np.asarray(time_to_event, dtype=np.float64)
    events = np.asarray(event_observed, dtype=np.int32)
    preds = np.asarray(predicted_times, dtype=np.float64)

    n = len(times)
    concordant = 0.0
    permissible = 0.0

    for i in range(n):
        if events[i] != 1:
            continue

        for j in range(n):
            if i == j:
                continue

            # Permissible pair if i failed earlier than j's time
            if times[i] < times[j]:
                permissible += 1.0
                if preds[i] < preds[j]:
                    concordant += 1.0
                elif preds[i] == preds[j]:
                    concordant += 0.5

    if permissible == 0.0:
        return 0.5

    return float(concordant / permissible)


def evaluate_survival_model(
    time_to_event: List[float],
    event_observed: List[int],
    predicted_times: List[float],
    name: str = "Weibull Survival Model",
) -> Dict[str, Any]:
    """Compute comprehensive survival evaluation metrics.

    Args:
        time_to_event: True event/censoring times in days.
        event_observed: Binary event flags (1 = uncensored failure, 0 = right-censored).
        predicted_times: Predicted median remaining days to failure.
        name: Model identifier string.

    Returns:
        Dict containing C-Index, uncensored MAE, RMSE, and sample counts.
    """
    t_arr = np.asarray(time_to_event, dtype=np.float64)
    delta_arr = np.asarray(event_observed, dtype=np.int32)
    pred_arr = np.asarray(predicted_times, dtype=np.float64)

    c_index = calculate_concordance_index(t_arr, delta_arr, pred_arr)

    # MAE and RMSE on uncensored failures (delta == 1)
    uncensored_mask = delta_arr == 1
    if np.sum(uncensored_mask) > 0:
        mae_uncensored = float(mean_absolute_error(t_arr[uncensored_mask], pred_arr[uncensored_mask]))
        rmse_uncensored = float(np.sqrt(mean_squared_error(t_arr[uncensored_mask], pred_arr[uncensored_mask])))
    else:
        mae_uncensored = 0.0
        rmse_uncensored = 0.0

    metrics = {
        "model_name": name,
        "n_samples": len(t_arr),
        "n_events": int(np.sum(delta_arr)),
        "c_index": round(c_index, 4),
        "mae_uncensored_days": round(mae_uncensored, 2),
        "rmse_uncensored_days": round(rmse_uncensored, 2),
    }

    return metrics


def print_survival_evaluation_summary(metrics: Dict[str, Any]) -> None:
    """Print formatted survival evaluation metrics report."""
    print("\n==========================================")
    print(f" EVALUATION METRICS: {metrics['model_name']}")
    print("==========================================")
    print(f" Samples Evaluated    : {metrics['n_samples']}")
    print(f" Uncensored Failures  : {metrics['n_events']}")
    print(f" Concordance Index    : {metrics['c_index']:.4f}")
    print(f" MAE (Uncensored Days): {metrics['mae_uncensored_days']:.2f} days")
    print(f" RMSE (Uncensored Days): {metrics['rmse_uncensored_days']:.2f} days")
    print("-" * 42)
