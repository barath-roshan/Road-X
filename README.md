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

8. **Unified ML Pipeline** (`ml/pipeline/`)
   Orchestrates independent ML modules (Phases 2–8) into a unified inference workflow with partial execution support, failure isolation, stage profiling, and structured response outputs.

9. **Advanced Spatiotemporal Model** (Planned)
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

## Complaint Intelligence (Phase 5)

### 1. Problem Formulation
Citizen grievance reports are unstructured natural language text (e.g., *"There is a huge pothole near the railway station and bikes are falling at night"*).
The **Complaint Intelligence** module converts unstructured text into structured ML insights to assist government officers and downstream decision models:
* **Issue Category**: Controlled 12-class taxonomy (`POTHOLE`, `ROAD_CRACK`, `ROAD_SURFACE_DAMAGE`, `WATERLOGGING`, `FLOODING`, `STREETLIGHT`, `ACCIDENT`, `ROAD_OBSTRUCTION`, `DEBRIS`, `TRAFFIC_SIGNAL`, `ROAD_CLOSURE`, `OTHER`).
* **Urgency Level**: 4-class response priority tier (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
* **Safety Risk Level**: 3-class hazard severity tier (`LOW`, `MEDIUM`, `HIGH`).
* **Location Entity Mention Extraction**: Regex/rule-based extraction of location mentions (`ROAD`, `LANDMARK`, `AREA`, `LOCALITY`, `BUS_STOP`, `INTERSECTION`).
* **Semantic Embedding Generation**: Fixed-dimension ($300\text{-D}$) L2-normalized vector embedding for downstream **Phase 6 — Duplicate Complaint Detection**.

> **Human-in-the-Loop Safeguard:** Model output serves as assisted intelligence and does **not** make administrative government decisions.

### 2. Output Schema
```json
{
  "issue_category": "POTHOLE",
  "issue_confidence": 0.9123,
  "urgency": "HIGH",
  "urgency_confidence": 0.8411,
  "safety_risk": "HIGH",
  "safety_confidence": 0.8800,
  "location_mentions": [
    {
      "text": "railway station",
      "type": "LANDMARK",
      "start_idx": 31,
      "end_idx": 46
    }
  ],
  "embedding_available": true,
  "model_version": "v1"
}
```

### 3. Model Architecture & Baselines
* **Text Preprocessing**: `ComplaintPreprocessor` performs Unicode (NFKC) normalization, control character stripping, and whitespace normalization while preserving numbers, street names, punctuation, and key vocabulary.
* **Vectorization**: `ComplaintFeatureExtractor` uses `TfidfVectorizer` (unigrams & bigrams, sublinear TF scaling, max 1000 features).
* **Classifiers**: Three independent `LogisticRegression` classifiers with balanced class weights for Issue Category, Urgency Level, and Safety Risk Level, inheriting from `BaseModel`.
* **Embedding Interface**: `ComplaintEmbedder` exposes `embed(text)` returning a shape `(300,)` float32 numpy array.

### 4. Reproducible CLI Commands

```bash
# 1. Dataset Generation (Synthetic citizen complaint dataset)
python -m ml.complaint_intelligence.generate_synthetic_data

# 2. Model Training & Evaluation
python -m ml.complaint_intelligence.train

# 3. Inference Example via ComplaintAnalyzer
python -c "from ml.complaint_intelligence import ComplaintAnalyzer; a = ComplaintAnalyzer.load(); print(a.analyze('There is a large pothole near the railway station. It is dangerous for bikes at night.').model_dump_json(indent=2))"

# 4. Run Complete Automated Test Suite (111 tests)
pytest -v
```

### 5. Development Data & Transparency Notice
> [!WARNING]
> **DEVELOPMENT DATA DISCLAIMER:** Current NLP results are development results based on synthetic/manually annotated data (`SYNTHETIC / MANUALLY CREATED DEVELOPMENT DATA`) and must not be interpreted as production performance on real citizen complaints. Production deployment requires collecting and annotating real-world Indian citizen complaint data.

---

## Duplicate Complaint Detection (Phase 6)

### 1. Problem Formulation
Citizen complaints frequently address the same underlying road hazard (e.g., multiple citizens reporting the same dangerous pothole near a bus stop).
The **Duplicate Complaint Detection** module identifies and ranks existing historical complaints that likely represent the same real-world incident by fusing:
1. **Semantic Text Similarity**: Cosine similarity computed over Phase 5 $300\text{-D}$ `ComplaintEmbedder` vectors.
2. **Geographic Proximity**: Haversine surface distance in meters ($d_{\text{meters}}$) with exponential decay: $\text{geo\_score} = \exp(-d / d_0)$ where $d_0 = 500\text{m}$.
3. **Temporal Proximity**: Time separation in hours ($\Delta t_{\text{hours}}$) with exponential decay: $\text{time\_score} = \exp(-\Delta t / t_0)$ where $t_0 = 168\text{h}$ ($7\text{ days}$).
4. **Issue Category Alignment**: Category match indicator.

> [!IMPORTANT]
> **Government Human-in-the-Loop Governance:** The system flags duplicate candidates with detailed evidence for municipal officer review. **Automatic complaint merging, deletion, or status mutation is strictly prohibited.**

### 2. Output Schema
```json
{
  "grievance_id": "GRV-NEW-101",
  "duplicate_score": 0.9125,
  "is_duplicate_candidate": true,
  "possible_duplicate_grievance_ids": ["GRV-EXISTING-202"],
  "candidates": [
    {
      "grievance_id": "GRV-EXISTING-202",
      "duplicate_score": 0.9125,
      "is_candidate": true,
      "evidence": {
        "text_similarity": 0.9500,
        "distance_m": 45.20,
        "time_difference_hours": 3.50,
        "same_issue_category": true
      }
    }
  ],
  "model_version": "v1",
  "disclaimer": "AI identifies duplicate candidates for assisted government review. Automatic complaint merging is strictly prohibited."
}
```

### 3. Pipeline Architecture
* **`DuplicateCandidateRetriever`**: Modular candidate filtering component (in-memory candidate pool supporting future FAISS/Pinecone/Chroma integration without API changes). Excludes self-matches.
* **`SimilarityCalculator`**: Reuses Phase 5 `ComplaintEmbedder` to compute cosine similarity without rebuilding embedding models.
* **`GeographicTemporalFeatureBuilder`**: Calculates Haversine distance in meters and temporal difference in hours. Gracefully handles missing coordinates or timestamps without fabricating data.
* **`DuplicateScorer`**: Features dynamic weight normalization when spatial or temporal features are absent, and supports supervised `LogisticRegression` classification.
* **`DuplicateDetector`**: Pipeline orchestrator returning sorted candidate lists and evidence.

### 4. Reproducible CLI Commands

```bash
# 1. Dataset Generation (Synthetic duplicate complaint pairs)
python -m ml.duplicate_detection.generate_synthetic_data

# 2. Model Training & Baseline Evaluation
python -m ml.duplicate_detection.train

# 3. Pipeline Inference Example
python -c "from ml.duplicate_detection import DuplicateDetector, ComplaintRecord; det = DuplicateDetector.load(); c1 = ComplaintRecord(grievance_id='GRV-1', text='Huge pothole near bus stand', latitude=13.0827, longitude=80.2707); c2 = ComplaintRecord(grievance_id='GRV-2', text='Large pothole near bus stop causing delays', latitude=13.0828, longitude=80.2708); print(det.detect_duplicates(c1, [c2]).model_dump_json(indent=2))"

# 4. Run Complete Automated Test Suite (131 tests)
pytest -v
```

### 5. Transparency & Development Data Notice
> [!WARNING]
> **DEVELOPMENT DATA DISCLAIMER:** Current duplicate detection results are based on synthetic development pairs (`SYNTHETIC / MANUALLY CREATED DEVELOPMENT DATA`). Supervised weights and thresholds are baseline prototypes and require domain-validated citizen complaint pair annotations prior to production deployment.

---

## Time-to-Failure Prediction (Phase 7)

### 1. Problem Formulation
While Phase 2 answers *"Will this road segment significantly deteriorate/fail within the next 30 days?"* (binary classification), **Phase 7** estimates:
> *"Approximately how much operational time (in days) remains before the road segment reaches a defined structural failure condition?"*

This continuous survival prognosis complements binary failure prediction to optimize long-term municipal maintenance scheduling.

### 2. Output Schema
```json
{
  "segment_id": "SEG-0042",
  "observation_date": "2026-09-01",
  "estimated_time_to_failure_days": 87.4,
  "estimated_failure_date": "2026-11-27",
  "confidence_interval_days": {
    "lower_bound": 71.7,
    "upper_bound": 106.6
  },
  "survival_probabilities": {
    "day_30": 0.8845,
    "day_90": 0.4512,
    "day_180": 0.1235,
    "day_365": 0.0123
  },
  "risk_level": "HIGH",
  "model_version": "v1",
  "top_contributing_risk_factors": [
    "damage_indicator",
    "structural_vulnerability",
    "traffic_stress"
  ]
}
```

### 3. Survival Analysis & Model Architecture
* **Event Definition**: Pavement failure threshold (`road_quality_score <= 0.35` OR `pothole_count >= 10` OR `crack_ratio >= 0.25`).
* **Censoring Handling**: Right-censoring is explicitly modeled ($\delta_i = 1$ for observed failures, $\delta_i = 0$ for operational segments censored at study end date).
* **Empirical Baseline**: Non-parametric `KaplanMeierEstimator` empirical survival curve fitting.
* **Parametric Survival Regression**: `WeibullSurvivalModel` fitting Weibull Accelerated Failure Time (AFT) log-likelihood over censored and uncensored observations:
  $$S(t \mid \mathbf{X}) = \exp\left(-\left(\frac{t}{\lambda(\mathbf{X})}\right)^\gamma\right)$$
* **Temporal Leakage Safeguard**: Features are constructed strictly at observation time $T$. No future repairs, post-observation weather, or future complaints are incorporated.

### 4. Reproducible CLI Commands

```bash
# 1. Dataset Generation (Synthetic longitudinal survival telemetry)
python -m ml.time_to_failure.generate_synthetic_data

# 2. Model Training & Survival Evaluation
python -m ml.time_to_failure.train

# 3. Pipeline Inference Example
python -c "from ml.time_to_failure import TimeToFailurePredictor; from ml.failure_prediction.schemas import RoadFailureInput; pred = TimeToFailurePredictor.load(); print(pred.predict(RoadFailureInput(segment_id='SEG-101', observation_date='2026-09-01', road_age_years=8.5, road_length_m=500.0, lane_count=2, road_quality_score=0.45, traffic_volume=22000.0, heavy_vehicle_ratio=0.30, average_speed_kmph=40.0, rainfall_7d_mm=80.0, rainfall_30d_mm=250.0, temperature_avg_c=32.0, flood_events_30d=1, days_since_repair=700.0, previous_repairs=2, previous_failures=1, citizen_complaints_30d=6, pothole_count=5, crack_ratio=0.12)).model_dump_json(indent=2))"

# 4. Run Complete Automated Test Suite (142 tests)
pytest -v
```

### 5. Transparency & Development Data Notice
> [!WARNING]
> **DEVELOPMENT DATA DISCLAIMER:** Current time-to-failure predictions are trained on synthetic longitudinal survival data (`SYNTHETIC DEVELOPMENT DATA`). Real-world deployment requires collecting longitudinal pavement deterioration telemetry across municipal road networks.

---

## Maintenance Priority Engine (Phase 8)

### 1. Problem Formulation
The **Maintenance Priority Engine** synthesizes heterogeneous multi-signal predictions across all preceding ML modules (Phases 2–7) into a unified, actionable maintenance priority score (0.0 to 100.0) and administrative priority level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`):

> **Core Objective:** *"Which road maintenance case should government engineers prioritize first, and what evidence supports that priority recommendation?"*

```text
Phase 2: Road Failure Probability & Risk Level
Phase 4: Physical Damage Severity Score & Level
Phase 5: Complaint Intelligence Urgency, Safety Risk & Category
Phase 6: Duplicate Complaint Volume & Evidence
Phase 7: Time-to-Failure Horizon & Survival Probabilities
                        │
                        ▼
           Maintenance Priority Engine
                        │
                        ├── Dynamic Signal Weight Normalization
                        ├── Safety-First Guardrail Rule Enforcement
                        └── Grounded Evidence Explanation Generation
                        │
                        ▼
      Recommended Priority Level & Score + Evidence
                        │
                        ▼
          Government Administrative Officer Review
```

> [!IMPORTANT]
> **Government Human-in-the-Loop Governance:** The priority engine recommends maintenance priorities for officer review; **it does not make final administrative decisions or automatically dispatch work orders.**

### 2. Output Schema
```json
{
  "road_segment_id": "SEG-0042",
  "complaint_id": "COMP-0101",
  "priority_score": 88.5,
  "priority_level": "CRITICAL",
  "evidence": {
    "failure_probability": 0.85,
    "failure_risk_level": "HIGH",
    "severity_score": 82.0,
    "severity_level": "CRITICAL",
    "safety_risk": "HIGH",
    "urgency": "HIGH",
    "issue_category": "POTHOLE",
    "related_complaint_count": 4,
    "estimated_time_to_failure_days": 18.5,
    "survival_probability_30d": 0.3521,
    "traffic_volume": 25000.0
  },
  "reasons": [
    "High predicted road failure risk (85.0% failure probability within 30 days).",
    "Severe physical pavement damage detected (Severity Score: 82.0/100).",
    "High public safety hazard risk identified in citizen complaint report.",
    "Short remaining operational lifespan before structural failure (18.5 days remaining).",
    "Multiple duplicate citizen reports logged addressing this issue (4 related complaints).",
    "Safety Guardrail Triggered: Critical damage severity or structural failure risk enforces CRITICAL priority."
  ],
  "missing_evidence_notices": [],
  "requires_government_review": true,
  "model_version": "v1",
  "disclaimer": "AI recommends maintenance priority for assisted government review. Final work order dispatch requires government officer approval."
}
```

### 3. Engine Architecture & Safety-First Guardrails
* **`PriorityNormalizer`**: Scales multi-scale signals (probabilities, severity 0-100, remaining days, complaint counts) into a uniform 0.0 - 100.0 scale. Handles missing signals gracefully without assigning 0 risk.
* **`PriorityRuleEngine`**: Enforces Safety-First Guardrails to prevent severe hazards from being diluted by low traffic:
  - `IF safety_risk == HIGH` $\implies$ Min Score: 65.0, Min Level: `HIGH`
  - `IF urgency == CRITICAL` $\implies$ Min Score: 75.0, Min Level: `HIGH`
  - `IF severity_level == CRITICAL` OR `failure_risk_level == CRITICAL` $\implies$ Min Score: 80.0, Level: `CRITICAL`
  - `IF estimated_time_to_failure_days <= 14.0` $\implies$ Min Score: 70.0, Min Level: `HIGH`
* **`PriorityExplainer`**: Generates human-readable evidence bullet points strictly grounded in input data.

### 4. Reproducible CLI Commands

```bash
# 1. Dataset Generation (Synthetic maintenance priority scenarios)
python -m ml.priority_engine.generate_synthetic_data

# 2. Pipeline Initialization & Invariant Check
python -m ml.priority_engine.train

# 3. Pipeline Inference Example
python -c "from ml.priority_engine import MaintenancePriorityEngine, MaintenancePriorityInput; from ml.failure_prediction.schemas import FailurePredictionOutput, FailureRiskLevel; from ml.severity.schemas import SeverityPredictionOutput, DamageSeverityLevel; eng = MaintenancePriorityEngine(); print(eng.prioritize(MaintenancePriorityInput(road_segment_id='SEG-101', failure_prediction=FailurePredictionOutput(failure_probability=0.85, risk_level=FailureRiskLevel.HIGH, model_version='v1'), severity_prediction=SeverityPredictionOutput(severity_score=85.0, severity_level=DamageSeverityLevel.CRITICAL, model_version='v1'))).model_dump_json(indent=2))"

# 4. Run Complete Automated Test Suite (170 tests)
pytest -v
```

### 5. Transparency & Development Data Notice
> [!WARNING]
> **DEVELOPMENT DATA DISCLAIMER:** Current priority engine rules and weights are development baselines. Final priority thresholds require calibration against historical municipal government maintenance decisions.

---

## Unified ML Pipeline (Phase 9)

### 1. Objective & Design
The **Unified ML Pipeline** (`ml/pipeline/`) orchestrates all independent RoadX ML modules (Phases 2–8) into a cohesive inference workflow without merging models into a single monolithic architecture or model file. Each ML module remains independently testable and reusable.

```text
                  ┌─────────────────────┐
                  │    Pipeline Input   │
                  └──────────┬──────────┘
                             ↓
                  ┌─────────────────────┐
                  │ Input Validation    │
                  └──────────┬──────────┘
                             ↓
       ┌─────────────────────┼─────────────────────┐
       ↓                     ↓                     ↓
 Failure Prediction    Damage Detection    Complaint Intelligence
       ↓                     ↓                     ↓
       │                 Severity              Embeddings
       │                                         ↓
       │                                  Duplicate Detection
       ↓
 Time-to-Failure
       │
       └─────────────────────┬─────────────────────┘
                             ↓
                 Maintenance Priority
                             ↓
                    Unified ML Result
```

### 2. Core Capabilities
* **Dependency & Execution Graph**: Executes stages in logical dependency order (e.g. Damage Severity depends on Damage Detection; Duplicate Detection consumes Complaint Intelligence embeddings; Priority Engine synthesizes outputs across all stages).
* **Failure Isolation**: A failure or exception in an optional stage (e.g. corrupted image) is isolated to that stage (marked `FAILED`), allowing remaining independent stages to execute cleanly.
* **Partial Execution**: Supports complaint-only, road-only, image-only, or full multi-modal pipeline runs. Unsupplied inputs are cleanly `SKIPPED` without error or dummy data fabrication.
* **Operational Latency Profiling**: Tracks per-stage execution durations (`duration_ms`) and model versions in a structured summary table.
* **Model Instance Reuse**: Model artifacts are loaded once upon pipeline initialization and reused across requests.

### 3. Execution CLI Example

```bash
# Unified Pipeline Inference Example
python -c "from ml.pipeline import RoadXPipeline; pipe = RoadXPipeline(auto_load=True); res = pipe.run({'road_segment_id': 'SEG-101', 'complaint_text': 'Dangerous pothole near hospital.'}); print(res.model_dump_json(indent=2))"
```

---

## Repository Structure

```text
Road-X/
├── ml/
│   ├── common/                  # Shared base classes, config, logging & exceptions
│   ├── failure_prediction/      # Failure prediction pipeline module
│   ├── damage_detection/        # Adapter placeholder for existing CV detector
│   ├── severity/                # Damage severity estimation
│   ├── complaint_intelligence/  # NLP grievance classification & intelligence (Phase 5)
│   ├── duplicate_detection/     # Duplicate complaint detection & ranking (Phase 6)
│   ├── time_to_failure/         # Survival analysis & time-to-failure prediction (Phase 7)
│   ├── priority_engine/         # Multi-criteria maintenance priority engine (Phase 8)
│   ├── pipeline/                # Unified ML Pipeline orchestrator (Phase 9)
│   │   ├── __init__.py
│   │   ├── config.py            # Signal weights, thresholds, and guardrail rules
│   │   ├── schemas.py           # Pydantic priority input, evidence, and output schemas
│   │   ├── normalizer.py        # Signal extractor and 0-100 normalizer
│   │   ├── rules.py             # Safety-First guardrail rule engine
│   │   ├── scorer.py            # Dynamic composite priority scorer
│   │   ├── explainer.py         # Human-readable evidence reasoning generator
│   │   ├── engine.py            # MaintenancePriorityEngine pipeline orchestrator
│   │   ├── train.py             # Pipeline metadata initialization & verification
│   │   ├── evaluate.py          # System invariants & rule compliance helper
│   │   └── tests/               # 11 unit tests covering priority scoring
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

## FastAPI ML Service (Phase 10)

### 1. Architecture

Phase 10 exposes the RoadX Unified ML Pipeline through a production-grade **FastAPI ML Inference Service**. FastAPI functions strictly as the HTTP API and service boundary layer, delegating all domain logic to the unified pipeline.

```text
                 RoadX Application
                        │
                        │ HTTP
                        ↓
              ┌───────────────────┐
              │   FastAPI Service │
              │                   │
              │ /health           │
              │ /ready            │
              │ /api/v1/ml/...    │
              └─────────┬─────────┘
                        ↓
              MLInferenceService
                        ↓
              Unified ML Pipeline
                        ↓
       ┌────────────────┼────────────────┐
       ↓                ↓                ↓
 Failure Prediction  Damage Analysis  Complaint Analysis
       ↓                ↓                ↓
 Time-to-Failure     Severity         Duplicate Detection
       │                │                │
       └────────────────┼────────────────┘
                        ↓
             Maintenance Priority
                        ↓
                 API Response
```

### 2. Service Endpoints

* **`GET /health`**: Returns HTTP 200 OK with basic service health metadata (`status: healthy`, `service: roadx-ml-service`, `version: 1.0.0`).
* **`GET /ready`**: Probes ML component load status. Returns HTTP 200 OK when the pipeline is initialized, or HTTP 503 Service Unavailable when model loading fails.
* **`POST /api/v1/ml/analyze`**: Main unified ML pipeline inference endpoint. Accepts JSON requests matching `MLAnalyzeRequest` (road tabular data, citizen complaint text, image path, duplicate records) and returns `MLAnalyzeResponse`.
* **`POST /api/v1/ml/damage/analyze`**: Visual damage detection endpoint (`multipart/form-data`). Accepts uploaded road surface images (JPEG, PNG, WebP up to 10MB) and optional road context JSON.

### 3. Key Design Features

* **Single Model Initialization**: ML predictors and YOLO/XGBoost model artifacts are loaded once during FastAPI application startup lifespan context and reused across requests.
* **Structured Error Handling**: All HTTP exceptions, validation errors (HTTP 422), service unreadiness (HTTP 503), and runtime pipeline errors (HTTP 500) return a consistent `APIErrorResponse` schema without exposing internal tracebacks, machine paths, or secrets.
* **Request ID Traceability**: Middleware generates or propagates an `X-Request-ID` header (e.g. `req-a1b2c3d4e5f6`) on every request, linking HTTP logs, execution timings, and error payloads.
* **Clean Decoupling**: Routes do not execute model logic directly. Instead, they interact with `MLInferenceService` injected via FastAPI dependency injection (`get_ml_service`).

### 4. Running the Service Locally

Start the FastAPI ML server using Uvicorn:

```bash
# Start development server with auto-reload
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Access Interactive API Documentation:
* **Swagger UI Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **OpenAPI Schema**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

### 5. API Testing

Run API-specific unit and integration tests:

```bash
# Run API test suite
pytest api/tests

# Run complete workspace test suite (Phases 1-11)
pytest
```

---

## Backend & Database Subsystem (Phase 11)

### 1. Layered Architecture

Phase 11 introduces a clean, multi-tier backend persistence layer supporting PostgreSQL (production) and SQLite (local development/testing).

```text
FastAPI Routes (api/routes/grievance.py)
       │
       ▼
Services (backend/services/)
       │
       ▼
Repositories (backend/repositories/)
       │
       ▼
SQLAlchemy 2.x Models (backend/models/)
       │
       ▼
Alembic Migrations / Database (PostgreSQL / SQLite)
```

```text
ML Pipeline (ml/pipeline/)
     │
     ▼
Unified ML Result (UnifiedPipelineResult)
     │
     ▼
MLAnalysisService (backend/services/ml_analysis_service.py)
     │
     ▼
Database (ml_analysis_results table)
```

### 2. Database Entities & Relationships

* **`User`** (`users` table): Platform actors supporting roles `CITIZEN`, `GOVERNMENT_OFFICER`, `CONTRACTOR`.
* **`RoadSegment`** (`road_segments` table): Physical municipal road segments identified by `segment_id` (e.g. `SEG-MH-4001`) used by ML failure prediction models.
* **`Grievance`** (`grievances` table): Central grievance/report entity tracking lifecycle status (`SUBMITTED`, `UNDER_REVIEW`, `IN_PROGRESS`, `PENDING_VERIFICATION`, `RESOLVED`, `REJECTED`).
* **`Evidence`** (`evidences` table): Visual grievance evidence file metadata (`file_name`, `file_type`, `storage_path`, `file_size_bytes`).
* **`MLAnalysisResult`** (`ml_analysis_results` table): Persistent store for Phase 9/10 Unified ML Pipeline prediction outputs (JSONB/JSON structures for failure prediction, damage detection, severity, complaint intelligence, duplicate detection, time-to-failure, and priority scores).

### 3. Backend Endpoints

* `POST /api/v1/grievances`: Create and persist a citizen grievance report.
* `GET /api/v1/grievances/{id}`: Retrieve a stored grievance by ID.
* `GET /api/v1/grievances`: Query grievances with optional status, category, road, or citizen filtering.
* `PATCH /api/v1/grievances/{id}`: Update grievance status or details.
* `POST /api/v1/grievances/{id}/analysis`: Explicitly invoke Phase 9/10 ML pipeline for a grievance and persist structured predictions in the database.
* `GET /api/v1/grievances/{id}/analysis`: Retrieve historical stored ML analysis outputs for a grievance.
* `POST /api/v1/users`, `GET /api/v1/users/{id}`: Create and manage platform user records.
* `POST /api/v1/roads`, `GET /api/v1/roads/{id}`: Create and manage physical road segment metadata.

### 4. Database Migrations (Alembic)

Run Alembic schema migrations:

```bash
# Apply migrations to database head
alembic upgrade head

# Generate a new migration script after model changes
alembic revision --autogenerate -m "Descriptive migration name"
```

### 5. Running Backend & ML Tests

Execute the complete test suite across all Phase 1–11 components:

```bash
# Run backend specific unit & integration tests
pytest backend/tests

# Run complete workspace test suite (211 tests)
pytest
```

---

## Phase 12 — Government Officer Workflow

### 1. Architectural Overview & Conceptual Workflow

Phase 12 establishes the administrative **Government Officer workflow** for reviewing citizen road grievances, converting accepted grievances into maintenance work orders, assigning contractors, and enforcing strict government verification before a grievance can be resolved.

```text
Citizen submits grievance
        │
        ▼
    SUBMITTED
        │
Government Officer reviews
        │
  UNDER_REVIEW
   /        \
Reject    Accept
  /            \
REJECTED      Create work order
                    │
                ASSIGNED / OPEN
                    │
            Contractor repair work (Phase 13)
                    │
           PENDING_VERIFICATION
             /              \
     Government Verifies
         /              \
      APPROVE         REJECT
        │                │
    RESOLVED        IN_PROGRESS
```

### 2. Strict Business Rules & Controls

1. **Strict Resolution Rule:** A grievance **NEVER** transitions to `RESOLVED` merely because a contractor completed work. A contractor completion submission transitions the status to `PENDING_VERIFICATION`. Only a Government Officer `APPROVE` verification decision transitions a grievance to `RESOLVED`.
2. **Role Boundaries & Authorization:** Administrative operations (review, work order creation/assignment, completion verification) are restricted strictly to `GOVERNMENT_OFFICER` actors. Requests by `CITIZEN` or `CONTRACTOR` actors yield `403 Forbidden` (`UnauthorizedError`).
3. **Explicit State Machine Transitions:** State transitions for `Grievance` and `WorkOrder` entities are strictly validated via `GrievanceStateMachine` and `WorkOrderStateMachine`. Arbitrary or invalid transitions (e.g. `SUBMITTED → RESOLVED`) trigger `InvalidStateTransitionError` (HTTP 400).
4. **Atomic Transactions:** All combined workflow state mutations (e.g., Accepting grievance + creating work order + updating grievance status + writing audit history) execute inside single atomic database transactions.

### 3. Database Entities & Schemas

* **`GovernmentReview`** (`government_reviews` table): Persistent record of an officer's evaluation decision (`ACCEPT` or `REJECT`), rejection reasons, officer notes, and timestamps.
* **`WorkOrder`** (`work_orders` table): Maintenance work order entity tracking title, description, priority (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), contractor assignment, and status (`OPEN`, `ASSIGNED`, `IN_PROGRESS`, `PENDING_VERIFICATION`, `COMPLETED`, `CANCELLED`).
* **`GovernmentVerification`** (`government_verifications` table): Record of final government completion audits (`APPROVE` or `REJECT`), officer notes, and timestamps.
* **`WorkflowEvent`** (`workflow_events` table): Immutable chronological audit log recording actor ID, event type (`GRIEVANCE_SUBMITTED`, `GRIEVANCE_ACCEPTED`, `GRIEVANCE_REJECTED`, `WORK_ORDER_CREATED`, `WORK_ORDER_ASSIGNED`, `WORK_VERIFICATION_SUBMITTED`, `WORK_VERIFICATION_APPROVED`, `WORK_VERIFICATION_REJECTED`), old/new state, and notes.

### 4. Government API Endpoints

* `GET /api/v1/government/grievances`: List citizen grievances with status, issue category, road, and pagination filters.
* `GET /api/v1/government/grievances/{id}`: Retrieve grievance details, evidence metadata, and stored ML decision support analysis.
* `POST /api/v1/government/grievances/{id}/review`: Submit government review decision (`ACCEPT` or `REJECT`).
* `POST /api/v1/government/grievances/{id}/work-orders`: Create a work order and assign a contractor for an accepted grievance.
* `GET /api/v1/government/work-orders`: List maintenance work orders with optional status, priority, and contractor filters.
* `GET /api/v1/government/work-orders/{id}`: Retrieve specific work order details.
* `POST /api/v1/government/work-orders/{id}/verify`: Verify contractor completion (`APPROVE` → transitions grievance to `RESOLVED` and work order to `COMPLETED`; `REJECT` → reverts both to `IN_PROGRESS`).
* `GET /api/v1/government/grievances/{id}/history`: Fetch complete chronological audit trail of workflow events for a grievance.

### 5. Running Phase 12 Tests

Execute the test suite (211 total passing tests across all modules):

```bash
# Run government workflow service & state machine tests
pytest backend/tests/test_government_workflow.py backend/tests/test_state_machine.py backend/tests/test_authorization.py

# Run government API integration tests
pytest api/tests/test_government_api.py

# Run complete workspace test suite (218 tests)
pytest
```

---

## Phase 13 — Contractor Workflow

### 1. Architectural Overview & Conceptual Workflow

Phase 13 implements the **Contractor Workflow** for executing government-approved maintenance work orders. Contractors can view assigned work orders, acknowledge tasks, start repairs, submit progress percentage updates, attach completion evidence metadata, and submit completed work for government verification.

```text
Government assigns work order
        │
        ▼
     ASSIGNED
        │
Contractor acknowledges & starts work
        │
    IN_PROGRESS ◄────────────────────────┐
   /           \                         │ (Government Rejection)
Progress    Upload Evidence              │
   \           /                         │
Contractor Submits Completion            │
        │                                │
  PENDING_VERIFICATION                   │
        │                                │
Government Verification (Phase 12) ──────┘
   /         \
APPROVE    REJECT
  /           \
RESOLVED     IN_PROGRESS
```

### 2. Strict Business Rules & Security

1. **Contractor Completion Cannot Resolve Grievance:** Submitting work order completion transitions the `WorkOrder` and `Grievance` to `PENDING_VERIFICATION`. Only Phase 12 Government Verification can transition a grievance to `RESOLVED` and work order to `COMPLETED`.
2. **Work Order Ownership Scoping:** Contractor A cannot access, view, or modify work orders assigned to Contractor B (`work_order.assigned_contractor_id == current_actor.user_id`). Access attempts to unassigned work orders yield `403 Forbidden` (`UnauthorizedError`).
3. **Role Enforcement:** All contractor endpoints strictly enforce `UserRole.CONTRACTOR` actor context.
4. **Progress Percentage Validation:** Progress updates are strictly validated ($0 \le \text{progress\_percentage} \le 100$). Progress updates—even at 100%—never automatically mark a work order or grievance as completed or resolved.
5. **Rejection & Rework Loop:** When a government officer rejects completion verification (`REJECT`), the work order and grievance revert to `IN_PROGRESS`. The contractor can view the officer's rejection feedback, perform required rework, attach updated evidence, and re-submit for verification.

### 3. Database Entities & Schemas

* **`WorkProgress`** (`work_progresses` table): Logs contractor progress percentage updates (0-100%), progress notes, and timestamps.
* **`Evidence`** (`evidences` table): Extended with `work_order_id` foreign key for attaching completion photos and proof metadata to work orders.
* **`WorkflowEvent`** (`workflow_events` table): Extended with contractor audit event types (`WORK_ORDER_ACKNOWLEDGED`, `WORK_STARTED`, `WORK_PROGRESS_UPDATED`, `WORK_COMPLETION_SUBMITTED`).

### 4. Contractor API Endpoints

* `GET /api/v1/contractor/work-orders`: List work orders assigned to the authenticated contractor.
* `GET /api/v1/contractor/work-orders/{id}`: Retrieve detailed work order view including grievance description, road location, instructions, progress history, evidence list, and latest government rejection feedback.
* `POST /api/v1/contractor/work-orders/{id}/accept`: Acknowledge assignment receipt.
* `POST /api/v1/contractor/work-orders/{id}/start`: Start work (`ASSIGNED → IN_PROGRESS`).
* `POST /api/v1/contractor/work-orders/{id}/progress`: Log progress percentage update (0-100%).
* `POST /api/v1/contractor/work-orders/{id}/evidence`: Attach completion evidence photo/document metadata.
* `POST /api/v1/contractor/work-orders/{id}/submit`: Submit completed repair work for government verification (`IN_PROGRESS → PENDING_VERIFICATION`).

### 5. Running Phase 13 Tests

Execute the workspace test suite (218 total passing tests across all modules):

```bash
# Run contractor workflow service & unit tests
pytest backend/tests/test_contractor_workflow.py

# Run contractor API integration tests
pytest api/tests/test_contractor_api.py

# Run full project test suite (218 tests)
pytest
```

#barath-roshan


