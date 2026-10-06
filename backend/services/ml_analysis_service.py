"""Service connecting ML Pipeline inference to backend database storage."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.models.ml_analysis import MLAnalysisResult
from backend.repositories.grievance_repository import GrievanceRepository
from backend.repositories.ml_analysis_repository import MLAnalysisRepository
from ml.common.exceptions import RoadXDataError
from ml.common.logging_config import get_logger
from ml.pipeline.orchestrator import RoadXPipeline
from ml.pipeline.schemas import PipelineInput, UnifiedPipelineResult

logger = get_logger("backend.services.ml_analysis")


class MLAnalysisService:
    """MLAnalysisService linking Phase 9/10 pipeline inference with persistent DB storage."""

    def __init__(self, db: Session, pipeline: Optional[RoadXPipeline] = None) -> None:
        self.db = db
        self.grievance_repo = GrievanceRepository(db)
        self.ml_analysis_repo = MLAnalysisRepository(db)
        self.pipeline = pipeline

    def _get_pipeline(self) -> RoadXPipeline:
        """Lazy load or return existing pipeline instance."""
        if self.pipeline is None:
            self.pipeline = RoadXPipeline(auto_load=True)
        return self.pipeline

    def analyze_and_store_grievance(
        self,
        grievance_id: str,
        road_data_override: Optional[Dict[str, Any]] = None,
        enabled_stages: Optional[Dict[str, bool]] = None,
    ) -> MLAnalysisResult:
        """Invoke ML pipeline for a persisted grievance report and store structured result.

        Args:
            grievance_id: Target grievance database UUID.
            road_data_override: Optional tabular features override for failure prediction.
            enabled_stages: Optional stage activation override flags.

        Returns:
            Persisted MLAnalysisResult SQLAlchemy model instance.
        """
        grievance = self.grievance_repo.get_by_id(grievance_id)
        if not grievance:
            raise RoadXDataError(f"Grievance with ID '{grievance_id}' not found.")

        # Construct ML PipelineInput from grievance record
        segment_id_str = (
            grievance.road_segment.segment_id if grievance.road_segment else None
        )

        pipeline_input = PipelineInput(
            road_segment_id=segment_id_str,
            complaint_id=grievance.id,
            complaint_text=grievance.description,
            road_data=road_data_override,
            enabled_stages=enabled_stages,
        )

        logger.info(
            "Executing ML pipeline analysis for grievance '%s' (road_segment_id=%s)",
            grievance_id,
            segment_id_str,
        )

        pipeline = self._get_pipeline()
        result: UnifiedPipelineResult = pipeline.run(pipeline_input)
        res_dict = result.model_dump()

        # Persist ML Analysis Output in Database
        analysis_record = MLAnalysisResult(
            grievance_id=grievance.id,
            pipeline_version=result.pipeline_version,
            overall_status=result.overall_status,
            total_duration_ms=result.total_duration_ms,
            failure_prediction=res_dict.get("failure_prediction"),
            damage_detection=res_dict.get("damage_detection"),
            severity_prediction=res_dict.get("severity_prediction"),
            complaint_analysis=res_dict.get("complaint_analysis"),
            duplicate_detection=res_dict.get("duplicate_detection"),
            time_to_failure=res_dict.get("time_to_failure"),
            maintenance_priority=res_dict.get("maintenance_priority"),
            stage_summaries=res_dict.get("stage_summaries"),
        )

        saved = self.ml_analysis_repo.add(analysis_record)
        logger.info(
            "Successfully stored ML analysis record '%s' for grievance '%s'",
            saved.id,
            grievance_id,
        )
        return saved

    def get_analyses_for_grievance(self, grievance_id: str) -> List[MLAnalysisResult]:
        """Fetch all stored ML analysis records for a grievance."""
        # Verify grievance exists first
        grievance = self.grievance_repo.get_by_id(grievance_id)
        if not grievance:
            raise RoadXDataError(f"Grievance with ID '{grievance_id}' not found.")
        return self.ml_analysis_repo.get_by_grievance_id(grievance_id)
