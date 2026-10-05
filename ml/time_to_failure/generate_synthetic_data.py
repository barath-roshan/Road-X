"""Generate synthetic road segment survival dataset for development and baseline training.

DISCLAIMER:
SYNTHETIC DEVELOPMENT DATA
This dataset is created solely for pipeline development, schema validation, and unit testing.
Metrics on this dataset do NOT reflect real-world production NLP or physical pavement performance. Real road
segment failure telemetry must be collected and annotated before deploying to production.
"""

from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

from ml.time_to_failure.config import config


HEADER_DISCLAIMER = "# SYNTHETIC DEVELOPMENT DATA"


def generate_synthetic_survival_dataset(
    output_path: Path, num_samples: int = 500, seed: int = 42
) -> Path:
    """Generate realistic longitudinal road segment survival observations with censoring flags."""
    random.seed(seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base_date = datetime(2025, 1, 1)
    rows: List[Dict[str, str]] = []

    for i in range(1, num_samples + 1):
        segment_id = f"SEG-{i:04d}"
        obs_date = base_date + timedelta(days=random.randint(0, 180))

        # Road parameters
        age = round(random.uniform(1.0, 15.0), 1)
        length_m = round(random.uniform(100.0, 2500.0), 1)
        lanes = random.choice([1, 2, 4, 6])
        quality = round(random.uniform(0.20, 0.95), 2)
        traffic = round(random.uniform(1000.0, 45000.0), 1)
        heavy_ratio = round(random.uniform(0.05, 0.45), 2)
        avg_speed = round(random.uniform(25.0, 75.0), 1)

        rain_7d = round(random.uniform(0.0, 150.0), 1)
        rain_30d = round(rain_7d + random.uniform(20.0, 300.0), 1)
        temp_c = round(random.uniform(18.0, 38.0), 1)
        floods = random.choice([0, 0, 0, 1, 2, 3])

        days_repair = round(random.uniform(30.0, 1800.0), 1)
        prev_repairs = random.randint(0, 5)
        prev_failures = random.randint(0, 3)
        complaints = random.randint(0, 15)
        potholes = random.randint(0, 12)
        crack_ratio = round(random.uniform(0.01, 0.35), 2)

        # Baseline hazard / degradation acceleration formula
        damage_score = (potholes * 0.70) + (crack_ratio * 100.0 * 0.30)
        vulnerability = age * (1.0 - quality)
        traffic_stress = (traffic / 10000.0) * heavy_ratio

        # Scale parameter lambda_days (higher distress -> shorter remaining days)
        log_lambda = 5.5 - (0.05 * damage_score) - (0.08 * vulnerability) - (0.20 * traffic_stress) - (0.0005 * days_repair)
        lambda_days = max(10.0, math.exp(log_lambda))

        # Generate Weibull survival time
        weibull_shape = 1.3
        u = random.uniform(0.001, 0.999)
        true_survival_days = lambda_days * ((-math.log(u)) ** (1.0 / weibull_shape))

        # Study window censoring at 365 days
        study_window_days = 365.0
        if true_survival_days <= study_window_days:
            time_to_event = round(max(1.0, true_survival_days), 1)
            event_observed = 1
        else:
            time_to_event = round(study_window_days, 1)
            event_observed = 0

        rows.append(
            {
                "segment_id": segment_id,
                "observation_date": obs_date.strftime("%Y-%m-%d"),
                "road_age_years": str(age),
                "road_length_m": str(length_m),
                "lane_count": str(lanes),
                "road_quality_score": str(quality),
                "traffic_volume": str(traffic),
                "heavy_vehicle_ratio": str(heavy_ratio),
                "average_speed_kmph": str(avg_speed),
                "rainfall_7d_mm": str(rain_7d),
                "rainfall_30d_mm": str(rain_30d),
                "temperature_avg_c": str(temp_c),
                "flood_events_30d": str(floods),
                "days_since_repair": str(days_repair),
                "previous_repairs": str(prev_repairs),
                "previous_failures": str(prev_failures),
                "citizen_complaints_30d": str(complaints),
                "pothole_count": str(potholes),
                "crack_ratio": str(crack_ratio),
                "time_to_event_days": str(time_to_event),
                "event_observed": str(event_observed),
            }
        )

    fieldnames = [
        "segment_id",
        "observation_date",
        "road_age_years",
        "road_length_m",
        "lane_count",
        "road_quality_score",
        "traffic_volume",
        "heavy_vehicle_ratio",
        "average_speed_kmph",
        "rainfall_7d_mm",
        "rainfall_30d_mm",
        "temperature_avg_c",
        "flood_events_30d",
        "days_since_repair",
        "previous_repairs",
        "previous_failures",
        "citizen_complaints_30d",
        "pothole_count",
        "crack_ratio",
        "time_to_event_days",
        "event_observed",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        f.write(f"{HEADER_DISCLAIMER}\n")
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} synthetic road survival observations at {output_path}")
    return output_path


if __name__ == "__main__":
    generate_synthetic_survival_dataset(config.raw_dataset_path)
