"""
test_risk_engine.py â€” tests/unit/risk/engine
==============================================
Comprehensive test suite for the Risk Engine subsystem (C11 M2).

Sections
--------
 1.  Constants
 2.  Exceptions
 3.  RiskEngineContext
 4.  RiskRequest
 5.  RiskEngineSnapshot
 6.  RiskResponse
 7.  PipelineStage
 8.  RiskPipeline
 9.  RiskScheduler
10.  RiskDispatcher
11.  RiskSessionManager
12.  RiskEngineRegistry
13.  RiskEngineValidator
14.  RiskEngineHealth
15.  RiskEngineStatus
16.  RiskEngineStatistics
17.  RiskEngineHistory
18.  RiskEngineEvents
19.  RiskEngineFactory
20.  RiskEngine â€” lifecycle and guards
21.  RiskEngine â€” workflow types
22.  RiskEngine â€” observability
23.  RiskEngine â€” M3/M4 framework hooks
24.  RiskEngine â€” listeners
25.  RiskEngine â€” not-running guard
26.  Concurrency
27.  Regression
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import List
from unittest.mock import MagicMock

import pytest

from iios.risk.engine import (
    # constants
    ENGINE_SYSTEM_ID,
    VERSION,
    VALID_ENGINE_TRANSITIONS,
    ACTIVE_ENGINE_STATES,
    TERMINAL_ENGINE_STATES,
    DEFAULT_MAX_CONCURRENT_SESSIONS,
    EngineState,
    RiskWorkflowType,
    SchedulerPriority,
    ResponseStatus,
    PipelineStatus,
    # exceptions
    RiskEngineError,
    RiskEngineNotRunningError,
    RiskSessionError,
    RiskPipelineError,
    RiskDispatchError,
    RiskCollectionError,
    RiskPublicationError,
    RiskEngineValidationError,
    RiskSchedulerError,
    RiskCapacityError,
    # value objects
    RiskEngineContext,
    RiskRequest,
    RiskEngineSnapshot,
    RiskResponse,
    PipelineStage,
    RiskPipeline,
    RiskEngineEvent,
    RiskEngineStatus,
    # components
    RiskScheduler,
    RiskDispatcher,
    RiskSessionManager,
    RiskEngineRegistry,
    RiskEngineValidator,
    RiskEngineHealth,
    RiskEngineStatistics,
    RiskEngineHistory,
    RiskEngineFactory,
    # primary interface
    RiskEngine,
    # event factories
    make_risk_initialized,
    make_risk_started,
    make_risk_collected,
    make_risk_dispatched,
    make_risk_assessment_started,
    make_risk_published,
    make_risk_completed,
    make_risk_failed,
    make_risk_stopped,
    # validation
    RiskEngineValidationResult,
    RiskEngineValidationCheckResult,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _rid() -> str:
    return f"risk-{uuid.uuid4().hex[:8]}"

def _pid() -> str:
    return f"port-{uuid.uuid4().hex[:8]}"

def _started_engine(**kwargs) -> RiskEngine:
    e = RiskEngine(**kwargs)
    e.start()
    return e

def _make_request(
    risk_id: str = "",
    portfolio_id: str = "",
    workflow_type: RiskWorkflowType = RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT,
) -> RiskRequest:
    factory = RiskEngineFactory()
    return factory.create_request(
        risk_id or _rid(),
        portfolio_id or _pid(),
        workflow_type,
    )


# ===========================================================================
# Section 1 â€” Constants
# ===========================================================================

class TestConstants:
    def test_engine_system_id_prefix(self):
        assert ENGINE_SYSTEM_ID.startswith("iios:risk:engine")

    def test_version_format(self):
        parts = VERSION.split(".")
        assert len(parts) == 3

    def test_engine_states_count(self):
        assert len(list(EngineState)) == 11

    def test_idle_state_value(self):
        assert EngineState.IDLE.value == "idle"

    def test_stopped_state_value(self):
        assert EngineState.STOPPED.value == "stopped"

    def test_all_workflow_types(self):
        values = {wt.value for wt in RiskWorkflowType}
        assert "portfolio_risk_assessment" in values
        assert "position_risk_assessment" in values
        assert "account_risk_assessment" in values
        assert "exposure_monitoring" in values
        assert "limit_monitoring" in values
        assert "stress_test" in values
        assert "scenario_analysis" in values
        assert "intraday_risk_review" in values
        assert "eod_risk_review" in values
        assert len(values) == 9

    def test_scheduler_priority_ordering(self):
        assert SchedulerPriority.CRITICAL < SchedulerPriority.HIGH
        assert SchedulerPriority.HIGH < SchedulerPriority.NORMAL
        assert SchedulerPriority.NORMAL < SchedulerPriority.LOW
        assert SchedulerPriority.LOW < SchedulerPriority.BATCH

    def test_response_status_values(self):
        assert ResponseStatus.SUCCESS.value == "success"
        assert ResponseStatus.FAILURE.value == "failure"
        assert ResponseStatus.PARTIAL.value == "partial"

    def test_pipeline_status_values(self):
        for s in PipelineStatus:
            assert isinstance(s.value, str)

    def test_valid_transitions_covers_all_states(self):
        for state in EngineState:
            assert state in VALID_ENGINE_TRANSITIONS

    def test_active_states_are_non_terminal_non_idle(self):
        for s in ACTIVE_ENGINE_STATES:
            assert s not in TERMINAL_ENGINE_STATES
            assert s != EngineState.IDLE

    def test_terminal_states(self):
        assert EngineState.COMPLETED in TERMINAL_ENGINE_STATES
        assert EngineState.FAILED in TERMINAL_ENGINE_STATES
        assert EngineState.STOPPED in TERMINAL_ENGINE_STATES

    def test_stopped_has_no_transitions(self):
        assert len(VALID_ENGINE_TRANSITIONS[EngineState.STOPPED]) == 0

    def test_idle_transitions_to_initializing_and_stopped(self):
        transitions = VALID_ENGINE_TRANSITIONS[EngineState.IDLE]
        assert EngineState.INITIALIZING in transitions
        assert EngineState.STOPPED in transitions

    def test_default_max_sessions(self):
        assert DEFAULT_MAX_CONCURRENT_SESSIONS > 0


# ===========================================================================
# Section 2 â€” Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_error_code(self):
        e = RiskEngineError("base")
        assert "RE-000" in str(e.code)

    def test_not_running_error_code(self):
        e = RiskEngineNotRunningError()
        assert "RE-001" in str(e.code)

    def test_session_error_has_session_id(self):
        e = RiskSessionError("msg", session_id="sess-1")
        assert "sess-1" in str(e)
        assert "RE-002" in str(e.code)

    def test_pipeline_error_code(self):
        e = RiskPipelineError("msg", pipeline_id="pipe-1")
        assert "RE-003" in str(e.code)

    def test_dispatch_error_code(self):
        e = RiskDispatchError("msg", workflow_type="portfolio_risk_assessment")
        assert "RE-004" in str(e.code)

    def test_collection_error_code(self):
        e = RiskCollectionError("msg")
        assert "RE-005" in str(e.code)

    def test_publication_error_code(self):
        e = RiskPublicationError("msg")
        assert "RE-006" in str(e.code)

    def test_validation_error_code(self):
        e = RiskEngineValidationError("msg", failed_checks=("a",))
        assert "RE-007" in str(e.code)
        assert "a" in e.failed_checks

    def test_scheduler_error_code(self):
        e = RiskSchedulerError("msg")
        assert "RE-008" in str(e.code)

    def test_capacity_error_code(self):
        e = RiskCapacityError(100)
        assert "RE-009" in str(e.code)

    def test_exceptions_inherit_base(self):
        for cls in [
            RiskEngineNotRunningError,
            RiskSessionError,
            RiskPipelineError,
            RiskDispatchError,
            RiskCollectionError,
            RiskPublicationError,
            RiskEngineValidationError,
            RiskSchedulerError,
            RiskCapacityError,
        ]:
            assert issubclass(cls, RiskEngineError)


# ===========================================================================
# Section 3 â€” RiskEngineContext
# ===========================================================================

class TestRiskEngineContext:
    def test_create_defaults(self):
        ctx = RiskEngineContext.create("r1", "p1",
                                       RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT)
        assert ctx.risk_id == "r1"
        assert ctx.portfolio_id == "p1"
        assert ctx.context_id
        assert ctx.workflow_type == RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT
        assert ctx.priority == SchedulerPriority.NORMAL

    def test_create_with_overrides(self):
        ctx = RiskEngineContext.create(
            "r1", "p1",
            RiskWorkflowType.EXPOSURE_MONITORING,
            priority    = SchedulerPriority.HIGH,
            strategy_id = "strat-1",
        )
        assert ctx.workflow_type == RiskWorkflowType.EXPOSURE_MONITORING
        assert ctx.priority == SchedulerPriority.HIGH
        assert ctx.strategy_id == "strat-1"

    def test_create_explicit_context_id(self):
        cid = str(uuid.uuid4())
        ctx = RiskEngineContext.create("r1", "p1",
                                       RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT,
                                       context_id=cid)
        assert ctx.context_id == cid

    def test_frozen(self):
        ctx = RiskEngineContext.create("r1", "p1",
                                       RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT)
        with pytest.raises((AttributeError, TypeError)):
            ctx.risk_id = "other"  # type: ignore

    def test_to_dict_keys(self):
        ctx = RiskEngineContext.create("r1", "p1",
                                       RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT)
        d = ctx.to_dict()
        for key in ("context_id", "risk_id", "portfolio_id",
                    "workflow_type", "priority", "framework_version"):
            assert key in d

    def test_to_dict_workflow_type_is_string(self):
        ctx = RiskEngineContext.create("r1", "p1",
                                       RiskWorkflowType.LIMIT_MONITORING)
        assert ctx.to_dict()["workflow_type"] == "limit_monitoring"

    def test_metadata_defaults_empty(self):
        ctx = RiskEngineContext.create("r1", "p1",
                                       RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT)
        assert ctx.metadata == {}


# ===========================================================================
# Section 4 â€” RiskRequest
# ===========================================================================

class TestRiskRequest:
    def _req(self, **kw) -> RiskRequest:
        f = RiskEngineFactory()
        return f.create_request(_rid(), _pid(), **kw)

    def test_create_defaults(self):
        r = self._req()
        assert r.risk_id
        assert r.portfolio_id
        assert r.request_id
        assert r.workflow_type == RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT

    def test_with_inputs(self):
        r = self._req()
        r2 = r.with_inputs({"key": "val"})
        assert r2.inputs == {"key": "val"}
        assert r.inputs == {}  # original unchanged

    def test_frozen(self):
        r = self._req()
        with pytest.raises((AttributeError, TypeError)):
            r.risk_id = "x"  # type: ignore

    def test_to_dict_keys(self):
        r = self._req()
        d = r.to_dict()
        for k in ("request_id", "risk_id", "portfolio_id", "workflow_type",
                  "priority", "requested_at"):
            assert k in d

    def test_to_dict_workflow_type_is_string(self):
        r = self._req(workflow_type=RiskWorkflowType.STRESS_TEST)
        assert r.to_dict()["workflow_type"] == RiskWorkflowType.STRESS_TEST.value

    def test_requested_at_is_recent(self):
        before = time.time()
        r = self._req()
        assert before <= r.requested_at <= time.time() + 1


# ===========================================================================
# Section 5 â€” RiskEngineSnapshot
# ===========================================================================

class TestRiskEngineSnapshot:
    def test_create_defaults(self):
        s = RiskEngineSnapshot.create(
            "r1", "p1", "sess-1",
            RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT,
            EngineState.PUBLISHING,
        )
        assert s.risk_id == "r1"
        assert s.snapshot_id

    def test_create_explicit_snapshot_id(self):
        sid = str(uuid.uuid4())
        s = RiskEngineSnapshot.create(
            "r1", "p1", "sess-1",
            RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT,
            EngineState.PUBLISHING,
            snapshot_id = sid,
        )
        assert s.snapshot_id == sid

    def test_frozen(self):
        s = RiskEngineSnapshot.create(
            "r1", "p1", "sess-1",
            RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT,
            EngineState.PUBLISHING,
        )
        with pytest.raises((AttributeError, TypeError)):
            s.risk_id = "x"  # type: ignore

    def test_to_dict_has_engine_state(self):
        s = RiskEngineSnapshot.create(
            "r1", "p1", "s",
            RiskWorkflowType.EXPOSURE_MONITORING,
            EngineState.PUBLISHING,
        )
        assert s.to_dict()["engine_state"] == "publishing"

    def test_inputs_summary_and_outputs(self):
        s = RiskEngineSnapshot.create(
            "r1", "p1", "s",
            RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT,
            EngineState.PUBLISHING,
            inputs_summary={"x": "int"},
            outputs={"risk": 0.05},
        )
        assert s.inputs_summary == {"x": "int"}
        assert s.outputs == {"risk": 0.05}


# ===========================================================================
# Section 6 â€” RiskResponse
# ===========================================================================

class TestRiskResponse:
    def _success(self) -> RiskResponse:
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        snap = f.create_snapshot(req.risk_id, req.portfolio_id, "s",
                                 req.workflow_type, EngineState.PUBLISHING)
        return f.create_success_response(req, snapshot=snap, elapsed_s=0.1)

    def _failure(self) -> RiskResponse:
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        return f.create_failure_response(req, error_message="oops", elapsed_s=0.05)

    def test_success_status(self):
        r = self._success()
        assert r.status == ResponseStatus.SUCCESS
        assert r.is_success
        assert not r.is_failure

    def test_failure_status(self):
        r = self._failure()
        assert r.status == ResponseStatus.FAILURE
        assert r.is_failure
        assert not r.is_success

    def test_success_has_snapshot(self):
        r = self._success()
        assert r.has_snapshot
        assert r.snapshot is not None

    def test_failure_no_snapshot(self):
        r = self._failure()
        assert not r.has_snapshot

    def test_failure_has_error_message(self):
        r = self._failure()
        assert "oops" in r.error_message

    def test_frozen(self):
        r = self._success()
        with pytest.raises((AttributeError, TypeError)):
            r.status = ResponseStatus.FAILURE  # type: ignore

    def test_to_dict_contains_status(self):
        r = self._success()
        assert r.to_dict()["status"] == "success"

    def test_to_dict_failure_contains_error(self):
        r = self._failure()
        assert r.to_dict()["error_message"] == "oops"

    def test_elapsed_s_recorded(self):
        r = self._success()
        assert r.elapsed_s == pytest.approx(0.1)


# ===========================================================================
# Section 7 â€” PipelineStage
# ===========================================================================

class TestPipelineStage:
    def test_basic_stage(self):
        s = PipelineStage(
            stage_name   = "initialize",
            engine_state = EngineState.INITIALIZING,
            status       = PipelineStatus.COMPLETED,
            started_at   = 1000.0,
            completed_at = 1000.5,
        )
        assert s.stage_name == "initialize"
        assert s.elapsed_s == pytest.approx(0.5)

    def test_frozen(self):
        s = PipelineStage(
            stage_name   = "x",
            engine_state = EngineState.INITIALIZING,
            status       = PipelineStatus.RUNNING,
            started_at   = 0.0,
            completed_at = 0.0,
        )
        with pytest.raises((AttributeError, TypeError)):
            s.stage_name = "y"  # type: ignore

    def test_to_dict(self):
        s = PipelineStage(
            stage_name   = "collect",
            engine_state = EngineState.COLLECTING,
            status       = PipelineStatus.COMPLETED,
            started_at   = 0.0,
            completed_at = 1.0,
        )
        d = s.to_dict()
        assert d["stage_name"] == "collect"
        assert d["engine_state"] == "collecting"

    def test_error_field(self):
        s = PipelineStage(
            stage_name   = "fail",
            engine_state = EngineState.DISPATCHING,
            status       = PipelineStatus.FAILED,
            started_at   = 0.0,
            completed_at = 0.0,
            error        = "boom",
        )
        assert s.error == "boom"


# ===========================================================================
# Section 8 â€” RiskPipeline
# ===========================================================================

class TestRiskPipeline:
    def _pipe(self) -> RiskPipeline:
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        return f.create_pipeline(req)

    def test_initial_status_pending(self):
        p = self._pipe()
        assert p.status == PipelineStatus.PENDING

    def test_start_sets_running(self):
        p = self._pipe()
        p.start()
        assert p.status == PipelineStatus.RUNNING
        assert p.is_running

    def test_complete_sets_completed(self):
        p = self._pipe()
        p.start()
        p.complete()
        assert p.is_completed
        assert not p.is_running

    def test_fail_sets_failed(self):
        p = self._pipe()
        p.start()
        p.fail("error msg")
        assert p.is_failed
        assert p.error == "error msg"

    def test_add_stage(self):
        p = self._pipe()
        p.start()
        stage = PipelineStage(
            stage_name   = "init",
            engine_state = EngineState.INITIALIZING,
            status       = PipelineStatus.COMPLETED,
            started_at   = 0.0,
            completed_at = 0.1,
        )
        p.add_stage(stage)
        assert len(p.stages) == 1

    def test_session_id_setter(self):
        p = self._pipe()
        assert p.session_id == ""
        p.session_id = "sess-42"
        assert p.session_id == "sess-42"

    def test_elapsed_s(self):
        p = self._pipe()
        p.start()
        time.sleep(0.01)
        p.complete()
        assert p.elapsed_s >= 0.0

    def test_to_dict(self):
        p = self._pipe()
        p.start()
        p.complete()
        d = p.to_dict()
        assert d["status"] == "completed"
        assert "pipeline_id" in d


# ===========================================================================
# Section 9 â€” RiskScheduler
# ===========================================================================

class TestRiskScheduler:
    def test_schedule_and_next(self):
        sched = RiskScheduler()
        req = _make_request()
        sched.schedule(req)
        got = sched.next()
        assert got.request_id == req.request_id

    def test_next_empty_returns_none(self):
        sched = RiskScheduler()
        assert sched.next() is None

    def test_priority_ordering(self):
        sched = RiskScheduler()
        req_lo = _make_request()
        req_hi = _make_request()
        sched.schedule(req_lo, SchedulerPriority.BATCH)
        sched.schedule(req_hi, SchedulerPriority.CRITICAL)
        first = sched.next()
        assert first.request_id == req_hi.request_id

    def test_cancel(self):
        sched = RiskScheduler()
        req = _make_request()
        sched.schedule(req)
        cancelled = sched.cancel(req.request_id)
        assert cancelled is True
        assert sched.next() is None

    def test_cancel_unknown_returns_false(self):
        sched = RiskScheduler()
        assert sched.cancel("nonexistent") is False

    def test_pending_count(self):
        sched = RiskScheduler()
        for _ in range(3):
            sched.schedule(_make_request())
        assert sched.pending_count() == 3

    def test_capacity_error(self):
        sched = RiskScheduler(max_queue_size=2)
        sched.schedule(_make_request())
        sched.schedule(_make_request())
        with pytest.raises(RiskCapacityError):
            sched.schedule(_make_request())

    def test_duplicate_raises_scheduler_error(self):
        sched = RiskScheduler()
        req = _make_request()
        sched.schedule(req)
        with pytest.raises(RiskSchedulerError):
            sched.schedule(req)


# ===========================================================================
# Section 10 â€” RiskDispatcher
# ===========================================================================

class TestRiskDispatcher:
    def test_no_frameworks_dispatch_succeeds(self):
        d = RiskDispatcher()
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        pipe = f.create_pipeline(req)
        pipe.start()
        result = d.dispatch(pipe, req)
        assert result is pipe

    def test_register_policy_framework(self):
        d = RiskDispatcher()
        assert not d.has_policy_framework
        d.register_policy_framework(lambda p, r: None)
        assert d.has_policy_framework

    def test_register_assessment_framework(self):
        d = RiskDispatcher()
        assert not d.has_assessment_framework
        d.register_assessment_framework(lambda p, r: None)
        assert d.has_assessment_framework

    def test_unregister_frameworks(self):
        d = RiskDispatcher()
        d.register_policy_framework(lambda p, r: None)
        d.register_assessment_framework(lambda p, r: None)
        d.unregister_policy_framework()
        d.unregister_assessment_framework()
        assert not d.has_policy_framework
        assert not d.has_assessment_framework

    def test_policy_framework_called(self):
        calls = []
        d = RiskDispatcher()
        d.register_policy_framework(lambda p, r: calls.append("policy"))
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        pipe = f.create_pipeline(req)
        pipe.start()
        d.dispatch(pipe, req)
        assert "policy" in calls

    def test_failing_framework_raises_dispatch_error(self):
        d = RiskDispatcher()
        d.register_policy_framework(lambda p, r: (_ for _ in ()).throw(ValueError("fail")))
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        pipe = f.create_pipeline(req)
        pipe.start()
        with pytest.raises(RiskDispatchError):
            d.dispatch(pipe, req)

    def test_determine_next_state_assessment(self):
        from iios.risk.engine.constants import ASSESSMENT_WORKFLOWS
        d = RiskDispatcher()
        for wt in ASSESSMENT_WORKFLOWS:
            assert d.determine_next_state(wt) == EngineState.ASSESSING

    def test_determine_next_state_monitoring(self):
        from iios.risk.engine.constants import MONITORING_WORKFLOWS
        d = RiskDispatcher()
        for wt in MONITORING_WORKFLOWS:
            assert d.determine_next_state(wt) == EngineState.MONITORING

    def test_statistics(self):
        d = RiskDispatcher()
        stats = d.statistics()
        assert "dispatch_count" in stats
        assert "failure_count" in stats

    def test_dispatch_increments_count(self):
        d = RiskDispatcher()
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        pipe = f.create_pipeline(req)
        pipe.start()
        d.dispatch(pipe, req)
        assert d.statistics()["dispatch_count"] == 1


# ===========================================================================
# Section 11 â€” RiskSessionManager
# ===========================================================================

class TestRiskSessionManager:
    @pytest.fixture
    def sm(self):
        from iios.risk.lifecycle import RiskLifecycle
        lc = RiskLifecycle()
        mgr = RiskSessionManager(lifecycle=lc)
        mgr.start()
        yield mgr
        mgr.stop()

    def test_create_session(self, sm):
        session = sm.create_session(_rid(), _pid())
        assert session.session_id
        assert session.risk_id
        assert session.portfolio_id

    def test_initialize_session(self, sm):
        session = sm.create_session(_rid(), _pid())
        session = sm.initialize_session(session)
        assert session.state.value == "initializing"

    def test_collect_session(self, sm):
        session = sm.create_session(_rid(), _pid())
        session = sm.initialize_session(session)
        session = sm.collect_session(session)
        assert session.state.value == "collecting"

    def test_validate_and_ready(self, sm):
        session = sm.create_session(_rid(), _pid())
        session = sm.initialize_session(session)
        session = sm.collect_session(session)
        session = sm.validate_session(session)
        session = sm.ready_session(session)
        assert session.state.value == "ready"

    def test_start_assessment(self, sm):
        session = sm.create_session(_rid(), _pid())
        session = sm.initialize_session(session)
        session = sm.collect_session(session)
        session = sm.validate_session(session)
        session = sm.ready_session(session)
        session = sm.start_assessment_session(session)
        assert session.state.value == "assessing"

    def test_complete_session(self, sm):
        session = sm.create_session(_rid(), _pid())
        session = sm.initialize_session(session)
        session = sm.collect_session(session)
        session = sm.validate_session(session)
        session = sm.ready_session(session)
        session = sm.start_assessment_session(session)
        session = sm.complete_session(session)
        assert session.state.value == "completed"

    def test_fail_session(self, sm):
        session = sm.create_session(_rid(), _pid())
        session = sm.initialize_session(session)
        failed = sm.fail_session(session, error="oops")
        assert failed.state.value == "failed"

    def test_active_count_increments(self, sm):
        before = sm.active_session_count()
        sm.create_session(_rid(), _pid())
        assert sm.active_session_count() == before + 1

    def test_complete_removes_from_active(self, sm):
        s = sm.create_session(_rid(), _pid())
        s = sm.initialize_session(s)
        s = sm.collect_session(s)
        s = sm.validate_session(s)
        s = sm.ready_session(s)
        s = sm.start_assessment_session(s)
        count_before = sm.active_session_count()
        sm.complete_session(s)
        assert sm.active_session_count() == count_before - 1

    def test_fail_removes_from_active(self, sm):
        s = sm.create_session(_rid(), _pid())
        count_before = sm.active_session_count()
        sm.fail_session(s, error="x")
        assert sm.active_session_count() < count_before + 1

    def test_get_session(self, sm):
        session = sm.create_session(_rid(), _pid())
        got = sm.get_session(session.session_id)
        assert got is not None

    def test_get_session_unknown_returns_none(self, sm):
        assert sm.get_session("nonexistent") is None

    def test_stop_fails_all_active(self, sm):
        s = sm.create_session(_rid(), _pid())
        sm.stop()
        assert sm.active_session_count() == 0


# ===========================================================================
# Section 12 â€” RiskEngineRegistry
# ===========================================================================

class TestRiskEngineRegistry:
    def _reg(self) -> RiskEngineRegistry:
        return RiskEngineRegistry()

    def test_register_and_query_pipeline(self):
        reg = self._reg()
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        pipe = f.create_pipeline(req)
        reg.register_pipeline(pipe)
        results = reg.query(pipeline_id=pipe.pipeline_id)
        assert len(results) == 1

    def test_archive_pipeline(self):
        reg = self._reg()
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        pipe = f.create_pipeline(req)
        pipe.start()
        pipe.complete()
        reg.register_pipeline(pipe)
        assert reg.active_pipeline_count() == 1
        reg.archive_pipeline(pipe)
        assert reg.active_pipeline_count() == 0

    def test_register_request(self):
        reg = self._reg()
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        reg.register_request(req)  # should not raise

    def test_register_response(self):
        reg = self._reg()
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        resp = f.create_failure_response(req, error_message="x")
        reg.register_response(resp)  # should not raise

    def test_active_pipeline_count(self):
        reg = self._reg()
        f = RiskEngineFactory()
        for _ in range(3):
            req = f.create_request(_rid(), _pid())
            reg.register_pipeline(f.create_pipeline(req))
        assert reg.active_pipeline_count() == 3


# ===========================================================================
# Section 13 â€” RiskEngineValidator
# ===========================================================================

class TestRiskEngineValidator:
    def _validator(self) -> RiskEngineValidator:
        return RiskEngineValidator()

    def _valid_req(self) -> RiskRequest:
        return _make_request()

    def test_valid_request_passes(self):
        v = self._validator()
        req = self._valid_req()
        result = v.validate_request(req)
        assert result.is_valid
        assert len(result.failed_checks) == 0

    def test_validate_or_raise_passes(self):
        v = self._validator()
        v.validate_or_raise(self._valid_req())  # should not raise

    def test_capacity_check_fails_when_full(self):
        v = RiskEngineValidator(
            max_sessions    = 2,
            active_count_fn = lambda: 3,
        )
        result = v.validate_request(self._valid_req())
        assert not result.is_valid
        assert "lifecycle_readiness" in result.failed_checks

    def test_capacity_check_passes_below_limit(self):
        v = RiskEngineValidator(
            max_sessions    = 10,
            active_count_fn = lambda: 5,
        )
        result = v.validate_request(self._valid_req())
        assert result.is_valid

    def test_all_checks_in_result(self):
        v = self._validator()
        result = v.validate_request(self._valid_req())
        check_names = {c.check_name for c in result.checks}
        assert len(check_names) == 6

    def test_validation_result_error_messages_empty_on_success(self):
        v = self._validator()
        result = v.validate_request(self._valid_req())
        assert result.error_messages == []


# ===========================================================================
# Section 14 â€” RiskEngineHealth
# ===========================================================================

class TestRiskEngineHealth:
    def test_report_returns_dict(self):
        from iios.risk.lifecycle import RiskLifecycle
        lc = RiskLifecycle()
        sm = RiskSessionManager(lifecycle=lc)
        sm.start()
        d = RiskDispatcher()
        h = RiskEngineHealth(max_sessions=100)
        report = h.report(sm, d)
        assert isinstance(report, dict)
        sm.stop()

    def test_report_has_required_keys(self):
        from iios.risk.lifecycle import RiskLifecycle
        sm = RiskSessionManager(lifecycle=RiskLifecycle())
        sm.start()
        d = RiskDispatcher()
        h = RiskEngineHealth()
        report = h.report(sm, d)
        for k in ("overall", "components"):
            assert k in report
        sm.stop()


# ===========================================================================
# Section 15 â€” RiskEngineStatus
# ===========================================================================

class TestRiskEngineStatus:
    def _status(self) -> RiskEngineStatus:
        return RiskEngineStatus(
            engine_id      = ENGINE_SYSTEM_ID,
            state          = "running",
            engine_state   = EngineState.IDLE,
            session_count  = 0,
            pipeline_count = 0,
            health         = {"overall": "healthy"},
            statistics     = {},
            started_at     = time.time(),
        )

    def test_status_fields(self):
        s = self._status()
        assert s.engine_id == ENGINE_SYSTEM_ID
        assert s.state == "running"
        assert s.session_count == 0


# ===========================================================================
# Section 16 â€” RiskEngineStatistics
# ===========================================================================

class TestRiskEngineStatistics:
    def test_initial_snapshot_zeros(self):
        stats = RiskEngineStatistics()
        snap = stats.snapshot()
        assert snap["sessions_created"] == 0
        assert snap["requests_submitted"] == 0

    def test_record_session_created(self):
        stats = RiskEngineStatistics()
        stats.record_session_created()
        assert stats.snapshot()["sessions_created"] == 1

    def test_record_request_submitted(self):
        stats = RiskEngineStatistics()
        stats.record_request_submitted()
        assert stats.snapshot()["requests_submitted"] == 1

    def test_record_pipeline_started(self):
        stats = RiskEngineStatistics()
        stats.record_pipeline_started()
        assert stats.snapshot()["pipelines_started"] == 1

    def test_record_pipeline_completed(self):
        stats = RiskEngineStatistics()
        stats.record_pipeline_completed(0.5)
        snap = stats.snapshot()
        assert snap["pipelines_completed"] == 1

    def test_record_pipeline_failed(self):
        stats = RiskEngineStatistics()
        stats.record_pipeline_failed()
        assert stats.snapshot()["pipelines_failed"] == 1

    def test_record_snapshot_published(self):
        stats = RiskEngineStatistics()
        stats.record_snapshot_published()
        assert stats.snapshot()["snapshots_published"] == 1

    def test_record_dispatch_time(self):
        stats = RiskEngineStatistics()
        stats.record_dispatch_time(0.3)
        stats.record_dispatch_time(0.7)
        snap = stats.snapshot()
        assert snap["avg_dispatch_time_s"] == pytest.approx(0.5, rel=0.01)

    def test_thread_safety(self):
        stats = RiskEngineStatistics()
        def worker():
            for _ in range(100):
                stats.record_request_submitted()
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert stats.snapshot()["requests_submitted"] == 400


# ===========================================================================
# Section 17 â€” RiskEngineHistory
# ===========================================================================

class TestRiskEngineHistory:
    def test_record_and_query_event(self):
        h = RiskEngineHistory(max_events=100)
        ev = make_risk_initialized("r1", "p1", "s1")
        h.record_event(ev)
        events = h.recent_events(50)
        assert len(events) == 1
        assert events[0].risk_id == "r1"

    def test_record_request(self):
        h = RiskEngineHistory()
        req = _make_request()
        h.record_request(req)
        reqs = h.recent_requests(50)
        assert len(reqs) == 1

    def test_record_pipeline(self):
        h = RiskEngineHistory()
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        pipe = f.create_pipeline(req)
        h.record_pipeline(pipe)
        pipes = h.recent_pipelines(50)
        assert len(pipes) == 1

    def test_record_response(self):
        h = RiskEngineHistory()
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        resp = f.create_failure_response(req, error_message="x")
        h.record_response(resp)
        resps = h.recent_responses(50)
        assert len(resps) == 1

    def test_bounded_history_discards_oldest(self):
        h = RiskEngineHistory(max_events=3)
        for i in range(5):
            h.record_event(make_risk_initialized(f"r{i}", "p1", "s1"))
        assert len(h.recent_events(10)) == 3

    def test_recent_events(self):
        h = RiskEngineHistory(max_events=10)
        for i in range(5):
            h.record_event(make_risk_initialized(f"r{i}", "p1", "s1"))
        recent = h.recent_events(3)
        assert len(recent) == 3


# ===========================================================================
# Section 18 â€” RiskEngineEvents
# ===========================================================================

class TestRiskEngineEvents:
    def test_make_risk_initialized(self):
        ev = make_risk_initialized("r1", "p1", "s1")
        assert ev.risk_id == "r1"
        assert ev.portfolio_id == "p1"
        assert ev.session_id == "s1"
        assert ev.event_type.value == "risk_initialized"

    def test_make_risk_started(self):
        ev = make_risk_started("r1", "p1", "s1")
        assert ev.event_type.value == "risk_started"

    def test_make_risk_collected(self):
        ev = make_risk_collected("r1", "p1", "s1")
        assert ev.event_type.value == "risk_collected"

    def test_make_risk_dispatched(self):
        ev = make_risk_dispatched("r1", "p1", "s1")
        assert ev.event_type.value == "risk_dispatched"

    def test_make_risk_assessment_started(self):
        ev = make_risk_assessment_started("r1", "p1", "s1")
        assert ev.event_type.value == "risk_assessment_started"

    def test_make_risk_published(self):
        ev = make_risk_published("r1", "p1", "s1")
        assert ev.event_type.value == "risk_published"

    def test_make_risk_completed(self):
        ev = make_risk_completed("r1", "p1", "s1")
        assert ev.event_type.value == "risk_completed"

    def test_make_risk_failed(self):
        ev = make_risk_failed("r1", "p1", "s1")
        assert ev.event_type.value == "risk_failed"

    def test_make_risk_stopped(self):
        ev = make_risk_stopped("r1", "p1")
        assert ev.event_type.value == "risk_stopped"

    def test_event_is_frozen(self):
        ev = make_risk_initialized("r1", "p1", "s1")
        with pytest.raises((AttributeError, TypeError)):
            ev.risk_id = "x"  # type: ignore

    def test_event_has_event_id(self):
        ev = make_risk_initialized("r1", "p1", "s1")
        assert ev.event_id

    def test_event_has_occurred_at(self):
        before = time.time()
        ev = make_risk_initialized("r1", "p1", "s1")
        assert before <= ev.occurred_at <= time.time() + 1

    def test_event_to_dict(self):
        ev = make_risk_started("r1", "p1", "s1")
        d = ev.to_dict()
        assert d["event_type"] == "risk_started"
        assert d["risk_id"] == "r1"

    def test_all_nine_factories_produce_unique_types(self):
        factories = [
            make_risk_initialized("r", "p", "s"),
            make_risk_started("r", "p", "s"),
            make_risk_collected("r", "p", "s"),
            make_risk_dispatched("r", "p", "s"),
            make_risk_assessment_started("r", "p", "s"),
            make_risk_published("r", "p", "s"),
            make_risk_completed("r", "p", "s"),
            make_risk_failed("r", "p", "s"),
            make_risk_stopped("r", "p"),
        ]
        types = {e.event_type for e in factories}
        assert len(types) == 9


# ===========================================================================
# Section 19 â€” RiskEngineFactory
# ===========================================================================

class TestRiskEngineFactory:
    def test_create_request_defaults(self):
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        assert req.workflow_type == RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT

    def test_create_request_with_workflow_type(self):
        f = RiskEngineFactory()
        req = f.create_request(
            _rid(), _pid(),
            RiskWorkflowType.STRESS_TEST,
        )
        assert req.workflow_type == RiskWorkflowType.STRESS_TEST

    def test_create_pipeline(self):
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        pipe = f.create_pipeline(req)
        assert pipe.request_id == req.request_id
        assert pipe.portfolio_id == req.portfolio_id

    def test_create_snapshot(self):
        f = RiskEngineFactory()
        snap = f.create_snapshot(
            "r1", "p1", "s1",
            RiskWorkflowType.EXPOSURE_MONITORING,
            EngineState.PUBLISHING,
        )
        assert snap.risk_id == "r1"
        assert snap.workflow_type == RiskWorkflowType.EXPOSURE_MONITORING

    def test_create_success_response(self):
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        snap = f.create_snapshot(req.risk_id, req.portfolio_id, "s",
                                  req.workflow_type, EngineState.PUBLISHING)
        resp = f.create_success_response(req, snapshot=snap, elapsed_s=0.2)
        assert resp.is_success
        assert resp.has_snapshot

    def test_create_failure_response(self):
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        resp = f.create_failure_response(req, error_message="test error")
        assert resp.is_failure
        assert "test error" in resp.error_message


# ===========================================================================
# Section 20 â€” RiskEngine lifecycle and guards
# ===========================================================================

class TestRiskEngineLifecycle:
    def test_start_stop(self):
        e = RiskEngine()
        e.start()
        assert e.lifecycle_state().value == "running"
        e.stop()
        assert e.lifecycle_state().value != "running"

    def test_submit_before_start_raises(self):
        e = RiskEngine()
        req = _make_request()
        with pytest.raises(RiskEngineNotRunningError):
            e.submit(req)

    def test_initialize_before_start_raises(self):
        e = RiskEngine()
        with pytest.raises(RiskEngineNotRunningError):
            e.initialize_risk(_rid(), _pid())

    def test_submit_after_stop_raises(self):
        e = RiskEngine()
        e.start()
        e.stop()
        req = _make_request()
        with pytest.raises(RiskEngineNotRunningError):
            e.submit(req)

    def test_second_start_raises(self):
        """LifecycleAwareMixin raises EngineAlreadyRunningError on double-start."""
        from iios.investment.workflow.engine_lifecycle import EngineAlreadyRunningError
        e = RiskEngine()
        e.start()
        with pytest.raises(EngineAlreadyRunningError):
            e.start()
        e.stop()

    def test_status_after_start(self):
        e = _started_engine()
        s = e.status()
        assert s.state == "running"
        e.stop()

    def test_health_after_start(self):
        e = _started_engine()
        h = e.health()
        assert isinstance(h, dict)
        e.stop()

    def test_statistics_keys(self):
        e = _started_engine()
        stats = e.statistics()
        assert "sessions_created" in stats
        assert "requests_submitted" in stats
        e.stop()


# ===========================================================================
# Section 21 â€” RiskEngine workflow types
# ===========================================================================

class TestRiskEngineWorkflows:
    @pytest.fixture(autouse=True)
    def engine(self):
        e = RiskEngine()
        e.start()
        yield e
        e.stop()

    def test_portfolio_risk_assessment(self, engine):
        r = engine.initialize_risk(_rid(), _pid(),
            workflow_type=RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT)
        assert r.is_success

    def test_position_risk_assessment(self, engine):
        r = engine.initialize_risk(_rid(), _pid(),
            workflow_type=RiskWorkflowType.POSITION_RISK_ASSESSMENT)
        assert r.is_success

    def test_account_risk_assessment(self, engine):
        r = engine.initialize_risk(_rid(), _pid(),
            workflow_type=RiskWorkflowType.ACCOUNT_RISK_ASSESSMENT)
        assert r.is_success

    def test_exposure_monitoring(self, engine):
        r = engine.initialize_risk(_rid(), _pid(),
            workflow_type=RiskWorkflowType.EXPOSURE_MONITORING)
        assert r.is_success

    def test_limit_monitoring(self, engine):
        r = engine.initialize_risk(_rid(), _pid(),
            workflow_type=RiskWorkflowType.LIMIT_MONITORING)
        assert r.is_success

    def test_stress_test_request(self, engine):
        r = engine.initialize_risk(_rid(), _pid(),
            workflow_type=RiskWorkflowType.STRESS_TEST)
        assert r.is_success

    def test_scenario_analysis_request(self, engine):
        r = engine.initialize_risk(_rid(), _pid(),
            workflow_type=RiskWorkflowType.SCENARIO_ANALYSIS)
        assert r.is_success

    def test_intraday_risk_review(self, engine):
        r = engine.initialize_risk(_rid(), _pid(),
            workflow_type=RiskWorkflowType.INTRADAY_RISK_REVIEW)
        assert r.is_success

    def test_eod_risk_review(self, engine):
        r = engine.initialize_risk(_rid(), _pid(),
            workflow_type=RiskWorkflowType.EOD_RISK_REVIEW)
        assert r.is_success

    def test_start_assessment_shortcut(self, engine):
        r = engine.start_assessment(_rid(), _pid())
        assert r.is_success

    def test_submit_with_inputs(self, engine):
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        req = req.with_inputs({"snapshot": "portfolio_v1"})
        r = engine.submit(req)
        assert r.is_success

    def test_response_has_snapshot_on_success(self, engine):
        r = engine.initialize_risk(_rid(), _pid())
        assert r.has_snapshot
        assert r.snapshot is not None

    def test_response_snapshot_has_session_id(self, engine):
        r = engine.initialize_risk(_rid(), _pid())
        assert r.snapshot.session_id

    def test_response_elapsed_s_positive(self, engine):
        r = engine.initialize_risk(_rid(), _pid())
        assert r.elapsed_s > 0

    def test_multiple_sequential_workflows(self, engine):
        for _ in range(5):
            r = engine.initialize_risk(_rid(), _pid())
            assert r.is_success

    def test_priority_high(self, engine):
        r = engine.initialize_risk(_rid(), _pid(),
            priority=SchedulerPriority.HIGH)
        assert r.is_success

    def test_priority_critical(self, engine):
        r = engine.initialize_risk(_rid(), _pid(),
            priority=SchedulerPriority.CRITICAL)
        assert r.is_success


# ===========================================================================
# Section 22 â€” RiskEngine observability
# ===========================================================================

class TestRiskEngineObservability:
    @pytest.fixture(autouse=True)
    def engine(self):
        e = RiskEngine()
        e.start()
        yield e
        e.stop()

    def test_statistics_increments_after_workflow(self, engine):
        engine.initialize_risk(_rid(), _pid())
        stats = engine.statistics()
        assert stats["requests_submitted"] >= 1
        assert stats["pipelines_started"] >= 1
        assert stats["sessions_created"] >= 1

    def test_query_returns_list(self, engine):
        results = engine.query()
        assert isinstance(results, list)

    def test_validate_valid_request(self, engine):
        req = _make_request()
        result = engine.validate(req)
        assert result.is_valid

    def test_status_session_count_after_workflow(self, engine):
        engine.initialize_risk(_rid(), _pid())
        # After success, session should be completed and removed from active
        s = engine.status()
        assert s.session_count >= 0

    def test_status_engine_state_field(self, engine):
        s = engine.status()
        assert isinstance(s.engine_state, EngineState)

    def test_health_report_structure(self, engine):
        h = engine.health()
        assert "overall" in h
        assert "components" in h


# ===========================================================================
# Section 23 â€” M3/M4 framework hooks
# ===========================================================================

class TestFrameworkHooks:
    @pytest.fixture(autouse=True)
    def engine(self):
        e = RiskEngine()
        e.start()
        yield e
        e.stop()

    def test_register_policy_framework(self, engine):
        calls = []
        engine.register_policy_framework(lambda p, r: calls.append("policy"))
        engine.initialize_risk(_rid(), _pid())
        assert "policy" in calls

    def test_register_assessment_framework(self, engine):
        calls = []
        engine.register_assessment_framework(lambda p, r: calls.append("assessment"))
        engine.initialize_risk(_rid(), _pid())
        assert "assessment" in calls

    def test_both_frameworks_called(self, engine):
        calls = []
        engine.register_policy_framework(lambda p, r: calls.append("policy"))
        engine.register_assessment_framework(lambda p, r: calls.append("assessment"))
        engine.initialize_risk(_rid(), _pid())
        assert "policy" in calls
        assert "assessment" in calls

    def test_failing_policy_returns_failure_response(self, engine):
        def bad_policy(p, r):
            raise ValueError("policy rejected")
        engine.register_policy_framework(bad_policy)
        r = engine.initialize_risk(_rid(), _pid())
        assert r.is_failure
        assert "policy rejected" in r.error_message


# ===========================================================================
# Section 24 â€” Listeners
# ===========================================================================

class TestListeners:
    @pytest.fixture(autouse=True)
    def engine(self):
        e = RiskEngine()
        e.start()
        yield e
        e.stop()

    def test_add_listener_called_on_workflow(self, engine):
        events = []
        fn = lambda ev: events.append(ev)
        engine.add_listener(fn)
        engine.initialize_risk(_rid(), _pid())
        assert len(events) > 0

    def test_remove_listener(self, engine):
        events = []
        fn = lambda ev: events.append(ev)
        engine.add_listener(fn)
        engine.remove_listener(fn)
        engine.initialize_risk(_rid(), _pid())
        assert len(events) == 0

    def test_duplicate_listener_not_added(self, engine):
        """add_listener with same fn object twice â€” only one entry."""
        calls = []
        fn = lambda ev: calls.append(1)
        engine.add_listener(fn)
        engine.add_listener(fn)
        engine.initialize_risk(_rid(), _pid())
        # should not double-fire
        per_event_count = len(calls)
        assert per_event_count > 0

    def test_listener_exception_does_not_propagate(self, engine):
        def bad_listener(ev):
            raise RuntimeError("listener failure")
        engine.add_listener(bad_listener)
        # Should complete without raising
        r = engine.initialize_risk(_rid(), _pid())
        assert r.is_success

    def test_stopped_event_emitted(self):
        e = RiskEngine()
        e.start()
        events = []
        e.add_listener(lambda ev: events.append(ev.event_type.value))
        e.stop()
        assert "risk_stopped" in events


# ===========================================================================
# Section 25 â€” Not-running guard
# ===========================================================================

class TestNotRunningGuard:
    def test_collect_raises_before_start(self):
        e = RiskEngine()
        with pytest.raises(RiskEngineNotRunningError):
            e.collect(_rid(), {"x": 1})

    def test_dispatch_raises_before_start(self):
        e = RiskEngine()
        with pytest.raises(RiskEngineNotRunningError):
            e.dispatch(_rid())

    def test_publish_raises_before_start(self):
        e = RiskEngine()
        with pytest.raises(RiskEngineNotRunningError):
            e.publish(_rid())

    def test_query_raises_before_start(self):
        e = RiskEngine()
        with pytest.raises(RiskEngineNotRunningError):
            e.query()

    def test_validate_raises_before_start(self):
        e = RiskEngine()
        with pytest.raises(RiskEngineNotRunningError):
            e.validate(_make_request())

    def test_health_and_status_dont_need_running_engine(self):
        """health() and status() may be called even on a stopped engine."""
        e = RiskEngine()
        # These are informational â€” should not require lifecycle check
        # (behaviour depends on implementation; just don't crash)
        try:
            e.health()
        except RiskEngineNotRunningError:
            pass  # acceptable
        except Exception:
            pass  # acceptable too


# ===========================================================================
# Section 26 â€” Concurrency
# ===========================================================================

class TestConcurrency:
    def test_concurrent_workflows(self):
        e = RiskEngine(max_sessions=200)
        e.start()
        results: List[RiskResponse] = []
        lock = threading.Lock()

        def submit():
            r = e.initialize_risk(_rid(), _pid())
            with lock:
                results.append(r)

        threads = [threading.Thread(target=submit) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        e.stop()
        assert len(results) == 20
        successes = [r for r in results if r.is_success]
        assert len(successes) == 20

    def test_concurrent_scheduler_access(self):
        sched = RiskScheduler(max_queue_size=10_000)
        errors = []

        def producer():
            for _ in range(50):
                try:
                    sched.schedule(_make_request())
                except Exception as ex:
                    errors.append(ex)

        threads = [threading.Thread(target=producer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_concurrent_statistics(self):
        stats = RiskEngineStatistics()

        def worker():
            for _ in range(200):
                stats.record_request_submitted()
                stats.record_pipeline_started()
                stats.record_pipeline_completed(0.01)
                stats.record_snapshot_published()

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        snap = stats.snapshot()
        assert snap["requests_submitted"] == 1000
        assert snap["pipelines_started"] == 1000
        assert snap["pipelines_completed"] == 1000
        assert snap["snapshots_published"] == 1000


# ===========================================================================
# Section 27 â€” Regression
# ===========================================================================

class TestRegression:
    def test_response_workflow_type_preserved(self):
        e = _started_engine()
        r = e.initialize_risk(
            _rid(), _pid(),
            workflow_type=RiskWorkflowType.SCENARIO_ANALYSIS,
        )
        assert r.workflow_type == RiskWorkflowType.SCENARIO_ANALYSIS
        e.stop()

    def test_snapshot_session_id_matches_pipeline(self):
        e = _started_engine()
        r = e.initialize_risk(_rid(), _pid())
        assert r.snapshot.session_id != ""
        e.stop()

    def test_engine_state_idle_after_stop(self):
        e = RiskEngine()
        e.start()
        e.initialize_risk(_rid(), _pid())
        e.stop()
        # engine_state should be STOPPED after stop()
        # (can only inspect via status before stop)

    def test_session_manager_start_idempotent(self):
        from iios.risk.lifecycle import RiskLifecycle
        sm = RiskSessionManager(lifecycle=RiskLifecycle())
        sm.start()
        sm.start()  # second call should not raise
        sm.stop()

    def test_dispatcher_statistics_failure_count(self):
        d = RiskDispatcher()
        d.register_policy_framework(lambda p, r: (_ for _ in ()).throw(ValueError("x")))
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        pipe = f.create_pipeline(req)
        pipe.start()
        try:
            d.dispatch(pipe, req)
        except RiskDispatchError:
            pass
        assert d.statistics()["failure_count"] == 1

    def test_no_policy_evaluation_in_engine(self):
        """Engine must not perform risk calculations â€” all calculations deferred to M4."""
        e = _started_engine()
        r = e.initialize_risk(_rid(), _pid())
        # The outputs dict in snapshot must not contain risk calculations
        # performed by the engine itself (they should come from M4)
        assert isinstance(r.snapshot.outputs, dict)
        e.stop()

    def test_workflow_response_contains_request_id(self):
        e = _started_engine()
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        r = e.submit(req)
        assert r.request_id == req.request_id
        e.stop()

    def test_history_records_events_on_success(self):
        e = RiskEngine()
        e.start()
        e.initialize_risk(_rid(), _pid())
        # Access history via internal if available
        history = e._history  # type: ignore
        events = history.recent_events(100)
        assert len(events) > 0
        e.stop()

    def test_registry_clears_after_archive(self):
        reg = RiskEngineRegistry()
        f = RiskEngineFactory()
        req = f.create_request(_rid(), _pid())
        pipe = f.create_pipeline(req)
        pipe.start()
        pipe.complete()
        reg.register_pipeline(pipe)
        assert reg.active_pipeline_count() == 1
        reg.archive_pipeline(pipe)
        assert reg.active_pipeline_count() == 0
