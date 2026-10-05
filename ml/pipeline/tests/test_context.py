"""Unit tests for MLPipelineContext state management (Phase 9)."""

import pytest
from ml.pipeline.context import MLPipelineContext
from ml.pipeline.schemas import PipelineInput, PipelineStageStatus


def test_context_initialization():
    inp = PipelineInput(road_segment_id="SEG-101", complaint_id="COMP-505")
    ctx = MLPipelineContext(inp)

    assert ctx.input_data.road_segment_id == "SEG-101"
    assert ctx.input_data.complaint_id == "COMP-505"
    assert len(ctx.stage_summaries) == 0
    assert ctx.failure_prediction is None


def test_context_stage_recording_and_overall_status():
    inp = PipelineInput(road_segment_id="SEG-101")
    ctx = MLPipelineContext(inp)

    ctx.record_stage_summary("stage_1", PipelineStageStatus.SUCCESS, 12.5)
    ctx.record_stage_summary("stage_2", PipelineStageStatus.SKIPPED, 0.0, error_message="Skipped")

    assert ctx.determine_overall_status() == "SUCCESS"

    ctx.record_stage_summary("stage_3", PipelineStageStatus.FAILED, 5.0, error_code="ERR", error_message="Fail")
    assert ctx.determine_overall_status() == "PARTIAL_SUCCESS"

    res = ctx.to_unified_result("v1", total_duration_ms=20.0)
    assert res.pipeline_version == "v1"
    assert res.overall_status == "PARTIAL_SUCCESS"
    assert res.total_duration_ms == 20.0
    assert "stage_1" in res.stage_summaries
    assert res.stage_summaries["stage_1"].duration_ms == 12.5


def test_context_all_failed_status():
    inp = PipelineInput()
    ctx = MLPipelineContext(inp)

    ctx.record_stage_summary("stage_1", PipelineStageStatus.FAILED, 5.0)
    ctx.record_stage_summary("stage_2", PipelineStageStatus.FAILED, 2.0)

    assert ctx.determine_overall_status() == "FAILED"
