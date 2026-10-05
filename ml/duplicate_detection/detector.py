"""DuplicateDetector orchestrator pipeline for RoadX Duplicate Complaint Detection (Phase 6)."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from ml.duplicate_detection.config import config
from ml.duplicate_detection.schemas import (
    ComplaintRecord,
    DuplicateCandidate,
    DuplicateDetectionRequest,
    DuplicateDetectionResponse,
)
from ml.duplicate_detection.similarity import SimilarityCalculator
from ml.duplicate_detection.features import GeographicTemporalFeatureBuilder
from ml.duplicate_detection.candidate_retriever import DuplicateCandidateRetriever
from ml.duplicate_detection.scorer import DuplicateScorer
from ml.complaint_intelligence.embedder import ComplaintEmbedder


class DuplicateDetector:
    """Orchestrates candidate retrieval, semantic similarity calculation, spatial/temporal proximity analysis,

    and candidate scoring for duplicate complaint detection.

    Note: This module provides decision-support evidence for municipal officers and
    STRICTLY PROHIBITS automatic complaint merging or status mutation.
    """

    def __init__(
        self,
        similarity_calculator: Optional[SimilarityCalculator] = None,
        feature_builder: Optional[GeographicTemporalFeatureBuilder] = None,
        candidate_retriever: Optional[DuplicateCandidateRetriever] = None,
        scorer: Optional[DuplicateScorer] = None,
        version: str = "v1",
    ) -> None:
        embedder = ComplaintEmbedder()
        self.similarity_calculator = similarity_calculator or SimilarityCalculator(embedder=embedder)
        self.feature_builder = feature_builder or GeographicTemporalFeatureBuilder()
        self.candidate_retriever = candidate_retriever or DuplicateCandidateRetriever()
        self.scorer = scorer or DuplicateScorer(version=version)
        self.version = version

    def detect_duplicates(
        self,
        new_complaint: ComplaintRecord,
        existing_complaints: List[ComplaintRecord],
    ) -> DuplicateDetectionResponse:
        """Analyze a new complaint against a pool of historical existing complaints to detect candidates.

        Args:
            new_complaint: The newly logged ComplaintRecord.
            existing_complaints: List of historical ComplaintRecords to search against.

        Returns:
            DuplicateDetectionResponse containing sorted duplicate candidates and evidence breakdown.
        """
        # Validate input schema
        req = DuplicateDetectionRequest(
            new_complaint=new_complaint, existing_complaints=existing_complaints
        )

        # 1. Retrieve Candidate Complaints (excluding target self-matches)
        candidate_records = self.candidate_retriever.retrieve_candidates(
            target_complaint=req.new_complaint, candidate_pool=req.existing_complaints
        )

        evaluated_candidates: List[DuplicateCandidate] = []

        # 2. Iterate through candidates, extract features, and score
        for cand_record in candidate_records:
            # Semantic text similarity using Phase 5 embeddings
            text_sim = self.similarity_calculator.calculate_similarity(
                req.new_complaint.text, cand_record.text
            )

            # Spatial, temporal, and metadata evidence extraction
            evidence = self.feature_builder.build_evidence(
                complaint_a=req.new_complaint,
                complaint_b=cand_record,
                text_similarity=text_sim,
            )

            # Candidate scoring
            cand_result = self.scorer.score_candidate(
                candidate_id=cand_record.grievance_id, evidence=evidence
            )
            evaluated_candidates.append(cand_result)

        # 3. Sort candidates by duplicate score in descending order
        evaluated_candidates.sort(key=lambda c: c.duplicate_score, reverse=True)

        # Truncate to top_k candidates
        top_candidates = evaluated_candidates[: config.top_k_candidates]

        # Extract candidates exceeding score threshold
        possible_ids = [
            c.grievance_id for c in top_candidates if c.duplicate_score >= self.scorer.threshold
        ]

        top_score = top_candidates[0].duplicate_score if top_candidates else 0.0
        is_candidate = top_score >= self.scorer.threshold

        return DuplicateDetectionResponse(
            grievance_id=req.new_complaint.grievance_id,
            duplicate_score=top_score,
            is_duplicate_candidate=is_candidate,
            possible_duplicate_grievance_ids=possible_ids,
            candidates=top_candidates,
            model_version=self.version,
        )

    def save(self, model_dir: Optional[Union[str, Path]] = None) -> None:
        """Save detector scorer artifact to disk."""
        target_dir = Path(model_dir or config.model_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        self.scorer.save(target_dir / "model.joblib")

    @classmethod
    def load(cls, model_dir: Optional[Union[str, Path]] = None) -> DuplicateDetector:
        """Load detector pipeline from model directory."""
        target_dir = Path(model_dir or config.model_dir)
        model_path = target_dir / "model.joblib"

        scorer = DuplicateScorer.load(model_path) if model_path.exists() else DuplicateScorer()
        return cls(scorer=scorer, version=scorer.version)
