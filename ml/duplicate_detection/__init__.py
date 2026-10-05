"""Duplicate Grievance Detection module for RoadX (Phase 6).

Detects and ranks candidate duplicate citizen complaints regarding identical road hazards
using semantic similarity (Phase 5 embeddings), spatial proximity (Haversine meters), and temporal proximity.
"""

from ml.duplicate_detection.detector import DuplicateDetector
from ml.duplicate_detection.candidate_retriever import DuplicateCandidateRetriever
from ml.duplicate_detection.similarity import SimilarityCalculator
from ml.duplicate_detection.features import GeographicTemporalFeatureBuilder
from ml.duplicate_detection.scorer import DuplicateScorer
from ml.duplicate_detection.schemas import (
    ComplaintRecord,
    DuplicateEvidence,
    DuplicateCandidate,
    DuplicateDetectionRequest,
    DuplicateDetectionResponse,
)

__all__ = [
    "DuplicateDetector",
    "DuplicateCandidateRetriever",
    "SimilarityCalculator",
    "GeographicTemporalFeatureBuilder",
    "DuplicateScorer",
    "ComplaintRecord",
    "DuplicateEvidence",
    "DuplicateCandidate",
    "DuplicateDetectionRequest",
    "DuplicateDetectionResponse",
]
