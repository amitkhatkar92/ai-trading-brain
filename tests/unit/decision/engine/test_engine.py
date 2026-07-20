"""
tests/unit/decision/engine/test_engine.py
==========================================
Comprehensive test suite for iios.decision.engine — C9 M2.

Coverage areas
--------------
* Engine lifecycle (start/stop)
* Request submission (synchronous)
* Async scheduling
* Workflow orchestration
* Pipeline state machine
* Scheduler (priority, cancellation)
* Dispatcher (stub / real frameworks)
* Validation (all six checks)
* Statistics (all eight counters)
* History (events, responses)
* Health assessment
* Status reporting
* Registry
* Factory
* Events (all eight types)
* Context / Snapshot value objects
* Concurrency (parallel submits)
* Stress (100 concurrent requests)
* Framework injection
* Regression (interface contracts)
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict

import pytest

from iios.decision.engine import (
    PIPELINE_ACTIVE_STATES,
    PIPELINE_TERMINAL_STATES,
    PIPELINE_VALID_TRANSITIONS,
    DecisionCollectionError,
    DecisionDispatchError,
    DecisionDispatcher,
    DecisionEngine,
    DecisionEngineContext,
    DecisionEngineError,
    DecisionEngineEvent,
    DecisionEngineEventType,
    DecisionEngineFactory,
    DecisionEngineHealth,
    DecisionEngineHistory,
    DecisionEngineNotRunningError,
    DecisionEngineRegistry,
    DecisionEngineStatistics,
    DecisionEngineStatus,
    DecisionEngineValidator,
    DecisionMode,
    DecisionPipeline,
    DecisionPriority,
    DecisionPublishError,
    DecisionRequest,
    DecisionRequestValidationError,
    DecisionResponse,
    DecisionResponseStatus,
    DecisionScheduler,
    DecisionSessionError,
    DecisionSnapshot,
    EngineHealthStatus,
    EngineOperationalStatus,
    EngineValidationCode,
    EngineValidationResult,
    OptimizationFrameworkProtocol,
    PipelineState,
    PolicyFrameworkProtocol,
    SubsystemHealth,
    assess_engine_health,
    build_engine_status,
    make_decision_engine_collected,
    make_decision_engine_completed,
    make_decision_engine_dispatched,
    make_decision_engine_failed,
    make_decision_engine_initialized,
    make_decision_engine_published,
    make_decision_engine_started,
    make_decision_engine_stopped,
)
from iios.decision.engine.exceptions import (
    DecisionEngineError,
    DecisionPipelineError,
    DecisionRequestNotFoundError,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _engine(**kwargs) -> DecisionEngine:
    """Return a started DecisionEngine."""
    e = DecisionEngine(**kwargs)
    e.start()
    return e


def _req(decision_id: str | None = None, **kwargs) -> DecisionRequest:
    return DecisionRequest.create(decision_id or f"d-{uuid.uuid4()}", **kwargs)


# ===========================================================================
# 1. Engine lifecycle
# ===========================================================================

class TestEngineLifecycle:
    def test_create(self):
        e = DecisionEngine()
        assert repr(e)

    def test_start_and_stop(self):
        e = _engine()
        e.stop()

    def test_repr(self):
        e = _engine()
        r = repr(e)
        assert "DecisionEngine" in r
        assert "1.0.0" in r
        e.stop()

    def test_not_running_raises_on_submit(self):
        e = DecisionEngine()
        with pytest.raises(DecisionEngineNotRunningError):
            e.submit(_req())

    def test_not_running_raises_on_schedule(self):
        e = DecisionEngine()
        with pytest.raises(DecisionEngineNotRunningError):
            e.schedule(_req())

    def test_validate_not_running_fails_health(self):
        e = DecisionEngine()
        r = e.validate(_req())
        assert EngineValidationCode.SUBSYSTEM_HEALTH in r.failed_checks

    def test_double_stop_raises(self):
        """LifecycleAwareMixin.stop() raises when not running — second call must raise."""
        from iios.investment.workflow.engine_lifecycle import EngineNotRunningError
        e = _engine()
        e.stop()
        with pytest.raises(EngineNotRunningError):
            e.stop()


# ===========================================================================
# 2. Request creation
# ===========================================================================

class TestRequestCreation:
    def test_create_request(self):
        r = DecisionRequest.create("d-001")
        assert r.decision_id == "d-001"

    def test_auto_request_id(self):
        r1 = DecisionRequest.create("d")
        r2 = DecisionRequest.create("d")
        assert r1.request_id != r2.request_id

    def test_explicit_request_id(self):
        r = DecisionRequest.create("d", request_id="my-id")
        assert r.request_id == "my-id"

    def test_all_fields(self):
        r = DecisionRequest.create(
            "d-full",
            workflow_id     = "wf-1",
            portfolio_id    = "p-1",
            strategy_id     = "st-1",
            decision_mode   = DecisionMode.SCHEDULED,
            decision_reason = "rebalance",
            priority        = DecisionPriority.HIGH,
            deadline_s      = 10.0,
            inputs          = {"price": 100.0},
        )
        assert r.workflow_id     == "wf-1"
        assert r.portfolio_id    == "p-1"
        assert r.strategy_id     == "st-1"
        assert r.decision_mode   == DecisionMode.SCHEDULED
        assert r.decision_reason == "rebalance"
        assert r.priority        == DecisionPriority.HIGH
        assert r.deadline_s      == 10.0
        assert r.inputs          == {"price": 100.0}

    def test_request_is_frozen(self):
        r = DecisionRequest.create("d")
        with pytest.raises(Exception):
            r.decision_id = "mutate"  # type: ignore[misc]


# ===========================================================================
# 3. Synchronous submission
# ===========================================================================

class TestSynchronousSubmit:
    def setup_method(self): self.engine = _engine()
    def teardown_method(self): self.engine.stop()

    def test_submit_returns_response(self):
        r = self.engine.submit(_req())
        assert isinstance(r, DecisionResponse)

    def test_submit_success(self):
        r = self.engine.submit(_req())
        assert r.is_success
        assert r.status == DecisionResponseStatus.SUCCESS

    def test_submit_has_snapshot(self):
        r = self.engine.submit(_req())
        assert r.snapshot is not None

    def test_submit_snapshot_decision_id(self):
        r = self.engine.submit(_req(decision_id="snap-d"))
        assert r.snapshot.decision_id == "snap-d"

    def test_submit_snapshot_has_ids(self):
        r = self.engine.submit(_req())
        s = r.snapshot
        assert s.snapshot_id != ""
        assert s.request_id  == r.request_id
        assert s.session_id  != ""

    def test_submit_with_inputs(self):
        r = self.engine.submit(_req(inputs={"price": 100.0, "volume": 500}))
        assert r.snapshot.collection_inputs == {"price": 100.0, "volume": 500}

    def test_submit_increments_requests(self):
        self.engine.submit(_req())
        self.engine.submit(_req())
        assert self.engine.statistics().decision_requests == 2

    def test_submit_increments_pipelines(self):
        self.engine.submit(_req())
        assert self.engine.statistics().decision_pipelines == 1

    def test_submit_ten_times(self):
        responses = [self.engine.submit(_req()) for _ in range(10)]
        assert all(r.is_success for r in responses)

    def test_response_is_frozen(self):
        r = self.engine.submit(_req())
        with pytest.raises(Exception):
            r.status = DecisionResponseStatus.FAILED  # type: ignore[misc]

    def test_query_after_submit(self):
        r = self.engine.submit(_req())
        found = self.engine.query(r.session_id)
        assert found is not None
        assert found.request_id == r.request_id


# ===========================================================================
# 4. Async scheduling
# ===========================================================================

class TestScheduling:
    def test_schedule_adds_to_queue(self):
        engine = DecisionEngine()
        engine.start()
        # Stop workers so queue doesn't drain
        for w in engine._workers:
            w.stop()
        engine._workers.clear()
        try:
            req = _req()
            engine.schedule(req)
            assert engine.status().queued_requests >= 1
        finally:
            engine.stop()

    def test_cancel_removes_from_queue(self):
        engine = DecisionEngine()
        engine.start()
        for w in engine._workers:
            w.stop()
        engine._workers.clear()
        try:
            req = _req()
            engine.schedule(req)
            assert engine.cancel(req.request_id)
        finally:
            engine.stop()

    def test_cancel_nonexistent_returns_false(self):
        engine = _engine()
        try:
            assert not engine.cancel("nonexistent")
        finally:
            engine.stop()

    def test_scheduler_priority_ordering(self):
        sched = DecisionScheduler()
        r_low  = DecisionRequest.create("d-low",  priority=DecisionPriority.LOW)
        r_high = DecisionRequest.create("d-high", priority=DecisionPriority.HIGH)
        r_crit = DecisionRequest.create("d-crit", priority=DecisionPriority.CRITICAL)
        sched.schedule(r_low)
        sched.schedule(r_high)
        sched.schedule(r_crit)
        assert sched.next().priority == DecisionPriority.CRITICAL
        assert sched.next().priority == DecisionPriority.HIGH

    def test_scheduler_cancel(self):
        sched = DecisionScheduler()
        r = DecisionRequest.create("d")
        sched.schedule(r)
        sched.cancel(r.request_id)
        assert sched.next() is None

    def test_scheduler_clear(self):
        sched = DecisionScheduler()
        for _ in range(5):
            sched.schedule(DecisionRequest.create("d"))
        sched.clear()
        assert sched.is_empty()

    def test_scheduler_pending_count(self):
        sched = DecisionScheduler()
        for _ in range(3):
            sched.schedule(DecisionRequest.create("d"))
        assert sched.pending_count() == 3

    def test_scheduler_max_queue(self):
        sched = DecisionScheduler(max_queue=1)
        sched.schedule(DecisionRequest.create("d"))
        with pytest.raises(RuntimeError):
            sched.schedule(DecisionRequest.create("d2"))

    def test_total_scheduled(self):
        sched = DecisionScheduler()
        for _ in range(5):
            sched.schedule(DecisionRequest.create("d"))
        assert sched.total_scheduled() == 5


# ===========================================================================
# 5. Pipeline state machine
# ===========================================================================

class TestPipelineStateMachine:
    def setup_method(self):
        self.fac = DecisionEngineFactory()

    def test_initial_state(self):
        p = self.fac.create_pipeline(decision_id="d")
        assert p.state == PipelineState.IDLE

    def test_happy_path(self):
        p = self.fac.create_pipeline(decision_id="d")
        p.start()
        p.begin_collecting()
        p.begin_validating()
        p.begin_dispatching()
        p.begin_evaluating()
        p.begin_publishing()
        p.complete()
        assert p.state == PipelineState.COMPLETED
        assert p.is_terminal

    def test_fail_from_collecting(self):
        p = self.fac.create_pipeline(decision_id="d")
        p.start()
        p.begin_collecting()
        p.fail("error")
        assert p.state == PipelineState.FAILED
        assert p.failure_reason == "error"

    def test_fail_from_idle(self):
        p = self.fac.create_pipeline(decision_id="d")
        p.fail("immediate")
        assert p.state == PipelineState.FAILED

    def test_cancel_from_idle(self):
        p = self.fac.create_pipeline(decision_id="d")
        p.cancel()
        assert p.state == PipelineState.CANCELLED

    def test_stop_from_collecting(self):
        p = self.fac.create_pipeline(decision_id="d")
        p.start()
        p.begin_collecting()
        p.stop()
        assert p.state == PipelineState.STOPPED

    def test_collection_time(self):
        p = self.fac.create_pipeline(decision_id="d")
        p.start()
        p.begin_collecting()
        time.sleep(0.01)
        p.begin_validating()
        assert p.collection_time_s >= 0.01

    def test_total_time(self):
        p = self.fac.create_pipeline(decision_id="d")
        p.start()
        p.begin_collecting()
        p.begin_validating()
        p.begin_dispatching()
        p.begin_evaluating()
        p.begin_publishing()
        p.complete()
        assert p.total_time_s > 0.0

    def test_add_get_input(self):
        p = self.fac.create_pipeline(decision_id="d")
        p.add_input("price", 100.0)
        assert p.get_input("price") == 100.0

    def test_add_get_result(self):
        p = self.fac.create_pipeline(decision_id="d")
        p.add_result("policy", {"ok": True})
        assert p.get_result("policy") == {"ok": True}

    def test_to_dict(self):
        p = self.fac.create_pipeline(decision_id="d")
        d = p.to_dict()
        assert "pipeline_id" in d
        assert "state" in d

    def test_invalid_transition_raises(self):
        p = self.fac.create_pipeline(decision_id="d")
        with pytest.raises(DecisionPipelineError):
            p.begin_collecting()  # IDLE → COLLECTING is invalid

    def test_all_states_in_machine(self):
        for state in PipelineState:
            assert state in PIPELINE_VALID_TRANSITIONS

    def test_terminal_states_no_outgoing(self):
        for ts in PIPELINE_TERMINAL_STATES:
            assert len(PIPELINE_VALID_TRANSITIONS[ts]) == 0

    def test_retry_collecting(self):
        p = self.fac.create_pipeline(decision_id="d")
        p.start()
        p.begin_collecting()
        p.begin_validating()
        p.retry_collecting()
        assert p.state == PipelineState.COLLECTING


# ===========================================================================
# 6. Dispatcher
# ===========================================================================

class TestDispatcher:
    def setup_method(self):
        self.fac        = DecisionEngineFactory()
        self.dispatcher = DecisionDispatcher()

    def _validating_pipeline(self) -> DecisionPipeline:
        p = self.fac.create_pipeline(decision_id="d")
        p.start()
        p.begin_collecting()
        p.begin_validating()
        return p

    def _context(self) -> DecisionEngineContext:
        return DecisionEngineContext(
            context_id  = str(uuid.uuid4()),
            request_id  = "req-1",
            session_id  = "sess-1",
            pipeline_id = "pipe-1",
            decision_id = "d-1",
        )

    def test_dispatch_no_frameworks(self):
        p      = self._validating_pipeline()
        result = self.dispatcher.dispatch(p, self._context())
        assert "policy" in result
        assert "optimization" in result
        assert p.state == PipelineState.PUBLISHING

    def test_dispatch_with_policy(self):
        class FP:
            def evaluate(self, ctx, inputs):
                return {"approved": True}
        self.dispatcher.set_policy_framework(FP())
        p      = self._validating_pipeline()
        result = self.dispatcher.dispatch(p, self._context())
        assert result["policy"]["approved"] is True

    def test_dispatch_with_optimization(self):
        class FO:
            def optimize(self, ctx, pr, inputs):
                return {"size": 100}
        self.dispatcher.set_optimization_framework(FO())
        p      = self._validating_pipeline()
        result = self.dispatcher.dispatch(p, self._context())
        assert result["optimization"]["size"] == 100

    def test_policy_error_fails_pipeline(self):
        class BP:
            def evaluate(self, ctx, inputs):
                raise RuntimeError("boom")
        self.dispatcher.set_policy_framework(BP())
        p = self._validating_pipeline()
        with pytest.raises(DecisionDispatchError):
            self.dispatcher.dispatch(p, self._context())
        assert p.state == PipelineState.FAILED

    def test_optimization_error_fails_pipeline(self):
        class BO:
            def optimize(self, ctx, pr, inputs):
                raise RuntimeError("opt boom")
        self.dispatcher.set_optimization_framework(BO())
        p = self._validating_pipeline()
        with pytest.raises(DecisionDispatchError):
            self.dispatcher.dispatch(p, self._context())
        assert p.state == PipelineState.FAILED

    def test_has_policy_false(self):
        assert not self.dispatcher.has_policy_framework

    def test_has_policy_true(self):
        class F:
            def evaluate(self, c, i): ...
        self.dispatcher.set_policy_framework(F())
        assert self.dispatcher.has_policy_framework

    def test_has_optimization_false(self):
        assert not self.dispatcher.has_optimization_framework


# ===========================================================================
# 7. Validation
# ===========================================================================

class TestValidationUnit:
    def setup_method(self):
        self.validator = DecisionEngineValidator()

    def test_valid_request(self):
        r = self.validator.validate_request(_req(), engine_running=True)
        assert r.is_valid

    def test_all_six_checks_present(self):
        r = self.validator.validate_request(_req(), engine_running=True)
        codes = {c.code for c in r.checks}
        for code in EngineValidationCode:
            assert code in codes

    def test_empty_request_id_fails(self):
        import dataclasses
        req = dataclasses.replace(_req(), request_id="  ")
        r   = self.validator.validate_request(req, engine_running=True)
        assert EngineValidationCode.SESSION_VALIDITY in r.failed_checks

    def test_engine_not_running_fails_health(self):
        r = self.validator.validate_request(_req(), engine_running=False)
        assert EngineValidationCode.SUBSYSTEM_HEALTH in r.failed_checks

    def test_terminal_pipeline_fails_consistency(self):
        fac  = DecisionEngineFactory()
        pipe = fac.create_pipeline(decision_id="d")
        pipe.fail("forced")
        r = self.validator.validate_request(_req(), engine_running=True, pipeline=pipe)
        assert EngineValidationCode.PIPELINE_CONSISTENCY in r.failed_checks

    def test_empty_decision_id_fails(self):
        req = DecisionRequest.create("")
        r   = self.validator.validate_request(req, engine_running=True)
        assert EngineValidationCode.LIFECYCLE_CONSISTENCY in r.failed_checks

    def test_none_inputs_fails_snapshot(self):
        import dataclasses
        req = dataclasses.replace(_req(), inputs=None)
        r   = self.validator.validate_request(req, engine_running=True)
        assert EngineValidationCode.SNAPSHOT_CONSISTENCY in r.failed_checks

    def test_passed_count_valid(self):
        r = self.validator.validate_request(_req(), engine_running=True)
        assert r.passed_count == 6

    def test_failed_count_zero_on_valid(self):
        r = self.validator.validate_request(_req(), engine_running=True)
        assert r.failed_count == 0


class TestValidationIntegration:
    def setup_method(self): self.engine = _engine()
    def teardown_method(self): self.engine.stop()

    def test_validate_passes_when_running(self):
        r = self.engine.validate(_req())
        assert r.is_valid

    def test_six_checks(self):
        r = self.engine.validate(_req())
        assert r.passed_count == 6


# ===========================================================================
# 8. Statistics
# ===========================================================================

class TestStatisticsUnit:
    def setup_method(self):
        self.stats = DecisionEngineStatistics()

    def test_initial_zero(self):
        assert self.stats.decision_sessions   == 0
        assert self.stats.decision_requests   == 0
        assert self.stats.decision_pipelines  == 0
        assert self.stats.average_decision_time_s   == 0.0
        assert self.stats.average_collection_time_s == 0.0
        assert self.stats.average_dispatch_time_s   == 0.0
        assert self.stats.subsystem_availability    == 1.0

    def test_record_session(self):
        self.stats.record_session_created()
        assert self.stats.decision_sessions == 1

    def test_record_request(self):
        self.stats.record_request_submitted()
        assert self.stats.decision_requests == 1

    def test_record_pipeline(self):
        self.stats.record_pipeline_executed(
            total_time_s=2.0, collection_time_s=0.5, dispatch_time_s=1.0
        )
        assert self.stats.decision_pipelines       == 1
        assert self.stats.average_decision_time_s  == pytest.approx(2.0)

    def test_ema_smoothing(self):
        self.stats.record_pipeline_executed(total_time_s=10.0)
        self.stats.record_pipeline_executed(total_time_s=20.0)
        assert 10.0 < self.stats.average_decision_time_s < 20.0

    def test_health_availability(self):
        self.stats.record_health_check(True)
        self.stats.record_health_check(True)
        self.stats.record_health_check(False)
        assert pytest.approx(2/3, abs=0.01) == self.stats.subsystem_availability

    def test_throughput_count(self):
        self.stats.record_pipeline_executed(total_time_s=0.0)
        self.stats.record_pipeline_executed(total_time_s=0.0)
        assert self.stats.decision_throughput == 2.0

    def test_reset(self):
        self.stats.record_session_created()
        self.stats.reset()
        assert self.stats.decision_sessions == 0

    def test_snapshot_eight_keys(self):
        d = self.stats.snapshot()
        assert len(d) == 8

    def test_thread_safety(self):
        errors = []
        def work():
            try:
                for _ in range(100):
                    self.stats.record_session_created()
                    self.stats.record_request_submitted()
                    self.stats.record_pipeline_executed(total_time_s=0.1)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=work) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert self.stats.decision_sessions  == 1000
        assert self.stats.decision_requests  == 1000
        assert self.stats.decision_pipelines == 1000


class TestStatisticsIntegration:
    def setup_method(self): self.engine = _engine()
    def teardown_method(self): self.engine.stop()

    def test_submit_updates_stats(self):
        self.engine.submit(_req())
        st = self.engine.statistics()
        assert st.decision_requests  >= 1
        assert st.decision_pipelines >= 1


# ===========================================================================
# 9. History
# ===========================================================================

class TestHistory:
    def setup_method(self):
        self.hist = DecisionEngineHistory(max_events=10, max_responses=10)

    def test_record_event(self):
        e = make_decision_engine_initialized("s", "r", "d")
        self.hist.record_event(e)
        assert self.hist.event_count() == 1

    def test_record_response(self):
        snap = DecisionSnapshot("sid", "req", "sess", "pipe", "d")
        r = DecisionResponse.success("req", "sess", "d", snap)
        self.hist.record_response(r)
        assert self.hist.response_count() == 1

    def test_latest_event(self):
        e = make_decision_engine_started("s", "r", "d")
        self.hist.record_event(e)
        assert self.hist.latest_event() is e

    def test_latest_response(self):
        r = DecisionResponse.failure("req", "sess", "d", error="x")
        self.hist.record_response(r)
        assert self.hist.latest_response() is r

    def test_events_for_session(self):
        e = make_decision_engine_started("my-sess", "r", "d")
        self.hist.record_event(e)
        assert len(self.hist.events_for_session("my-sess")) == 1

    def test_events_for_decision(self):
        e = make_decision_engine_completed("s", "r", "my-d")
        self.hist.record_event(e)
        assert len(self.hist.events_for_decision("my-d")) == 1

    def test_events_by_type(self):
        self.hist.record_event(make_decision_engine_initialized("s", "r", "d"))
        self.hist.record_event(make_decision_engine_failed("s", "r", "d"))
        assert len(self.hist.events_by_type(DecisionEngineEventType.DECISION_INITIALIZED)) == 1

    def test_bounded_events(self):
        for _ in range(15):
            self.hist.record_event(make_decision_engine_started("s", "r", "d"))
        assert self.hist.event_count() == 10

    def test_responses_for_decision(self):
        r = DecisionResponse.failure("req", "sess", "my-d", error="x")
        self.hist.record_response(r)
        assert len(self.hist.responses_for_decision("my-d")) == 1

    def test_clear(self):
        self.hist.record_event(make_decision_engine_started("s", "r", "d"))
        self.hist.clear()
        assert self.hist.event_count()    == 0
        assert self.hist.response_count() == 0

    def test_latest_event_none(self):
        assert self.hist.latest_event() is None

    def test_latest_response_none(self):
        assert self.hist.latest_response() is None


class TestHistoryIntegration:
    def setup_method(self): self.engine = _engine()
    def teardown_method(self): self.engine.stop()

    def test_submit_populates_history(self):
        self.engine.submit(_req(decision_id="hist-d"))
        evts = self.engine.history().events_for_decision("hist-d")
        assert len(evts) > 0

    def test_submit_populates_responses(self):
        self.engine.submit(_req())
        assert self.engine.history().response_count() >= 1


# ===========================================================================
# 10. Health
# ===========================================================================

class TestHealth:
    def setup_method(self): self.engine = _engine()
    def teardown_method(self): self.engine.stop()

    def test_health_healthy(self):
        h = self.engine.health()
        assert h.overall == EngineHealthStatus.HEALTHY
        assert h.is_healthy

    def test_health_has_subsystems(self):
        h = self.engine.health()
        assert h.total_subsystems > 0

    def test_assess_all_healthy(self):
        h = assess_engine_health(engine_running=True)
        assert h.overall == EngineHealthStatus.HEALTHY

    def test_assess_engine_unhealthy(self):
        h = assess_engine_health(engine_running=False)
        assert h.overall == EngineHealthStatus.UNHEALTHY

    def test_assess_subsystem_unhealthy(self):
        h = assess_engine_health(engine_running=True, lifecycle_ok=False)
        assert h.overall == EngineHealthStatus.UNHEALTHY

    def test_subsystem_health_frozen(self):
        sh = SubsystemHealth(name="test", status=EngineHealthStatus.HEALTHY)
        with pytest.raises(Exception):
            sh.name = "mutate"  # type: ignore[misc]

    def test_health_updates_stats(self):
        self.engine.health()
        avail = self.engine.statistics().subsystem_availability
        assert avail > 0.0


# ===========================================================================
# 11. Status
# ===========================================================================

class TestStatus:
    def setup_method(self): self.engine = _engine()
    def teardown_method(self): self.engine.stop()

    def test_status_running(self):
        st = self.engine.status()
        assert st.is_running

    def test_status_has_uptime(self):
        time.sleep(0.01)
        assert self.engine.status().uptime_s >= 0.0

    def test_status_after_submit(self):
        self.engine.submit(_req())
        assert self.engine.status().completed_total >= 1

    def test_build_engine_status(self):
        st = build_engine_status(
            EngineOperationalStatus.RUNNING,
            active_sessions  = 5,
            active_pipelines = 3,
            completed_total  = 100,
        )
        assert st.active_sessions  == 5
        assert st.active_pipelines == 3
        assert st.completed_total  == 100

    def test_status_to_dict(self):
        d = self.engine.status().to_dict()
        assert "operational" in d
        assert "active_sessions" in d

    def test_status_frozen(self):
        st = self.engine.status()
        with pytest.raises(Exception):
            st.operational = EngineOperationalStatus.STOPPED  # type: ignore[misc]


# ===========================================================================
# 12. Registry
# ===========================================================================

class TestRegistry:
    def setup_method(self):
        self.reg = DecisionEngineRegistry(max_active=10, max_completed=20)
        self.fac = DecisionEngineFactory()

    def test_register_and_get_pipeline(self):
        p = self.fac.create_pipeline(decision_id="d")
        self.reg.register_pipeline(p)
        assert self.reg.get_pipeline(p.pipeline_id) is p

    def test_register_request(self):
        r = _req()
        self.reg.register_request(r)
        assert self.reg.find_request(r.request_id) is r

    def test_move_to_completed(self):
        p = self.fac.create_pipeline(decision_id="d")
        self.reg.register_pipeline(p)
        self.reg.move_to_completed(p.pipeline_id)
        assert self.reg.get_pipeline(p.pipeline_id) is None
        assert self.reg.find_completed(p.pipeline_id) is p

    def test_find_any(self):
        p = self.fac.create_pipeline(decision_id="d")
        self.reg.register_pipeline(p)
        self.reg.move_to_completed(p.pipeline_id)
        assert self.reg.find_any(p.pipeline_id) is p

    def test_active_count(self):
        for _ in range(3):
            self.reg.register_pipeline(self.fac.create_pipeline(decision_id="d"))
        assert self.reg.active_count() == 3

    def test_cap_raises(self):
        reg = DecisionEngineRegistry(max_active=2)
        reg.register_pipeline(self.fac.create_pipeline(decision_id="d"))
        reg.register_pipeline(self.fac.create_pipeline(decision_id="d"))
        with pytest.raises(RuntimeError):
            reg.register_pipeline(self.fac.create_pipeline(decision_id="d"))

    def test_pipelines_for_decision(self):
        for _ in range(3):
            self.reg.register_pipeline(self.fac.create_pipeline(decision_id="shared"))
        assert len(self.reg.pipelines_for_decision("shared")) == 3

    def test_request_not_found_raises(self):
        with pytest.raises(DecisionRequestNotFoundError):
            self.reg.get_request("nonexistent")

    def test_clear(self):
        self.reg.register_pipeline(self.fac.create_pipeline(decision_id="d"))
        self.reg.clear()
        assert self.reg.active_count() == 0


# ===========================================================================
# 13. Factory
# ===========================================================================

class TestFactory:
    def setup_method(self):
        self.fac = DecisionEngineFactory()

    def test_create_request(self):
        r = self.fac.create_request("d-1")
        assert r.decision_id == "d-1"

    def test_create_pipeline(self):
        p = self.fac.create_pipeline(decision_id="d-1")
        assert p.state == PipelineState.IDLE

    def test_unique_pipeline_ids(self):
        ids = {self.fac.create_pipeline(decision_id="d").pipeline_id for _ in range(50)}
        assert len(ids) == 50


# ===========================================================================
# 14. Events
# ===========================================================================

class TestEventFactories:
    def test_initialized(self):
        e = make_decision_engine_initialized("s", "r", "d")
        assert e.event_type == DecisionEngineEventType.DECISION_INITIALIZED

    def test_started(self):
        e = make_decision_engine_started("s", "r", "d")
        assert e.event_type == DecisionEngineEventType.DECISION_STARTED

    def test_collected(self):
        e = make_decision_engine_collected("s", "r", "d", collection_time_s=1.0, input_count=3)
        assert e.event_type == DecisionEngineEventType.DECISION_COLLECTED
        assert e.payload["collection_time_s"] == 1.0
        assert e.payload["input_count"] == 3

    def test_dispatched(self):
        e = make_decision_engine_dispatched("s", "r", "d", dispatch_time_s=0.5)
        assert e.event_type == DecisionEngineEventType.DECISION_DISPATCHED
        assert e.payload["dispatch_time_s"] == 0.5

    def test_completed(self):
        e = make_decision_engine_completed("s", "r", "d", total_time_s=2.0)
        assert e.event_type == DecisionEngineEventType.DECISION_COMPLETED
        assert e.payload["total_time_s"] == 2.0

    def test_published(self):
        e = make_decision_engine_published("s", "r", "d", snapshot_id="snap-1")
        assert e.event_type == DecisionEngineEventType.DECISION_PUBLISHED
        assert e.payload["snapshot_id"] == "snap-1"

    def test_failed(self):
        e = make_decision_engine_failed("s", "r", "d", reason="bad")
        assert e.event_type == DecisionEngineEventType.DECISION_FAILED
        assert e.payload["reason"] == "bad"

    def test_stopped(self):
        e = make_decision_engine_stopped("s", "r", "d", reason="shutdown")
        assert e.event_type == DecisionEngineEventType.DECISION_STOPPED

    def test_all_eight_types(self):
        assert len(list(DecisionEngineEventType)) == 8

    def test_event_frozen(self):
        e = make_decision_engine_initialized("s", "r", "d")
        with pytest.raises(Exception):
            e.event_id = "mutate"  # type: ignore[misc]

    def test_unique_event_ids(self):
        e1 = make_decision_engine_initialized("s", "r", "d")
        e2 = make_decision_engine_initialized("s", "r", "d")
        assert e1.event_id != e2.event_id


class TestAllEventTypesFromSubmit:
    def setup_method(self): self.engine = _engine()
    def teardown_method(self): self.engine.stop()

    def test_workflow_events_emitted(self):
        resp = self.engine.submit(_req(decision_id="ev-d"))
        evts = self.engine.history().events_for_decision("ev-d")
        found = {e.event_type for e in evts}
        for et in [
            DecisionEngineEventType.DECISION_INITIALIZED,
            DecisionEngineEventType.DECISION_STARTED,
            DecisionEngineEventType.DECISION_COLLECTED,
            DecisionEngineEventType.DECISION_DISPATCHED,
            DecisionEngineEventType.DECISION_PUBLISHED,
            DecisionEngineEventType.DECISION_COMPLETED,
        ]:
            assert et in found, f"Missing: {et}"


# ===========================================================================
# 15. Context and Snapshot
# ===========================================================================

class TestContextSnapshot:
    def test_context_from_request(self):
        req = _req(decision_id="ctx-d", workflow_id="wf-1")
        ctx = DecisionEngineContext.from_request(req, session_id="s-1", pipeline_id="p-1")
        assert ctx.decision_id == "ctx-d"
        assert ctx.workflow_id == "wf-1"
        assert ctx.session_id  == "s-1"

    def test_context_frozen(self):
        ctx = DecisionEngineContext.from_request(_req(), session_id="s", pipeline_id="p")
        with pytest.raises(Exception):
            ctx.decision_id = "mutate"  # type: ignore[misc]

    def test_context_inherits_inputs(self):
        req = _req(inputs={"price": 50.0})
        ctx = DecisionEngineContext.from_request(req, session_id="s", pipeline_id="p")
        assert ctx.inputs == {"price": 50.0}

    def test_snapshot_frozen(self):
        s = DecisionSnapshot("sid", "req", "sess", "pipe", "d")
        with pytest.raises(Exception):
            s.snapshot_id = "mutate"  # type: ignore[misc]

    def test_response_success(self):
        snap = DecisionSnapshot("sid", "req", "sess", "pipe", "d")
        r = DecisionResponse.success("req", "sess", "d", snap, total_time_s=1.5)
        assert r.is_success
        assert r.total_time_s == 1.5

    def test_response_failure(self):
        r = DecisionResponse.failure("req", "sess", "d", error="oops")
        assert r.is_failed
        assert r.error == "oops"
        assert r.snapshot is None


# ===========================================================================
# 16. Listeners
# ===========================================================================

class TestListeners:
    def setup_method(self): self.engine = _engine()
    def teardown_method(self): self.engine.stop()

    def test_listener_called(self):
        received = []
        self.engine.add_listener(received.append)
        self.engine.submit(_req())
        assert len(received) > 0

    def test_listener_removed(self):
        received = []
        self.engine.add_listener(received.append)
        self.engine.remove_listener(received.append)
        self.engine.submit(_req())
        assert len(received) == 0

    def test_faulty_listener_no_crash(self):
        def bad(e):
            raise RuntimeError("bad")
        self.engine.add_listener(bad)
        self.engine.submit(_req())  # should not raise


# ===========================================================================
# 17. Framework injection
# ===========================================================================

class TestFrameworkInjection:
    def setup_method(self): self.engine = _engine()
    def teardown_method(self): self.engine.stop()

    def test_inject_policy(self):
        class FP:
            def evaluate(self, ctx, inputs):
                return {"approved": True}
        self.engine.set_policy_framework(FP())
        resp = self.engine.submit(_req())
        assert resp.snapshot.dispatch_results["policy"]["approved"] is True

    def test_inject_optimization(self):
        class FO:
            def optimize(self, ctx, pr, inputs):
                return {"size": 200}
        self.engine.set_optimization_framework(FO())
        resp = self.engine.submit(_req())
        assert resp.snapshot.dispatch_results["optimization"]["size"] == 200

    def test_inject_both(self):
        class FP:
            def evaluate(self, ctx, inputs): return {"p": "ok"}
        class FO:
            def optimize(self, ctx, pr, inputs): return {"o": "ok"}
        self.engine.set_policy_framework(FP())
        self.engine.set_optimization_framework(FO())
        resp = self.engine.submit(_req())
        assert resp.snapshot.dispatch_results["policy"]["p"]      == "ok"
        assert resp.snapshot.dispatch_results["optimization"]["o"] == "ok"

    def test_policy_error_returns_failed_response(self):
        class BP:
            def evaluate(self, ctx, inputs):
                raise RuntimeError("boom")
        self.engine.set_policy_framework(BP())
        resp = self.engine.submit(_req())
        assert resp.is_failed
        assert "boom" in resp.error


# ===========================================================================
# 18. Concurrency
# ===========================================================================

class TestConcurrency:
    def test_parallel_submits(self):
        engine  = _engine()
        results = []
        errors  = []
        lock    = threading.Lock()

        def submit():
            try:
                r = engine.submit(_req())
                with lock:
                    results.append(r)
            except Exception as e:
                with lock:
                    errors.append(e)

        try:
            threads = [threading.Thread(target=submit) for _ in range(50)]
            for t in threads: t.start()
            for t in threads: t.join()
            assert not errors
            assert len(results) == 50
        finally:
            engine.stop()

    def test_parallel_statistics(self):
        stats  = DecisionEngineStatistics()
        errors = []

        def work():
            try:
                for _ in range(100):
                    stats.record_request_submitted()
                    stats.record_pipeline_executed(total_time_s=0.1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=work) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert stats.decision_requests  == 1000
        assert stats.decision_pipelines == 1000

    def test_concurrent_registry(self):
        reg    = DecisionEngineRegistry(max_active=1000)
        fac    = DecisionEngineFactory()
        errors = []

        def ops():
            try:
                p = fac.create_pipeline(decision_id="d")
                reg.register_pipeline(p)
                reg.move_to_completed(p.pipeline_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=ops) for _ in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors


# ===========================================================================
# 19. Stress test
# ===========================================================================

class TestStress:
    def test_100_concurrent_requests(self):
        engine  = _engine(worker_threads=4)
        results = []
        errors  = []
        lock    = threading.Lock()

        def submit():
            try:
                r = engine.submit(_req())
                with lock:
                    results.append(r)
            except Exception as e:
                with lock:
                    errors.append(e)

        try:
            threads = [threading.Thread(target=submit) for _ in range(100)]
            for t in threads: t.start()
            for t in threads: t.join()
            assert not errors
            assert len(results) == 100
            assert all(r.is_success for r in results)
            assert engine.statistics().decision_pipelines == 100
        finally:
            engine.stop()


# ===========================================================================
# 20. Regression — interface contracts
# ===========================================================================

class TestRegression:
    def test_engine_has_all_public_methods(self):
        required = [
            "submit", "schedule", "cancel", "query",
            "history", "statistics", "validate", "health", "status",
            "set_policy_framework", "set_optimization_framework",
            "add_listener", "remove_listener",
        ]
        for m in required:
            assert hasattr(DecisionEngine, m), f"Missing: {m}"

    def test_all_eight_event_types(self):
        assert len(list(DecisionEngineEventType)) == 8

    def test_all_six_validation_codes(self):
        assert len(list(EngineValidationCode)) == 6

    def test_all_eleven_pipeline_states(self):
        assert len(list(PipelineState)) == 11

    def test_all_decision_modes(self):
        modes = {m.value for m in DecisionMode}
        for m in ("real_time", "event_driven", "scheduled", "manual", "priority", "batch"):
            assert m in modes

    def test_response_statuses(self):
        statuses = {s.value for s in DecisionResponseStatus}
        for s in ("success", "failed", "partial", "timeout"):
            assert s in statuses

    def test_exception_hierarchy(self):
        for cls in [
            DecisionEngineNotRunningError,
            DecisionRequestValidationError,
            DecisionPipelineError,
            DecisionSessionError,
            DecisionDispatchError,
            DecisionPublishError,
            DecisionCollectionError,
        ]:
            assert issubclass(cls, DecisionEngineError)

    def test_priority_ordering(self):
        assert DecisionPriority.CRITICAL < DecisionPriority.HIGH
        assert DecisionPriority.HIGH     < DecisionPriority.MEDIUM
        assert DecisionPriority.MEDIUM   < DecisionPriority.LOW

    def test_request_fields(self):
        r = DecisionRequest.create("d")
        for attr in [
            "request_id", "decision_id", "workflow_id", "portfolio_id",
            "strategy_id", "decision_mode", "decision_reason",
            "priority", "deadline_s", "inputs", "metadata", "requested_at",
        ]:
            assert hasattr(r, attr), f"Missing: {attr}"

    def test_snapshot_fields(self):
        s = DecisionSnapshot("sid", "req", "sess", "pipe", "d")
        for attr in [
            "snapshot_id", "request_id", "session_id", "pipeline_id",
            "decision_id", "collection_inputs", "dispatch_results",
            "collection_time_s", "dispatch_time_s", "total_time_s",
        ]:
            assert hasattr(s, attr), f"Missing: {attr}"

    def test_response_fields(self):
        r = DecisionResponse.failure("req", "sess", "d")
        for attr in [
            "response_id", "request_id", "session_id", "decision_id",
            "status", "snapshot", "error", "responded_at",
        ]:
            assert hasattr(r, attr), f"Missing: {attr}"

    def test_statistics_eight_counters(self):
        assert len(DecisionEngineStatistics().snapshot()) == 8

    def test_version_string(self):
        from iios.decision.engine.constants import VERSION
        assert VERSION == "1.0.0"
