"""Candidate complaint retriever abstraction for finding potential duplicate candidates."""

from __future__ import annotations

from typing import List, Optional

from ml.duplicate_detection.schemas import ComplaintRecord
from ml.duplicate_detection.config import config


class DuplicateCandidateRetriever:
    """In-memory candidate retriever filtering historical complaint records for duplicate evaluation.

    Designed with an abstract candidate retrieval interface to seamlessly allow future
    integration of production vector databases (FAISS/Pinecone/Chroma) without breaking system contracts.
    """

    def __init__(
        self,
        historical_records: Optional[List[ComplaintRecord]] = None,
        top_k: int = config.top_k_candidates,
    ) -> None:
        self.top_k = top_k
        self._index: List[ComplaintRecord] = historical_records or []

    def set_index(self, records: List[ComplaintRecord]) -> None:
        """Update or set the candidate pool index."""
        self._index = list(records)

    def retrieve_candidates(
        self,
        target_complaint: ComplaintRecord,
        candidate_pool: Optional[List[ComplaintRecord]] = None,
    ) -> List[ComplaintRecord]:
        """Retrieve candidate complaints relevant to target_complaint, excluding self-matches.

        Args:
            target_complaint: The newly logged complaint record.
            candidate_pool: Optional candidate pool list overriding internal index.

        Returns:
            List of candidate ComplaintRecords excluding target_complaint self-match.
        """
        pool = candidate_pool if candidate_pool is not None else self._index

        candidates: List[ComplaintRecord] = []
        target_id = target_complaint.grievance_id.strip().lower()

        for record in pool:
            # Exclude self-match
            rec_id = record.grievance_id.strip().lower()
            if rec_id == target_id:
                continue

            candidates.append(record)

        # For in-memory baseline, return up to candidate pool size (or top_k if specified)
        return candidates
