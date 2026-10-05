"""Generate synthetic maintenance priority scenarios dataset for development and testing.

DISCLAIMER:
SYNTHETIC DEVELOPMENT DATA
This dataset is created solely for pipeline development, schema validation, and unit testing.
Metrics on this dataset do NOT reflect real-world production performance. Real municipal maintenance
priority decisions must be collected and annotated before deploying to production.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import List, Dict

from ml.priority_engine.config import config


HEADER_DISCLAIMER = "# SYNTHETIC DEVELOPMENT DATA"


def generate_synthetic_priority_dataset(
    output_path: Path, num_samples: int = 250, seed: int = 42
) -> Path:
    """Generate synthetic maintenance priority input and recommendation scenarios."""
    random.seed(seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, str]] = []

    for i in range(1, num_samples + 1):
        segment_id = f"SEG-{i:04d}"
        complaint_id = f"COMP-{i:04d}"

        fail_prob = round(random.uniform(0.05, 0.95), 2)
        sev_score = round(random.uniform(10.0, 95.0), 1)
        safety_risk = random.choice(["LOW", "MEDIUM", "HIGH"])
        urgency = random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        related_count = random.choice([0, 1, 2, 4, 7, 12])
        ttf_days = round(random.uniform(5.0, 300.0), 1)

        # Baseline score calculation for synthetic data target
        raw_score = (
            (fail_prob * 100.0 * 0.25)
            + (sev_score * 0.25)
            + ({"HIGH": 90.0, "MEDIUM": 50.0, "LOW": 10.0}[safety_risk] * 0.20)
            + ({"CRITICAL": 100.0, "HIGH": 75.0, "MEDIUM": 45.0, "LOW": 15.0}[urgency] * 0.10)
        )

        if safety_risk == "HIGH" or urgency == "CRITICAL" or fail_prob > 0.8:
            raw_score = max(raw_score, 65.0)

        raw_score = round(min(100.0, max(0.0, raw_score)), 1)

        if raw_score >= 80.0:
            p_level = "CRITICAL"
        elif raw_score >= 60.0:
            p_level = "HIGH"
        elif raw_score >= 35.0:
            p_level = "MEDIUM"
        else:
            p_level = "LOW"

        rows.append(
            {
                "road_segment_id": segment_id,
                "complaint_id": complaint_id,
                "failure_probability": str(fail_prob),
                "severity_score": str(sev_score),
                "safety_risk": safety_risk,
                "urgency": urgency,
                "related_complaint_count": str(related_count),
                "estimated_time_to_failure_days": str(ttf_days),
                "target_priority_score": str(raw_score),
                "target_priority_level": p_level,
            }
        )

    fieldnames = [
        "road_segment_id",
        "complaint_id",
        "failure_probability",
        "severity_score",
        "safety_risk",
        "urgency",
        "related_complaint_count",
        "estimated_time_to_failure_days",
        "target_priority_score",
        "target_priority_level",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        f.write(f"{HEADER_DISCLAIMER}\n")
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} synthetic priority scenario records at {output_path}")
    return output_path


if __name__ == "__main__":
    generate_synthetic_priority_dataset(config.raw_dataset_path)
