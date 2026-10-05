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

## Road Failure Prediction (Phase 2)

### 1. Problem Formulation
Given the current structural and environmental condition of a road segment at observation time $t$, predict the probability that the segment will experience critical structural deterioration or failure within a 30-day forward horizon:
$$\hat{y} = P(\text{failure in } (t, t + 30\text{ days}] \mid \mathcal{F}_t)$$
This enables municipal engineers to schedule preventative maintenance before high-speed hazards, acute potholing, or pavement collapse endanger citizens.

### 2. Input Features
The pipeline processes 17 base road segment attributes and derives 6 civil engineering indicators:

* **Raw Road & Traffic Attributes**: `road_age_years`, `road_length_m`, `lane_count`, `road_quality_score` (0.0=poor, 1.0=pristine), `traffic_volume`, `heavy_vehicle_ratio`, `average_speed_kmph`, `rainfall_7d_mm`, `rainfall_30d_mm`, `temperature_avg_c`, `flood_events_30d`, `days_since_repair`, `previous_repairs`, `previous_failures`, `citizen_complaints_30d`, `pothole_count`, `crack_ratio`.
* **Engineered Civil Engineering Features**:
  * `traffic_stress = traffic_volume * heavy_vehicle_ratio` (Represents heavy axle repetitions causing pavement sub-grade fatigue).
  * `repair_aging = days_since_repair / (365.25 * (previous_repairs + 1))` (Normalized time elapsed since latest repair cadence).
  * `damage_indicator = (pothole_count * 0.70) + (crack_ratio * 100.0 * 0.30)` (Composite surface distress metric).
  * `weather_stress = rainfall_30d_mm * (1.0 + flood_events_30d * 0.50) + rainfall_7d_mm * 1.50` (Pavement saturation and dynamic water pounding).
  * `structural_vulnerability = road_age_years * (1.0 - road_quality_score)` (Compound age and surface degradation wear).
  * `complaint_pressure = citizen_complaints_30d / ((traffic_volume / 1000.0) + 1.0)` (Citizen grievance density per traffic exposure).

### 3. Prediction Target (`failure_next_30d`)
A binary indicator ($y \in \{0, 1\}$) signifying whether the road segment required emergency intervention or experienced critical failure in the 30 days strictly following the observation date.

### 4. Validation & Temporal Leakage Prevention
* **Temporal Split**: Records are ordered chronologically. Observations up to October 17, 2025 form the training partition (80%), while observations from October 17 to December 17, 2025 form the unseen forward test partition (20%).
* **Leakage Safeguards**: No future complaints, subsequent repairs, post-observation weather events, or future damages are accessible to the model at observation time $t$. Preprocessing medians are fitted exclusively on the training split.

### 5. Progressive Models & Benchmark Results (Temporal Test Set)

| Model | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Brier Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression (Baseline)** | 0.7536 | **0.8277** | **0.7889** | **0.9130** | **0.8648** | **0.1169** |
| **Random Forest (Tree Baseline)** | 0.7455 | 0.8255 | 0.7834 | 0.9083 | 0.8558 | 0.1184 |
| **XGBoost (Calibrated, Primary)** | **0.7948** | 0.7539 | 0.7738 | 0.9069 | 0.8632 | 0.1185 |

*Selected Model:* Calibrated **XGBoost** provides the highest precision (0.7948) with strong PR-AUC (0.8632) and well-calibrated probabilities for administrative risk triage.

### 6. Probability Calibration & Risk Tiers
Predicted failure probabilities are mapped into configurable municipal action tiers:
* **LOW**: $p < 0.30$ (Routine monitoring)
* **MEDIUM**: $0.30 \le p < 0.60$ (Scheduled inspection)
* **HIGH**: $0.60 \le p < 0.80$ (Priority work order consideration)
* **CRITICAL**: $p \ge 0.80$ (Immediate engineering inspection and repair dispatch)

### 7. Reproducible CLI Commands

```bash
# 1. Dataset Generation (Synthetic development dataset)
python -m ml.failure_prediction.generate_synthetic_data

# 2. Exploratory Data Analysis & Diagnostic Plots
python -m ml.failure_prediction.eda

# 3. Model Training, Calibration & Artifact Serialization
python -m ml.failure_prediction.train

# 4. Inference on Single Road Segment
python -c "from ml.failure_prediction import RoadFailurePredictor; p = RoadFailurePredictor(); print(p.predict({'road_age_years': 9.2, 'road_length_m': 250, 'lane_count': 2, 'road_quality_score': 0.45, 'traffic_volume': 28000, 'heavy_vehicle_ratio': 0.32, 'average_speed_kmph': 42, 'rainfall_7d_mm': 120, 'rainfall_30d_mm': 380, 'temperature_avg_c': 32, 'flood_events_30d': 2, 'days_since_repair': 850, 'previous_repairs': 3, 'previous_failures': 2, 'citizen_complaints_30d': 8, 'pothole_count': 7, 'crack_ratio': 0.14}))"

# 5. Run Complete Automated Test Suite (53 tests)
pytest -v
```

### 8. Limitations & Transparency Notice
> [!WARNING]
> **SYNTHETIC — FOR DEVELOPMENT ONLY:** The current model is a development prototype trained on synthetic data representing structural civil engineering relationships. Its metrics must not be interpreted as real-world road-failure performance. Real municipal telemetry and sensor data will be ingested in production deployments.

---

## Road Damage Detection (Phase 3 Integration)

### 1. Existing Model Architecture
RoadX integrates a pre-trained computer vision model for detecting and segmenting road defects:
* **Model Checkpoint**: [`models/pathole_detection.pt`](file:///d:/Third%20year%20Projects/Road-X/models/pathole_detection.pt) (~179.6 MB)
* **Framework**: Ultralytics YOLO Segmentation Model (`ultralytics.nn.tasks.SegmentationModel`)
* **Task Type**: Object Detection & Instance Segmentation (`segment`)
* **Detected Classes**: `{0: 'Pothole'}` (Canonical mapping: `pothole`)

> **Preservation Guarantee**: RoadX does **not** retrain, rebuild, or alter the weights of this pre-existing model. It is integrated cleanly as a component of the RoadX ecosystem.

### 2. Integration & Adapter Design
To decouple RoadX from specific computer vision frameworks, inference is wrapped behind an abstract interface and dedicated adapter:

```text
Citizen Image / Image Path
            ↓
  RoadDamageDetector (ml/damage_detection/detector.py)
            ↓
ExistingPotholeModelAdapter (ml/damage_detection/adapter.py)
            ↓
Existing Trained Model (models/pathole_detection.pt)
            ↓
  RoadDamageDetectionResponse (ml/damage_detection/schemas.py)
```

### 3. Normalized Output Schema
Regardless of underlying framework variations, downstream modules (such as Phase 4 Damage Severity Estimation) consume a unified JSON output structure:

```json
{
  "detections": [
    {
      "class_name": "pothole",
      "confidence": 0.9142,
      "bbox": [120.0, 80.0, 420.0, 350.0],
      "area_ratio": 0.1771,
      "segmentation_polygon": [[120.0, 80.0], [420.0, 80.0], [420.0, 350.0], [120.0, 350.0]]
    }
  ],
  "image_width": 640,
  "image_height": 480,
  "detection_count": 1,
  "model_version": "v1"
}
```

### 4. Reproducible Inference Snippet

```python
from ml.damage_detection import ExistingPotholeModelAdapter

# 1. Initialize adapter (loads model checkpoint once into memory)
detector = ExistingPotholeModelAdapter()

# 2. Run detection on an image (Path, PIL Image, or BGR numpy array)
response = detector.detect("data/raw/sample_road_test.jpg", confidence_threshold=0.25)

# 3. Access normalized detections
print(f"Detected {response.detection_count} defects.")
for item in response.detections:
    print(f"Class: {item.class_name}, Confidence: {item.confidence}, BBox: {item.bbox}, Area Ratio: {item.area_ratio}")
```

---

## Damage Severity Estimation (Phase 4)

### 1. What This Module Does
Estimates the physical severity of detected road defects ($0.0 - 100.0$ continuous severity score and categorical level: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) using normalized vision detection outputs from Phase 3 and optional road infrastructure context.

### 2. Inputs & Feature Extraction
* **Phase 3 Vision Inputs**: `RoadDamageDetectionResponse` containing `detection_count`, `total_area_ratio`, `max_area_ratio`, `avg_area_ratio`, `max_confidence`, `avg_confidence`, `total_bbox_area`, `max_bbox_area`.
* **Road Infrastructure Context** (Optional): `RoadContextInput` containing `road_quality_score`, `traffic_volume`, `heavy_vehicle_ratio`, `road_age_years`, `citizen_complaints_30d`.
* **Engineered Feature Interactions**: `traffic_damage_interaction`, `quality_defect_ratio`, `complaint_defect_interaction`.

### 3. Model Architecture & Benchmark Evaluation
Evaluated via an 80/20 train/test split over 3,000 synthetic observations:

| Model | MAE | RMSE | $R^2$ Score | Level Precision | Level Recall | Level F1-Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ridge Regression (Baseline)** | **2.9183** | **3.7347** | **0.9647** | **0.8890** | **0.8660** | **0.8765** |
| **Random Forest Regressor** | 3.4494 | 4.4585 | 0.9497 | 0.8397 | 0.7944 | 0.8116 |
| **XGBoost Regressor (Primary)** | 2.9796 | 3.8558 | 0.9624 | 0.8672 | 0.8545 | 0.8577 |

*Selected Model:* **Ridge Regression / XGBoost Regressor** ($R^2 = 0.9647$, MAE = 2.9183) providing high accuracy and clear linear interpretability.

### 4. Presentation Categories & Configurable Thresholds
Continuous severity scores ($0.0 - 100.0$) are mapped into configurable presentation levels:
* **LOW**: $0.0 \le \text{score} < 30.0$
* **MEDIUM**: $30.0 \le \text{score} < 60.0$
* **HIGH**: $60.0 \le \text{score} < 80.0$
* **CRITICAL**: $\text{score} \ge 80.0$

### 5. Reproducible CLI Commands

```bash
# 1. Dataset Generation (Synthetic damage severity dataset)
python -m ml.severity.generate_synthetic_data

# 2. Model Training, Calibration & Artifact Serialization
python -m ml.severity.train

# 3. End-to-End Detector -> Severity Inference Test
python -c "from ml.damage_detection import ExistingPotholeModelAdapter; from ml.severity import DamageSeverityPredictor, RoadContextInput; det = ExistingPotholeModelAdapter(); res = det.detect('data/raw/sample_road_test.jpg'); sev = DamageSeverityPredictor(); out = sev.predict(res, RoadContextInput(road_quality_score=0.45, traffic_volume=25000, heavy_vehicle_ratio=0.30, road_age_years=9.0, citizen_complaints_30d=7)); print(out.model_dump_json(indent=2))"

# 4. Run Complete Automated Test Suite (92 tests)
pytest -v
```

### 6. Limitations & Transparency Notice
> [!WARNING]
> **SYNTHETIC — DEVELOPMENT ONLY:** The current severity model is a development prototype trained on synthetic data simulating physical pavement degradation formulas. Real-world deployment requires a properly annotated, domain-validated road-damage severity dataset.

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
