"""Training and metadata initialization script for Maintenance Priority Engine (Phase 8)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from ml.priority_engine.config import config
from ml.priority_engine.generate_synthetic_data import generate_synthetic_priority_dataset
from ml.priority_engine.engine import MaintenancePriorityEngine
from ml.priority_engine.evaluate import (
    evaluate_priority_engine_invariants,
    print_priority_evaluation_summary,
)


def train_priority_engine(
    dataset_path: Path = config.raw_dataset_path,
    model_dir: Path = config.model_dir,
) -> Dict[str, Any]:
    """Initialize priority engine, evaluate system invariants against synthetic scenarios, and save metadata."""
    config.ensure_directories()

    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}. Generating synthetic scenarios...")
        generate_synthetic_priority_dataset(dataset_path)

    print("Initializing Maintenance Priority Engine...")
    engine = MaintenancePriorityEngine(version=config.model_version)
    engine.save(model_dir)

    print("Evaluating system invariants and safety guardrails...")
    results = evaluate_priority_engine_invariants(engine)
    print_priority_evaluation_summary(results)

    # Save Metadata JSON
    metadata = {
        "dataset_type": "SYNTHETIC DEVELOPMENT DATA",
        "disclaimer": (
            "Current maintenance priority rules are development baselines based on synthetic scenarios and "
            "must not be interpreted as production government decisions."
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_version": config.model_version,
        "weights": {
            "failure_risk_weight": config.failure_risk_weight,
            "severity_weight": config.severity_weight,
            "safety_risk_weight": config.safety_risk_weight,
            "time_to_failure_weight": config.time_to_failure_weight,
            "urgency_weight": config.urgency_weight,
            "complaint_volume_weight": config.complaint_volume_weight,
        },
        "score_thresholds": config.score_thresholds,
        "system_invariants_passed": results["all_invariants_passed"],
    }

    metadata_path = model_dir / "metadata" / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nPriority Engine configuration artifacts initialized at: {model_dir}")
    print(f"Metadata written to: {metadata_path}")

    return {
        "evaluation_results": results,
        "metadata_path": str(metadata_path),
    }


if __name__ == "__main__":
    train_priority_engine()
