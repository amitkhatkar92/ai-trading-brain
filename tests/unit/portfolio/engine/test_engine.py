"""
tests/unit/portfolio/engine/test_engine.py
==========================================
Comprehensive unit tests for the Portfolio Engine subsystem (C10 M2).

Coverage targets:
- constants, state machine, enums
- exceptions (all 10 subclasses)
- PortfolioContext.create() / to_dict()
- PortfolioRequest.create() / with_inputs() / to_dict()
- PortfolioSnapshot / PortfolioResponse — all properties and factories
- PipelineStage / PortfolioPipeline — lifecycle
- PortfolioScheduler — add, priority ordering, cancel, clear
- PortfolioDispatcher — dispatch w/wo frameworks, framework registration
- PortfolioEngineValidator — all 6 checks
- PortfolioEngineHealth — report, is_healthy, unavailable
- PortfolioEngineStatus — to_dict
- PortfolioEngineStatistics — all counters, EMA, reset
- PortfolioEngineHistory — bounded, queries
- PortfolioEngineEvent / all 8 factories
- PortfolioEngineFactory — create_request, create_pipeline, etc.
- PortfolioSessionManager — create, advance, fail sessions
- PortfolioEngineRegistry — register, update, query pipelines
- PortfolioManager — run_workflow success / failure
- PortfolioEngine — full happy path, all named operations,
  guard, listeners, statistics, history, health, status,
  concurrency, stress
"""
from __future__ import annotations

import threading
import time
from typing import List
from unittest.mock import MagicMock

import pytest

from iios.portfolio.engine import (
    # Primary interface
    PortfolioEngine,
    # Request / Response / Snapshot
    PortfolioRequest,
    PortfolioResponse,
    PortfolioSnapshot,
    # Context
    PortfolioContext,
    # Domain objects
    PortfolioPipeline,
    PipelineStage,
    PortfolioEngineEvent,
    # Sub-components
    PortfolioDispatcher,
    PortfolioEngineFactory,
    PortfolioEngineHealth,
    PortfolioEngineHistory,
    PortfolioEngineRegistry,
    PortfolioEngineStatistics,
    PortfolioEngineStatus,
    PortfolioEngineValidator,
    PortfolioScheduler,
    SubsystemHealthRecord,
    # Validation
    PortfolioValidationCheckResult,
    PortfolioValidationResult,
    # Enums
    EngineState,
    PipelineStatus,
    PortfolioEventType,
    PortfolioWorkflowType,
    ResponseStatus,
    SchedulerPriority,
    ValidationCode,
    # Exceptions
    PortfolioEngineError,
    PortfolioEngineNotRunningError,
    PortfolioSessionError,
    PortfolioPipelineError,
    PortfolioDispatchError,
    PortfolioCollectionError,
    PortfolioPublicationError,
    PortfolioEngineValidationError,
    PortfolioSchedulerError,
    PortfolioCapacityError,
    # Constants
    ACTIVE_ENGINE_STATES,
    TERMINAL_ENGINE_STATES,
    VALID_ENGINE_TRANSITIONS,
    # Event factories
    make_portfolio_initialized,
    make_portfolio_started,
    make_portfolio_collected,
    make_portfolio_dispatched,
    make_portfolio_published,
    make_portfolio_completed,
    make_portfolio_failed,
    make_portfolio_stopped,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _started_engine(**kw) -> PortfolioEngine:
    e = PortfolioEngine(**kw)
    e.start()
    return e


def _request(
    portfolio_id:  str = "pf-001",
    workflow_type: PortfolioWorkflowType = PortfolioWorkflowType.PORTFOLIO_CREATION,
    **kw,
) -> PortfolioRequest:
    return PortfolioRequest.create(portfolio_id, workflow_type, **kw)


def _full_submit(engine: PortfolioEngine, portfolio_id: str = "pf-001") -> PortfolioResponse:
    req = _request(portfolio_id)
    return engine.submit(req)


# ===========================================================================
# Constants
# ===========================================================================

class TestConstants:
    def test_active_engine_states(self):
        for s in [
            EngineState.INITIALIZING,
            EngineState.COLLECTING,
            EngineState.VALIDATING,
            EngineState.DISPATCHING,
            EngineState.ALLOCATING,
            EngineState.REBALANCING,
            EngineState.PUBLISHING,
        ]:
            assert s in ACTIVE_ENGINE_STATES

    def test_terminal_engine_states(self):
        assert EngineState.COMPLETED in TERMINAL_ENGINE_STATES
        assert EngineState.FAILED    in TERMINAL_ENGINE_STATES
        assert EngineState.STOPPED   in TERMINAL_ENGINE_STATES

    def test_idle_not_in_active_or_terminal(self):
        assert EngineState.IDLE not in ACTIVE_ENGINE_STATES
        assert EngineState.IDLE not in TERMINAL_ENGINE_STATES

    def test_valid_transitions_idle(self):
        allowed = VALID_ENGINE_TRANSITIONS[EngineState.IDLE]
        assert EngineState.INITIALIZING in allowed
        assert EngineState.STOPPED      in allowed

    def test_valid_transitions_stopped_is_empty(self):
        assert not VALID_ENGINE_TRANSITIONS[EngineState.STOPPED]

    def test_workflow_types_all_present(self):
        expected = {
            "portfolio_creation", "portfolio_update", "portfolio_validation",
            "portfolio_rebalancing", "capital_allocation", "exposure_management",
            "risk_synchronization", "portfolio_synchronization", "portfolio_closure",
        }
        actual = {wt.value for wt in PortfolioWorkflowType}
        assert expected == actual

    def test_event_types_all_present(self):
        assert len(list(PortfolioEventType)) == 8


# ===========================================================================
# Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert isinstance(PortfolioEngineError("x"), IIOSError)
        assert PortfolioEngineError("x").error_code == "PE-000"

    def test_not_running(self):
        e = PortfolioEngineNotRunningError()
        assert e.error_code == "PE-001"

    def test_session_error(self):
        e = PortfolioSessionError("bad", session_id="s1")
        assert e.error_code == "PE-002"
        assert e.session_id == "s1"

    def test_pipeline_error(self):
        e = PortfolioPipelineError("bad", pipeline_id="p1")
        assert e.error_code == "PE-003"
        assert e.pipeline_id == "p1"

    def test_dispatch_error(self):
        e = PortfolioDispatchError("bad", workflow_type="portfolio_creation")
        assert e.error_code == "PE-004"

    def test_collection_error(self):
        e = PortfolioCollectionError("bad", missing_inputs=("a", "b"))
        assert e.error_code == "PE-005"
        assert e.missing_inputs == ("a", "b")

    def test_publication_error(self):
        e = PortfolioPublicationError("bad", portfolio_id="pf-1")
        assert e.error_code == "PE-006"

    def test_validation_error(self):
        e = PortfolioEngineValidationError("bad", failed_checks=("x",))
        assert e.error_code == "PE-007"
        assert e.failed_checks == ("x",)

    def test_scheduler_error(self):
        e = PortfolioSchedulerError("bad")
        assert e.error_code == "PE-008"

    def test_capacity_error(self):
        e = PortfolioCapacityError(100)
        assert e.error_code == "PE-009"
        assert e.limit == 100


# ===========================================================================
# PortfolioContext
# ===========================================================================

class TestPortfolioContext:
    def test_create_defaults(self):
        ctx = PortfolioContext.create("pf-001")
        assert ctx.portfolio_id   == "pf-001"
        assert ctx.priority       == SchedulerPriority.NORMAL
        assert ctx.context_id          # non-empty UUID

    def test_create_custom(self):
        ctx = PortfolioContext.create(
            "pf-002",
            workflow_type = PortfolioWorkflowType.PORTFOLIO_REBALANCING,
            priority      = SchedulerPriority.HIGH,
            source        = "test-source",
        )
        assert ctx.workflow_type == PortfolioWorkflowType.PORTFOLIO_REBALANCING
        assert ctx.priority      == SchedulerPriority.HIGH
        assert ctx.source        == "test-source"

    def test_to_dict(self):
        ctx = PortfolioContext.create("pf-003")
        d = ctx.to_dict()
        assert d["portfolio_id"]  == "pf-003"
        assert "workflow_type"    in d
        assert "priority"         in d

    def test_frozen(self):
        ctx = PortfolioContext.create("pf-004")
        with pytest.raises((AttributeError, TypeError)):
            ctx.portfolio_id = "mutated"  # type: ignore[misc]


# ===========================================================================
# PortfolioRequest
# ===========================================================================

class TestPortfolioRequest:
    def test_create_defaults(self):
        req = PortfolioRequest.create("pf-001")
        assert req.portfolio_id   == "pf-001"
        assert req.workflow_type  == PortfolioWorkflowType.PORTFOLIO_CREATION
        assert req.priority       == SchedulerPriority.NORMAL
        assert req.request_id          # non-empty UUID
        assert req.requested_at   > 0

    def test_create_custom(self):
        req = PortfolioRequest.create(
            "pf-002",
            PortfolioWorkflowType.PORTFOLIO_REBALANCING,
            priority = SchedulerPriority.HIGH,
            inputs   = {"decision_snapshot": {"score": 8.0}},
        )
        assert req.workflow_type    == PortfolioWorkflowType.PORTFOLIO_REBALANCING
        assert req.priority         == SchedulerPriority.HIGH
        assert "decision_snapshot"  in req.inputs

    def test_with_inputs(self):
        req  = PortfolioRequest.create("pf-003")
        req2 = req.with_inputs({"order_snapshot": {"count": 5}})
        assert "order_snapshot" in req2.inputs
        assert req2.request_id == req.request_id  # same ID

    def test_frozen(self):
        req = PortfolioRequest.create("pf-004")
        with pytest.raises((AttributeError, TypeError)):
            req.portfolio_id = "mutated"  # type: ignore[misc]

    def test_to_dict(self):
        req = PortfolioRequest.create("pf-005")
        d = req.to_dict()
        assert d["portfolio_id"]  == "pf-005"
        assert "workflow_type"    in d
        assert "input_keys"       in d


# ===========================================================================
# PortfolioSnapshot / PortfolioResponse
# ===========================================================================

class TestPortfolioSnapshot:
    def test_create(self):
        snap = PortfolioSnapshot.create(
            "pf-001", "s1",
            PortfolioWorkflowType.PORTFOLIO_CREATION,
            EngineState.PUBLISHING,
        )
        assert snap.portfolio_id  == "pf-001"
        assert snap.session_id    == "s1"
        assert snap.snapshot_id        # UUID
        assert snap.published_at  > 0

    def test_to_dict(self):
        snap = PortfolioSnapshot.create(
            "pf-002", "s2",
            PortfolioWorkflowType.CAPITAL_ALLOCATION,
            EngineState.ALLOCATING,
            outputs = {"allocated": True},
        )
        d = snap.to_dict()
        assert d["workflow_type"] == "capital_allocation"
        assert d["engine_state"]  == "allocating"
        assert d["outputs"]["allocated"] is True

    def test_frozen(self):
        snap = PortfolioSnapshot.create("pf", "s", PortfolioWorkflowType.PORTFOLIO_UPDATE, EngineState.IDLE)
        with pytest.raises((AttributeError, TypeError)):
            snap.portfolio_id = "mutated"  # type: ignore[misc]


class TestPortfolioResponse:
    def test_create_success(self):
        r = PortfolioResponse.create_success(
            "req-1", "pf-001", PortfolioWorkflowType.PORTFOLIO_CREATION
        )
        assert r.is_success
        assert not r.is_failure
        assert not r.has_snapshot
        assert r.error_message == ""

    def test_create_failure(self):
        r = PortfolioResponse.create_failure(
            "req-2", "pf-001", PortfolioWorkflowType.PORTFOLIO_UPDATE,
            error_message="something failed",
        )
        assert r.is_failure
        assert not r.is_success
        assert r.error_message == "something failed"

    def test_has_snapshot(self):
        snap = PortfolioSnapshot.create(
            "pf", "s", PortfolioWorkflowType.PORTFOLIO_CREATION, EngineState.PUBLISHING
        )
        r = PortfolioResponse.create_success(
            "req-3", "pf", PortfolioWorkflowType.PORTFOLIO_CREATION, snapshot=snap
        )
        assert r.has_snapshot
        assert r.snapshot is snap

    def test_to_dict(self):
        r = PortfolioResponse.create_success("req-4", "pf", PortfolioWorkflowType.PORTFOLIO_CLOSURE)
        d = r.to_dict()
        assert d["status"] == "success"
        assert "workflow_type" in d


# ===========================================================================
# PipelineStage / PortfolioPipeline
# ===========================================================================

class TestPipelineStage:
    def test_create(self):
        s = PipelineStage(
            stage_name   = "collect",
            engine_state = EngineState.COLLECTING,
            status       = PipelineStatus.COMPLETED,
        )
        assert s.stage_name   == "collect"
        assert s.status       == PipelineStatus.COMPLETED
        assert s.elapsed_s    >= 0

    def test_to_dict(self):
        s = PipelineStage(
            stage_name   = "dispatch",
            engine_state = EngineState.DISPATCHING,
            status       = PipelineStatus.RUNNING,
        )
        d = s.to_dict()
        assert d["stage_name"]   == "dispatch"
        assert d["engine_state"] == "dispatching"


class TestPortfolioPipeline:
    def test_initial_state(self):
        p = PortfolioPipeline(
            request_id    = "r1",
            portfolio_id  = "pf-001",
            workflow_type = PortfolioWorkflowType.PORTFOLIO_CREATION,
        )
        assert p.status       == PipelineStatus.PENDING
        assert not p.is_running
        assert not p.is_completed
        assert not p.is_failed
        assert len(p.stages)  == 0

    def test_start_complete(self):
        p = PortfolioPipeline("r1", "pf", PortfolioWorkflowType.PORTFOLIO_UPDATE)
        p.start()
        assert p.is_running
        assert p.started_at > 0
        p.complete()
        assert p.is_completed
        assert p.completed_at > 0

    def test_fail(self):
        p = PortfolioPipeline("r1", "pf", PortfolioWorkflowType.PORTFOLIO_CLOSURE)
        p.start()
        p.fail("test error")
        assert p.is_failed
        assert p.error == "test error"

    def test_add_stage(self):
        p = PortfolioPipeline("r1", "pf", PortfolioWorkflowType.PORTFOLIO_VALIDATION)
        p.start()
        p.add_stage(PipelineStage(
            stage_name   = "collect",
            engine_state = EngineState.COLLECTING,
            status       = PipelineStatus.COMPLETED,
        ))
        assert len(p.stages) == 1

    def test_to_dict(self):
        p = PortfolioPipeline("r1", "pf", PortfolioWorkflowType.PORTFOLIO_CREATION)
        d = p.to_dict()
        assert d["portfolio_id"] == "pf"
        assert d["status"]       == "pending"

    def test_session_id_settable(self):
        p = PortfolioPipeline("r1", "pf", PortfolioWorkflowType.PORTFOLIO_UPDATE)
        p.session_id = "s-123"
        assert p.session_id == "s-123"

    def test_elapsed_s(self):
        p = PortfolioPipeline("r1", "pf", PortfolioWorkflowType.PORTFOLIO_CREATION)
        p.start()
        time.sleep(0.01)
        p.complete()
        assert p.elapsed_s >= 0.0


# ===========================================================================
# PortfolioScheduler
# ===========================================================================

class TestPortfolioScheduler:
    def test_schedule_and_next(self):
        s   = PortfolioScheduler()
        req = _request()
        s.schedule(req)
        got = s.next()
        assert got is req

    def test_priority_ordering(self):
        s    = PortfolioScheduler()
        low  = _request("pf-low")
        high = _request("pf-high")
        s.schedule(low,  SchedulerPriority.LOW)
        s.schedule(high, SchedulerPriority.CRITICAL)
        first = s.next()
        assert first is high

    def test_fifo_within_same_priority(self):
        s   = PortfolioScheduler()
        r1  = _request("pf-1")
        r2  = _request("pf-2")
        s.schedule(r1, SchedulerPriority.NORMAL)
        s.schedule(r2, SchedulerPriority.NORMAL)
        assert s.next().request_id == r1.request_id

    def test_cancel(self):
        s   = PortfolioScheduler()
        req = _request()
        s.schedule(req)
        assert s.cancel(req.request_id)
        assert s.next() is None

    def test_cancel_nonexistent_returns_false(self):
        s = PortfolioScheduler()
        assert not s.cancel("ghost")

    def test_pending_count(self):
        s = PortfolioScheduler()
        s.schedule(_request("a"))
        s.schedule(_request("b"))
        assert s.pending_count() == 2

    def test_capacity_exceeded(self):
        s   = PortfolioScheduler(max_queue_size=1)
        s.schedule(_request("pf-1"))
        with pytest.raises(PortfolioCapacityError):
            s.schedule(_request("pf-2"))

    def test_duplicate_raises(self):
        s   = PortfolioScheduler()
        req = _request()
        s.schedule(req)
        with pytest.raises(PortfolioSchedulerError):
            s.schedule(req)

    def test_clear(self):
        s = PortfolioScheduler()
        s.schedule(_request("a"))
        s.clear()
        assert s.pending_count() == 0

    def test_statistics(self):
        s   = PortfolioScheduler()
        req = _request()
        s.schedule(req)
        s.next()
        stats = s.statistics()
        assert stats["scheduled"]  == 1
        assert stats["dispatched"] == 1


# ===========================================================================
# PortfolioDispatcher
# ===========================================================================

class TestPortfolioDispatcher:
    def test_dispatch_no_frameworks(self):
        d    = PortfolioDispatcher()
        req  = _request()
        pipe = PortfolioPipeline("r1", "pf", req.workflow_type)
        result = d.dispatch(pipe, req)
        assert result is pipe

    def test_dispatch_with_policy_framework(self):
        d = PortfolioDispatcher()
        calls = []
        d.register_policy_framework(lambda p, r: calls.append("policy"))
        req  = _request()
        pipe = PortfolioPipeline("r1", "pf", req.workflow_type)
        d.dispatch(pipe, req)
        assert "policy" in calls

    def test_dispatch_with_optimization_framework(self):
        d = PortfolioDispatcher()
        calls = []
        d.register_optimization_framework(lambda p, r: calls.append("opt"))
        req  = _request()
        pipe = PortfolioPipeline("r1", "pf", req.workflow_type)
        d.dispatch(pipe, req)
        assert "opt" in calls

    def test_dispatch_policy_framework_error_raises(self):
        d = PortfolioDispatcher()
        d.register_policy_framework(lambda p, r: (_ for _ in ()).throw(RuntimeError("m3 fail")))
        req  = _request()
        pipe = PortfolioPipeline("r1", "pf", req.workflow_type)
        with pytest.raises(PortfolioDispatchError):
            d.dispatch(pipe, req)

    def test_has_framework_flags(self):
        d = PortfolioDispatcher()
        assert not d.has_policy_framework
        assert not d.has_optimization_framework
        d.register_policy_framework(lambda p, r: None)
        assert d.has_policy_framework

    def test_unregister_frameworks(self):
        d = PortfolioDispatcher()
        d.register_policy_framework(lambda p, r: None)
        d.unregister_policy_framework()
        assert not d.has_policy_framework

    def test_determine_next_state_allocation(self):
        d = PortfolioDispatcher()
        s = d.determine_next_state(PortfolioWorkflowType.CAPITAL_ALLOCATION)
        assert s == EngineState.ALLOCATING

    def test_determine_next_state_rebalancing(self):
        d = PortfolioDispatcher()
        s = d.determine_next_state(PortfolioWorkflowType.PORTFOLIO_REBALANCING)
        assert s == EngineState.REBALANCING

    def test_determine_next_state_default(self):
        d = PortfolioDispatcher()
        s = d.determine_next_state(PortfolioWorkflowType.PORTFOLIO_VALIDATION)
        assert s == EngineState.PUBLISHING


# ===========================================================================
# PortfolioEngineValidator
# ===========================================================================

class TestPortfolioEngineValidator:
    def test_valid_request_all_pass(self):
        v   = PortfolioEngineValidator()
        req = _request()
        r   = v.validate_request(req)
        assert r.is_valid
        assert r.passed_count == 6
        assert r.failed_count == 0

    def test_empty_portfolio_id_fails(self):
        v   = PortfolioEngineValidator()
        req = PortfolioRequest.create("")
        r   = v.validate_request(req)
        assert not r.is_valid
        assert r.failed_count > 0

    def test_mismatched_workflow_type_fails(self):
        v   = PortfolioEngineValidator()
        ctx = PortfolioContext.create(
            "pf", workflow_type=PortfolioWorkflowType.PORTFOLIO_REBALANCING
        )
        # Force mismatch: request has CREATION but context has REBALANCING
        req = PortfolioRequest(
            request_id    = "rid",
            portfolio_id  = "pf",
            workflow_type = PortfolioWorkflowType.PORTFOLIO_CREATION,
            priority      = SchedulerPriority.NORMAL,
            context       = ctx,
        )
        r = v.validate_request(req)
        assert not r.is_valid

    def test_error_messages_on_failure(self):
        v   = PortfolioEngineValidator()
        req = PortfolioRequest.create("")
        r   = v.validate_request(req)
        assert len(r.error_messages) > 0

    def test_validate_pipeline(self):
        v    = PortfolioEngineValidator()
        pipe = PortfolioPipeline("r1", "pf-001", PortfolioWorkflowType.PORTFOLIO_CREATION)
        r    = v.validate_pipeline(pipe)
        assert r.is_valid

    def test_failed_checks_are_subset_of_checks(self):
        v   = PortfolioEngineValidator()
        req = _request()
        r   = v.validate_request(req)
        for fc in r.failed_checks:
            assert fc in r.checks


# ===========================================================================
# PortfolioEngineHealth
# ===========================================================================

class TestPortfolioEngineHealth:
    def test_initially_healthy(self):
        h = PortfolioEngineHealth()
        assert h.is_healthy()

    def test_report_unavailable(self):
        h = PortfolioEngineHealth()
        h.report("lifecycle", is_available=False, error="timeout")
        assert not h.is_healthy()
        assert "lifecycle" in h.unavailable_subsystems()

    def test_report_recovery(self):
        h = PortfolioEngineHealth()
        h.report("scheduler", is_available=False)
        h.report("scheduler", is_available=True)
        assert h.is_healthy()

    def test_subsystem_availability(self):
        h = PortfolioEngineHealth()
        avail = h.subsystem_availability()
        assert all(v is True for v in avail.values())

    def test_snapshot(self):
        h    = PortfolioEngineHealth()
        snap = h.snapshot()
        assert "is_healthy"  in snap
        assert "subsystems"  in snap
        assert "checked_at"  in snap

    def test_register_custom_subsystem(self):
        h = PortfolioEngineHealth()
        h.report("custom_subsystem", is_available=True)
        assert h.get("custom_subsystem") is not None


# ===========================================================================
# PortfolioEngineStatistics
# ===========================================================================

class TestPortfolioEngineStatistics:
    def test_initial_zeros(self):
        s = PortfolioEngineStatistics()
        snap = s.snapshot()
        assert snap["portfolio_sessions"]            == 0
        assert snap["portfolio_requests"]            == 0
        assert snap["portfolio_pipelines"]           == 0
        assert snap["portfolio_pipelines_completed"] == 0
        assert snap["portfolio_pipelines_failed"]    == 0
        assert snap["portfolio_snapshots_published"] == 0
        assert snap["average_portfolio_time_s"]      == 0.0
        assert snap["average_dispatch_time_s"]       == 0.0

    def test_record_session_created(self):
        s = PortfolioEngineStatistics()
        s.record_session_created()
        s.record_session_created()
        assert s.snapshot()["portfolio_sessions"] == 2

    def test_record_request_with_type(self):
        s = PortfolioEngineStatistics()
        s.record_request(PortfolioWorkflowType.PORTFOLIO_CREATION)
        s.record_request(PortfolioWorkflowType.PORTFOLIO_CREATION)
        snap = s.snapshot()
        assert snap["portfolio_requests"] == 2
        assert snap["portfolio_requests_by_type"]["portfolio_creation"] == 2

    def test_record_pipeline_completed(self):
        s = PortfolioEngineStatistics()
        s.record_pipeline_completed(elapsed_s=5.0)
        s.record_pipeline_completed(elapsed_s=15.0)
        snap = s.snapshot()
        assert snap["portfolio_pipelines_completed"] == 2
        assert snap["average_portfolio_time_s"]      == 10.0

    def test_record_pipeline_failed(self):
        s = PortfolioEngineStatistics()
        s.record_pipeline_failed()
        assert s.snapshot()["portfolio_pipelines_failed"] == 1

    def test_record_snapshot_published(self):
        s = PortfolioEngineStatistics()
        s.record_snapshot_published()
        assert s.snapshot()["portfolio_snapshots_published"] == 1

    def test_record_dispatch(self):
        s = PortfolioEngineStatistics()
        s.record_dispatch(elapsed_s=2.0)
        s.record_dispatch(elapsed_s=4.0)
        snap = s.snapshot()
        assert snap["average_dispatch_time_s"] == 3.0

    def test_record_subsystem_availability(self):
        s = PortfolioEngineStatistics()
        s.record_subsystem_availability(True)
        s.record_subsystem_availability(False)
        snap = s.snapshot()
        assert 0.0 <= snap["subsystem_availability"] <= 1.0

    def test_reset(self):
        s = PortfolioEngineStatistics()
        s.record_request()
        s.record_pipeline_failed()
        s.reset()
        snap = s.snapshot()
        assert snap["portfolio_requests"]          == 0
        assert snap["portfolio_pipelines_failed"]  == 0

    def test_uptime_positive(self):
        s = PortfolioEngineStatistics()
        time.sleep(0.01)
        assert s.snapshot()["uptime_s"] > 0


# ===========================================================================
# PortfolioEngineHistory
# ===========================================================================

class TestPortfolioEngineHistory:
    def test_record_and_retrieve_event(self):
        h = PortfolioEngineHistory()
        e = make_portfolio_initialized("pf-001")
        h.record_event(e)
        assert h.latest_event() is e
        assert h.event_count() == 1

    def test_events_by_type(self):
        h  = PortfolioEngineHistory()
        e1 = make_portfolio_initialized("pf-001")
        e2 = make_portfolio_completed("pf-001")
        h.record_event(e1); h.record_event(e2)
        result = h.events_by_type(PortfolioEventType.PORTFOLIO_INITIALIZED)
        assert len(result) == 1

    def test_events_for_portfolio(self):
        h  = PortfolioEngineHistory()
        e1 = make_portfolio_initialized("pf-A")
        e2 = make_portfolio_initialized("pf-B")
        h.record_event(e1); h.record_event(e2)
        result = h.events_for_portfolio("pf-A")
        assert len(result) == 1

    def test_record_request(self):
        h   = PortfolioEngineHistory()
        req = _request()
        h.record_request(req)
        assert h.request_count() == 1
        assert h.latest_request() is req

    def test_record_response(self):
        h   = PortfolioEngineHistory()
        req = _request()
        r   = PortfolioResponse.create_success(req.request_id, req.portfolio_id, req.workflow_type)
        h.record_response(r)
        assert h.response_count()  == 1
        assert h.latest_response() is r

    def test_record_pipeline(self):
        h    = PortfolioEngineHistory()
        pipe = PortfolioPipeline("r1", "pf", PortfolioWorkflowType.PORTFOLIO_CREATION)
        h.record_pipeline(pipe)
        assert h.pipeline_count()  == 1
        assert h.latest_pipeline() is pipe

    def test_bounded_maxlen(self):
        h = PortfolioEngineHistory(max_entries=3)
        for i in range(5):
            h.record_event(make_portfolio_initialized(f"pf-{i}"))
        assert h.event_count() == 3

    def test_clear(self):
        h = PortfolioEngineHistory()
        h.record_event(make_portfolio_initialized("pf-001"))
        h.record_request(_request())
        h.clear()
        assert h.event_count()   == 0
        assert h.request_count() == 0

    def test_summary(self):
        h = PortfolioEngineHistory()
        h.record_event(make_portfolio_initialized("pf-001"))
        s = h.summary()
        assert s["events"] == 1


# ===========================================================================
# PortfolioEngineEvent / factories
# ===========================================================================

class TestPortfolioEngineEvents:
    def _check(self, event: PortfolioEngineEvent, expected_type: PortfolioEventType):
        assert event.event_type   == expected_type
        assert event.event_id          # non-empty UUID
        assert event.portfolio_id == "pf-001"
        assert event.occurred_at  > 0

    def test_make_portfolio_initialized(self):
        self._check(make_portfolio_initialized("pf-001"), PortfolioEventType.PORTFOLIO_INITIALIZED)

    def test_make_portfolio_started(self):
        self._check(make_portfolio_started("pf-001"), PortfolioEventType.PORTFOLIO_STARTED)

    def test_make_portfolio_collected(self):
        e = make_portfolio_collected("pf-001", input_keys=["k1", "k2"])
        assert e.event_type == PortfolioEventType.PORTFOLIO_COLLECTED
        assert "k1" in e.payload.get("input_keys", [])

    def test_make_portfolio_dispatched(self):
        self._check(make_portfolio_dispatched("pf-001"), PortfolioEventType.PORTFOLIO_DISPATCHED)

    def test_make_portfolio_published(self):
        e = make_portfolio_published("pf-001", snapshot_id="snap-1")
        assert e.event_type == PortfolioEventType.PORTFOLIO_PUBLISHED
        assert e.payload.get("snapshot_id") == "snap-1"

    def test_make_portfolio_completed(self):
        e = make_portfolio_completed("pf-001", elapsed_s=5.0)
        assert e.event_type            == PortfolioEventType.PORTFOLIO_COMPLETED
        assert e.payload.get("elapsed_s") == 5.0

    def test_make_portfolio_failed(self):
        e = make_portfolio_failed("pf-001", reason="error")
        assert e.event_type            == PortfolioEventType.PORTFOLIO_FAILED
        assert e.payload.get("reason") == "error"

    def test_make_portfolio_stopped(self):
        self._check(make_portfolio_stopped("pf-001"), PortfolioEventType.PORTFOLIO_STOPPED)

    def test_event_to_dict(self):
        e = make_portfolio_initialized("pf-001", session_id="s1")
        d = e.to_dict()
        assert d["event_type"]  == "portfolio_initialized"
        assert d["portfolio_id"] == "pf-001"
        assert d["session_id"]  == "s1"

    def test_frozen(self):
        e = make_portfolio_initialized("pf-001")
        with pytest.raises((AttributeError, TypeError)):
            e.portfolio_id = "mutated"  # type: ignore[misc]


# ===========================================================================
# PortfolioEngineFactory
# ===========================================================================

class TestPortfolioEngineFactory:
    def test_create_request(self):
        f   = PortfolioEngineFactory()
        req = f.create_request("pf-001")
        assert isinstance(req, PortfolioRequest)
        assert req.portfolio_id == "pf-001"

    def test_create_pipeline(self):
        f    = PortfolioEngineFactory()
        req  = f.create_request("pf-001")
        pipe = f.create_pipeline(req)
        assert isinstance(pipe, PortfolioPipeline)
        assert pipe.portfolio_id == "pf-001"

    def test_create_snapshot(self):
        f    = PortfolioEngineFactory()
        req  = f.create_request("pf-001")
        snap = f.create_snapshot(req, "s1")
        assert isinstance(snap, PortfolioSnapshot)
        assert snap.session_id == "s1"

    def test_create_success_response(self):
        f   = PortfolioEngineFactory()
        req = f.create_request("pf-001")
        r   = f.create_success_response(req)
        assert r.is_success

    def test_create_failure_response(self):
        f   = PortfolioEngineFactory()
        req = f.create_request("pf-001")
        r   = f.create_failure_response(req, error_message="oops")
        assert r.is_failure
        assert r.error_message == "oops"


# ===========================================================================
# PortfolioEngineRegistry
# ===========================================================================

class TestPortfolioEngineRegistry:
    def _pipeline(self, pid: str = "pf") -> PortfolioPipeline:
        return PortfolioPipeline(
            request_id    = "r1",
            portfolio_id  = pid,
            workflow_type = PortfolioWorkflowType.PORTFOLIO_CREATION,
        )

    def test_register_and_get(self):
        reg  = PortfolioEngineRegistry()
        pipe = self._pipeline()
        reg.register_pipeline(pipe)
        got  = reg.get_pipeline(pipe.pipeline_id)
        assert got is pipe

    def test_update_to_completed(self):
        reg  = PortfolioEngineRegistry()
        pipe = self._pipeline()
        reg.register_pipeline(pipe)
        pipe.complete()
        reg.update_pipeline(pipe)
        assert reg.active_count()    == 0
        assert reg.completed_count() == 1

    def test_update_to_failed(self):
        reg  = PortfolioEngineRegistry()
        pipe = self._pipeline()
        reg.register_pipeline(pipe)
        pipe.fail("err")
        reg.update_pipeline(pipe)
        assert reg.failed_count() == 1

    def test_capacity_exceeded(self):
        reg = PortfolioEngineRegistry(max_active_pipelines=1)
        reg.register_pipeline(self._pipeline("a"))
        with pytest.raises(PortfolioCapacityError):
            reg.register_pipeline(self._pipeline("b"))

    def test_register_request(self):
        reg = PortfolioEngineRegistry()
        req = _request()
        reg.register_request(req)
        assert reg.get_request(req.request_id) is req

    def test_clear(self):
        reg = PortfolioEngineRegistry()
        reg.register_pipeline(self._pipeline())
        reg.clear()
        assert reg.active_count() == 0

    def test_get_pipeline_from_completed(self):
        reg  = PortfolioEngineRegistry()
        pipe = self._pipeline()
        reg.register_pipeline(pipe)
        pipe.complete()
        reg.update_pipeline(pipe)
        found = reg.get_pipeline(pipe.pipeline_id)
        assert found is not None


# ===========================================================================
# PortfolioEngine — guard / not-running
# ===========================================================================

class TestPortfolioEngineGuard:
    def test_operations_blocked_when_stopped(self):
        e = PortfolioEngine()
        with pytest.raises(PortfolioEngineNotRunningError):
            e.submit(_request())

    def test_start_then_stop_then_submit_blocked(self):
        e = _started_engine()
        e.stop()
        with pytest.raises(PortfolioEngineNotRunningError):
            e.submit(_request())


# ===========================================================================
# PortfolioEngine — submit / full workflow
# ===========================================================================

class TestPortfolioEngineSubmit:
    def test_submit_returns_success_response(self):
        e = _started_engine()
        r = _full_submit(e)
        assert r.is_success
        assert r.has_snapshot
        assert r.portfolio_id == "pf-001"
        e.stop()

    def test_submit_snapshot_is_valid(self):
        e    = _started_engine()
        r    = _full_submit(e)
        snap = r.snapshot
        assert snap.portfolio_id == "pf-001"
        assert snap.workflow_type == PortfolioWorkflowType.PORTFOLIO_CREATION
        e.stop()

    def test_submit_with_inputs(self):
        e   = _started_engine()
        req = _request("pf-002", inputs={"decision_snapshot": {"score": 8.0}})
        r   = e.submit(req)
        assert r.is_success
        e.stop()

    def test_submit_invalid_request_returns_failure(self):
        e   = _started_engine()
        req = PortfolioRequest.create("")  # empty portfolio_id
        r   = e.submit(req)
        assert r.is_failure
        e.stop()

    def test_submit_increments_statistics(self):
        e = _started_engine()
        _full_submit(e, "pf-A")
        _full_submit(e, "pf-B")
        snap = e.statistics()
        assert snap["portfolio_requests"] >= 2
        e.stop()


# ===========================================================================
# PortfolioEngine — named operations
# ===========================================================================

class TestPortfolioEngineNamedOperations:
    def test_initialize_portfolio(self):
        e = _started_engine()
        r = e.initialize_portfolio("pf-001")
        assert r.is_success
        e.stop()

    def test_start_portfolio(self):
        e = _started_engine()
        r = e.start_portfolio("pf-002")
        assert r.is_success
        e.stop()

    def test_stop_portfolio(self):
        e = _started_engine()
        r = e.stop_portfolio("pf-003")
        assert r.is_success
        e.stop()

    def test_collect(self):
        e = _started_engine()
        r = e.collect("pf-004", {"order_snapshot": {"count": 3}})
        assert r.is_success
        e.stop()

    def test_dispatch(self):
        e = _started_engine()
        r = e.dispatch("pf-005")
        assert r.is_success
        e.stop()

    def test_publish(self):
        e = _started_engine()
        r = e.publish("pf-006")
        assert r.is_success
        e.stop()

    def test_query_no_history(self):
        e = _started_engine()
        r = e.query("pf-new")
        assert r.is_success
        assert r.metadata.get("query_result") == "no_history"
        e.stop()

    def test_query_with_history(self):
        e = _started_engine()
        _full_submit(e, "pf-007")
        r = e.query("pf-007")
        assert r.is_success
        e.stop()

    def test_validate_request(self):
        e   = _started_engine()
        req = _request("pf-008")
        r   = e.validate(req)
        assert r.is_valid
        e.stop()


# ===========================================================================
# PortfolioEngine — rebalancing / allocation workflows
# ===========================================================================

class TestPortfolioEngineWorkflows:
    def test_rebalancing_workflow(self):
        e   = _started_engine()
        req = _request("pf-reb", PortfolioWorkflowType.PORTFOLIO_REBALANCING)
        r   = e.submit(req)
        assert r.is_success
        e.stop()

    def test_capital_allocation_workflow(self):
        e   = _started_engine()
        req = _request("pf-alloc", PortfolioWorkflowType.CAPITAL_ALLOCATION)
        r   = e.submit(req)
        assert r.is_success
        e.stop()

    def test_risk_synchronization_workflow(self):
        e   = _started_engine()
        req = _request("pf-risk", PortfolioWorkflowType.RISK_SYNCHRONIZATION)
        r   = e.submit(req)
        assert r.is_success
        e.stop()

    def test_portfolio_closure_workflow(self):
        e   = _started_engine()
        req = _request("pf-close", PortfolioWorkflowType.PORTFOLIO_CLOSURE)
        r   = e.submit(req)
        assert r.is_success
        e.stop()


# ===========================================================================
# PortfolioEngine — statistics / history / health / status
# ===========================================================================

class TestPortfolioEngineIntrospection:
    def test_statistics_keys(self):
        e = _started_engine()
        _full_submit(e)
        snap = e.statistics()
        assert "portfolio_sessions"            in snap
        assert "portfolio_requests"            in snap
        assert "portfolio_pipelines_completed" in snap
        assert "portfolio_snapshots_published" in snap
        assert "active_pipelines"              in snap
        e.stop()

    def test_history_structure(self):
        e = _started_engine()
        _full_submit(e)
        h = e.history()
        assert "events"    in h
        assert "requests"  in h
        assert "responses" in h
        assert "pipelines" in h
        assert len(h["events"])    > 0
        assert len(h["requests"])  > 0
        assert len(h["responses"]) > 0
        e.stop()

    def test_health_structure(self):
        e = _started_engine()
        h = e.health()
        assert "is_healthy"  in h
        assert "subsystems"  in h
        assert "dispatcher"  in h
        e.stop()

    def test_status_structure(self):
        e = _started_engine()
        _full_submit(e)
        s = e.status()
        assert isinstance(s, PortfolioEngineStatus)
        assert s.lifecycle_state  == "running"
        assert s.completed_pipelines >= 1
        d = s.to_dict()
        assert "engine_state"    in d
        assert "lifecycle_state" in d
        e.stop()

    def test_statistics_snapshot_published_count(self):
        e = _started_engine()
        _full_submit(e)
        _full_submit(e, "pf-002")
        snap = e.statistics()
        assert snap["portfolio_snapshots_published"] >= 2
        e.stop()


# ===========================================================================
# PortfolioEngine — framework registration
# ===========================================================================

class TestPortfolioEngineFrameworks:
    def test_register_policy_framework_called(self):
        e     = _started_engine()
        calls = []
        e.register_policy_framework(lambda p, r: calls.append("m3"))
        _full_submit(e)
        assert "m3" in calls
        e.stop()

    def test_register_optimization_framework_called(self):
        e     = _started_engine()
        calls = []
        e.register_optimization_framework(lambda p, r: calls.append("m4"))
        _full_submit(e)
        assert "m4" in calls
        e.stop()

    def test_failing_policy_framework_returns_failure_response(self):
        e = _started_engine()
        e.register_policy_framework(
            lambda p, r: (_ for _ in ()).throw(RuntimeError("m3 error"))
        )
        r = _full_submit(e)
        assert r.is_failure
        e.stop()


# ===========================================================================
# PortfolioEngine — event listeners
# ===========================================================================

class TestPortfolioEngineListeners:
    def test_listener_receives_events(self):
        e        = _started_engine()
        received = []
        e.add_listener(received.append)
        _full_submit(e)
        assert len(received) > 0
        e.stop()

    def test_listener_initialized_event(self):
        e        = _started_engine()
        received = []
        e.add_listener(received.append)
        _full_submit(e)
        types = {ev.event_type for ev in received}
        assert PortfolioEventType.PORTFOLIO_INITIALIZED in types
        e.stop()

    def test_listener_completed_event(self):
        e        = _started_engine()
        received = []
        e.add_listener(received.append)
        _full_submit(e)
        types = {ev.event_type for ev in received}
        assert PortfolioEventType.PORTFOLIO_COMPLETED in types
        e.stop()

    def test_listener_removed(self):
        e        = _started_engine()
        received = []
        e.add_listener(received.append)
        e.remove_listener(received.append)
        _full_submit(e)
        assert len(received) == 0
        e.stop()

    def test_listener_error_does_not_propagate(self):
        e = _started_engine()
        e.add_listener(lambda ev: (_ for _ in ()).throw(RuntimeError("bad listener")))
        _full_submit(e)  # should not raise
        e.stop()

    def test_multiple_listeners(self):
        e    = _started_engine()
        acc1 = []
        acc2 = []
        e.add_listener(acc1.append)
        e.add_listener(acc2.append)
        _full_submit(e)
        assert len(acc1) > 0
        assert len(acc2) > 0
        e.stop()

    def test_duplicate_listener_not_registered_twice(self):
        e   = _started_engine()
        acc = []
        e.add_listener(acc.append)
        e.add_listener(acc.append)  # duplicate
        _full_submit(e)
        # Each event received once
        first_event_count = sum(
            1 for ev in acc if ev.event_type == PortfolioEventType.PORTFOLIO_INITIALIZED
        )
        assert first_event_count == 1
        e.stop()


# ===========================================================================
# PortfolioEngine — concurrency
# ===========================================================================

class TestPortfolioEngineConcurrency:
    def test_concurrent_submits(self):
        e      = _started_engine(max_concurrent_sessions=200)
        errors  = []
        results = []

        def worker(i: int):
            try:
                r = e.submit(_request(f"pf-{i}"))
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(errors)  == 0
        assert len(results) == 30
        assert all(r.is_success for r in results)
        e.stop()

    def test_concurrent_statistics_reads(self):
        e      = _started_engine()
        _full_submit(e)
        errors = []

        def reader():
            try:
                e.statistics()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert len(errors) == 0
        e.stop()

    def test_concurrent_history_reads(self):
        e      = _started_engine()
        _full_submit(e)
        errors = []

        def reader():
            try:
                e.history()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert len(errors) == 0
        e.stop()


# ===========================================================================
# PortfolioEngine — stress test
# ===========================================================================

class TestPortfolioEngineStress:
    def test_fifty_sequential_submits(self):
        e = _started_engine(max_concurrent_sessions=200)
        results = []
        for i in range(50):
            r = e.submit(_request(f"pf-stress-{i}"))
            results.append(r)
        assert all(r.is_success for r in results)
        snap = e.statistics()
        assert snap["portfolio_requests"] >= 50
        e.stop()

    def test_all_workflow_types(self):
        e = _started_engine()
        for wt in PortfolioWorkflowType:
            req = _request(f"pf-{wt.value}", wt)
            r   = e.submit(req)
            assert r.is_success, f"Workflow {wt.value} failed: {r.error_message}"
        e.stop()


# ===========================================================================
# Integration
# ===========================================================================

class TestPortfolioEngineIntegration:
    def test_full_portfolio_lifecycle(self):
        e = _started_engine()
        # Initialize
        r1 = e.initialize_portfolio("pf-int-001")
        assert r1.is_success
        # Collect inputs
        r2 = e.collect("pf-int-001", {"decision_snapshot": {"score": 9.0}})
        assert r2.is_success
        # Rebalance
        r3 = e.dispatch("pf-int-001", PortfolioWorkflowType.PORTFOLIO_REBALANCING)
        assert r3.is_success
        # Publish
        r4 = e.publish("pf-int-001")
        assert r4.is_success
        # Stop
        r5 = e.stop_portfolio("pf-int-001")
        assert r5.is_success
        e.stop()

    def test_history_populated_after_integration(self):
        e = _started_engine()
        e.initialize_portfolio("pf-hist-001")
        h = e.history()
        types = {ev["event_type"] for ev in h["events"]}
        assert "portfolio_initialized" in types
        assert "portfolio_completed"   in types
        e.stop()

    def test_statistics_after_integration(self):
        e = _started_engine()
        for wt in [
            PortfolioWorkflowType.PORTFOLIO_CREATION,
            PortfolioWorkflowType.PORTFOLIO_REBALANCING,
            PortfolioWorkflowType.PORTFOLIO_CLOSURE,
        ]:
            e.submit(_request(f"pf-stat", wt))
        snap = e.statistics()
        assert snap["portfolio_sessions"]            >= 1
        assert snap["portfolio_requests"]            >= 3
        assert snap["portfolio_snapshots_published"] >= 3
        e.stop()

    def test_engine_start_stop_new_instance(self):
        """Verify a fresh engine instance works correctly after a separate instance is stopped."""
        e1 = PortfolioEngine()
        e1.start()
        r1 = _full_submit(e1)
        assert r1.is_success
        e1.stop()
        # A new engine instance starts cleanly
        e2 = PortfolioEngine()
        e2.start()
        r2 = _full_submit(e2, "pf-restart")
        assert r2.is_success
        e2.stop()
