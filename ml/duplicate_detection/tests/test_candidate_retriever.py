"""Unit tests for DuplicateCandidateRetriever and self-match exclusion."""

from ml.duplicate_detection.candidate_retriever import DuplicateCandidateRetriever
from ml.duplicate_detection.schemas import ComplaintRecord


def test_self_match_exclusion():
    c1 = ComplaintRecord(grievance_id="GRV-101", text="Pothole near Anna Salai")
    c2 = ComplaintRecord(grievance_id="GRV-102", text="Waterlogging near Airport road")

    retriever = DuplicateCandidateRetriever(historical_records=[c1, c2])

    # Target is c1: retriever must exclude c1 and return only c2
    candidates = retriever.retrieve_candidates(target_complaint=c1)
    assert len(candidates) == 1
    assert candidates[0].grievance_id == "GRV-102"


def test_candidate_retriever_empty_pool():
    c1 = ComplaintRecord(grievance_id="GRV-101", text="Pothole near Anna Salai")
    retriever = DuplicateCandidateRetriever()
    candidates = retriever.retrieve_candidates(target_complaint=c1)
    assert candidates == []
