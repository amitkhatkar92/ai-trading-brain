"""tests/unit/investment/workflow/test_institutional_workflow.py
Comprehensive tests for InstitutionalWorkflowOrchestrator and
InstitutionalInvestmentWorkflow.
"""
from __future__ import annotations

import uuid
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest

from iios.investment.investment_constants import AssetClass, InvestmentObjective
from iios.investment.models.investment_request import InvestmentRequest
from iios.investment.workflow.institutional_investment_workflow import (
    InstitutionalInvestmentWorkflow,
    InstitutionalWorkflowOrchestrator,
    WorkflowResult,
)
from iios.investment.workflow.workflow_context import WorkflowEngines, WorkflowParameters
from iios.investment.workflow.workflow_events import WorkflowEvent, WorkflowEventPublisher
from iios.investment.workflow.workflow_history import WorkflowRunRecord
from iios.investment.workflow.workflow_statistics import WorkflowStatisticsSnapshot
from iios.investment.workflow.workflow_types import (
    PIPELINE_STAGES, PipelineEventType, WorkflowStage,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _orchestrator(
    engines:      WorkflowEngines,
    params:       WorkflowParameters = WorkflowParameters(max_retries=0, retry_delay_sec=0.0),
    pub:          WorkflowEventPublisher | None = None,
) -> InstitutionalWorkflowOrchestrator:
    return InstitutionalWorkflowOrchestrator(
        params          = params,
        engines         = engines,
        event_publisher = pub,
    )


# ── Version ───────────────────────────────────────────────────────────────────

class TestWorkflowVersion:
    def test_version_set(self):
        assert InstitutionalInvestmentWorkflow.VERSION
        assert "." in InstitutionalInvestmentWorkflow.VERSION

    def test_orchestrator_version(self):
        assert InstitutionalWorkflowOrchestrator.VERSION == InstitutionalInvestmentWorkflow.VERSION


# ── Happy-path: full pipeline ─────────────────────────────────────────────────

class TestHappyPath:
    def test_run_returns_workflow_result(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-HAPPY")
        assert isinstance(result, WorkflowResult)

    def test_result_succeeded(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-HAPPY")
        assert result.succeeded

    def test_portfolio_snapshot_not_none(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-HAPPY")
        assert result.portfolio_snapshot is not None

    def test_portfolio_id_in_result(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-HAPPY")
        assert result.portfolio_id == "P-HAPPY"

    def test_request_id_in_result(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-HAPPY")
        assert result.request_id == request_obj.request_id

    def test_terminal_stage_published(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-HAPPY")
        assert result.run_record.terminal_stage == WorkflowStage.PUBLISHED

    def test_all_five_stage_snapshots_present(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-HAPPY")
        for stage in PIPELINE_STAGES:
            assert stage in result.stage_snapshots

    def test_market_engine_called(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-HAPPY")
        engines.market_engine.update.assert_called_once()

    def test_company_engine_called(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-HAPPY")
        engines.company_engine.integrate.assert_called_once()

    def test_strategy_engine_called(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-HAPPY")
        assert engines.strategy_engine.get_snapshot_sync.called

    def test_decision_engine_called(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-HAPPY")
        engines.decision_engine.integrate_sync.assert_called_once()

    def test_portfolio_engine_integrate_called(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-HAPPY")
        engines.portfolio_engine.integrate.assert_called_once()

    def test_portfolio_receive_called_for_framework(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-HAPPY")
        # receive() must have been called at least once (for framework data)
        assert engines.portfolio_engine.receive.called

    def test_to_dict(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-HAPPY")
        d      = result.to_dict()
        assert d["succeeded"] is True
        assert "workflow_id" in d
        assert "total_duration_ms" in d

    def test_n_stages_completed_is_five(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-HAPPY")
        assert result.run_record.n_stages_completed == 5


# ── Stage skip flags ──────────────────────────────────────────────────────────

class TestSkipStages:
    def test_skip_company_stage(self, engines, request_obj):
        params = WorkflowParameters(
            max_retries=0, retry_delay_sec=0.0,
            skip_company_stage=True,
        )
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-SKIP")
        assert result.succeeded
        engines.company_engine.integrate.assert_not_called()

    def test_skip_strategy_stage(self, engines, request_obj):
        params = WorkflowParameters(
            max_retries=0, retry_delay_sec=0.0,
            skip_strategy_stage=True,
        )
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-SKIP-S")
        assert result.succeeded

    def test_skip_decision_stage(self, engines, request_obj):
        params = WorkflowParameters(
            max_retries=0, retry_delay_sec=0.0,
            skip_decision_stage=True,
        )
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-SKIP-D")
        assert result.succeeded
        engines.decision_engine.integrate_sync.assert_not_called()

    def test_skip_all_optional_stages(self, engines, request_obj):
        params = WorkflowParameters(
            max_retries=0, retry_delay_sec=0.0,
            skip_company_stage=True,
            skip_strategy_stage=True,
            skip_decision_stage=True,
        )
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-SKIP-ALL")
        assert result.succeeded


# ── Failure and retry ─────────────────────────────────────────────────────────

class TestFailureScenarios:
    def test_market_engine_failure_fails_workflow(self, request_obj, params):
        from tests.unit.investment.workflow.conftest import make_engines
        engines = make_engines()
        engines.market_engine.update.side_effect = RuntimeError("market down")
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-FAIL")
        assert not result.succeeded
        assert result.run_record.terminal_stage == WorkflowStage.FAILED

    def test_company_engine_failure_fails_workflow(self, request_obj, params):
        from tests.unit.investment.workflow.conftest import make_engines
        engines = make_engines()
        engines.company_engine.integrate.side_effect = RuntimeError("company crash")
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-FAIL")
        assert not result.succeeded

    def test_portfolio_engine_failure_fails_workflow(self, request_obj, params):
        from tests.unit.investment.workflow.conftest import make_engines
        engines = make_engines()
        engines.portfolio_engine.integrate.side_effect = RuntimeError("portfolio crash")
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-FAIL-P")
        assert not result.succeeded

    def test_errors_recorded_in_result(self, request_obj, params):
        from tests.unit.investment.workflow.conftest import make_engines
        engines = make_engines()
        engines.market_engine.update.side_effect = RuntimeError("explode")
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-ERR")
        assert len(result.run_record.errors) > 0

    def test_retry_success_on_second_attempt(self, request_obj):
        from tests.unit.investment.workflow.conftest import make_engines, _MarketSnap
        engines = make_engines()
        call_count = {"n": 0}
        def flaky(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise RuntimeError("first attempt fails")
            return _MarketSnap()
        engines.market_engine.update.side_effect = flaky
        params = WorkflowParameters(max_retries=2, retry_delay_sec=0.0)
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-RETRY")
        assert result.succeeded
        assert call_count["n"] == 2

    def test_retry_exhausted_fails_workflow(self, request_obj):
        from tests.unit.investment.workflow.conftest import make_engines
        engines = make_engines()
        engines.market_engine.update.side_effect = RuntimeError("always fails")
        params = WorkflowParameters(max_retries=2, retry_delay_sec=0.0)
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-RETRY-FAIL")
        assert not result.succeeded
        assert engines.market_engine.update.call_count == 3  # 1 + 2 retries

    def test_stage_returns_none_fails_workflow(self, request_obj, params):
        from tests.unit.investment.workflow.conftest import make_engines
        engines = make_engines()
        engines.market_engine.update.return_value = None  # stage returns None
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-NONE")
        assert not result.succeeded


# ── Cancellation ──────────────────────────────────────────────────────────────

class TestCancellation:
    def test_cancel_returns_false_when_no_active_run(self, engines, params):
        orch = _orchestrator(engines, params)
        assert orch.cancel() is False

    def test_cancel_after_run_returns_false(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-C")
        # Already terminal — cancel is a no-op
        assert orch.cancel() is False


# ── APIs ─────────────────────────────────────────────────────────────────────

class TestAPIs:
    def test_status_none_before_run(self, engines, params):
        orch = _orchestrator(engines, params)
        assert orch.status() is None

    def test_status_after_run(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-API")
        s = orch.status()
        assert s is not None
        assert "current_stage" in s

    def test_timeline_after_run(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-TL")
        tl = orch.timeline()
        assert isinstance(tl, list)
        assert len(tl) > 0

    def test_current_snapshot_after_run(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-CUR")
        snap = orch.current_snapshot()
        assert snap is not None

    def test_history_after_run(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-HIST")
        recs = orch.history()
        assert len(recs) == 1
        assert isinstance(recs[0], WorkflowRunRecord)

    def test_history_for_portfolio(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-H1")
        orch.run(request_obj, portfolio_id="P-H2")
        assert len(orch.history_for_portfolio("P-H1")) == 1
        assert len(orch.history_for_portfolio("P-H2")) == 1

    def test_statistics_after_run(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-STATS")
        stats = orch.statistics()
        assert isinstance(stats, WorkflowStatisticsSnapshot)
        assert stats.total_runs == 1
        assert stats.total_succeeded == 1

    def test_missing_portfolio_id_raises(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        with pytest.raises(ValueError):
            orch.run(request_obj, portfolio_id="")

    def test_current_stage_after_run(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-ST")
        assert orch.current_stage() == WorkflowStage.PUBLISHED


# ── Events ────────────────────────────────────────────────────────────────────

class TestEvents:
    def test_workflow_started_event_emitted(self, engines, params, request_obj):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        orch = _orchestrator(engines, params, pub=pub)
        orch.run(request_obj, portfolio_id="P-EV")
        types = {e.event_type for e in captured}
        assert PipelineEventType.WORKFLOW_STARTED in types

    def test_stage_started_events_emitted_for_each_stage(self, engines, params, request_obj):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        orch = _orchestrator(engines, params, pub=pub)
        orch.run(request_obj, portfolio_id="P-EV")
        stages = {e.stage for e in captured if e.event_type == PipelineEventType.STAGE_STARTED}
        for s in PIPELINE_STAGES:
            assert s in stages

    def test_stage_completed_events_emitted(self, engines, params, request_obj):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        orch = _orchestrator(engines, params, pub=pub)
        orch.run(request_obj, portfolio_id="P-EV")
        stages = {e.stage for e in captured if e.event_type == PipelineEventType.STAGE_COMPLETED}
        assert WorkflowStage.MARKET in stages

    def test_workflow_completed_event_emitted(self, engines, params, request_obj):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        orch = _orchestrator(engines, params, pub=pub)
        orch.run(request_obj, portfolio_id="P-EV")
        types = {e.event_type for e in captured}
        assert PipelineEventType.WORKFLOW_COMPLETED in types

    def test_snapshot_published_event_emitted(self, engines, params, request_obj):
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        orch = _orchestrator(engines, params, pub=pub)
        orch.run(request_obj, portfolio_id="P-EV")
        types = {e.event_type for e in captured}
        assert PipelineEventType.PORTFOLIO_SNAPSHOT_PUBLISHED in types

    def test_workflow_failed_event_on_error(self, request_obj, params):
        from tests.unit.investment.workflow.conftest import make_engines
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        engines = make_engines()
        engines.market_engine.update.side_effect = RuntimeError("fail")
        orch = _orchestrator(engines, params, pub=pub)
        orch.run(request_obj, portfolio_id="P-FAIL-EV")
        types = {e.event_type for e in captured}
        assert PipelineEventType.WORKFLOW_FAILED in types

    def test_retry_event_emitted_on_retry(self, request_obj):
        from tests.unit.investment.workflow.conftest import make_engines, _MarketSnap
        captured: List[WorkflowEvent] = []
        pub = WorkflowEventPublisher()
        pub.register(lambda e: captured.append(e))
        engines = make_engines()
        call_n = {"n": 0}
        def flaky(*args, **kwargs):
            call_n["n"] += 1
            if call_n["n"] < 2:
                raise RuntimeError("temp")
            return _MarketSnap()
        engines.market_engine.update.side_effect = flaky
        params = WorkflowParameters(max_retries=2, retry_delay_sec=0.0)
        orch   = _orchestrator(engines, params, pub=pub)
        orch.run(request_obj, portfolio_id="P-RETRY-EV")
        types = {e.event_type for e in captured}
        assert PipelineEventType.STAGE_RETRYING in types

    def test_register_and_unregister_callback(self, engines, params, request_obj):
        captured: List[WorkflowEvent] = []
        cb = lambda e: captured.append(e)
        orch = _orchestrator(engines, params)
        orch.register_event_callback(cb)
        orch.run(request_obj, portfolio_id="P-CB1")
        n_after_first = len(captured)
        orch.unregister_event_callback(cb)
        orch.run(request_obj, portfolio_id="P-CB2")
        assert len(captured) == n_after_first  # no new events


# ── Metrics and monitoring ────────────────────────────────────────────────────

class TestMonitoring:
    def test_run_record_duration_positive(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-MON")
        assert result.run_record.total_duration_ms >= 0

    def test_stage_durations_recorded(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-DUR")
        assert len(result.run_record.stage_durations_ms) > 0

    def test_quality_scores_in_run_record(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-Q")
        rr     = result.run_record
        # Market quality should be extracted (0.82 from _MarketSnap)
        assert rr.market_quality is not None
        assert 0.0 <= rr.market_quality <= 1.0

    def test_multiple_runs_statistics(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        for i in range(5):
            req = InvestmentRequest(symbols=["SYM"])
            orch.run(req, portfolio_id=f"P-{i}")
        stats = orch.statistics()
        assert stats.total_runs == 5
        assert stats.success_rate == 1.0

    def test_failed_run_tracked_in_stats(self, request_obj, params):
        from tests.unit.investment.workflow.conftest import make_engines
        engines = make_engines()
        engines.market_engine.update.side_effect = RuntimeError("fail")
        orch = _orchestrator(engines, params)
        orch.run(request_obj, portfolio_id="P-FAIL")
        stats = orch.statistics()
        assert stats.total_failed == 1
        assert stats.success_rate < 1.0


# ── Snapshot propagation ──────────────────────────────────────────────────────

class TestSnapshotPropagation:
    def test_market_snapshot_in_stage_snapshots(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-PROP")
        assert result.stage_snapshots[WorkflowStage.MARKET] is not None

    def test_portfolio_snapshot_matches_engine_output(self, engines, params, request_obj):
        expected_snap = engines.portfolio_engine.integrate.return_value
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-PROP")
        assert result.portfolio_snapshot is expected_snap

    def test_run_record_snapshot_id_matches(self, engines, params, request_obj):
        orch   = _orchestrator(engines, params)
        result = orch.run(request_obj, portfolio_id="P-PROP")
        assert result.run_record.snapshot_id == "prt-snap-001"


# ── InstitutionalInvestmentWorkflow ──────────────────────────────────────────

class TestInstitutionalInvestmentWorkflow:
    def test_workflow_id(self):
        wf = InstitutionalInvestmentWorkflow()
        assert wf.workflow_id == "institutional_investment_pipeline"

    def test_name(self):
        wf = InstitutionalInvestmentWorkflow()
        assert len(wf.name) > 0

    def test_priority_zero(self):
        wf = InstitutionalInvestmentWorkflow()
        assert wf.priority == 0

    def test_execute_returns_analysis(self, engines, params, request_obj):
        from iios.investment.models.investment_context_model import InvestmentContext
        from iios.investment.investment_constants import AssetClass

        request_obj.metadata["portfolio_id"] = "P-WF"
        ctx = InvestmentContext(
            request_id  = request_obj.request_id,
            asset_class = AssetClass.EQUITY,
            symbols     = request_obj.symbols,
        )
        # Patch the orchestrator to use mock engines
        with patch(
            "iios.investment.workflow.institutional_investment_workflow"
            ".InstitutionalWorkflowOrchestrator",
        ) as MockOrch:
            mock_result = MagicMock()
            mock_result.succeeded        = True
            mock_result.portfolio_snapshot = MagicMock()
            mock_result.to_dict.return_value = {"succeeded": True}
            mock_result.run_record.errors = ()
            MockOrch.return_value.run.return_value = mock_result

            wf       = InstitutionalInvestmentWorkflow()
            analysis = wf.execute(request_obj, ctx)

        from iios.investment.investment_constants import AnalysisStatus
        assert analysis.status == AnalysisStatus.COMPLETED
        assert analysis.findings["succeeded"] is True

    def test_to_dict(self):
        wf = InstitutionalInvestmentWorkflow()
        d  = wf.to_dict()
        assert d["workflow_id"] == "institutional_investment_pipeline"


# ── Recovery / checkpoint ─────────────────────────────────────────────────────

class TestRecovery:
    def test_independent_runs_do_not_share_state(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        r1   = orch.run(request_obj, portfolio_id="P-R1")
        r2   = orch.run(request_obj, portfolio_id="P-R2")
        assert r1.workflow_id == r2.workflow_id
        # Different run records
        assert r1.run_record.run_id != r2.run_record.run_id

    def test_history_accumulates_across_runs(self, engines, params, request_obj):
        orch = _orchestrator(engines, params)
        for _ in range(3):
            orch.run(request_obj, portfolio_id="P-ACC")
        assert len(orch.history()) == 3

    def test_failed_run_does_not_corrupt_next_run(self, request_obj, params):
        from tests.unit.investment.workflow.conftest import make_engines, _PortfolioSnap
        engines = make_engines()
        # First run fails at market
        engines.market_engine.update.side_effect = RuntimeError("transient")
        orch = _orchestrator(engines, params)
        r1   = orch.run(request_obj, portfolio_id="P-CORR")
        assert not r1.succeeded

        # Fix engine and run again
        from tests.unit.investment.workflow.conftest import _MarketSnap
        engines.market_engine.update.side_effect = None
        engines.market_engine.update.return_value = _MarketSnap()
        r2 = orch.run(request_obj, portfolio_id="P-CORR")
        assert r2.succeeded
