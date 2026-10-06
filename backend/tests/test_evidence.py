"""Unit tests for Evidence metadata persistence."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models.evidence import Evidence
from backend.repositories.base_repository import BaseRepository
from backend.schemas.grievance import GrievanceCreate
from backend.services.grievance_service import GrievanceService


def test_attach_and_retrieve_evidence(db_session: Session):
    """Test attaching evidence file metadata to a grievance report."""
    grievance_service = GrievanceService(db_session)
    evidence_repo = BaseRepository(Evidence, db_session)

    # 1. Create grievance
    grievance = grievance_service.create_grievance(
        GrievanceCreate(issue_category="POTHOLE", description="Severe pothole.")
    )

    # 2. Attach evidence metadata
    evidence = Evidence(
        grievance_id=grievance.id,
        file_name="pothole_photo_1.jpg",
        file_type="image/jpeg",
        storage_path="uploads/evidences/pothole_photo_1.jpg",
        file_size_bytes=2048500,
    )
    saved_evidence = evidence_repo.add(evidence)

    assert saved_evidence.id is not None
    assert saved_evidence.grievance_id == grievance.id

    # 3. Retrieve grievance with evidence relationship
    fetched_grievance = grievance_service.get_grievance(grievance.id)
    assert len(fetched_grievance.evidence_items) == 1
    assert fetched_grievance.evidence_items[0].file_name == "pothole_photo_1.jpg"
