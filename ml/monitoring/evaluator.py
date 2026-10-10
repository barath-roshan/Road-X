"""Candidate Model Evaluation and Promotion Safeguard Subsystem (Phase 21)."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ml.common.logging_config import get_logger
from ml.monitoring.config import monitoring_config

logger = get_logger("monitoring.evaluator")


@dataclass
class ModelMetadata:
    """Standardized metadata container for model versioning and audit trails."""

    model_id: str
    version: str
    algorithm: str
    feature_schema_version: str
    target: str
    created_at: str
    metrics: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationDecision:
    """Result payload summarizing candidate evaluation and promotion decision."""

    candidate_version: str
    baseline_version: str
    recommended_for_promotion: bool
    decision_reason: str
    criteria_evaluations: Dict[str, bool]
    candidate_metrics: Dict[str, float]
    baseline_metrics: Dict[str, float]
    evaluated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CandidateModelEvaluator:
    """Evaluates candidate models against active baseline models before promotion."""

    def __init__(
        self,
        min_precision: float = monitoring_config.min_acceptance_precision,
        min_recall: float = monitoring_config.min_acceptance_recall,
        min_f1: float = monitoring_config.min_acceptance_f1,
        min_roc_auc: float = monitoring_config.min_acceptance_roc_auc,
        max_f1_drop_margin: float = 0.01,
    ) -> None:
        self.min_precision = min_precision
        self.min_recall = min_recall
        self.min_f1 = min_f1
        self.min_roc_auc = min_roc_auc
        self.max_f1_drop_margin = max_f1_drop_margin

    def evaluate_candidate(
        self,
        candidate_metrics: Dict[str, float],
        baseline_metrics: Dict[str, float],
        candidate_version: str = "v2.0_candidate",
        baseline_version: str = "v1.0_baseline",
    ) -> EvaluationDecision:
        """Compare candidate model metrics against baseline metrics and acceptance thresholds.

        Args:
            candidate_metrics: Metrics for newly trained candidate model.
            baseline_metrics: Metrics for currently active production model.
            candidate_version: Candidate model version label.
            baseline_version: Active baseline model version label.

        Returns:
            EvaluationDecision object containing promotion decision and criteria breakdown.
        """
        eval_time = datetime.now(timezone.utc).isoformat()

        cand_f1 = candidate_metrics.get("f1_score", 0.0)
        cand_prec = candidate_metrics.get("precision", 0.0)
        cand_rec = candidate_metrics.get("recall", 0.0)
        cand_auc = candidate_metrics.get("roc_auc", 0.0)

        base_f1 = baseline_metrics.get("f1_score", 0.0)

        criteria = {
            "min_precision_passed": cand_prec >= self.min_precision,
            "min_recall_passed": cand_rec >= self.min_recall,
            "min_f1_passed": cand_f1 >= self.min_f1,
            "min_roc_auc_passed": cand_auc >= self.min_roc_auc,
            "f1_improvement_or_parity_passed": cand_f1 >= (base_f1 - self.max_f1_drop_margin),
        }

        all_passed = all(criteria.values())

        if all_passed:
            reason = (
                f"Candidate model ({candidate_version}) passed all criteria "
                f"(F1={cand_f1:.4f}, ROC-AUC={cand_auc:.4f} vs Baseline F1={base_f1:.4f}). "
                "Recommended for controlled promotion."
            )
        else:
            failed_criteria = [k for k, v in criteria.items() if not v]
            reason = (
                f"Candidate model ({candidate_version}) rejected. Failed criteria: {', '.join(failed_criteria)}. "
                f"Preserving active baseline model ({baseline_version})."
            )

        decision = EvaluationDecision(
            candidate_version=candidate_version,
            baseline_version=baseline_version,
            recommended_for_promotion=all_passed,
            decision_reason=reason,
            criteria_evaluations=criteria,
            candidate_metrics=candidate_metrics,
            baseline_metrics=baseline_metrics,
            evaluated_at=eval_time,
        )

        logger.info("Candidate Model Evaluation Result: %s | Decision: %s", "PROMOTED" if all_passed else "REJECTED", reason)
        return decision
