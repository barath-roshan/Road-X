"""Feature and Data Drift Analysis Subsystem (Phase 21).

Provides statistical distribution comparison using Population Stability Index (PSI)
and Kolmogorov-Smirnov (KS) tests between reference baselines and inference observations.
Includes schema validation, missing-value accounting, and ground-truth quality evaluation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats

from ml.common.logging_config import get_logger
from ml.monitoring.config import monitoring_config

logger = get_logger("monitoring.drift")


@dataclass
class FeatureDriftResult:
    """Individual feature drift assessment result."""

    feature_name: str
    feature_type: str  # 'numeric' or 'categorical'
    drift_status: str  # 'NO_DRIFT', 'MODERATE_DRIFT', 'HIGH_DRIFT', 'INSUFFICIENT_DATA', 'SCHEMA_ERROR'
    psi: Optional[float] = None
    ks_statistic: Optional[float] = None
    ks_pvalue: Optional[float] = None
    ref_missing_pct: float = 0.0
    curr_missing_pct: float = 0.0
    ref_count: int = 0
    curr_count: int = 0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DriftReport:
    """Consolidated drift report across analyzed feature distributions."""

    timestamp: str
    overall_drift_detected: bool
    overall_status: str  # 'NO_DRIFT', 'MODERATE_DRIFT', 'HIGH_DRIFT', 'INSUFFICIENT_DATA', 'SCHEMA_MISMATCH'
    features_analyzed: int
    features_with_drift: List[str]
    feature_results: Dict[str, Dict[str, Any]]
    schema_warnings: List[str]
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_numeric_psi(
    reference: np.ndarray,
    current: np.ndarray,
    num_bins: int = 10,
    epsilon: float = 1e-4,
) -> float:
    """Calculate Population Stability Index (PSI) for numerical arrays.

    PSI = sum((Actual% - Expected%) * ln(Actual% / Expected%))
    """
    ref_clean = reference[~np.isnan(reference)]
    curr_clean = current[~np.isnan(current)]

    if len(ref_clean) == 0 or len(curr_clean) == 0:
        return 0.0

    # Create quantile or uniform bins from reference distribution
    try:
        quantiles = np.linspace(0, 100, num_bins + 1)
        bins = np.percentile(ref_clean, quantiles)
        bins[0] -= 1e-6
        bins[-1] += 1e-6
        bins = np.unique(bins)
        if len(bins) < 2:
            return 0.0
    except Exception:
        bins = np.linspace(np.min(ref_clean) - 1e-4, np.max(ref_clean) + 1e-4, num_bins + 1)

    ref_counts, _ = np.histogram(ref_clean, bins=bins)
    curr_counts, _ = np.histogram(curr_clean, bins=bins)

    ref_pct = (ref_counts / len(ref_clean)) + epsilon
    curr_pct = (curr_counts / len(curr_clean)) + epsilon

    # Normalize back to sum to 1
    ref_pct /= np.sum(ref_pct)
    curr_pct /= np.sum(curr_pct)

    psi_value = float(np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct)))
    return max(0.0, psi_value)


def calculate_categorical_psi(
    ref_series: pd.Series,
    curr_series: pd.Series,
    epsilon: float = 1e-4,
) -> float:
    """Calculate PSI across discrete category distributions."""
    ref_clean = ref_series.dropna().astype(str)
    curr_clean = curr_series.dropna().astype(str)

    if len(ref_clean) == 0 or len(curr_clean) == 0:
        return 0.0

    all_categories = sorted(list(set(ref_clean.unique()) | set(curr_clean.unique())))
    if not all_categories:
        return 0.0

    ref_val_counts = ref_clean.value_counts(normalize=True).to_dict()
    curr_val_counts = curr_clean.value_counts(normalize=True).to_dict()

    ref_pcts = np.array([ref_val_counts.get(cat, 0.0) + epsilon for cat in all_categories])
    curr_pcts = np.array([curr_val_counts.get(cat, 0.0) + epsilon for cat in all_categories])

    ref_pcts /= np.sum(ref_pcts)
    curr_pcts /= np.sum(curr_pcts)

    psi_val = float(np.sum((curr_pcts - ref_pcts) * np.log(curr_pcts / ref_pcts)))
    return max(0.0, psi_val)


class DriftAnalyzer:
    """Modular statistical drift detector between reference baseline and incoming data."""

    def __init__(
        self,
        min_sample_size: int = 15,
        psi_moderate_threshold: float = monitoring_config.psi_moderate_threshold,
        psi_high_threshold: float = monitoring_config.psi_high_threshold,
        ks_pvalue_threshold: float = monitoring_config.ks_pvalue_threshold,
    ) -> None:
        self.min_sample_size = min_sample_size
        self.psi_moderate_threshold = psi_moderate_threshold
        self.psi_high_threshold = psi_high_threshold
        self.ks_pvalue_threshold = ks_pvalue_threshold

    def analyze(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        feature_columns: Optional[List[str]] = None,
    ) -> DriftReport:
        """Run statistical drift analysis on feature columns between reference and current data.

        Args:
            reference_data: Historical or baseline dataset.
            current_data: Monitored inference observations.
            feature_columns: Subset of features to evaluate (evaluates all common columns if None).

        Returns:
            DriftReport containing individual feature results and overall drift flags.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        schema_warnings: List[str] = []
        feature_results: Dict[str, Dict[str, Any]] = {}
        drifted_features: List[str] = []

        # Validate input structures
        if not isinstance(reference_data, pd.DataFrame) or not isinstance(current_data, pd.DataFrame):
            return DriftReport(
                timestamp=now_str,
                overall_drift_detected=False,
                overall_status="SCHEMA_MISMATCH",
                features_analyzed=0,
                features_with_drift=[],
                feature_results={},
                schema_warnings=["Input data must be valid pandas DataFrames."],
                notes="Analysis aborted due to invalid DataFrame types.",
            )

        ref_cols = set(reference_data.columns)
        curr_cols = set(current_data.columns)

        missing_in_curr = list(ref_cols - curr_cols)
        extra_in_curr = list(curr_cols - ref_cols)

        if missing_in_curr:
            schema_warnings.append(f"Features present in reference but missing in current: {missing_in_curr}")
        if extra_in_curr:
            schema_warnings.append(f"Features present in current but not in reference: {extra_in_curr}")

        # Determine target feature columns
        target_features = feature_columns or [c for c in reference_data.columns if c in curr_cols]

        has_high_drift = False
        has_moderate_drift = False
        all_insufficient = True

        for feat in target_features:
            if feat not in ref_cols or feat not in curr_cols:
                res = FeatureDriftResult(
                    feature_name=feat,
                    feature_type="unknown",
                    drift_status="SCHEMA_ERROR",
                    message="Feature missing in either reference or current dataset.",
                )
                feature_results[feat] = res.to_dict()
                continue

            ref_series = reference_data[feat]
            curr_series = current_data[feat]

            ref_n = len(ref_series)
            curr_n = len(curr_series)
            ref_missing = float(ref_series.isna().mean() * 100)
            curr_missing = float(curr_series.isna().mean() * 100)

            ref_valid_cnt = int(ref_series.dropna().shape[0])
            curr_valid_cnt = int(curr_series.dropna().shape[0])

            # Check sample size requirements
            if ref_valid_cnt < self.min_sample_size or curr_valid_cnt < self.min_sample_size:
                res = FeatureDriftResult(
                    feature_name=feat,
                    feature_type="unknown",
                    drift_status="INSUFFICIENT_DATA",
                    ref_missing_pct=round(ref_missing, 2),
                    curr_missing_pct=round(curr_missing, 2),
                    ref_count=ref_valid_cnt,
                    curr_count=curr_valid_cnt,
                    message=f"Insufficient non-null samples (ref={ref_valid_cnt}, curr={curr_valid_cnt}, min={self.min_sample_size}).",
                )
                feature_results[feat] = res.to_dict()
                continue

            all_insufficient = False

            # Differentiate numerical vs categorical
            is_numeric = pd.api.types.is_numeric_dtype(ref_series) and pd.api.types.is_numeric_dtype(curr_series)

            if is_numeric:
                ref_arr = ref_series.dropna().to_numpy(dtype=float)
                curr_arr = curr_series.dropna().to_numpy(dtype=float)

                psi = calculate_numeric_psi(ref_arr, curr_arr)
                ks_stat, ks_pval = stats.ks_2samp(ref_arr, curr_arr)

                # Classify drift severity
                if psi >= self.psi_high_threshold:
                    drift_status = "HIGH_DRIFT"
                    has_high_drift = True
                    drifted_features.append(feat)
                    msg = f"Significant numerical drift detected (PSI={psi:.4f} >= {self.psi_high_threshold})."
                elif psi >= self.psi_moderate_threshold or ks_pval < self.ks_pvalue_threshold:
                    drift_status = "MODERATE_DRIFT"
                    has_moderate_drift = True
                    drifted_features.append(feat)
                    msg = f"Moderate distribution shift (PSI={psi:.4f}, KS p-value={ks_pval:.4f})."
                else:
                    drift_status = "NO_DRIFT"
                    msg = "Distribution stable."

                res = FeatureDriftResult(
                    feature_name=feat,
                    feature_type="numeric",
                    drift_status=drift_status,
                    psi=round(psi, 4),
                    ks_statistic=round(float(ks_stat), 4),
                    ks_pvalue=round(float(ks_pval), 4),
                    ref_missing_pct=round(ref_missing, 2),
                    curr_missing_pct=round(curr_missing, 2),
                    ref_count=ref_valid_cnt,
                    curr_count=curr_valid_cnt,
                    message=msg,
                )
            else:
                # Categorical drift
                psi = calculate_categorical_psi(ref_series, curr_series)
                if psi >= self.psi_high_threshold:
                    drift_status = "HIGH_DRIFT"
                    has_high_drift = True
                    drifted_features.append(feat)
                    msg = f"Significant categorical shift detected (PSI={psi:.4f})."
                elif psi >= self.psi_moderate_threshold:
                    drift_status = "MODERATE_DRIFT"
                    has_moderate_drift = True
                    drifted_features.append(feat)
                    msg = f"Moderate categorical shift detected (PSI={psi:.4f})."
                else:
                    drift_status = "NO_DRIFT"
                    msg = "Category frequencies stable."

                res = FeatureDriftResult(
                    feature_name=feat,
                    feature_type="categorical",
                    drift_status=drift_status,
                    psi=round(psi, 4),
                    ref_missing_pct=round(ref_missing, 2),
                    curr_missing_pct=round(curr_missing, 2),
                    ref_count=ref_valid_cnt,
                    curr_count=curr_valid_cnt,
                    message=msg,
                )

            feature_results[feat] = res.to_dict()

        # Overall Status
        if all_insufficient and target_features:
            overall_status = "INSUFFICIENT_DATA"
            overall_drift = False
        elif has_high_drift:
            overall_status = "HIGH_DRIFT"
            overall_drift = True
        elif has_moderate_drift:
            overall_status = "MODERATE_DRIFT"
            overall_drift = True
        else:
            overall_status = "NO_DRIFT"
            overall_drift = False

        return DriftReport(
            timestamp=now_str,
            overall_drift_detected=overall_drift,
            overall_status=overall_status,
            features_analyzed=len(target_features),
            features_with_drift=drifted_features,
            feature_results=feature_results,
            schema_warnings=schema_warnings,
            notes="Defensible statistical drift check (PSI / KS). Synthetic data must not be claimed as real-world municipal drift.",
        )


class PredictionQualityMonitor:
    """Evaluates prediction accuracy against verified ground-truth maintenance outcomes (Phase 21).

    Explicitly separates operational telemetry from ground-truth verification.
    """

    @staticmethod
    def evaluate(
        predictions: List[Union[int, float]],
        ground_truth: Optional[List[Union[int, float]]],
        is_classification: bool = True,
    ) -> Dict[str, Any]:
        """Compute model performance against observed real-world outcomes if available."""
        if not ground_truth or len(ground_truth) == 0:
            return {
                "status": "UNAVAILABLE_NO_GROUND_TRUTH",
                "message": (
                    "Ground-truth outcome labels are currently unavailable. Model-quality monitoring "
                    "requires verified municipal field inspection / road failure records."
                ),
                "is_validated": False,
            }

        if len(predictions) != len(ground_truth):
            return {
                "status": "SAMPLE_MISMATCH_ERROR",
                "message": f"Mismatched count between predictions ({len(predictions)}) and ground truth ({len(ground_truth)}).",
                "is_validated": False,
            }

        y_pred = np.array(predictions)
        y_true = np.array(ground_truth)

        if is_classification:
            accuracy = float(np.mean(y_pred == y_true))
            tp = int(np.sum((y_pred == 1) & (y_true == 1)))
            fp = int(np.sum((y_pred == 1) & (y_true == 0)))
            fn = int(np.sum((y_pred == 0) & (y_true == 1)))
            tn = int(np.sum((y_pred == 0) & (y_true == 0)))

            precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
            f1 = (
                float(2 * precision * recall / (precision + recall))
                if (precision + recall) > 0
                else 0.0
            )

            return {
                "status": "EVALUATED_WITH_GROUND_TRUTH",
                "is_validated": True,
                "metrics": {
                    "sample_size": len(predictions),
                    "accuracy": round(accuracy, 4),
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1_score": round(f1, 4),
                    "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
                },
            }
        else:
            mae = float(np.mean(np.abs(y_pred - y_true)))
            rmse = float(np.sqrt(np.mean((y_pred - y_true) ** 2)))
            return {
                "status": "EVALUATED_WITH_GROUND_TRUTH",
                "is_validated": True,
                "metrics": {
                    "sample_size": len(predictions),
                    "mae": round(mae, 4),
                    "rmse": round(rmse, 4),
                },
            }
