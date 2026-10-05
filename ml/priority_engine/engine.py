"""MaintenancePriorityEngine orchestrator pipeline for RoadX (Phase 8)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union, Dict, Any

from ml.priority_engine.config import config
from ml.priority_engine.schemas import (
    MaintenancePriorityInput,
    MaintenancePriorityOutput,
    MaintenancePriorityLevel,
)
from ml.priority_engine.normalizer import PriorityNormalizer
from ml.priority_engine.rules import PriorityRuleEngine
from ml.priority_engine.scorer import PriorityScorer
from ml.priority_engine.explainer import PriorityExplainer


class MaintenancePriorityEngine:
    """Orchestrates multi-signal ML outputs into an actionable, ranked maintenance priority recommendation

    for municipal government officer review.
    """

    def __init__(
        self,
        normalizer: Optional[PriorityNormalizer] = None,
        rule_engine: Optional[PriorityRuleEngine] = None,
        scorer: Optional[PriorityScorer] = None,
        explainer: Optional[PriorityExplainer] = None,
        version: str = "v1",
    ) -> None:
        self.normalizer = normalizer or PriorityNormalizer()
        self.rule_engine = rule_engine or PriorityRuleEngine()
        self.scorer = scorer or PriorityScorer(version=version)
        self.explainer = explainer or PriorityExplainer()
        self.version = version

    def prioritize(self, input_data: MaintenancePriorityInput) -> MaintenancePriorityOutput:
        """Synthesize multi-source ML signals and compute maintenance priority recommendation.

        Args:
            input_data: MaintenancePriorityInput Pydantic model.

        Returns:
            MaintenancePriorityOutput structured Pydantic response.
        """
        # 1. Extract Granular Evidence
        evidence = self.normalizer.extract_evidence(input_data)

        # 2. Normalize Available Feature Signals & Identify Missing Evidence
        normalized_scores, missing_notices = self.normalizer.normalize_signals(evidence)

        # 3. Compute Composite Raw Score & Priority Level
        raw_score, base_level = self.scorer.predict(normalized_scores)

        # 4. Apply Safety-First Guardrail Rules
        final_score, final_level, guardrail_triggers = self.rule_engine.apply_guardrails(
            raw_score=raw_score, assigned_level=base_level, evidence=evidence
        )

        # 5. Generate Human-Readable Supporting Evidence Reasons
        reasons = self.explainer.generate_explanations(
            evidence=evidence, guardrail_triggers=guardrail_triggers
        )

        segment_id = input_data.road_segment_id or "SEG-UNKNOWN"
        complaint_id = input_data.complaint_id or "COMP-UNKNOWN"

        return MaintenancePriorityOutput(
            road_segment_id=segment_id,
            complaint_id=complaint_id,
            priority_score=final_score,
            priority_level=final_level,
            evidence=evidence,
            reasons=reasons,
            missing_evidence_notices=missing_notices,
            requires_government_review=True,
            model_version=self.version,
        )

    def save(self, model_dir: Optional[Union[str, Path]] = None) -> None:
        """Save priority engine configuration metadata."""
        target_dir = Path(model_dir or config.model_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        # Priority engine is deterministic and rule-assisted
        config.ensure_directories()

    @classmethod
    def load(cls, model_dir: Optional[Union[str, Path]] = None) -> MaintenancePriorityEngine:
        """Load MaintenancePriorityEngine instance."""
        return cls()
