"""Synthetic Damage Severity Dataset Generator.

LABEL: SYNTHETIC — FOR DEVELOPMENT ONLY
This dataset is engineered strictly for machine learning pipeline development and testing.
The metrics derived from this dataset represent pipeline validation and must not be
interpreted as real-world civil infrastructure performance.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from ml.common.config import settings
from ml.common.logging_config import get_logger

logger = get_logger("severity.generate_synthetic_data")


def generate_synthetic_severity_data(
    n_samples: int = 3000,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a realistic synthetic damage severity dataset.

    Args:
        n_samples: Number of observation records to generate.
        seed: Random seed for exact reproducibility.

    Returns:
        pd.DataFrame containing synthetic vision detection + road context features and severity_score target.
    """
    logger.info("Generating synthetic damage severity dataset: %d samples (seed=%d)", n_samples, seed)
    rng = np.random.default_rng(seed)

    records = []
    for i in range(n_samples):
        # 1. Vision detection signals
        has_detection = bool(rng.choice([True, False], p=[0.85, 0.15]))

        if has_detection:
            detection_count = int(rng.choice([1, 2, 3, 4, 5, 6], p=[0.50, 0.25, 0.13, 0.07, 0.03, 0.02]))
            area_ratios = list(rng.exponential(scale=0.04, size=detection_count) + 0.005)
            confidences = list(rng.uniform(0.35, 0.98, size=detection_count))

            img_width, img_height = 640.0, 480.0
            surface_area = img_width * img_height

            bbox_areas = [ar * surface_area for ar in area_ratios]

            total_area_ratio = float(np.clip(sum(area_ratios), 0.005, 0.60))
            max_area_ratio = float(max(area_ratios))
            avg_area_ratio = float(np.mean(area_ratios))
            max_confidence = float(max(confidences))
            avg_confidence = float(np.mean(confidences))
            total_bbox_area = float(sum(bbox_areas))
            max_bbox_area = float(max(bbox_areas))
        else:
            detection_count = 0
            total_area_ratio = 0.0
            max_area_ratio = 0.0
            avg_area_ratio = 0.0
            max_confidence = 0.0
            avg_confidence = 0.0
            total_bbox_area = 0.0
            max_bbox_area = 0.0

        # 2. Road context signals
        road_age_years = round(float(rng.uniform(0.5, 18.0)), 2)
        road_quality_score = round(float(np.clip(1.0 - (road_age_years / 22.0) + rng.normal(0, 0.06), 0.10, 0.98)), 4)
        traffic_volume = round(float(rng.uniform(800.0, 50000.0)), 0)
        heavy_vehicle_ratio = round(float(rng.uniform(0.03, 0.40)), 3)
        citizen_complaints_30d = int(max(0, rng.poisson(lam=max(0.1, (1.0 - road_quality_score) * 8.0))))

        # 3. Ground-truth physical damage severity score (0.0 to 100.0)
        # Structural equation: area extent + defect count + pavement fragility + traffic stress
        base_severity = (
            10.0
            + (135.0 * total_area_ratio)
            + (5.0 * detection_count)
            - (30.0 * road_quality_score)
            + (0.000035 * traffic_volume * heavy_vehicle_ratio)
            + (1.2 * citizen_complaints_30d)
            + (0.8 * road_age_years)
            + rng.normal(0.0, 3.5)  # Stochastic variation
        )

        severity_score = round(float(np.clip(base_severity, 0.0, 100.0)), 1)

        records.append({
            "detection_count": detection_count,
            "total_area_ratio": total_area_ratio,
            "max_area_ratio": max_area_ratio,
            "avg_area_ratio": avg_area_ratio,
            "max_confidence": max_confidence,
            "avg_confidence": avg_confidence,
            "total_bbox_area": total_bbox_area,
            "max_bbox_area": max_bbox_area,
            "road_quality_score": road_quality_score,
            "traffic_volume": traffic_volume,
            "heavy_vehicle_ratio": heavy_vehicle_ratio,
            "road_age_years": road_age_years,
            "citizen_complaints_30d": citizen_complaints_30d,
            "severity_score": severity_score,
        })

    df = pd.DataFrame(records)
    logger.info("Generated synthetic severity dataset: %d rows x %d cols. Mean severity: %.2f", len(df), df.shape[1], df["severity_score"].mean())
    return df


def main() -> None:
    """CLI entrypoint to generate synthetic severity dataset."""
    parser = argparse.ArgumentParser(description="Generate synthetic damage severity dataset.")
    parser.add_argument("--output", type=str, default=str(settings.raw_data_dir / "synthetic_damage_severity_data.csv"))
    parser.add_argument("--samples", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = generate_synthetic_severity_data(n_samples=args.samples, seed=args.seed)
    df.to_csv(out_path, index=False)
    print(f"Synthetic severity dataset successfully written to: {out_path} ({len(df)} records)")


if __name__ == "__main__":
    main()
