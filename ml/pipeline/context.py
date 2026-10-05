"""Execution context and state management for RoadX Unified ML Pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from ml.pipeline.schemas import (
    PipelineInput,
    PipelineStageStatus,
    PipelineStageSummary,
    UnifiedPipelineResult,
)
from ml.failure_prediction.schemas import FailurePredictionOutput
from ml.damage_detection.schemas import RoadDamageDetectionResponse
from ml.severity.schemas import SeverityPredictionOutput
from ml.complaint_intelligence.schemas import ComplaintAnalysisResponse
from ml.duplicate_detection.schemas import DuplicateDetectionResponse
from ml.time_to_failure.schemas import TimeToFailureOutput
from ml.priority_engine.schemas import MaintenancePriorityOutput


class MLPipelineContext:
    """Shared context object maintaining pipeline state, stage outputs, and latency metrics."""

    def __init__(self, input_data: PipelineInput) -> None:
        self.input_data = input_data

        # Accumulated ML stage outputs
        self.failure_prediction: Optional[FailurePredictionOutput] = None
        self.damage_detection: Optional[RoadDamageDetectionResponse] = None
        self.severity_prediction: Optional[SeverityPredictionOutput] = None
        self.complaint_analysis: Optional[ComplaintAnalysisResponse] = None
        self.duplicate_detection: Optional[DuplicateDetectionResponse] = None
        self.time_to_failure: Optional[TimeToFailureOutput] = None
        self.maintenance_priority: Optional[MaintenancePriorityOutput] = None

        # Stage status & execution profiling
        self.stage_summaries: Dict[str, PipelineStageSummary] = {}
        self.start_timestamp_utc = datetime.now(timezone.utc).isoformat()

    def is_stage_enabled(self, stage_name: str, default_flags: Dict[str, bool]) -> bool:
        """Determine if a stage is enabled based on request input overrides or pipeline defaults."""
        if self.input_data.enabled_stages and stage_name in self.input_data.enabled_stages:
            return bool(self.input_data.enabled_stages[stage_name])
        return default_flags.get(stage_name, True)

    def record_stage_summary(
        self,
        stage_name: str,
        status: PipelineStageStatus,
        duration_ms: float,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        model_version: Optional[str] = None,
    ) -> None:
        """Record execution metric and status for a pipeline stage."""
        self.stage_summaries[stage_name] = PipelineStageSummary(
            stage_name=stage_name,
            status=status,
            duration_ms=round(duration_ms, 2),
            error_code=error_code,
            error_message=error_message,
            model_version=model_version,
        )

    def determine_overall_status(self) -> str:
        """Determine overall status: SUCCESS, PARTIAL_SUCCESS, or FAILED."""
        statuses = [s.status for s in self.stage_summaries.values()]
        if not statuses:
            return "SUCCESS"

        failed_count = statuses.count(PipelineStageStatus.FAILED)
        success_count = statuses.count(PipelineStageStatus.SUCCESS)

        if failed_count == 0:
            return "SUCCESS"
        elif success_count == 0:
            return "FAILED"
        else:
            return "PARTIAL_SUCCESS"

    def to_unified_result(self, pipeline_version: str, total_duration_ms: float) -> UnifiedPipelineResult:
        """Compile accumulated stage outputs and summaries into a UnifiedPipelineResult."""
        overall_status = self.determine_overall_status()

        return UnifiedPipelineResult(
            pipeline_version=pipeline_version,
            timestamp_utc=self.start_timestamp_utc,
            overall_status=overall_status,
            road_segment_id=self.input_data.road_segment_id,
            complaint_id=self.input_data.complaint_id,
            failure_prediction=self.failure_prediction,
            damage_detection=self.damage_detection,
            severity_prediction=self.severity_prediction,
            complaint_analysis=self.complaint_analysis,
            duplicate_detection=self.duplicate_detection,
            time_to_failure=self.time_to_failure,
            maintenance_priority=self.maintenance_priority,
            stage_summaries=self.stage_summaries,
            total_duration_ms=round(total_duration_ms, 2),
        )
