# RoadX

**RoadX** is an intelligent road grievance and municipal infrastructure maintenance platform.

Citizens can report road-related hazards and defects—such as potholes, road cracks, surface erosion, waterlogging/flooding, accidents, malfunctioning streetlights, and structural damages—by providing descriptions, geolocations, and imagery.

RoadX leverages Machine Learning to assist government engineers and municipal officers in understanding citizen complaints, evaluating road damage, predicting failure risks, estimating remaining lifespan, and prioritizing repairs.

> **Human-in-the-Loop Governance:** AI predictions assist government officers with data-driven decision support; they do **not** automatically make final administrative decisions. Government officers review all AI results, approve work orders dispatched to contractors, and inspect post-repair completion evidence. A grievance is officially resolved only after government officer verification.

---

## Current ML Architecture

The RoadX machine learning subsystem is designed with strict modularity and separation of concerns across 8 key components:

1. **Road Failure Prediction** (`ml/failure_prediction/`)
   Predicts the probability and risk level of imminent structural road failure using grievance telemetry, pavement characteristics, historical stress factors, and weather conditions.

2. **Existing Road Damage Detection Integration** (`ml/damage_detection/`)
   Integrates computer vision capabilities for detecting potholes, surface cracks, and road degradation.
   > **Note:** Road damage detection is already developed separately and will be integrated into RoadX rather than rebuilt. It will be incorporated via a clean adapter interface in a subsequent phase.

3. **Damage Severity Estimation** (`ml/severity/`)
   Quantifies defect depth, surface area coverage, and hazard levels to gauge physical severity.

4. **Complaint Intelligence** (`ml/complaint_intelligence/`)
   Applies Natural Language Processing to extract complaint categories, assess urgency, identify sentiment, and parse unstructured citizen reports.

5. **Duplicate Complaint Detection** (`ml/duplicate_detection/`)
   Clusters multi-citizen reports addressing the same incident using spatiotemporal proximity and content matching to eliminate duplicate tickets.

6. **Time-to-Failure Prediction** (`ml/time_to_failure/`)
   Estimates deterioration velocity and forecasts the expected time horizon before road damage escalates into critical failure.

7. **Maintenance Priority Engine** (`ml/priority_engine/`)
   Synthesizes failure risk, severity ratings, traffic impact, weather vulnerability, and public complaints into an actionable, ranked maintenance queue for municipal officers.

8. **Advanced Spatiotemporal Model** (Planned)
   A future graph/spatiotemporal neural architecture modeling network-wide road degradation dynamics across connected urban road networks.

---

## Repository Structure

```text
Road-X/
├── ml/
│   ├── common/                  # Shared base classes, config, logging & exceptions
│   │   ├── __init__.py
│   │   ├── base.py              # BaseModel lifecycle abstraction (train, predict, save, load)
│   │   ├── config.py            # Dynamic path resolution and environment settings
│   │   ├── exceptions.py        # Custom RoadX exception hierarchy
│   │   └── logging_config.py    # Structured logging configuration
│   │
│   ├── failure_prediction/      # Failure prediction pipeline module
│   │   ├── __init__.py
│   │   ├── config.py            # Feature definitions and model parameters
│   │   ├── schemas.py           # Pydantic input/output validation schemas
│   │   ├── preprocessing.py     # Data cleaning and input validation
│   │   ├── features.py          # Distress index and feature extraction
│   │   ├── model.py             # RoadFailurePredictionModel implementation skeleton
│   │   ├── train.py             # Training pipeline entrypoint
│   │   ├── evaluate.py          # Metric computation and evaluation utilities
│   │   ├── predict.py           # Batch and real-time inference wrappers
│   │   └── tests/               # Failure prediction unit tests
│   │
│   ├── damage_detection/        # Adapter placeholder for existing CV detector
│   ├── severity/                # Damage severity estimation
│   ├── complaint_intelligence/  # NLP grievance classification
│   ├── duplicate_detection/     # Spatiotemporal duplicate clustering
│   ├── time_to_failure/         # Degradation timeline forecasting
│   └── priority_engine/         # Multi-criteria maintenance prioritization
│
├── data/                        # Data directories (tracked via .gitkeep)
│   ├── raw/
│   ├── processed/
│   └── external/
│
├── models/                      # Model checkpoints and serialization artifacts
├── tests/                       # Global unit and integration tests
├── .env.example                 # Environment configuration template
├── .gitignore                   # Version control ignore rules
├── requirements.txt             # Lightweight Phase 1 dependencies
└── README.md                    # Project documentation
```

---

## Getting Started (Phase 1)

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Environment Setup

Copy `.env.example` to `.env` if custom path or logging overrides are needed:

```bash
cp .env.example .env
```

### 3. Run Tests

Execute the unit tests to verify package integrity and configurations:

```bash
pytest
```
