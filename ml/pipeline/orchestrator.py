"""Orchestrator pipeline for RoadX Unified ML Pipeline (Phase 9)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ml.common.exceptions import ModelArtifactNotFoundError, RoadXDataError, RoadXModelError
from ml.common.logging_config import get_logger
from ml.pipeline.config import PipelineConfig, pipeline_config
from ml.pipeline.context import MLPipelineContext
from ml.pipeline.schemas import PipelineInput, UnifiedPipelineResult
from ml.pipeline.stages import (
    execute_complaint_intelligence_stage,
    execute_damage_detection_stage,
    execute_duplicate_detection_stage,
    execute_failure_prediction_stage,
    execute_maintenance_priority_stage,
    execute_severity_stage,
    execute_time_to_failure_stage,
)

# ML Predictor interfaces
from ml.failure_prediction.predict import RoadFailurePredictor
from ml.damage_detection.detector import RoadDamageDetector
from ml.damage_detection.adapter import ExistingPotholeModelAdapter
from ml.severity.predict import DamageSeverityPredictor
from ml.complaint_intelligence.analyzer import ComplaintAnalyzer
from ml.duplicate_detection.detector import DuplicateDetector
from ml.time_to_failure.predictor import TimeToFailurePredictor
from ml.priority_engine.engine import MaintenancePriorityEngine

logger = get_logger("pipeline.orchestrator")


class RoadXPipeline:
    """Orchestrates independent ML modules (Phases 2-8) into a unified inference workflow.

    The pipeline maintains modular independence across model implementations, executing stages
    according to input availability and dependency order, and isolating stage failures.
    """

    def __init__(
        self,
        failure_predictor: Optional[RoadFailurePredictor] = None,
        damage_detector: Optional[RoadDamageDetector] = None,
        severity_predictor: Optional[DamageSeverityPredictor] = None,
        complaint_analyzer: Optional[ComplaintAnalyzer] = None,
        duplicate_detector: Optional[DuplicateDetector] = None,
        time_to_failure_predictor: Optional[TimeToFailurePredictor] = None,
        priority_engine: Optional[MaintenancePriorityEngine] = None,
        config: Optional[PipelineConfig] = None,
        auto_load: bool = True,
    ) -> None:
        self.config = config or pipeline_config
        self.failure_predictor = failure_predictor
        self.damage_detector = damage_detector
        self.severity_predictor = severity_predictor
        self.complaint_analyzer = complaint_analyzer
        self.duplicate_detector = duplicate_detector
        self.time_to_failure_predictor = time_to_failure_predictor
        self.priority_engine = priority_engine

        if auto_load:
            self._auto_load_default_predictors()

    def _auto_load_default_predictors(self) -> None:
        """Attempt to load trained default model artifacts for uninitialized predictors."""
        # 1. Failure Predictor
        if self.failure_predictor is None:
            try:
                self.failure_predictor = RoadFailurePredictor()
                logger.info("Loaded default RoadFailurePredictor model bundle.")
            except Exception as e:
                logger.warning("Default RoadFailurePredictor unavailable: %s", e)

        # 2. Damage Detector
        if self.damage_detector is None:
            try:
                self.damage_detector = ExistingPotholeModelAdapter()
                logger.info("Loaded default ExistingPotholeModelAdapter vision model.")
            except Exception as e:
                logger.warning("Default ExistingPotholeModelAdapter unavailable: %s", e)

        # 3. Severity Predictor
        if self.severity_predictor is None:
            try:
                self.severity_predictor = DamageSeverityPredictor()
                logger.info("Loaded default DamageSeverityPredictor model bundle.")
            except Exception as e:
                logger.warning("Default DamageSeverityPredictor unavailable: %s", e)

        # 4. Complaint Analyzer
        if self.complaint_analyzer is None:
            try:
                self.complaint_analyzer = ComplaintAnalyzer.load()
                logger.info("Loaded default ComplaintAnalyzer model bundle.")
            except Exception as e:
                logger.warning("Default ComplaintAnalyzer unavailable: %s", e)

        # 5. Duplicate Detector
        if self.duplicate_detector is None:
            try:
                self.duplicate_detector = DuplicateDetector()
                logger.info("Initialized default DuplicateDetector pipeline.")
            except Exception as e:
                logger.warning("Default DuplicateDetector unavailable: %s", e)

        # 6. Time-to-Failure Predictor
        if self.time_to_failure_predictor is None:
            try:
                self.time_to_failure_predictor = TimeToFailurePredictor.load()
                logger.info("Loaded default TimeToFailurePredictor model bundle.")
            except Exception as e:
                logger.warning("Default TimeToFailurePredictor unavailable: %s", e)

        # 7. Priority Engine
        if self.priority_engine is None:
            try:
                self.priority_engine = MaintenancePriorityEngine()
                logger.info("Initialized default MaintenancePriorityEngine.")
            except Exception as e:
                logger.warning("Default MaintenancePriorityEngine unavailable: %s", e)

    def run(
        self,
        input_data: Union[PipelineInput, Dict[str, Any]],
        enabled_stages: Optional[Dict[str, bool]] = None,
    ) -> UnifiedPipelineResult:
        """Execute the Unified ML Pipeline over single or combined input payloads.

        Args:
            input_data: PipelineInput Pydantic object or raw dictionary.
            enabled_stages: Optional dict overriding stage activation flags.

        Returns:
            UnifiedPipelineResult containing all stage outputs, summaries, and latency metrics.
        """
        start_t = time.perf_counter()

        # Validate input schema
        if isinstance(input_data, dict):
            try:
                parsed_input = PipelineInput(**input_data)
            except Exception as e:
                raise RoadXDataError(f"Invalid pipeline input payload: {e}") from e
        elif isinstance(input_data, PipelineInput):
            parsed_input = input_data
        else:
            raise RoadXDataError(f"Unsupported pipeline input type: {type(input_data)}")

        if enabled_stages:
            if parsed_input.enabled_stages:
                parsed_input.enabled_stages.update(enabled_stages)
            else:
                parsed_input.enabled_stages = enabled_stages

        context = MLPipelineContext(input_data=parsed_input)
        default_flags = self.config.get_default_stage_flags()

        logger.info(
            "Executing RoadX Unified ML Pipeline (road_segment_id=%s, complaint_id=%s)",
            parsed_input.road_segment_id,
            parsed_input.complaint_id,
        )

        # Execution Graph in Dependency Order:
        # 1. Road Failure Prediction (Phase 2)
        execute_failure_prediction_stage(context, self.failure_predictor, default_flags)

        # 2. Road Damage Detection (Phase 3)
        execute_damage_detection_stage(context, self.damage_detector, default_flags)

        # 3. Damage Severity Estimation (Phase 4 - depends on Phase 3 output)
        execute_severity_stage(context, self.severity_predictor, default_flags)

        # 4. Complaint Intelligence (Phase 5)
        execute_complaint_intelligence_stage(context, self.complaint_analyzer, default_flags)

        # 5. Duplicate Complaint Detection (Phase 6 - uses complaint context)
        execute_duplicate_detection_stage(context, self.duplicate_detector, default_flags)

        # 6. Time-to-Failure Prediction (Phase 7)
        execute_time_to_failure_stage(context, self.time_to_failure_predictor, default_flags)

        # 7. Maintenance Priority Recommendation (Phase 8 - synthesizes outputs 2-7)
        execute_maintenance_priority_stage(context, self.priority_engine, default_flags)

        total_duration_ms = (time.perf_counter() - start_t) * 1000.0
        result = context.to_unified_result(
            pipeline_version=self.config.pipeline_version, total_duration_ms=total_duration_ms
        )

        logger.info(
            "Pipeline completed in %.2f ms with overall status: %s",
            total_duration_ms,
            result.overall_status,
        )
        return result
