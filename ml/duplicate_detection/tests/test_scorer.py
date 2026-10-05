"""Unit tests for DuplicateScorer heuristic and supervised scoring."""

import pytest
from ml.duplicate_detection.scorer import DuplicateScorer
from ml.duplicate_detection.schemas import DuplicateEvidence


def test_heuristic_score_computation():
    scorer = DuplicateScorer()

    # High text similarity + close geographic + close temporal
    evidence_high = DuplicateEvidence(
        text_similarity=0.90,
        distance_m=10.0,
        time_difference_hours=2.0,
        same_issue_category=True,
    )
    score_high = scorer.compute_heuristic_score(evidence_high)
    assert score_high > 0.80

    # High text similarity but missing geographic and temporal data
    evidence_text_only = DuplicateEvidence(
        text_similarity=0.90,
        distance_m=None,
        time_difference_hours=None,
        same_issue_category=None,
    )
    score_text = scorer.compute_heuristic_score(evidence_text_only)
    assert round(score_text, 2) == 0.90


def test_scorer_candidate_threshold():
    scorer = DuplicateScorer(threshold=0.65)
    evidence_low = DuplicateEvidence(
        text_similarity=0.20,
        distance_m=5000.0,
        time_difference_hours=200.0,
        same_issue_category=False,
    )
    cand = scorer.score_candidate("GRV-999", evidence_low)
    assert cand.is_candidate is False
    assert cand.duplicate_score < 0.65


def test_scorer_save_and_load(tmp_path):
    scorer = DuplicateScorer(threshold=0.75)
    save_path = tmp_path / "model.joblib"

    scorer.save(save_path)
    loaded = DuplicateScorer.load(save_path)

    assert loaded.threshold == 0.75
    assert loaded.model_name == "DuplicateScorer"
