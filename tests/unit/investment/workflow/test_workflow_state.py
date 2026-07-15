"""tests/unit/investment/workflow/test_workflow_state.py
Tests for WorkflowState, StageRecord.
"""
from __future__ import annotations

import pytest

from iios.investment.workflow.workflow_state import StageRecord, WorkflowState
from iios.investment.workflow.workflow_types import (
    StageStatus, WorkflowStage,
)


class TestStageRecord:
    def test_frozen(self):
        rec = StageRecord(
            stage        = WorkflowStage.MARKET,
            attempt      = 1,
            status       = StageStatus.COMPLETED,
            started_at   = "2026-01-01T00:00:00+00:00",
            completed_at = "2026-01-01T00:00:01+00:00",
            duration_ms  = 100.0,
            error        = None,
            snapshot_id  = "snap-1",
        )
        with pytest.raises((AttributeError, TypeError)):
            rec.attempt = 99  # type: ignore

    def test_to_dict_keys(self):
        rec = StageRecord(
            stage=WorkflowStage.MARKET, attempt=1,
            status=StageStatus.COMPLETED, started_at="iso", completed_at="iso",
            duration_ms=50.0, error=None, snapshot_id="x",
        )
        d = rec.to_dict()
        assert "stage"        in d
        assert "status"       in d
        assert "duration_ms"  in d
        assert "snapshot_id"  in d


class TestWorkflowState:
    def test_initial_stage(self):
        state = WorkflowState()
        assert state.current_stage == WorkflowStage.INITIALIZED

    def test_begin_and_complete_stage(self):
        state = WorkflowState()
        state.begin_stage(WorkflowStage.MARKET)
        assert state.current_stage == WorkflowStage.MARKET
        rec = state.complete_stage(WorkflowStage.MARKET, snapshot="snap", snapshot_id="id1")
        assert rec.status == StageStatus.COMPLETED
        assert WorkflowStage.MARKET in state.completed_stages

    def test_snapshot_stored(self):
        state = WorkflowState()
        obj   = object()
        state.begin_stage(WorkflowStage.MARKET)
        state.complete_stage(WorkflowStage.MARKET, snapshot=obj)
        assert state.get_snapshot(WorkflowStage.MARKET) is obj

    def test_fail_stage(self):
        state = WorkflowState()
        state.begin_stage(WorkflowStage.MARKET)
        rec = state.fail_stage(WorkflowStage.MARKET, "timeout", is_retry=True)
        assert rec.status == StageStatus.FAILED
        assert state.has_errors
        assert state.retry_count(WorkflowStage.MARKET) == 1

    def test_skip_stage(self):
        state = WorkflowState()
        rec   = state.skip_stage(WorkflowStage.COMPANY)
        assert rec.status == StageStatus.SKIPPED

    def test_cancellation(self):
        state = WorkflowState()
        state.cancel()
        assert state.is_cancelled
        assert state.current_stage == WorkflowStage.CANCELLED
        assert state.is_terminal

    def test_terminal_stage_transition(self):
        state = WorkflowState()
        state.transition_terminal(WorkflowStage.PUBLISHED)
        assert state.is_terminal
        assert state.current_stage == WorkflowStage.PUBLISHED

    def test_warnings(self):
        state = WorkflowState()
        state.add_warning("low quality")
        assert "low quality" in state.warnings

    def test_to_dict(self):
        state = WorkflowState(workflow_id="wf-1", request_id="req-1")
        d     = state.to_dict()
        assert d["workflow_id"]  == "wf-1"
        assert d["request_id"]   == "req-1"
        assert "current_stage"   in d
        assert "stage_records"   in d
        assert "errors"          in d

    def test_errors_property(self):
        state = WorkflowState()
        state.begin_stage(WorkflowStage.MARKET)
        state.fail_stage(WorkflowStage.MARKET, "error1")
        assert "error1" in state.errors[0]

    def test_stage_accessors(self):
        state = WorkflowState()
        state.begin_stage(WorkflowStage.MARKET)
        snap = object()
        state.complete_stage(WorkflowStage.MARKET, snapshot=snap)
        assert state.get_market_snapshot() is snap
        assert state.get_company_snapshot() is None

    def test_total_duration_ms(self):
        state = WorkflowState()
        state.begin_stage(WorkflowStage.MARKET)
        state.complete_stage(WorkflowStage.MARKET)
        assert state.total_duration_ms() >= 0.0

    def test_multiple_retry_count(self):
        state = WorkflowState()
        for _ in range(3):
            state.begin_stage(WorkflowStage.MARKET)
            state.fail_stage(WorkflowStage.MARKET, "err", is_retry=True)
        assert state.retry_count(WorkflowStage.MARKET) == 3
