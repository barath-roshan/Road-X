"""Unit tests for storing and retrieving Phase 9/10 ML analysis results in DB."""

from __future__ import annotations

from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from backend.schemas.grievance import GrievanceCreate
from backend.services.grievance_service import GrievanceService
from backend.services.ml_analysis_service import MLAnalysisService
from ml.pipeline.orchestrator import RoadXPipeline
from ml.pipeline.schemas import UnifiedPipelineResult, PipelineStageSummary, PipelineStageStatus


def test_analyze_and_store_grievance_ml_result(db_session: Session):
    """Test invoking ML pipeline and persisting structured analysis result in database."""
    grievance_service = GrievanceService(db_session)

    # 1. Create grievance
    grievance = grievance_service.create_grievance(
        GrievanceCreate(
            issue_category="POTHOLE",
            description="Deep pothole causing vehicle tire damage on main road.",
        )
    )

    # 2. Mock RoadXPipeline to return synthetic UnifiedPipelineResult
    mock_pipeline = MagicMock(spec=RoadXPipeline)
    mock_pipeline.run.return_value = UnifiedPipelineResult(
        pipeline_version="v1",
        timestamp_utc="2026-10-06T12:00:00Z",
        overall_status="SUCCESS",
        complaint_id=grievance.id,
        stage_summaries={
            "complaint_intelligence": PipelineStageSummary(
                stage_name="complaint_intelligence",
                status=PipelineStageStatus.SUCCESS,
                duration_ms=15.5,
                model_version="v1",
            )
        },
        total_duration_ms=25.0,
    )

    # 3. Execute MLAnalysisService
    ml_service = MLAnalysisService(db_session, pipeline=mock_pipeline)
    analysis_record = ml_service.analyze_and_store_grievance(grievance.id)

    assert analysis_record.id is not None
    assert analysis_record.grievance_id == grievance.id
    assert analysis_record.pipeline_version == "v1"
    assert analysis_record.overall_status == "SUCCESS"
    assert analysis_record.total_duration_ms == 25.0
    assert "stage_summaries" in analysis_record.__dict__ or analysis_record.stage_summaries is not None

    # 4. Query stored analysis records for grievance
    history = ml_service.get_analyses_for_grievance(grievance.id)
    assert len(history) == 1
    assert history[0].id == analysis_record.id
