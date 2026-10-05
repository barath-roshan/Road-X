"""Unit tests for TimeToFailurePredictor pipeline and artifact serialization."""

from ml.common.config import settings
from ml.failure_prediction.schemas import RoadFailureInput
from ml.time_to_failure.predictor import TimeToFailurePredictor
from ml.time_to_failure.schemas import TimeToFailureOutput, TimeToFailureRiskLevel


def test_predictor_end_to_end_inference():
    model_dir = settings.models_dir / "time_to_failure"
    predictor = TimeToFailurePredictor.load(model_dir)

    inp = RoadFailureInput(
        segment_id="SEG-TEST-101",
        observation_date="2026-09-01",
        road_age_years=8.5,
        road_length_m=450.0,
        lane_count=2,
        road_quality_score=0.45,
        traffic_volume=22000.0,
        heavy_vehicle_ratio=0.30,
        average_speed_kmph=40.0,
        rainfall_7d_mm=80.0,
        rainfall_30d_mm=250.0,
        temperature_avg_c=32.0,
        flood_events_30d=1,
        days_since_repair=700.0,
        previous_repairs=2,
        previous_failures=1,
        citizen_complaints_30d=6,
        pothole_count=5,
        crack_ratio=0.12,
    )

    output = predictor.predict(inp)

    assert isinstance(output, TimeToFailureOutput)
    assert output.segment_id == "SEG-TEST-101"
    assert output.estimated_time_to_failure_days >= 0.0
    assert output.estimated_failure_date is not None
    assert isinstance(output.risk_level, TimeToFailureRiskLevel)

    # Validate 95% Confidence Interval bounds
    assert output.confidence_interval_days.lower_bound <= output.estimated_time_to_failure_days
    assert output.confidence_interval_days.upper_bound >= output.estimated_time_to_failure_days

    # Validate survival probabilities monotonic order: P(S(30)) >= P(S(90)) >= P(S(180)) >= P(S(365))
    sp = output.survival_probabilities
    assert 0.0 <= sp.day_365 <= sp.day_180 <= sp.day_90 <= sp.day_30 <= 1.0


def test_predictor_save_and_load(tmp_path):
    model_dir = settings.models_dir / "time_to_failure"
    orig_predictor = TimeToFailurePredictor.load(model_dir)

    save_dir = tmp_path / "ttf_model"
    orig_predictor.save(save_dir)

    reloaded = TimeToFailurePredictor.load(save_dir)
    assert reloaded.is_fitted

    inp = RoadFailureInput(segment_id="SEG-99", road_age_years=4.0, road_length_m=300.0, lane_count=2, road_quality_score=0.8, traffic_volume=5000.0, heavy_vehicle_ratio=0.1, average_speed_kmph=50.0, rainfall_7d_mm=10.0, rainfall_30d_mm=40.0, temperature_avg_c=28.0, flood_events_30d=0, days_since_repair=100.0, previous_repairs=0, previous_failures=0, citizen_complaints_30d=0, pothole_count=0, crack_ratio=0.01)

    out1 = orig_predictor.predict(inp)
    out2 = reloaded.predict(inp)

    assert out1.estimated_time_to_failure_days == out2.estimated_time_to_failure_days
    assert out1.risk_level == out2.risk_level
