"""tests/unit/investment/workflow/test_workflow_history.py
Tests for WorkflowRunRecord and WorkflowHistory.
"""
from __future__ import annotations

import uuid
import pytest

from iios.investment.workflow.workflow_history import WorkflowHistory, WorkflowRunRecord
from iios.investment.workflow.workflow_types import WorkflowStage


def _make_record(
    *,
    portfolio_id: str   = "P-1",
    succeeded:    bool  = True,
    run_id:       str   = "",
) -> WorkflowRunRecord:
    return WorkflowRunRecord(
        run_id              = run_id or str(uuid.uuid4()),
        workflow_id         = "institutional_investment_pipeline",
        request_id          = str(uuid.uuid4()),
        portfolio_id        = portfolio_id,
        started_at          = "2026-01-01T09:00:00+00:00",
        completed_at        = "2026-01-01T09:00:01+00:00",
        terminal_stage      = WorkflowStage.PUBLISHED if succeeded else WorkflowStage.FAILED,
        total_duration_ms   = 200.0,
        n_stages_completed  = 5 if succeeded else 2,
        n_retries           = 0,
        n_errors            = 0 if succeeded else 1,
        n_warnings          = 0,
        snapshot_id         = "snap-1" if succeeded else None,
        market_quality      = 0.80,
        company_quality     = 0.75,
        strategy_quality    = 0.72,
        decision_quality    = 0.80,
        portfolio_quality   = 0.85,
        is_published        = succeeded,
        errors              = () if succeeded else ("stage failed",),
        warnings            = (),
        stage_durations_ms  = {"market": 50.0},
    )


class TestWorkflowRunRecord:
    def test_frozen(self):
        rec = _make_record()
        with pytest.raises((AttributeError, TypeError)):
            rec.run_id = "new"  # type: ignore

    def test_succeeded_property(self):
        assert _make_record(succeeded=True).succeeded
        assert not _make_record(succeeded=False).succeeded

    def test_to_dict_keys(self):
        d = _make_record().to_dict()
        for key in ["run_id", "workflow_id", "portfolio_id", "succeeded",
                    "total_duration_ms", "n_stages_completed", "errors"]:
            assert key in d


class TestWorkflowHistory:
    def test_add_and_get(self):
        h = WorkflowHistory()
        rec = _make_record(run_id="abc")
        h.add(rec)
        assert h.get("abc") is rec

    def test_unknown_run_returns_none(self):
        assert WorkflowHistory().get("nope") is None

    def test_recent_newest_first(self):
        h = WorkflowHistory()
        for i in range(5):
            h.add(_make_record(run_id=str(i)))
        recent = h.recent(3)
        assert len(recent) == 3
        # newest first (run_id "4")
        assert recent[0].run_id == "4"

    def test_for_portfolio(self):
        h = WorkflowHistory()
        h.add(_make_record(portfolio_id="P-A"))
        h.add(_make_record(portfolio_id="P-B"))
        h.add(_make_record(portfolio_id="P-A"))
        result = h.for_portfolio("P-A")
        assert all(r.portfolio_id == "P-A" for r in result)
        assert len(result) == 2

    def test_successful(self):
        h = WorkflowHistory()
        h.add(_make_record(succeeded=True))
        h.add(_make_record(succeeded=False))
        assert len(h.successful()) == 1

    def test_failed(self):
        h = WorkflowHistory()
        h.add(_make_record(succeeded=True))
        h.add(_make_record(succeeded=False))
        assert len(h.failed()) == 1

    def test_total_counts(self):
        h = WorkflowHistory()
        for i in range(4):
            h.add(_make_record(succeeded=(i % 2 == 0)))
        assert h.total_runs == 4
        assert h.total_successful == 2

    def test_max_runs_bounded(self):
        h = WorkflowHistory(max_runs=3)
        for i in range(10):
            h.add(_make_record(run_id=str(i)))
        assert h.total_runs == 3

    def test_to_dict(self):
        h = WorkflowHistory()
        h.add(_make_record())
        d = h.to_dict()
        assert "total_runs" in d
        assert "total_successful" in d

    def test_invalid_max_runs(self):
        with pytest.raises(ValueError):
            WorkflowHistory(max_runs=0)
