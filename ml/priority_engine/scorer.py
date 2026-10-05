"""Composite priority scorer computing administrative maintenance priority scores and tiers."""

from __future__ import annotations

from typing import Dict, List, Tuple

from ml.common.base import BaseModel
from ml.priority_engine.config import config
from ml.priority_engine.schemas import (
    MaintenancePriorityLevel,
    PrioritySignalEvidence,
)
from ml.priority_engine.normalizer import PriorityNormalizer
from ml.priority_engine.rules import PriorityRuleEngine


class PriorityScorer(BaseModel):
    """Calculates dynamic composite priority scores (0.0 to 100.0) and assigns maintenance priority levels."""

    def __init__(self, version: str = "v1") -> None:
        super().__init__(model_name="PriorityScorer", version=version)
        self.normalizer = PriorityNormalizer()
        self.rule_engine = PriorityRuleEngine()

        # Signal weights map
        self.weight_map: Dict[str, float] = {
            "failure_risk": config.failure_risk_weight,
            "severity": config.severity_weight,
            "safety_risk": config.safety_risk_weight,
            "time_to_failure": config.time_to_failure_weight,
            "urgency": config.urgency_weight,
            "complaint_volume": config.complaint_volume_weight,
        }

    def train(self, *args, **kwargs) -> Dict[str, Any]:
        """PriorityScorer is rule-assisted and deterministic. Returns configuration metadata."""
        self._is_fitted = True
        self.metadata = {
            "model_name": self.model_name,
            "version": self.version,
            "weights": self.weight_map,
            "thresholds": config.score_thresholds,
        }
        return self.metadata

    def predict(self, normalized_scores: Dict[str, float]) -> Tuple[float, MaintenancePriorityLevel]:
        """Compute composite priority score and assign administrative priority level."""
        if not normalized_scores:
            return 0.0, MaintenancePriorityLevel.LOW

        available_weights = []
        available_scores = []

        for signal_key, score_val in normalized_scores.items():
            if signal_key in self.weight_map:
                available_weights.append(self.weight_map[signal_key])
                available_scores.append(score_val)

        total_weight = sum(available_weights)
        if total_weight <= 0:
            return 0.0, MaintenancePriorityLevel.LOW

        normalized_weights = [w / total_weight for w in available_weights]
        raw_score = float(sum(w * s for w, s in zip(normalized_weights, available_scores)))
        raw_score = float(max(0.0, min(100.0, raw_score)))

        assigned_level = self.assign_priority_level(raw_score)
        return raw_score, assigned_level

    def assign_priority_level(self, score: float) -> MaintenancePriorityLevel:
        """Assign MaintenancePriorityLevel enum based on score thresholds."""
        if score >= config.score_thresholds["CRITICAL_MIN_SCORE"]:
            return MaintenancePriorityLevel.CRITICAL
        elif score >= config.score_thresholds["HIGH_MIN_SCORE"]:
            return MaintenancePriorityLevel.HIGH
        elif score >= config.score_thresholds["MEDIUM_MIN_SCORE"]:
            return MaintenancePriorityLevel.MEDIUM
        else:
            return MaintenancePriorityLevel.LOW

    def predict_proba(self, X: Any, *args: Any, **kwargs: Any) -> Any:
        """Not applicable for deterministic priority scoring."""
        raise NotImplementedError("PriorityScorer uses deterministic scoring rules.")

    def save(self, path: Any) -> None:
        """Save configuration metadata."""
        pass

    @classmethod
    def load(cls, path: Any) -> PriorityScorer:
        """Load default PriorityScorer instance."""
        return cls()
