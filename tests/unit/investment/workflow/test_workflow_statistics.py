"""tests/unit/investment/workflow/test_workflow_statistics.py
Tests for WorkflowRunMetric, WorkflowStatistics.
"""
from __future__ import annotations

import pytest

from iios.investment.workflow.workflow_statistics import (
    WorkflowRunMetric,
    WorkflowStatistics,
    WorkflowStatisticsSnapshot,
)


def _make_metric(
    *,
    succeeded:   bool  = True,
    duration_ms: float = 200.0,
    n_retries:   int   = 0,
    quality:     float = 0.80,
) -> WorkflowRunMetric:
    return WorkflowRunMetric(
        workflow_id       = "institutional_investment_pipeline",
        portfolio_id      = "P-1",
        succeeded         = succeeded,
        total_duration_ms = duration_ms,
        n_stages_done     = 5 if succeeded else 2,
        n_retries         = n_retries,
        n_errors          = 0 if succeeded else 1,
        n_warnings        = 0,
        market_quality    = quality,
        company_quality   = quality,
        strategy_quality  = quality,
        decision_quality  = quality,
        portfolio_quality = quality,
        snapshot_id       = "snap" if succeeded else None,
    )


class TestWorkflowRunMetric:
    def test_frozen(self):
        m = _make_metric()
        with pytest.raises((AttributeError, TypeError)):
            m.succeeded = False  # type: ignore

    def test_to_dict(self):
        d = _make_metric().to_dict()
        assert "succeeded" in d
        assert "total_duration_ms" in d


class TestWorkflowStatistics:
    def test_empty_returns_zeros(self):
        s   = WorkflowStatistics()
        assert s.total_runs == 0
        assert s.success_rate() == 0.0
        assert s.average_duration_ms() == 0.0

    def test_record_and_success_rate(self):
        s = WorkflowStatistics()
        s.record(_make_metric(succeeded=True))
        s.record(_make_metric(succeeded=True))
        s.record(_make_metric(succeeded=False))
        assert s.total_runs == 3
        assert abs(s.success_rate() - 2/3) < 0.001

    def test_average_duration(self):
        s = WorkflowStatistics()
        s.record(_make_metric(duration_ms=100.0))
        s.record(_make_metric(duration_ms=200.0))
        assert s.average_duration_ms() == 150.0

    def test_summary_keys(self):
        s = WorkflowStatistics()
        s.record(_make_metric())
        snap = s.summary()
        assert isinstance(snap, WorkflowStatisticsSnapshot)
        d = snap.to_dict()
        for key in ["total_runs", "success_rate", "avg_duration_ms",
                    "p95_duration_ms", "total_retries"]:
            assert key in d

    def test_summary_quality_averages(self):
        s = WorkflowStatistics()
        s.record(_make_metric(quality=0.80))
        s.record(_make_metric(quality=0.60))
        snap = s.summary()
        assert abs(snap.avg_market_quality - 0.70) < 0.001

    def test_summary_p95(self):
        s = WorkflowStatistics()
        for i in range(20):
            s.record(_make_metric(duration_ms=float(i * 10)))
        snap = s.summary()
        assert snap.p95_duration_ms > 0.0
        assert snap.p95_duration_ms <= 200.0  # max in dataset

    def test_max_runs_bounded(self):
        s = WorkflowStatistics(max_runs=5)
        for _ in range(10):
            s.record(_make_metric())
        assert s.total_runs == 5

    def test_invalid_max_runs(self):
        with pytest.raises(ValueError):
            WorkflowStatistics(max_runs=0)

    def test_retries_tracked(self):
        s = WorkflowStatistics()
        s.record(_make_metric(n_retries=2))
        s.record(_make_metric(n_retries=3))
        snap = s.summary()
        assert snap.total_retries == 5
