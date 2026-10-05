"""Generate synthetic duplicate complaint pairs dataset for development and evaluation.

DISCLAIMER:
SYNTHETIC / MANUALLY CREATED DEVELOPMENT DATA
This dataset is created solely for pipeline development, baseline model training, and unit testing.
Metrics on this dataset do NOT reflect real-world production performance. Real citizen complaint pairs
must be collected and annotated before deploying to production.
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict

from ml.duplicate_detection.config import config


HEADER_DISCLAIMER = "# SYNTHETIC / MANUALLY CREATED DEVELOPMENT DATA"

# Seed complaints for generating duplicates and non-duplicates
BASE_COMPLAINTS = [
    {
        "text": "Huge pothole near Gandhipuram bus stand causing severe traffic delays. Bikes falling.",
        "category": "POTHOLE",
        "lat": 11.0168,
        "lon": 76.9558,
    },
    {
        "text": "Deep dangerous pothole on Anna Salai road near station. Urgent repair needed.",
        "category": "POTHOLE",
        "lat": 13.0827,
        "lon": 80.2707,
    },
    {
        "text": "Streetlight pole non-functional outside MG Road junction. Dark and dangerous at night.",
        "category": "STREETLIGHT",
        "lat": 12.9716,
        "lon": 77.5946,
    },
    {
        "text": "Heavy waterlogging near Airport road bridge blocking two lanes of traffic.",
        "category": "WATERLOGGING",
        "lat": 12.9850,
        "lon": 77.6630,
    },
    {
        "text": "Long alligator cracks extending across Vadapalani signal road surface.",
        "category": "ROAD_CRACK",
        "lat": 13.0500,
        "lon": 80.2120,
    },
]

REPHRASINGS = [
    "A big pothole near {loc} is creating severe traffic congestion.",
    "Bikes are skidding due to a deep pothole near {loc}.",
    "Streetlight not working near {loc}, area is very dark.",
    "Road flooded and waterlogged near {loc}, vehicles stranded.",
    "Cracks formed on road surface near {loc}, dangerous for driving.",
]

LOCATIONS = [
    ("Gandhipuram bus stand", 11.0168, 76.9558),
    ("Anna Salai road", 13.0827, 80.2707),
    ("MG Road junction", 12.9716, 77.5946),
    ("Airport road", 12.9850, 77.6630),
    ("Vadapalani signal", 13.0500, 80.2120),
]


def generate_synthetic_pairs(
    output_path: Path, num_pairs: int = 300, seed: int = 42
) -> Path:
    """Generate synthetic pairs of duplicate (1) and non-duplicate (0) complaints."""
    random.seed(seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, str]] = []
    base_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)

    for i in range(num_pairs):
        is_duplicate = 1 if i % 2 == 0 else 0

        if is_duplicate:
            # Pick a base complaint and create a close spatial/temporal duplicate
            loc_name, lat, lon = random.choice(LOCATIONS)
            text_a = f"There is a huge pothole near {loc_name}. Bikes struggling to pass."
            text_b = f"Large dangerous pothole reported near {loc_name}. Please fix."
            cat = "POTHOLE"

            # Small coordinate jitter (< 100 meters, approx 0.0008 deg)
            lat_a, lon_a = lat, lon
            lat_b = lat + random.uniform(-0.0005, 0.0005)
            lon_b = lon + random.uniform(-0.0005, 0.0005)

            time_a = base_time + timedelta(hours=random.randint(0, 48))
            time_b = time_a + timedelta(hours=random.randint(1, 12))

            cat_a, cat_b = cat, cat
        else:
            # Pick two distinct complaints far apart spatially and temporally
            loc_a, lat_a, lon_a = LOCATIONS[i % len(LOCATIONS)]
            loc_b, lat_b, lon_b = LOCATIONS[(i + 2) % len(LOCATIONS)]

            text_a = f"Pothole near {loc_a} causing delay."
            text_b = f"Streetlight broken near {loc_b} outside park."

            time_a = base_time + timedelta(days=random.randint(0, 10))
            time_b = time_a + timedelta(days=random.randint(30, 90))

            cat_a = "POTHOLE"
            cat_b = "STREETLIGHT"

        rows.append(
            {
                "complaint_id_a": f"GRV-A-{i:03d}",
                "text_a": text_a,
                "lat_a": f"{lat_a:.6f}",
                "lon_a": f"{lon_a:.6f}",
                "created_at_a": time_a.isoformat(),
                "category_a": cat_a,
                "complaint_id_b": f"GRV-B-{i:03d}",
                "text_b": text_b,
                "lat_b": f"{lat_b:.6f}",
                "lon_b": f"{lon_b:.6f}",
                "created_at_b": time_b.isoformat(),
                "category_b": cat_b,
                "is_duplicate": str(is_duplicate),
            }
        )

    random.shuffle(rows)

    fieldnames = [
        "complaint_id_a",
        "text_a",
        "lat_a",
        "lon_a",
        "created_at_a",
        "category_a",
        "complaint_id_b",
        "text_b",
        "lat_b",
        "lon_b",
        "created_at_b",
        "category_b",
        "is_duplicate",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        f.write(f"{HEADER_DISCLAIMER}\n")
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} synthetic duplicate complaint pairs at {output_path}")
    return output_path


if __name__ == "__main__":
    generate_synthetic_pairs(config.raw_dataset_path)
