"""tests/unit/investment/workflow/test_workflow_types.py
Tests for workflow_types.py — enums, constants, stage ordering.
"""
from __future__ import annotations

import pytest

from iios.investment.workflow.workflow_types import (
    PIPELINE_STAGES,
    TERMINAL_STAGES,
    WORKFLOW_VERSION,
    PipelineEventType,
    StageStatus,
    WorkflowStage,
)


class TestWorkflowStage:
    def test_all_stages_have_str_value(self):
        for stage in WorkflowStage:
            assert isinstance(stage.value, str)
            assert len(stage.value) > 0

    def test_pipeline_stages_ordered(self):
        expected = ["market", "company", "strategy", "decision", "portfolio"]
        actual   = [s.value for s in PIPELINE_STAGES]
        assert actual == expected

    def test_terminal_stages(self):
        assert WorkflowStage.PUBLISHED in TERMINAL_STAGES
        assert WorkflowStage.FAILED    in TERMINAL_STAGES
        assert WorkflowStage.CANCELLED in TERMINAL_STAGES

    def test_pipeline_stages_not_terminal(self):
        for s in PIPELINE_STAGES:
            assert s not in TERMINAL_STAGES

    def test_five_pipeline_stages(self):
        assert len(PIPELINE_STAGES) == 5


class TestPipelineEventType:
    def test_all_event_types_str(self):
        for et in PipelineEventType:
            assert isinstance(et.value, str)

    def test_expected_events_present(self):
        values = {e.value for e in PipelineEventType}
        for expected in [
            "workflow_started", "stage_started", "stage_completed",
            "stage_failed", "workflow_completed", "workflow_failed",
            "workflow_cancelled", "portfolio_snapshot_published",
            "stage_retrying",
        ]:
            assert expected in values


class TestStageStatus:
    def test_all_statuses_str(self):
        for s in StageStatus:
            assert isinstance(s.value, str)

    def test_has_completed_and_failed(self):
        assert StageStatus.COMPLETED.value == "completed"
        assert StageStatus.FAILED.value    == "failed"


class TestWorkflowVersion:
    def test_version_semver(self):
        parts = WORKFLOW_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
