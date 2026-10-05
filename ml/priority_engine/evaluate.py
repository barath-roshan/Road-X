"""System invariants and rule compliance evaluation helper for Maintenance Priority Engine."""

from __future__ import annotations

from typing import Dict, Any, List
from ml.priority_engine.engine import MaintenancePriorityEngine
from ml.priority_engine.schemas import (
    MaintenancePriorityInput,
    MaintenancePriorityLevel,
)
from ml.failure_prediction.schemas import FailurePredictionOutput, FailureRiskLevel
from ml.severity.schemas import SeverityPredictionOutput, DamageSeverityLevel
from ml.complaint_intelligence.schemas import (
    ComplaintAnalysisResponse,
    IssueCategory,
    UrgencyLevel,
    SafetyRiskLevel,
)


def evaluate_priority_engine_invariants(
    engine: MaintenancePriorityEngine,
) -> Dict[str, Any]:
    """Evaluate core system invariants (monotonicity, safety guardrails, determinism, missing signal safety)."""
    results = {}

    # Invariant 1: Determinism (Same input -> Same output)
    inp1 = MaintenancePriorityInput(
        road_segment_id="SEG-DET-01",
        failure_prediction=FailurePredictionOutput(
            failure_probability=0.75,
            risk_level=FailureRiskLevel.HIGH,
            model_version="v1",
        ),
    )
    out1_a = engine.prioritize(inp1)
    out1_b = engine.prioritize(inp1)
    results["determinism"] = (
        out1_a.priority_score == out1_b.priority_score
        and out1_a.priority_level == out1_b.priority_level
    )

    # Invariant 2: Failure Risk Monotonicity (Higher failure prob -> Higher/Equal priority score)
    inp2_low = MaintenancePriorityInput(
        failure_prediction=FailurePredictionOutput(
            failure_probability=0.20, risk_level=FailureRiskLevel.LOW, model_version="v1"
        )
    )
    inp2_high = MaintenancePriorityInput(
        failure_prediction=FailurePredictionOutput(
            failure_probability=0.85, risk_level=FailureRiskLevel.HIGH, model_version="v1"
        )
    )
    out2_low = engine.prioritize(inp2_low)
    out2_high = engine.prioritize(inp2_high)
    results["failure_risk_monotonicity"] = out2_high.priority_score >= out2_low.priority_score

    # Invariant 3: Safety Guardrail Enforcement (High safety risk -> Minimum HIGH level)
    inp3 = MaintenancePriorityInput(
        complaint_analysis=ComplaintAnalysisResponse(
            issue_category=IssueCategory.POTHOLE,
            issue_confidence=0.9,
            urgency=UrgencyLevel.LOW,
            urgency_confidence=0.9,
            safety_risk=SafetyRiskLevel.HIGH,
            safety_confidence=0.9,
            location_mentions=[],
            embedding_available=True,
            model_version="v1",
        )
    )
    out3 = engine.prioritize(inp3)
    results["safety_guardrail_compliance"] = out3.priority_level in (
        MaintenancePriorityLevel.HIGH,
        MaintenancePriorityLevel.CRITICAL,
    )

    # Invariant 4: Missing Signals Safety (Engine runs safely without crashing)
    inp4_empty = MaintenancePriorityInput()
    out4 = engine.prioritize(inp4_empty)
    results["missing_signal_safety"] = (
        out4.priority_level == MaintenancePriorityLevel.LOW and len(out4.missing_evidence_notices) > 0
    )

    all_passed = all(results.values())
    results["all_invariants_passed"] = all_passed
    return results


def print_priority_evaluation_summary(results: Dict[str, Any]) -> None:
    """Print formatted system invariants evaluation report."""
    print("\n==========================================")
    print(" EVALUATION REPORT: Maintenance Priority Engine")
    print("==========================================")
    print(f" Determinism Check           : {'PASS' if results['determinism'] else 'FAIL'}")
    print(f" Failure Risk Monotonicity   : {'PASS' if results['failure_risk_monotonicity'] else 'FAIL'}")
    print(f" Safety Guardrail Compliance : {'PASS' if results['safety_guardrail_compliance'] else 'FAIL'}")
    print(f" Missing Signal Safety       : {'PASS' if results['missing_signal_safety'] else 'FAIL'}")
    print("-" * 42)
    print(f" Overall Status              : {'ALL INVARIANTS PASSED' if results['all_invariants_passed'] else 'INVARIANT FAILURE'}")
    print("==========================================")
