"""Generate synthetic citizen complaint dataset for development and baseline training.

DISCLAIMER:
SYNTHETIC / MANUALLY CREATED DEVELOPMENT DATA
This dataset is created solely for pipeline development, schema validation, and unit testing.
Metrics on this dataset do NOT reflect real-world production NLP performance. Real citizen complaint
data must be collected and annotated before deploying to production.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import List, Dict, Tuple

from ml.complaint_intelligence.config import config


HEADER_DISCLAIMER = "# SYNTHETIC / MANUALLY CREATED DEVELOPMENT DATA"

# Controlled templates for each issue category, urgency, safety_risk, and location entity
TEMPLATES: Dict[str, List[Tuple[str, str, str]]] = {
    "POTHOLE": [
        (
            "There is a huge pothole near {location} causing severe traffic delays. Bikes are falling into it.",
            "HIGH",
            "HIGH",
        ),
        (
            "Deep dangerous pothole right in the middle of {location}. Urgent repair needed before an accident happens.",
            "CRITICAL",
            "HIGH",
        ),
        (
            "Multiple small potholes formed on {location} after heavy rain. Needs patch work.",
            "MEDIUM",
            "MEDIUM",
        ),
        (
            "A small pothole has opened up near {location}. Please fix it before it expands.",
            "LOW",
            "LOW",
        ),
        (
            "Very large crater-like pothole near {location}. Two two-wheelers skidded yesterday night.",
            "CRITICAL",
            "HIGH",
        ),
        (
            "Potholes on {location} are making commute very uncomfortable and slow.",
            "MEDIUM",
            "LOW",
        ),
    ],
    "ROAD_CRACK": [
        (
            "Long alligator cracks extending across {location}. Road surface is breaking apart.",
            "MEDIUM",
            "MEDIUM",
        ),
        (
            "Severe longitudinal structural crack observed on {location}. Water seepage is making it worse.",
            "HIGH",
            "MEDIUM",
        ),
        (
            "Minor surface hair cracks developing along {location}. Early maintenance recommended.",
            "LOW",
            "LOW",
        ),
        (
            "Deep pavement cracks near {location} causing uneven driving surface.",
            "MEDIUM",
            "MEDIUM",
        ),
    ],
    "ROAD_SURFACE_DAMAGE": [
        (
            "Extensive asphalt peeling and surface erosion near {location}. Driving is extremely bumpy.",
            "MEDIUM",
            "MEDIUM",
        ),
        (
            "Complete tar surface degradation on {location}. Road has worn down to loose gravel.",
            "HIGH",
            "HIGH",
        ),
        (
            "Uneven road top and top coat stripping observed near {location}.",
            "LOW",
            "LOW",
        ),
        (
            "Severe surface rutting and depressions near {location}. Vehicles lose balance.",
            "HIGH",
            "HIGH",
        ),
    ],
    "WATERLOGGING": [
        (
            "Heavy waterlogging near {location} due to poor drainage outlet. Road completely submerged.",
            "HIGH",
            "HIGH",
        ),
        (
            "Stagnant rain water logged at {location} blocking two lanes of traffic.",
            "HIGH",
            "MEDIUM",
        ),
        (
            "Minor water pooling near {location} after evening showers.",
            "LOW",
            "LOW",
        ),
        (
            "Severe waterlogging outside {location}. Pedestrians cannot cross the street.",
            "MEDIUM",
            "MEDIUM",
        ),
    ],
    "FLOODING": [
        (
            "Catastrophic flash flooding on {location}! Water level reached 2 feet, vehicles trapped!",
            "CRITICAL",
            "HIGH",
        ),
        (
            "Knee-deep flood water on {location}. Entire road stretch closed for public safety.",
            "CRITICAL",
            "HIGH",
        ),
        (
            "Storm drain overflow causing localized flooding near {location}.",
            "HIGH",
            "HIGH",
        ),
    ],
    "STREETLIGHT": [
        (
            "All streetlights near {location} are non-functional for past 3 nights. Extremely dark and unsafe.",
            "HIGH",
            "HIGH",
        ),
        (
            "Flickering streetlight pole outside {location}. Needs bulb replacement.",
            "LOW",
            "LOW",
        ),
        (
            "Streetlights on {location} remain off at night, creating high risk for mugging and accidents.",
            "HIGH",
            "HIGH",
        ),
        (
            "Damaged electrical streetlight pole leaning dangerously near {location}.",
            "CRITICAL",
            "HIGH",
        ),
    ],
    "ACCIDENT": [
        (
            "Major road accident reported near {location}! Two vehicles collided, road blocked!",
            "CRITICAL",
            "HIGH",
        ),
        (
            "Near-miss accident happened at {location} due to missing signboards and poor visibility.",
            "HIGH",
            "HIGH",
        ),
        (
            "Skidding incident reported on {location} due to oil spill and wet pavement.",
            "HIGH",
            "HIGH",
        ),
    ],
    "ROAD_OBSTRUCTION": [
        (
            "Fallen tree branch completely obstructing traffic lane near {location}.",
            "HIGH",
            "HIGH",
        ),
        (
            "Illegal parking and unauthorized hoarding obstructing visibility at {location}.",
            "MEDIUM",
            "MEDIUM",
        ),
        (
            "Concrete barricades dumped randomly near {location} creating bottleneck.",
            "MEDIUM",
            "MEDIUM",
        ),
        (
            "Abandoned vehicle blocking the main road near {location}.",
            "MEDIUM",
            "LOW",
        ),
    ],
    "DEBRIS": [
        (
            "Construction debris and loose stones scattered all over {location}. Heavy dust and tire puncture hazard.",
            "MEDIUM",
            "MEDIUM",
        ),
        (
            "Garbage and sharp metal debris dumped on the side of {location}.",
            "MEDIUM",
            "HIGH",
        ),
        (
            "Gravel mud spill from truck near {location} making road slippery.",
            "HIGH",
            "HIGH",
        ),
    ],
    "TRAFFIC_SIGNAL": [
        (
            "Traffic signal lights at {location} are completely down! Chaos and traffic jam at intersection.",
            "CRITICAL",
            "HIGH",
        ),
        (
            "Red light signal timer malfunctioning at {location}.",
            "MEDIUM",
            "MEDIUM",
        ),
        (
            "Pedestrian crossing signal broken near {location}.",
            "LOW",
            "LOW",
        ),
    ],
    "ROAD_CLOSURE": [
        (
            "Road unannounced closure at {location} without proper detour signages.",
            "HIGH",
            "MEDIUM",
        ),
        (
            "Emergency pipeline work causing total road closure near {location}.",
            "HIGH",
            "MEDIUM",
        ),
        (
            "Ditch dug across {location} rendering road impassable for four-wheelers.",
            "CRITICAL",
            "HIGH",
        ),
    ],
    "OTHER": [
        (
            "General complaint regarding noise pollution and missing street signages near {location}.",
            "LOW",
            "LOW",
        ),
        (
            "Footpath paving tiles broken near {location}. Pedestrians tripping over.",
            "LOW",
            "LOW",
        ),
        (
            "Unidentified odor and damaged manhole cover near {location}.",
            "MEDIUM",
            "MEDIUM",
        ),
    ],
}

LOCATIONS: List[str] = [
    "Gandhipuram bus stand",
    "Anna Salai road",
    "MG Road junction",
    "Airport road",
    "Indiranagar 100ft road",
    "Old Madras road",
    "T Nagar bus stand",
    "Vadapalani signal",
    "Coimbatore railway station",
    "Guindy flyover",
    "Koramangala 5th block",
    "Velachery main road",
    "Hebbal flyover circle",
    "Marathahalli bridge",
    "Peenya industrial area",
    "Rajajinagar 4th block",
    "Anna Nagar roundtana",
    "Tambaram railway station",
    "Electronic City phase 1",
    "Whitefield main road",
]


def generate_synthetic_dataset(
    output_path: Path, num_samples_per_category: int = 35, seed: int = 42
) -> Path:
    """Generate synthetic citizen complaints CSV dataset with category, urgency, and safety risk labels."""
    random.seed(seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, str]] = []

    for category, template_list in TEMPLATES.items():
        for i in range(num_samples_per_category):
            template, urgency, safety_risk = random.choice(template_list)
            loc = random.choice(LOCATIONS)
            text = template.format(location=loc)

            # Add slight variations / natural noise
            if random.random() < 0.2:
                text += " Please take immediate action."
            elif random.random() < 0.2:
                text += " Reported multiple times by local residents."

            rows.append(
                {
                    "complaint_text": text,
                    "issue_category": category,
                    "urgency": urgency,
                    "safety_risk": safety_risk,
                }
            )

    # Shuffle rows deterministically
    random.shuffle(rows)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        f.write(f"{HEADER_DISCLAIMER}\n")
        writer = csv.DictWriter(
            f, fieldnames=["complaint_text", "issue_category", "urgency", "safety_risk"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} synthetic citizen complaint samples at {output_path}")
    return output_path


if __name__ == "__main__":
    generate_synthetic_dataset(config.raw_dataset_path)
