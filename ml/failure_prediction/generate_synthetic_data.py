"""Synthetic Road Failure Dataset Generator.

LABEL: SYNTHETIC — FOR DEVELOPMENT ONLY
This dataset is engineered strictly for machine learning pipeline development and testing.
The metrics derived from this dataset represent pipeline validation and must not be
interpreted as real-world civil infrastructure performance.

Temporal Integrity:
Each record represents one road segment at one observation time (t).
Features only include information available up to timestamp t.
The target 'failure_next_30d' indicates whether critical structural failure or
unserviceable road deterioration occurred in the window (t, t + 30 days].
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

from ml.common.config import settings
from ml.common.logging_config import get_logger

logger = get_logger("failure_prediction.generate_synthetic_data")


def generate_synthetic_road_data(
    n_segments: int = 250,
    start_date: str = "2025-01-01",
    num_months: int = 12,
    observations_per_month: int = 2,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a realistic, temporally ordered synthetic road failure dataset.

    Args:
        n_segments: Number of unique road segments across network.
        start_date: Starting observation date string (YYYY-MM-DD).
        num_months: Total span of observations in months.
        observations_per_month: Number of observations recorded per segment each month.
        seed: Random seed for exact reproducibility.

    Returns:
        pd.DataFrame containing historical records with valid temporal structure.
    """
    logger.info(
        "Generating synthetic road failure dataset: %d segments over %d months (seed=%d)",
        n_segments,
        num_months,
        seed,
    )
    rng = np.random.default_rng(seed)

    # 1. Establish segment static characteristics
    segment_ids = [f"SEG-{i+1:04d}" for i in range(n_segments)]
    road_types = rng.choice(["arterial", "collector", "local", "highway"], size=n_segments, p=[0.3, 0.3, 0.3, 0.1])
    road_lengths = np.round(rng.uniform(150.0, 1500.0, size=n_segments), 1)
    lane_counts = rng.choice([1, 2, 4, 6], size=n_segments, p=[0.15, 0.55, 0.25, 0.05])
    baseline_traffic = np.round(rng.uniform(1000.0, 45000.0, size=n_segments), 0)
    baseline_heavy_ratio = np.round(rng.uniform(0.04, 0.38, size=n_segments), 3)

    # 2. Generate observation dates
    base_dt = datetime.strptime(start_date, "%Y-%m-%d")
    total_intervals = num_months * observations_per_month
    date_offsets = [int(i * (365.25 / total_intervals)) for i in range(total_intervals)]
    observation_dates = [base_dt + timedelta(days=d) for d in date_offsets]

    records = []

    for seg_idx, seg_id in enumerate(segment_ids):
        # Segment baseline age and repair state at start of period
        road_age = float(rng.uniform(1.0, 15.0))
        road_quality = float(np.clip(1.0 - (road_age / 22.0) + rng.normal(0, 0.05), 0.15, 0.98))
        days_since_repair = float(rng.uniform(30, max(60, road_age * 280)))
        previous_repairs = int(max(0, road_age // 3.5 + rng.integers(-1, 2)))
        previous_failures = int(max(0, road_age // 5.0 + rng.integers(-1, 2)))

        pothole_count = int(max(0, (1.0 - road_quality) * 12 + rng.integers(-2, 3)))
        crack_ratio = float(np.clip((1.0 - road_quality) * 0.4 + rng.uniform(-0.03, 0.05), 0.0, 0.55))

        for obs_dt in observation_dates:
            # Pavement slowly ages over time
            days_elapsed = (obs_dt - base_dt).days
            current_age = round(road_age + (days_elapsed / 365.25), 2)
            current_days_since_repair = round(days_since_repair + days_elapsed, 1)

            # Seasonal weather simulation (monsoon/rainy spikes mid-year)
            day_of_year = obs_dt.timetuple().tm_yday
            rain_seasonality = np.sin((day_of_year - 80) * 2 * np.pi / 365.25)
            rainfall_30d = float(np.clip(rng.gamma(shape=2.5, scale=40.0) * (1.2 + rain_seasonality), 0.0, 650.0))
            rainfall_7d = float(np.clip(rainfall_30d * rng.uniform(0.15, 0.45), 0.0, rainfall_30d))
            temperature = float(np.round(26.0 + 8.0 * np.cos((day_of_year - 150) * 2 * np.pi / 365.25) + rng.normal(0, 2.5), 1))
            flood_events = int(rng.poisson(lam=0.7 if rainfall_30d > 220 else 0.08))

            # Traffic variations
            traffic = float(np.round(baseline_traffic[seg_idx] * rng.uniform(0.85, 1.15), 0))
            heavy_ratio = float(np.round(np.clip(baseline_heavy_ratio[seg_idx] + rng.normal(0, 0.02), 0.02, 0.45), 3))
            speed = float(np.round(np.clip(55.0 - (traffic / 1800.0) + rng.normal(0, 4.0), 18.0, 95.0), 1))

            # Gradual defect accumulation exacerbated by water and heavy traffic
            water_stress_delta = (rainfall_30d / 500.0) * 0.02
            traffic_stress_delta = (traffic * heavy_ratio / 15000.0) * 0.015
            quality_decay = (days_elapsed / (365.25 * 10.0)) + water_stress_delta + traffic_stress_delta
            current_quality = float(np.clip(road_quality - quality_decay + rng.normal(0, 0.02), 0.05, 0.98))

            current_potholes = int(np.clip(pothole_count + int(water_stress_delta * 40) + rng.integers(-1, 3), 0, 35))
            current_crack_ratio = float(np.clip(crack_ratio + (1.0 - current_quality) * 0.15 + rng.uniform(-0.02, 0.03), 0.0, 0.60))

            # Complaints correlated with defects and traffic exposure
            complaint_rate = (current_potholes * 0.6) + (current_crack_ratio * 15) + (traffic / 8000.0)
            citizen_complaints = int(np.clip(rng.poisson(lam=max(0.2, complaint_rate)), 0, 25))

            # 3. Ground-truth future failure probability (30-day forward horizon)
            # Logit model based on civil engineering failure drivers:
            # - High age and low quality score
            # - High heavy vehicle axle repetitions
            # - Severe rainfall saturation and flood pounding
            # - Acute surface distress (potholes, extensive cracking)
            # - Stale repairs and high citizen distress signals
            logit = (
                -3.5
                + (0.12 * current_age)
                - (4.0 * current_quality)
                + (0.000035 * traffic * heavy_ratio)
                + (0.0035 * rainfall_30d)
                + (0.45 * flood_events)
                + (0.0008 * current_days_since_repair)
                + (0.10 * current_potholes)
                + (3.2 * current_crack_ratio)
                + (0.08 * citizen_complaints)
                + rng.normal(0, 0.4)  # Real-world stochastic variation
            )

            failure_prob = 1.0 / (1.0 + np.exp(-logit))
            failure_next_30d = int(rng.binomial(n=1, p=failure_prob))

            records.append({
                "segment_id": seg_id,
                "observation_date": obs_dt.strftime("%Y-%m-%d"),
                "road_age_years": round(current_age, 2),
                "road_length_m": road_lengths[seg_idx],
                "lane_count": lane_counts[seg_idx],
                "road_quality_score": round(current_quality, 4),
                "traffic_volume": traffic,
                "heavy_vehicle_ratio": heavy_ratio,
                "average_speed_kmph": speed,
                "rainfall_7d_mm": round(rainfall_7d, 1),
                "rainfall_30d_mm": round(rainfall_30d, 1),
                "temperature_avg_c": temperature,
                "flood_events_30d": flood_events,
                "days_since_repair": round(current_days_since_repair, 1),
                "previous_repairs": previous_repairs,
                "previous_failures": previous_failures,
                "citizen_complaints_30d": citizen_complaints,
                "pothole_count": current_potholes,
                "crack_ratio": round(current_crack_ratio, 4),
                "failure_next_30d": failure_next_30d,
            })

    df = pd.DataFrame(records)
    # Sort chronologically to preserve temporal ordering
    df = df.sort_values(by=["observation_date", "segment_id"]).reset_index(drop=True)

    pos_pct = (df["failure_next_30d"].mean()) * 100.0
    logger.info(
        "Generated synthetic dataset: %d rows, %d columns. Positive class (failure_next_30d=1): %.2f%%",
        len(df),
        df.shape[1],
        pos_pct,
    )
    return df


def main() -> None:
    """CLI script entrypoint to generate and persist synthetic development dataset."""
    parser = argparse.ArgumentParser(description="Generate synthetic road failure prediction dataset.")
    parser.add_argument("--output", type=str, default=str(settings.raw_data_dir / "synthetic_road_failure_data.csv"))
    parser.add_argument("--segments", type=int, default=250)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = generate_synthetic_road_data(n_segments=args.segments, seed=args.seed)
    df.to_csv(out_path, index=False)
    print(f"Synthetic dataset successfully written to: {out_path} ({len(df)} records)")


if __name__ == "__main__":
    main()
