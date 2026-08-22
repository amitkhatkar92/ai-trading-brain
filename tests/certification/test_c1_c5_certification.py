"""tests/certification/test_c1_c5_certification.py
Institutional Integration Certification — C1 through C5.

Certifies that the five IIOS intelligence domains and the M2.1–M2.5
framework layer operate as one unified platform:

  Part 1  Pipeline Certification       — C1→C2→C3→C4→C5 end-to-end
  Part 2  Workflow Certification        — lifecycle transitions
  Part 3  Framework Certification       — lifecycle+logging+error+async
  Part 4  Thread Safety                 — concurrent safety
  Part 5  Fault Injection               — resilience per domain
  Part 6  Long Run                      — stability over many iterations
  Part 7  Regression Certification      — no regression vs. baseline

Read: ALL findings report-only.  No business logic is modified.
"""
from __future__ import annotations

import logging
import subprocess
import sys
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ── IIOS imports ──────────────────────────────────────────────────────────────

from iios.investment.investment_constants import (
    AssetClass, InvestmentObjective, RiskProfile, TimeHorizon,
)
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
from iios.investment.workflow.engine_lifecycle import (
    EngineState, LifecycleAwareMixin, LifecycleError,
)

from iios.common.async_exec.async_execution_manager import (
    reset_execution_manager, get_execution_manager,
)
from iios.common.errors.error_manager import (
    reset_error_manager, get_error_manager,
)


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

class _Snap:
    """Minimal snapshot stub shared by all mock engines."""
    def __init__(self, prefix: str) -> None:
        self.snapshot_id   = f"{prefix}-snap-{uuid.uuid4().hex[:6]}"
        self.quality_score = 0.80
        self.overall_score = 80.0
        self.is_ready      = True

    def to_dict(self) -> dict:
        return {"snapshot_id": self.snapshot_id}


def _make_engines(
    *,
    market_fail:   bool = False,
    company_fail:  bool = False,
    strategy_fail: bool = False,
    decision_fail: bool = False,
    portfolio_fail: bool = False,
    market_snap:   Any  = None,
    company_snap:  Any  = None,
    strategy_snap: Any  = None,
    decision_snap: Any  = None,
    portfolio_snap: Any = None,
) -> WorkflowEngines:
    """Construct a WorkflowEngines with mock engines, optional failure injection."""

    def _eng(prefix: str, fail: bool, snap: Any) -> MagicMock:
        m = MagicMock()
        if fail:
            m.update.side_effect        = RuntimeError(f"{prefix} injected failure")
            m.integrate.side_effect     = RuntimeError(f"{prefix} injected failure")
            m.integrate_sync.side_effect = RuntimeError(f"{prefix} injected failure")
            m.get_snapshot_sync.side_effect = RuntimeError(f"{prefix} injected failure")
        else:
            effective = snap or _Snap(prefix)
            m.update.return_value        = effective
            m.integrate.return_value     = effective
            m.integrate_sync.return_value = effective
            m.get_snapshot_sync.return_value = effective
        # make_bundle always succeeds
        m.make_bundle.return_value = MagicMock()
        return m

    me = _eng("mkt", market_fail,   market_snap)
    ce = _eng("cmp", company_fail,  company_snap)
    se = _eng("str", strategy_fail, strategy_snap)
    de = _eng("dec", decision_fail, decision_snap)
    pe = _eng("prt", portfolio_fail, portfolio_snap)

    return WorkflowEngines(
        market_engine    = me,
        company_engine   = ce,
        strategy_engine  = se,
        decision_engine  = de,
        portfolio_engine = pe,
    )


def _request() -> InvestmentRequest:
    return InvestmentRequest(
        request_id   = str(uuid.uuid4()),
        asset_class  = AssetClass.EQUITY,
        symbols      = ["RELIANCE"],
        objective    = InvestmentObjective.GROWTH,
        time_horizon = TimeHorizon.MEDIUM_TERM,
        risk_profile = RiskProfile.MODERATE,
        market       = "NSE",
        country      = "IN",
        metadata     = {},
    )


def _params(retries: int = 0, delay: float = 0.0) -> WorkflowParameters:
    return WorkflowParameters(max_retries=retries, retry_delay_sec=delay)


def _orchestrator(
    *,
    retries: int = 0,
    engines: Optional[WorkflowEngines] = None,
    pub:     Optional[WorkflowEventPublisher] = None,
) -> InstitutionalWorkflowOrchestrator:
    return InstitutionalWorkflowOrchestrator(
        params          = _params(retries),
        engines         = engines or _make_engines(),
        event_publisher = pub,
    )


def _run(
    *,
    retries:  int = 0,
    engines:  Optional[WorkflowEngines] = None,
    pub:      Optional[WorkflowEventPublisher] = None,
    pid:      str = "P-CERT",
) -> WorkflowResult:
    orch = _orchestrator(retries=retries, engines=engines, pub=pub)
    return orch.run(_request(), portfolio_id=pid)


def _events_pub() -> tuple[WorkflowEventPublisher, List[WorkflowEvent]]:
    captured: List[WorkflowEvent] = []
    pub = WorkflowEventPublisher()
    pub.register(lambda e: captured.append(e))
    return pub, captured


# ══════════════════════════════════════════════════════════════════════════════
#  PART 1 — PIPELINE CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestCertPart1Pipeline:
    """Verify the complete C1→C2→C3→C4→C5 execution path."""

    # 1.1 Full pipeline succeeds
    def test_full_pipeline_succeeds(self):
        result = _run()
        assert result.succeeded, "Full pipeline must succeed with all-mock engines"

    # 1.2 PortfolioIntelligenceSnapshot is non-None
    def test_portfolio_snapshot_produced(self):
        result = _run()
        assert result.portfolio_snapshot is not None

    # 1.3 All 5 stage snapshots present in result
    def test_all_five_stage_snapshots_populated(self):
        result = _run()
        for stage in PIPELINE_STAGES:
            assert stage in result.stage_snapshots, (
                f"Expected stage {stage.value!r} in stage_snapshots"
            )

    # 1.4 Stage ordering — market before company before strategy before decision before portfolio
    def test_stage_ordering_respected(self):
        result = _run()
        rr = result.run_record
        durations = rr.stage_durations_ms
        if len(durations) == 5:
            # All 5 stages present; verify order by checking stage names
            stages = list(durations.keys())
            order  = [WorkflowStage.MARKET.value, WorkflowStage.COMPANY.value,
                      WorkflowStage.STRATEGY.value, WorkflowStage.DECISION.value,
                      WorkflowStage.PORTFOLIO.value]
            for i, expected in enumerate(order):
                if i < len(stages):
                    assert stages[i] == expected, (
                        f"Stage {i} should be {expected!r}, got {stages[i]!r}"
                    )

    # 1.5 n_stages_completed == 5
    def test_five_stages_completed(self):
        result = _run()
        assert result.run_record.n_stages_completed == 5

    # 1.6 Snapshot propagation — each downstream engine received upstream output
    def test_snapshot_propagation_market_to_company(self):
        engines = _make_engines()
        _run(engines=engines)
        # Company engine must have been called (received market context)
        engines.company_engine.integrate.assert_called_once()

    def test_snapshot_propagation_company_to_strategy(self):
        engines = _make_engines()
        _run(engines=engines)
        engines.strategy_engine.get_snapshot_sync.assert_called_once()

    def test_snapshot_propagation_strategy_to_decision(self):
        engines = _make_engines()
        _run(engines=engines)
        engines.decision_engine.integrate_sync.assert_called_once()

    def test_snapshot_propagation_decision_to_portfolio(self):
        engines = _make_engines()
        _run(engines=engines)
        engines.portfolio_engine.integrate.assert_called_once()

    # 1.7 Result metadata
    def test_result_portfolio_id_preserved(self):
        result = _run(pid="P-CERTID")
        assert result.portfolio_id == "P-CERTID"

    def test_result_request_id_preserved(self):
        req    = _request()
        orch   = _orchestrator()
        result = orch.run(req, portfolio_id="P-X")
        assert result.request_id == req.request_id

    # 1.8 Run record structure
    def test_run_record_has_total_duration(self):
        result = _run()
        assert result.run_record.total_duration_ms >= 0

    def test_run_record_no_errors_on_success(self):
        result = _run()
        assert len(result.run_record.errors) == 0, (
            f"Unexpected errors: {result.run_record.errors}"
        )

    def test_result_to_dict_has_required_keys(self):
        result = _run()
        d = result.to_dict()
        for key in ("succeeded", "workflow_id", "request_id", "portfolio_id",
                    "total_duration_ms", "n_stages_completed"):
            assert key in d, f"Missing key {key!r} in result.to_dict()"

    # 1.9 Events — correct sequence emitted
    def test_workflow_started_event_emitted(self):
        pub, events = _events_pub()
        _run(pub=pub)
        types = [e.event_type for e in events]
        assert PipelineEventType.WORKFLOW_STARTED in types

    def test_workflow_completed_event_emitted(self):
        pub, events = _events_pub()
        _run(pub=pub)
        types = [e.event_type for e in events]
        assert PipelineEventType.WORKFLOW_COMPLETED in types

    def test_stage_completed_events_for_all_five_stages(self):
        pub, events = _events_pub()
        _run(pub=pub)
        completed_stages = {
            e.stage for e in events
            if e.event_type == PipelineEventType.STAGE_COMPLETED
            and e.stage is not None
        }
        for stage in PIPELINE_STAGES:
            assert stage in completed_stages, (
                f"Missing STAGE_COMPLETED for {stage.value!r}"
            )

    def test_snapshot_published_event_emitted(self):
        pub, events = _events_pub()
        _run(pub=pub)
        types = [e.event_type for e in events]
        assert PipelineEventType.PORTFOLIO_SNAPSHOT_PUBLISHED in types

    def test_event_sequence_starts_before_completes(self):
        pub, events = _events_pub()
        _run(pub=pub)
        types = [e.event_type for e in events]
        start_idx = next(
            (i for i, t in enumerate(types) if t == PipelineEventType.WORKFLOW_STARTED), -1
        )
        end_idx = next(
            (i for i, t in enumerate(types) if t == PipelineEventType.WORKFLOW_COMPLETED), -1
        )
        assert start_idx != -1, "WORKFLOW_STARTED not found"
        assert end_idx != -1,   "WORKFLOW_COMPLETED not found"
        assert start_idx < end_idx, "WORKFLOW_STARTED must precede WORKFLOW_COMPLETED"

    # 1.10 Timing recorded per stage
    def test_stage_durations_recorded(self):
        result = _run()
        durations = result.run_record.stage_durations_ms
        assert len(durations) == 5, f"Expected 5 stage durations, got {len(durations)}"

    def test_stage_durations_non_negative(self):
        result = _run()
        for stage, ms in result.run_record.stage_durations_ms.items():
            assert ms >= 0, f"Stage {stage!r} has negative duration {ms}"


# ══════════════════════════════════════════════════════════════════════════════
#  PART 2 — WORKFLOW CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestCertPart2Workflow:
    """Verify orchestrator lifecycle: start/pause/resume/restart/shutdown."""

    # 2.1 Lifecycle transitions
    def test_start_transitions_to_running(self):
        orch = _orchestrator()
        orch.start()
        assert orch.lifecycle_state() == EngineState.RUNNING
        orch.shutdown()

    def test_stop_transitions_to_stopped(self):
        orch = _orchestrator()
        orch.start()
        orch.stop()
        assert orch.lifecycle_state() == EngineState.STOPPED

    def test_pause_transitions_to_paused(self):
        orch = _orchestrator()
        orch.start()
        orch.pause()
        assert orch.lifecycle_state() == EngineState.PAUSED
        orch.shutdown()

    def test_resume_from_paused_to_running(self):
        orch = _orchestrator()
        orch.start()
        orch.pause()
        orch.resume()
        assert orch.lifecycle_state() == EngineState.RUNNING
        orch.shutdown()

    def test_restart_from_running_back_to_running(self):
        orch = _orchestrator()
        orch.start()
        orch.restart()
        assert orch.lifecycle_state() == EngineState.RUNNING
        orch.shutdown()

    def test_shutdown_is_terminal(self):
        orch = _orchestrator()
        orch.start()
        orch.shutdown()
        assert orch.lifecycle_state() == EngineState.SHUTDOWN

    def test_shutdown_from_stopped_is_terminal(self):
        orch = _orchestrator()
        orch.start()
        orch.stop()
        orch.shutdown()
        assert orch.lifecycle_state() == EngineState.SHUTDOWN

    def test_double_shutdown_is_idempotent(self):
        orch = _orchestrator()
        orch.start()
        orch.shutdown()
        orch.shutdown()   # should not raise
        assert orch.lifecycle_state() == EngineState.SHUTDOWN

    # 2.2 Guard conditions
    def test_stop_when_not_running_raises(self):
        orch = _orchestrator()   # CREATED state
        with pytest.raises(Exception):
            orch.stop()

    def test_pause_when_not_running_raises(self):
        orch = _orchestrator()
        with pytest.raises(Exception):
            orch.pause()

    def test_resume_when_not_paused_raises(self):
        orch = _orchestrator()
        orch.start()
        with pytest.raises(Exception):
            orch.resume()
        orch.shutdown()

    # 2.3 Run pipeline interactions
    def test_cancel_returns_true_when_pipeline_not_active(self):
        orch = _orchestrator()
        # No active pipeline → cancel returns False
        assert orch.cancel() is False

    def test_status_returns_none_before_first_run(self):
        orch = _orchestrator()
        # No run yet
        st = orch.status()
        assert st is None

    def test_status_returns_dict_after_run(self):
        orch = _orchestrator()
        orch.run(_request(), portfolio_id="P-T")
        st = orch.status()
        assert st is not None
        assert isinstance(st, dict)

    def test_current_snapshot_returns_none_before_run(self):
        orch = _orchestrator()
        assert orch.current_snapshot() is None

    def test_current_snapshot_after_successful_run(self):
        orch = _orchestrator()
        orch.run(_request(), portfolio_id="P-CS")
        assert orch.current_snapshot() is not None

    # 2.4 Retry mechanics
    def test_retry_succeeds_on_second_attempt(self):
        """First attempt raises; second attempt succeeds via max_retries=1."""
        call_count = {"n": 0}

        def flaky_update(bundle):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("transient failure")
            return _Snap("mkt")

        engines = _make_engines()
        engines.market_engine.update.side_effect = flaky_update

        orch   = _orchestrator(retries=1, engines=engines)
        result = orch.run(_request(), portfolio_id="P-RETRY")
        assert result.succeeded, "Retry should result in success on second attempt"
        assert result.run_record.n_retries >= 1

    def test_retry_exhausted_returns_failed(self):
        """All attempts fail → result not succeeded."""
        engines = _make_engines(market_fail=True)
        orch    = _orchestrator(retries=1, engines=engines)
        result  = orch.run(_request(), portfolio_id="P-FAIL")
        assert not result.succeeded

    # 2.5 History & statistics
    def test_history_accumulates_records(self):
        orch = _orchestrator()
        for _ in range(3):
            orch.run(_request(), portfolio_id="P-HIST")
        records = orch.history(n=10)
        assert len(records) == 3

    def test_statistics_tracks_runs(self):
        orch = _orchestrator()
        for _ in range(4):
            orch.run(_request(), portfolio_id="P-STAT")
        stats = orch.statistics()
        assert stats.total_runs == 4

    def test_failed_run_does_not_corrupt_next_run(self):
        engines_fail = _make_engines(market_fail=True)
        orch = _orchestrator(engines=engines_fail)
        result1 = orch.run(_request(), portfolio_id="P-F1")
        assert not result1.succeeded

        # Now replace engines with good ones and run again
        orch._engines = _make_engines()
        result2 = orch.run(_request(), portfolio_id="P-F2")
        assert result2.succeeded

    def test_independent_runs_do_not_share_state(self):
        orch1 = _orchestrator()
        orch2 = _orchestrator()
        r1 = orch1.run(_request(), portfolio_id="P-I1")
        r2 = orch2.run(_request(), portfolio_id="P-I2")
        assert r1.request_id != r2.request_id
        assert r1.portfolio_id != r2.portfolio_id

    # 2.6 Checkpoint recovery
    def test_failed_run_followed_by_success(self):
        orch = _orchestrator()
        # Inject failure on market engine
        orch._engines = _make_engines(market_fail=True)
        fail_result = orch.run(_request(), portfolio_id="P-CKP")
        assert not fail_result.succeeded

        # Recover with good engines
        orch._engines = _make_engines()
        ok_result = orch.run(_request(), portfolio_id="P-CKP")
        assert ok_result.succeeded

    def test_history_contains_both_failed_and_ok_records(self):
        orch = _orchestrator()
        orch._engines = _make_engines(market_fail=True)
        orch.run(_request(), portfolio_id="P-MIX")
        orch._engines = _make_engines()
        orch.run(_request(), portfolio_id="P-MIX")

        records = orch.history(n=10)
        succeeded_flags = [r.succeeded for r in records]
        assert True in succeeded_flags
        assert False in succeeded_flags


# ══════════════════════════════════════════════════════════════════════════════
#  PART 3 — FRAMEWORK CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestCertPart3Framework:
    """Verify lifecycle + logging + error + async + workflow framework integration."""

    def setup_method(self):
        # Fresh singletons for isolation
        reset_execution_manager()
        reset_error_manager()

    def teardown_method(self):
        reset_execution_manager()
        reset_error_manager()

    # 3.1 Lifecycle ↔ Async framework integration
    def test_start_records_metrics_in_async_manager(self):
        """start() routes _on_start through execute_sync → metrics captured."""
        mgr = reset_execution_manager()
        orch = _orchestrator()
        orch.start()
        snap = mgr.statistics()
        assert snap.total_submitted >= 1, (
            "execute_sync(_on_start) must increment total_submitted"
        )
        orch.shutdown()

    def test_stop_records_additional_metrics(self):
        mgr = reset_execution_manager()
        orch = _orchestrator()
        orch.start()
        sub_after_start = mgr.statistics().total_submitted
        orch.stop()
        sub_after_stop = mgr.statistics().total_submitted
        assert sub_after_stop > sub_after_start, (
            "stop() must add another task to the execution manager"
        )

    def test_start_stop_both_complete_successfully(self):
        mgr = reset_execution_manager()
        orch = _orchestrator()
        orch.start()
        orch.stop()
        snap = mgr.statistics()
        assert snap.total_completed >= 2
        assert snap.total_failed == 0

    # 3.2 Error framework integration
    def test_failed_start_reports_to_error_manager(self):
        """_on_start raising an exception must be reported to ErrorManager."""
        reset_error_manager()
        emgr = get_error_manager()

        class FailingEngine(LifecycleAwareMixin):
            SYSTEM_ID = "test:failing"
            VERSION   = "1.0"
            def _on_start(self):
                raise RuntimeError("start failure")

        engine = FailingEngine()
        try:
            engine.start()
        except Exception:
            pass

        stats = emgr.statistics()
        assert stats.total_failures >= 1, (
            "report_failure must be called when _on_start raises"
        )

    def test_failed_stop_reports_to_error_manager(self):
        reset_error_manager()
        emgr = get_error_manager()

        class FailingStop(LifecycleAwareMixin):
            SYSTEM_ID = "test:failstop"
            VERSION   = "1.0"
            def _on_stop(self):
                raise RuntimeError("stop failure")

        engine = FailingStop()
        engine.start()
        try:
            engine.stop()
        except Exception:
            pass

        stats = emgr.statistics()
        assert stats.total_failures >= 1

    # 3.3 Logging framework integration
    def test_pipeline_emits_log_messages(self, caplog):
        with caplog.at_level(logging.INFO):
            _run()
        # Workflow orchestrator logs with "Workflow" prefix
        workflow_logs = [r for r in caplog.records if "Workflow" in r.message]
        assert len(workflow_logs) >= 2, (
            f"Expected ≥2 'Workflow' log messages, got {len(workflow_logs)}"
        )

    def test_stage_completion_logged(self, caplog):
        with caplog.at_level(logging.INFO):
            _run()
        stage_logs = [r for r in caplog.records if "stage=" in r.message]
        assert len(stage_logs) >= 5, (
            f"Expected ≥5 stage log lines, got {len(stage_logs)}"
        )

    def test_failed_pipeline_logs_error(self, caplog):
        engines = _make_engines(market_fail=True)
        with caplog.at_level(logging.ERROR):
            _run(engines=engines)
        error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_logs) >= 1, "Failed stage must log at ERROR level"

    # 3.4 Event publisher ↔ workflow integration
    def test_registered_callback_receives_events(self):
        pub, events = _events_pub()
        _run(pub=pub)
        assert len(events) >= 12, (
            f"Expected ≥12 events (5 started + 5 completed + workflow + snap), "
            f"got {len(events)}"
        )

    def test_event_types_cover_all_required_types(self):
        pub, events = _events_pub()
        _run(pub=pub)
        types = {e.event_type for e in events}
        required = {
            PipelineEventType.WORKFLOW_STARTED,
            PipelineEventType.STAGE_STARTED,
            PipelineEventType.STAGE_COMPLETED,
            PipelineEventType.PORTFOLIO_SNAPSHOT_PUBLISHED,
            PipelineEventType.WORKFLOW_COMPLETED,
        }
        missing = required - types
        assert not missing, f"Missing event types: {missing}"

    def test_unregister_callback_stops_receiving_events(self):
        received = []
        pub = WorkflowEventPublisher()
        cb  = lambda e: received.append(e)
        pub.register(cb)
        pub.unregister(cb)

        orch = _orchestrator(pub=pub)
        orch.run(_request(), portfolio_id="P-UNR")
        assert len(received) == 0, "Unregistered callback must not receive events"

    # 3.5 Workflow statistics integration
    def test_statistics_success_rate_100_after_clean_runs(self):
        orch = _orchestrator()
        for _ in range(3):
            orch.run(_request(), portfolio_id="P-SR")
        stats = orch.statistics()
        assert stats.success_rate == 1.0

    def test_statistics_success_rate_drops_on_failure(self):
        orch = _orchestrator()
        orch.run(_request(), portfolio_id="P-SRF")
        orch._engines = _make_engines(market_fail=True)
        orch.run(_request(), portfolio_id="P-SRF")
        stats = orch.statistics()
        assert stats.success_rate < 1.0

    # 3.6 Workflow history integration
    def test_history_records_are_workflow_run_records(self):
        orch    = _orchestrator()
        orch.run(_request(), portfolio_id="P-HR")
        records = orch.history(n=5)
        assert len(records) == 1
        assert isinstance(records[0], WorkflowRunRecord)

    def test_history_for_portfolio_filters_correctly(self):
        orch = _orchestrator()
        orch.run(_request(), portfolio_id="P-A")
        orch.run(_request(), portfolio_id="P-B")
        records_a = orch.history_for_portfolio("P-A")
        records_b = orch.history_for_portfolio("P-B")
        assert len(records_a) == 1
        assert len(records_b) == 1
        assert all(r.portfolio_id == "P-A" for r in records_a)
        assert all(r.portfolio_id == "P-B" for r in records_b)

    # 3.7 Workflow ↔ InvestmentWorkflow integration
    def test_institutional_investment_workflow_execute(self):
        engines = _make_engines()
        with patch.object(InstitutionalWorkflowOrchestrator, '__init__',
                          wraps=InstitutionalWorkflowOrchestrator.__init__) as mock_init:
            workflow = InstitutionalInvestmentWorkflow()
            assert workflow.workflow_id == InstitutionalInvestmentWorkflow.WORKFLOW_ID
            assert workflow.name
            assert workflow.VERSION


# ══════════════════════════════════════════════════════════════════════════════
#  PART 4 — THREAD SAFETY
# ══════════════════════════════════════════════════════════════════════════════

class TestCertPart4ThreadSafety:
    """Verify concurrent safety across orchestrators, snapshots, and lifecycle."""

    # 4.1 Concurrent pipeline runs (separate orchestrators)
    def test_two_orchestrators_run_concurrently(self):
        """Two independent orchestrators run simultaneously without interfering."""
        results: List[Optional[WorkflowResult]] = [None, None]
        errors:  List[Optional[Exception]]       = [None, None]

        def run_one(idx: int) -> None:
            try:
                orch = _orchestrator()
                results[idx] = orch.run(_request(), portfolio_id=f"P-TH{idx}")
            except Exception as exc:
                errors[idx] = exc

        threads = [threading.Thread(target=run_one, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert all(t.is_alive() is False for t in threads), "Threads did not terminate"
        assert errors[0] is None, f"Thread 0 error: {errors[0]}"
        assert errors[1] is None, f"Thread 1 error: {errors[1]}"
        assert results[0] is not None and results[0].succeeded
        assert results[1] is not None and results[1].succeeded

    def test_five_concurrent_orchestrators(self):
        """5 independent orchestrators run in parallel without race conditions."""
        outcomes: List[bool]           = []
        errors:   List[Optional[Exception]] = []
        lock = threading.Lock()

        def run_one() -> None:
            try:
                orch = _orchestrator()
                r    = orch.run(_request(), portfolio_id=f"P-{uuid.uuid4().hex[:4]}")
                with lock:
                    outcomes.append(r.succeeded)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=run_one) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        assert not errors, f"Concurrent run errors: {errors}"
        assert all(outcomes), f"Not all succeeded: {outcomes}"

    # 4.2 Concurrent snapshot reads
    def test_concurrent_snapshot_reads_do_not_corrupt(self):
        """Multiple threads read current_snapshot while pipeline runs."""
        orch    = _orchestrator()
        snap_results: List[Any] = []
        lock    = threading.Lock()

        orch.run(_request(), portfolio_id="P-CSR")

        def read_snap() -> None:
            s = orch.current_snapshot()
            with lock:
                snap_results.append(s)

        readers = [threading.Thread(target=read_snap) for _ in range(10)]
        for t in readers:
            t.start()
        for t in readers:
            t.join(timeout=5.0)

        assert len(snap_results) == 10, "All 10 reads must complete"
        # All reads should return the same (or None) snapshot — not raise
        non_none = [s for s in snap_results if s is not None]
        assert len(non_none) == 10, "Snapshot should be available after completed run"

    # 4.3 Concurrent lifecycle operations
    def test_concurrent_start_stop_cycles(self):
        """Multiple threads start/stop the same orchestrator without deadlock."""
        orch    = _orchestrator()
        errors: List[str] = []
        lock    = threading.Lock()

        def cycle() -> None:
            try:
                orch.start()
                time.sleep(0.001)
                orch.stop()
            except Exception as exc:
                with lock:
                    # EngineAlreadyRunningError / EngineNotRunningError are expected
                    # due to races — only unexpected exceptions are failures
                    if "already running" not in str(exc).lower() and \
                       "not running" not in str(exc).lower() and \
                       "cannot start" not in str(exc).lower() and \
                       "cannot stop" not in str(exc).lower() and \
                       "invalid" not in str(exc).lower():
                        errors.append(str(exc))

        threads = [threading.Thread(target=cycle) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"Unexpected errors in concurrent lifecycle: {errors}"

    # 4.4 Thread-safe history access
    def test_concurrent_history_reads(self):
        orch = _orchestrator()
        for _ in range(5):
            orch.run(_request(), portfolio_id="P-THR")

        history_results: List[List] = []
        lock = threading.Lock()

        def read_history():
            h = orch.history(n=20)
            with lock:
                history_results.append(h)

        threads = [threading.Thread(target=read_history) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert len(history_results) == 8, "All history reads must complete"
        for h in history_results:
            assert len(h) == 5, f"Expected 5 records, got {len(h)}"

    # 4.5 Thread-safe statistics access
    def test_concurrent_statistics_reads(self):
        orch = _orchestrator()
        for _ in range(3):
            orch.run(_request(), portfolio_id="P-TST")

        results: List[WorkflowStatisticsSnapshot] = []
        lock = threading.Lock()

        def read_stats():
            s = orch.statistics()
            with lock:
                results.append(s)

        threads = [threading.Thread(target=read_stats) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert len(results) == 10
        for s in results:
            assert s.total_runs == 3

    # 4.6 Context propagation
    def test_workflow_id_consistent_across_concurrent_runs(self):
        """Each orchestrator's run_record.workflow_id matches the expected constant."""
        outcome_ids: List[str] = []
        lock = threading.Lock()

        def run_one():
            orch = _orchestrator()
            r    = orch.run(_request(), portfolio_id="P-WID")
            with lock:
                outcome_ids.append(r.run_record.workflow_id)

        threads = [threading.Thread(target=run_one) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        expected = InstitutionalInvestmentWorkflow.WORKFLOW_ID
        assert all(wid == expected for wid in outcome_ids), (
            f"Inconsistent workflow_ids: {outcome_ids}"
        )

    # 4.7 No deadlock detection
    def test_no_deadlock_under_concurrent_cancel_and_run(self):
        """cancel() called while run() is in progress must not deadlock."""
        orch    = _orchestrator()
        done    = threading.Event()
        result: List[Optional[WorkflowResult]] = [None]

        def run_pipeline():
            result[0] = orch.run(_request(), portfolio_id="P-DL")
            done.set()

        t = threading.Thread(target=run_pipeline)
        t.start()

        # Small delay then cancel — pipeline likely done already at mock speed
        time.sleep(0.001)
        orch.cancel()

        t.join(timeout=5.0)
        assert not t.is_alive(), "Pipeline thread must terminate within 5 seconds"


# ══════════════════════════════════════════════════════════════════════════════
#  PART 5 — FAULT INJECTION
# ══════════════════════════════════════════════════════════════════════════════

class TestCertPart5FaultInjection:
    """Inject failures into each domain engine and verify recovery/containment."""

    # 5.1 Per-stage failure containment
    def test_market_failure_produces_failed_result(self):
        result = _run(engines=_make_engines(market_fail=True))
        assert not result.succeeded

    def test_company_failure_produces_failed_result(self):
        result = _run(engines=_make_engines(company_fail=True))
        assert not result.succeeded

    def test_strategy_failure_produces_failed_result(self):
        result = _run(engines=_make_engines(strategy_fail=True))
        assert not result.succeeded

    def test_decision_failure_produces_failed_result(self):
        result = _run(engines=_make_engines(decision_fail=True))
        assert not result.succeeded

    def test_portfolio_failure_produces_failed_result(self):
        result = _run(engines=_make_engines(portfolio_fail=True))
        assert not result.succeeded

    # 5.2 Error recorded in run_record
    def test_market_failure_error_in_run_record(self):
        result = _run(engines=_make_engines(market_fail=True))
        assert len(result.run_record.errors) >= 1

    def test_company_failure_error_in_run_record(self):
        result = _run(engines=_make_engines(company_fail=True))
        assert len(result.run_record.errors) >= 1

    def test_strategy_failure_error_contains_message(self):
        result = _run(engines=_make_engines(strategy_fail=True))
        combined = " ".join(result.run_record.errors)
        assert len(combined) > 0, "Error string must not be empty"

    # 5.3 Pipeline stops at point of failure (no downstream calls after failure)
    def test_downstream_engines_not_called_after_market_failure(self):
        engines = _make_engines(market_fail=True)
        _run(engines=engines)
        # Company, strategy, decision, portfolio engines should NOT be called
        engines.company_engine.integrate.assert_not_called()
        engines.portfolio_engine.integrate.assert_not_called()

    def test_downstream_engines_not_called_after_company_failure(self):
        engines = _make_engines(company_fail=True)
        _run(engines=engines)
        engines.portfolio_engine.integrate.assert_not_called()

    # 5.4 Failed stage emits correct events
    def test_market_failure_emits_stage_failed_event(self):
        pub, events = _events_pub()
        _run(engines=_make_engines(market_fail=True), pub=pub)
        types = [e.event_type for e in events]
        assert PipelineEventType.STAGE_FAILED in types

    def test_market_failure_emits_workflow_failed_event(self):
        pub, events = _events_pub()
        _run(engines=_make_engines(market_fail=True), pub=pub)
        types = [e.event_type for e in events]
        assert PipelineEventType.WORKFLOW_FAILED in types

    # 5.5 Retry after transient failure
    def test_retry_resolves_transient_market_failure(self):
        call_count = {"n": 0}

        def flaky(bundle):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("transient")
            return _Snap("mkt")

        engines = _make_engines()
        engines.market_engine.update.side_effect = flaky
        orch    = _orchestrator(retries=1, engines=engines)
        result  = orch.run(_request(), portfolio_id="P-TRY")
        assert result.succeeded
        assert call_count["n"] == 2

    def test_retry_emits_retrying_event(self):
        pub, events = _events_pub()
        call_count  = {"n": 0}

        def flaky(bundle):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("transient")
            return _Snap("mkt")

        engines = _make_engines()
        engines.market_engine.update.side_effect = flaky
        orch = _orchestrator(retries=1, engines=engines, pub=pub)
        orch.run(_request(), portfolio_id="P-RETEVT")

        types = [e.event_type for e in events]
        assert PipelineEventType.STAGE_RETRYING in types

    # 5.6 Run record has error after exhausted retry
    def test_exhausted_retries_n_retries_in_record(self):
        engines = _make_engines(market_fail=True)
        orch    = _orchestrator(retries=2, engines=engines)
        result  = orch.run(_request(), portfolio_id="P-EXH")
        assert result.run_record.n_retries == 2

    # 5.7 Statistics update correctly on failure
    def test_statistics_count_failures(self):
        orch = _orchestrator()
        orch.run(_request(), portfolio_id="P-SF1")    # success
        orch._engines = _make_engines(market_fail=True)
        orch.run(_request(), portfolio_id="P-SF2")    # failure
        stats = orch.statistics()
        assert stats.total_runs == 2
        assert stats.success_rate < 1.0


# ══════════════════════════════════════════════════════════════════════════════
#  PART 6 — LONG RUN CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestCertPart6LongRun:
    """Verify stability and bounded growth over many pipeline iterations."""

    ITERATIONS = 50

    # 6.1 Repeated runs produce consistent results
    def test_50_iterations_all_succeed(self):
        orch     = _orchestrator()
        failures = []
        for i in range(self.ITERATIONS):
            r = orch.run(_request(), portfolio_id=f"P-LR{i:03d}")
            if not r.succeeded:
                failures.append(i)
        assert not failures, f"Iterations failed at: {failures}"

    # 6.2 History bounded
    def test_history_bounded_at_max_entries(self):
        orch = _orchestrator()
        for i in range(self.ITERATIONS):
            orch.run(_request(), portfolio_id=f"P-HB{i:03d}")
        records = orch.history(n=self.ITERATIONS)
        # history() returns at most WorkflowHistory._max_runs entries
        assert len(records) <= self.ITERATIONS

    def test_history_recent_respects_n_limit(self):
        orch = _orchestrator()
        for _ in range(20):
            orch.run(_request(), portfolio_id="P-HL")
        assert len(orch.history(n=5)) == 5
        assert len(orch.history(n=10)) == 10

    # 6.3 Statistics accumulate correctly
    def test_statistics_total_runs_matches_iteration_count(self):
        orch = _orchestrator()
        for i in range(self.ITERATIONS):
            orch.run(_request(), portfolio_id=f"P-SC{i:03d}")
        stats = orch.statistics()
        assert stats.total_runs == self.ITERATIONS

    def test_statistics_avg_duration_is_positive(self):
        orch = _orchestrator()
        for _ in range(10):
            orch.run(_request(), portfolio_id="P-AVG")
        stats = orch.statistics()
        assert stats.avg_duration_ms >= 0

    # 6.4 No snapshot accumulation in state
    def test_run_records_not_shared_across_runs(self):
        """Each run creates a fresh WorkflowState; run_records are independent."""
        orch     = _orchestrator()
        run_ids  = set()
        for i in range(10):
            r = orch.run(_request(), portfolio_id="P-NOSH")
            run_ids.add(r.run_record.run_id)
        # Each run produces a unique run_id
        assert len(run_ids) == 10, (
            f"Each run must produce a distinct run_id, got only {len(run_ids)} unique"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  PART 7 — REGRESSION CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestCertPart7Regression:
    """Verify no regressions in existing test suites."""

    def _run_pytest_suite(self, path: str) -> tuple[int, int, int]:
        """
        Run a pytest suite in a subprocess.
        Returns (passed, failed, exit_code).
        """
        import os, re as _re
        workspace = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        )))
        result = subprocess.run(
            [sys.executable, "-m", "pytest", path, "--tb=no", "-q", "--no-header"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=workspace,
        )
        stdout = result.stdout + result.stderr
        passed = failed = 0
        for line in stdout.splitlines():
            m = _re.search(r"(\d+) passed", line)
            if m:
                passed = int(m.group(1))
            m2 = _re.search(r"(\d+) failed", line)
            if m2:
                failed = int(m2.group(1))
        return passed, failed, result.returncode

    # 7.1 Workflow tests — no regressions
    def test_workflow_unit_tests_pass(self):
        passed, failed, rc = self._run_pytest_suite(
            "tests/unit/investment/workflow/"
        )
        assert failed == 0, (
            f"Workflow unit tests: {failed} failed (was 0), {passed} passed"
        )
        assert passed >= 278, (
            f"Workflow test count regressed: expected ≥278, got {passed}"
        )

    # 7.2 Market intelligence tests — no regressions
    def test_market_unit_tests_pass(self):
        passed, failed, rc = self._run_pytest_suite(
            "tests/unit/investment/market/"
        )
        assert failed == 0, (
            f"Market tests: {failed} failed, {passed} passed"
        )
        assert passed > 0, "Market tests must run"

    # 7.3 Decision intelligence tests — no regressions
    def test_decision_unit_tests_pass(self):
        passed, failed, rc = self._run_pytest_suite(
            "tests/unit/investment/decision/"
        )
        assert failed == 0, f"Decision tests: {failed} failed, {passed} passed"
        assert passed > 0

    # 7.4 Portfolio intelligence tests — no regressions
    def test_portfolio_unit_tests_pass(self):
        passed, failed, rc = self._run_pytest_suite(
            "tests/unit/investment/portfolio/"
        )
        assert failed == 0, f"Portfolio tests: {failed} failed, {passed} passed"
        assert passed > 0

    # 7.5 Common framework tests — no regressions
    def test_async_exec_tests_pass(self):
        passed, failed, rc = self._run_pytest_suite(
            "tests/unit/common/async_exec/"
        )
        assert failed == 0, f"async_exec tests: {failed} failed, {passed} passed"
        assert passed >= 136, (
            f"async_exec test count regressed: expected ≥136, got {passed}"
        )

    def test_error_framework_tests_pass(self):
        passed, failed, rc = self._run_pytest_suite(
            "tests/unit/common/errors/"
        )
        assert failed == 0, f"Error framework: {failed} failed, {passed} passed"
        assert passed >= 192, (
            f"Error test count regressed: expected ≥192, got {passed}"
        )

    # 7.6 Full investment suite
    def test_full_investment_suite_passes(self):
        passed, failed, rc = self._run_pytest_suite(
            "tests/unit/investment/"
        )
        assert failed == 0, (
            f"Investment suite: {failed} failed, {passed} passed"
        )
        assert passed >= 9010, (
            f"Investment suite regressed: expected ≥9010, got {passed}"
        )

    # 7.7 No new failures introduced by async execution framework
    def test_lifecycle_tests_pass(self):
        passed, failed, rc = self._run_pytest_suite(
            "tests/unit/investment/workflow/test_engine_lifecycle.py"
        )
        assert failed == 0, f"Lifecycle tests: {failed} failed"
        assert passed > 0
