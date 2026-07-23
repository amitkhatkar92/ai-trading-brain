"""
test_market_engine.py
======================
Unit tests for C12 M2 — Market Engine.

Coverage:
  Constants, Exceptions, Context, Request, Response,
  Pipeline, Scheduler, Dispatcher, Session Manager,
  Registry, Validation, Health, Status, Statistics,
  History, Events, Factory, Manager, Engine,
  Concurrency, Stress, Regression.

Target: 95%+ coverage, ~250 tests.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from iios.market.engine import (
    # Primary interface
    MarketEngine,
    # Value objects
    MarketEngineContext,
    MarketRequest,
    MarketEngineSnapshot,
    MarketResponse,
    MarketPipeline,
    PipelineStage,
    MarketEngineStatus,
    # Events
    MarketEngineEvent,
    MarketEngineEventType,
    make_market_engine_analysis_started,
    make_market_engine_collected,
    make_market_engine_completed,
    make_market_engine_dispatched,
    make_market_engine_failed,
    make_market_engine_initialized,
    make_market_engine_published,
    make_market_engine_started,
    make_market_engine_stopped,
    # Sub-components
    MarketDispatcher,
    MarketEngineFactory,
    MarketEngineHealth,
    MarketEngineHistory,
    MarketManager,
    MarketEngineRegistry,
    MarketScheduler,
    MarketSessionManager,
    MarketEngineStatistics,
    MarketEngineValidator,
    MarketEngineValidationResult,
    MarketEngineValidationCheckResult,
    # Enums & constants
    ENGINE_SYSTEM_ID,
    VERSION,
    EngineState,
    MarketWorkflowType,
    SchedulerPriority,
    ResponseStatus,
    PipelineStatus,
    VALID_ENGINE_TRANSITIONS,
    ACTIVE_ENGINE_STATES,
    TERMINAL_ENGINE_STATES,
    ANALYSIS_WORKFLOWS,
    MONITORING_WORKFLOWS,
    # Exceptions
    MarketEngineError,
    MarketEngineCapacityError,
    MarketCollectionError,
    MarketDispatchError,
    MarketEngineNotRunningError,
    MarketEngineValidationError,
    MarketPipelineError,
    MarketPublicationError,
    MarketSchedulerError,
    MarketSessionError,
)


# ============================================================================
# Helpers
# ============================================================================

def _started_engine(**kwargs) -> MarketEngine:
    e = MarketEngine(**kwargs)
    e.start()
    return e


def _make_request(
    analysis_id: str = "MKT-001",
    exchange: str = "NSE",
    workflow_type: MarketWorkflowType = MarketWorkflowType.MARKET_OVERVIEW,
    **kwargs,
) -> MarketRequest:
    return MarketRequest.create(analysis_id, exchange, workflow_type, **kwargs)


def _full_submit(engine: MarketEngine, analysis_id: str = "MKT-001") -> MarketResponse:
    return engine.initialize_market(analysis_id, "NSE")


# ============================================================================
# 1  CONSTANTS
# ============================================================================

class TestConstants:
    def test_engine_system_id(self):
        assert ENGINE_SYSTEM_ID == "iios:market:engine"

    def test_version_format(self):
        assert len(VERSION.split(".")) == 3

    def test_engine_state_count(self):
        assert len(EngineState) == 11

    def test_workflow_type_count(self):
        assert len(MarketWorkflowType) == 9

    def test_scheduler_priority_count(self):
        assert len(SchedulerPriority) == 5

    def test_response_status_count(self):
        assert len(ResponseStatus) == 3

    def test_pipeline_status_count(self):
        assert len(PipelineStatus) == 5

    def test_engine_event_type_count(self):
        assert len(MarketEngineEventType) == 9

    def test_active_engine_states_excludes_idle(self):
        assert EngineState.IDLE not in ACTIVE_ENGINE_STATES

    def test_stopped_is_terminal(self):
        assert EngineState.STOPPED in TERMINAL_ENGINE_STATES

    def test_stopped_has_no_transitions(self):
        assert VALID_ENGINE_TRANSITIONS[EngineState.STOPPED] == frozenset()

    def test_all_states_in_valid_transitions(self):
        for state in EngineState:
            assert state in VALID_ENGINE_TRANSITIONS

    def test_idle_can_reach_initializing(self):
        assert EngineState.INITIALIZING in VALID_ENGINE_TRANSITIONS[EngineState.IDLE]

    def test_analysis_workflows_not_empty(self):
        assert len(ANALYSIS_WORKFLOWS) > 0

    def test_monitoring_workflows_not_empty(self):
        assert len(MONITORING_WORKFLOWS) > 0

    def test_analysis_and_monitoring_disjoint(self):
        assert ANALYSIS_WORKFLOWS.isdisjoint(MONITORING_WORKFLOWS)


# ============================================================================
# 2  EXCEPTIONS
# ============================================================================

class TestExceptions:
    def test_base_inherits_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(MarketEngineError, IIOSError)

    def test_base_error_code(self):
        exc = MarketEngineError("test")
        assert exc.error_code == "ME-000"

    def test_not_running_code(self):
        exc = MarketEngineNotRunningError()
        assert exc.error_code == "ME-001"

    def test_session_error_code(self):
        exc = MarketSessionError("bad", session_id="SID")
        assert exc.error_code == "ME-002"
        assert exc.session_id == "SID"

    def test_pipeline_error_code(self):
        exc = MarketPipelineError("bad", pipeline_id="PID")
        assert exc.error_code == "ME-003"
        assert exc.pipeline_id == "PID"

    def test_dispatch_error_code(self):
        exc = MarketDispatchError("bad", workflow_type="market_overview")
        assert exc.error_code == "ME-004"
        assert exc.workflow_type == "market_overview"

    def test_collection_error_code(self):
        exc = MarketCollectionError("bad", missing_inputs=("feed",))
        assert exc.error_code == "ME-005"
        assert exc.missing_inputs == ("feed",)

    def test_publication_error_code(self):
        exc = MarketPublicationError("bad", market_analysis_id="MKT-001")
        assert exc.error_code == "ME-006"
        assert exc.market_analysis_id == "MKT-001"

    def test_validation_error_code(self):
        exc = MarketEngineValidationError("bad", failed_checks=("id",))
        assert exc.error_code == "ME-007"
        assert exc.failed_checks == ("id",)

    def test_scheduler_error_code(self):
        exc = MarketSchedulerError("bad")
        assert exc.error_code == "ME-008"

    def test_capacity_error_code(self):
        exc = MarketEngineCapacityError(100)
        assert exc.error_code == "ME-009"
        assert exc.limit == 100

    def test_all_subclass_base(self):
        for cls in [
            MarketEngineNotRunningError,
            MarketSessionError,
            MarketPipelineError,
            MarketDispatchError,
            MarketCollectionError,
            MarketPublicationError,
            MarketEngineValidationError,
            MarketSchedulerError,
            MarketEngineCapacityError,
        ]:
            assert issubclass(cls, MarketEngineError)


# ============================================================================
# 3  MARKET ENGINE CONTEXT
# ============================================================================

class TestMarketEngineContext:
    def test_create_minimal(self):
        ctx = MarketEngineContext.create("MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW)
        assert ctx.market_analysis_id == "MKT-001"
        assert ctx.exchange == "NSE"
        assert uuid.UUID(ctx.context_id)

    def test_create_with_options(self):
        ctx = MarketEngineContext.create(
            "MKT-002", "BSE", MarketWorkflowType.SECTOR_ANALYSIS,
            priority=SchedulerPriority.HIGH,
            instrument_id="NIFTY",
        )
        assert ctx.priority      == SchedulerPriority.HIGH
        assert ctx.instrument_id == "NIFTY"

    def test_is_frozen(self):
        ctx = MarketEngineContext.create("M", "N", MarketWorkflowType.MARKET_OVERVIEW)
        with pytest.raises((AttributeError, TypeError)):
            ctx.exchange = "X"  # type: ignore[misc]

    def test_to_dict(self):
        ctx = MarketEngineContext.create("MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW)
        d = ctx.to_dict()
        assert d["market_analysis_id"] == "MKT-001"
        assert d["exchange"]           == "NSE"
        assert d["workflow_type"]      == "market_overview"

    def test_explicit_context_id(self):
        ctx = MarketEngineContext.create(
            "M", "N", MarketWorkflowType.MARKET_OVERVIEW, context_id="CTX-1"
        )
        assert ctx.context_id == "CTX-1"


# ============================================================================
# 4  MARKET REQUEST
# ============================================================================

class TestMarketRequest:
    def test_create_defaults(self):
        r = MarketRequest.create("MKT-001", "NSE")
        assert r.market_analysis_id == "MKT-001"
        assert r.exchange           == "NSE"
        assert r.workflow_type      == MarketWorkflowType.MARKET_OVERVIEW
        assert r.priority           == SchedulerPriority.NORMAL
        assert uuid.UUID(r.request_id)

    def test_create_with_workflow_type(self):
        r = MarketRequest.create("MKT-001", "NSE", MarketWorkflowType.SECTOR_ANALYSIS)
        assert r.workflow_type == MarketWorkflowType.SECTOR_ANALYSIS

    def test_is_frozen(self):
        r = MarketRequest.create("MKT-001", "NSE")
        with pytest.raises((AttributeError, TypeError)):
            r.exchange = "BSE"  # type: ignore[misc]

    def test_with_inputs(self):
        r  = MarketRequest.create("MKT-001", "NSE")
        r2 = r.with_inputs({"market_feed": {"nifty": 22000}})
        assert "market_feed" in r2.inputs
        assert r.inputs == {}  # original unchanged

    def test_to_dict(self):
        r = MarketRequest.create("MKT-001", "NSE", inputs={"a": 1})
        d = r.to_dict()
        assert d["market_analysis_id"] == "MKT-001"
        assert d["exchange"]           == "NSE"
        assert "a" in d["input_keys"]

    def test_context_auto_created(self):
        r = MarketRequest.create("MKT-001", "NSE")
        assert r.context.market_analysis_id == "MKT-001"
        assert r.context.exchange           == "NSE"
        assert r.context.workflow_type      == r.workflow_type

    def test_explicit_request_id(self):
        r = MarketRequest.create("M", "N", request_id="REQ-1")
        assert r.request_id == "REQ-1"


# ============================================================================
# 5  MARKET RESPONSE & SNAPSHOT
# ============================================================================

class TestMarketResponseAndSnapshot:
    def test_snapshot_create(self):
        s = MarketEngineSnapshot.create(
            "MKT-001", "NSE", "SID",
            MarketWorkflowType.MARKET_OVERVIEW,
            EngineState.PUBLISHING,
        )
        assert s.market_analysis_id == "MKT-001"
        assert s.exchange           == "NSE"
        assert uuid.UUID(s.snapshot_id)

    def test_snapshot_is_frozen(self):
        s = MarketEngineSnapshot.create(
            "M", "N", "S",
            MarketWorkflowType.MARKET_OVERVIEW,
            EngineState.PUBLISHING,
        )
        with pytest.raises((AttributeError, TypeError)):
            s.exchange = "X"  # type: ignore[misc]

    def test_snapshot_to_dict(self):
        s = MarketEngineSnapshot.create(
            "MKT-001", "NSE", "SID",
            MarketWorkflowType.MARKET_OVERVIEW,
            EngineState.PUBLISHING,
        )
        d = s.to_dict()
        assert d["market_analysis_id"] == "MKT-001"
        assert d["exchange"]           == "NSE"

    def test_response_create_success(self):
        r = MarketResponse.create_success(
            "REQ-1", "MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW
        )
        assert r.is_success
        assert not r.is_failure

    def test_response_create_failure(self):
        r = MarketResponse.create_failure(
            "REQ-1", "MKT-001", "NSE",
            MarketWorkflowType.MARKET_OVERVIEW,
            error_message="boom",
        )
        assert r.is_failure
        assert r.error_message == "boom"
        assert not r.has_snapshot

    def test_response_with_snapshot(self):
        snap = MarketEngineSnapshot.create(
            "M", "N", "S", MarketWorkflowType.MARKET_OVERVIEW, EngineState.PUBLISHING
        )
        r = MarketResponse.create_success(
            "REQ-1", "MKT-001", "NSE",
            MarketWorkflowType.MARKET_OVERVIEW,
            snapshot=snap,
        )
        assert r.has_snapshot
        assert r.snapshot is snap

    def test_response_to_dict(self):
        r = MarketResponse.create_success(
            "REQ-1", "MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW
        )
        d = r.to_dict()
        assert d["status"] == "success"
        assert d["exchange"] == "NSE"


# ============================================================================
# 6  MARKET PIPELINE
# ============================================================================

class TestMarketPipeline:
    def test_initial_state(self):
        p = MarketPipeline("REQ-1", "MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW)
        assert p.status     == PipelineStatus.PENDING
        assert p.started_at == 0.0

    def test_start(self):
        p = MarketPipeline("REQ-1", "MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW)
        p.start()
        assert p.status    == PipelineStatus.RUNNING
        assert p.started_at > 0

    def test_complete(self):
        p = MarketPipeline("REQ-1", "MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW)
        p.start()
        p.complete()
        assert p.is_completed
        assert p.completed_at > 0

    def test_fail(self):
        p = MarketPipeline("REQ-1", "MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW)
        p.start()
        p.fail("test error")
        assert p.is_failed
        assert p.error == "test error"

    def test_cancel(self):
        p = MarketPipeline("REQ-1", "MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW)
        p.cancel()
        assert p.status == PipelineStatus.CANCELLED

    def test_add_stage(self):
        p = MarketPipeline("REQ-1", "MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW)
        stage = PipelineStage(
            stage_name   = "test",
            engine_state = EngineState.INITIALIZING,
            status       = PipelineStatus.COMPLETED,
        )
        p.add_stage(stage)
        assert len(p.stages) == 1

    def test_elapsed_s_after_start(self):
        p = MarketPipeline("REQ-1", "MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW)
        p.start()
        assert p.elapsed_s >= 0.0

    def test_session_id_settable(self):
        p = MarketPipeline("REQ-1", "MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW)
        p.session_id = "SID-1"
        assert p.session_id == "SID-1"

    def test_to_dict(self):
        p = MarketPipeline("REQ-1", "MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW)
        d = p.to_dict()
        assert d["market_analysis_id"] == "MKT-001"
        assert d["exchange"]           == "NSE"
        assert d["status"]             == "pending"


# ============================================================================
# 7  EVENTS
# ============================================================================

class TestMarketEngineEvents:
    def test_make_initialized(self):
        e = make_market_engine_initialized("M", "N", "S")
        assert e.event_type   == MarketEngineEventType.MARKET_INITIALIZED
        assert e.engine_state == EngineState.INITIALIZING

    def test_make_started(self):
        e = make_market_engine_started("M", "N", "S")
        assert e.event_type == MarketEngineEventType.MARKET_STARTED

    def test_make_collected(self):
        e = make_market_engine_collected("M", "N", "S")
        assert e.event_type == MarketEngineEventType.MARKET_COLLECTED

    def test_make_dispatched(self):
        e = make_market_engine_dispatched("M", "N", "S")
        assert e.event_type == MarketEngineEventType.MARKET_DISPATCHED

    def test_make_analysis_started(self):
        e = make_market_engine_analysis_started("M", "N", "S")
        assert e.event_type == MarketEngineEventType.MARKET_ANALYSIS_STARTED

    def test_make_published(self):
        e = make_market_engine_published("M", "N", "S")
        assert e.event_type == MarketEngineEventType.MARKET_PUBLISHED

    def test_make_completed(self):
        e = make_market_engine_completed("M", "N", "S")
        assert e.event_type == MarketEngineEventType.MARKET_COMPLETED

    def test_make_failed(self):
        e = make_market_engine_failed("M", "N", "S")
        assert e.event_type == MarketEngineEventType.MARKET_FAILED

    def test_make_stopped(self):
        e = make_market_engine_stopped("engine", ENGINE_SYSTEM_ID)
        assert e.event_type == MarketEngineEventType.MARKET_STOPPED

    def test_event_is_frozen(self):
        e = make_market_engine_initialized("M", "N", "S")
        with pytest.raises((AttributeError, TypeError)):
            e.exchange = "X"  # type: ignore[misc]

    def test_unique_event_ids(self):
        e1 = make_market_engine_initialized("M", "N", "S")
        e2 = make_market_engine_initialized("M", "N", "S")
        assert e1.event_id != e2.event_id

    def test_to_dict(self):
        e = make_market_engine_initialized("MKT-001", "NSE", "SID")
        d = e.to_dict()
        assert d["market_analysis_id"] == "MKT-001"
        assert d["exchange"]           == "NSE"
        assert d["event_type"]         == "market_initialized"

    def test_payload_passthrough(self):
        e = make_market_engine_completed("M", "N", "S", payload={"key": "val"})
        assert e.payload["key"] == "val"


# ============================================================================
# 8  SCHEDULER
# ============================================================================

class TestMarketScheduler:
    def test_schedule_and_next(self):
        s = MarketScheduler()
        r = _make_request()
        s.schedule(r)
        out = s.next()
        assert out is r

    def test_priority_ordering(self):
        s   = MarketScheduler()
        r_low  = _make_request("LOW", priority=SchedulerPriority.LOW)
        r_high = _make_request("HIGH", priority=SchedulerPriority.CRITICAL)
        s.schedule(r_low)
        s.schedule(r_high)
        first = s.next()
        assert first.market_analysis_id == "HIGH"

    def test_cancel(self):
        s = MarketScheduler()
        r = _make_request()
        s.schedule(r)
        result = s.cancel(r.request_id)
        assert result is True
        out = s.next()
        assert out is None

    def test_capacity_limit(self):
        s = MarketScheduler(max_queue_size=1)
        s.schedule(_make_request("A"))
        with pytest.raises(MarketEngineCapacityError):
            s.schedule(_make_request("B"))

    def test_duplicate_raises(self):
        s = MarketScheduler()
        r = _make_request()
        s.schedule(r)
        with pytest.raises(MarketSchedulerError):
            s.schedule(r)

    def test_empty_returns_none(self):
        s = MarketScheduler()
        assert s.next() is None

    def test_statistics(self):
        s = MarketScheduler()
        r = _make_request()
        s.schedule(r)
        s.next()
        st = s.statistics()
        assert st["scheduled"]  == 1
        assert st["dispatched"] == 1

    def test_pending_count(self):
        s = MarketScheduler()
        s.schedule(_make_request("A"))
        s.schedule(_make_request("B"))
        assert s.pending_count() == 2

    def test_clear(self):
        s = MarketScheduler()
        s.schedule(_make_request())
        s.clear()
        assert s.is_empty()

    def test_thread_safe(self):
        s      = MarketScheduler(max_queue_size=1000)
        errors: List[str] = []

        def worker(i: int):
            try:
                s.schedule(_make_request(f"MKT-{i}"))
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert s.pending_count() == 50


# ============================================================================
# 9  DISPATCHER
# ============================================================================

class TestMarketDispatcher:
    def test_default_no_frameworks(self):
        d = MarketDispatcher()
        assert not d.has_policy_framework
        assert not d.has_analytics_framework

    def test_register_policy_framework(self):
        d = MarketDispatcher()
        d.register_policy_framework(lambda p, r: None)
        assert d.has_policy_framework

    def test_register_analytics_framework(self):
        d = MarketDispatcher()
        d.register_analytics_framework(lambda p, r: None)
        assert d.has_analytics_framework

    def test_unregister(self):
        d = MarketDispatcher()
        d.register_policy_framework(lambda p, r: None)
        d.unregister_policy_framework()
        assert not d.has_policy_framework

    def test_dispatch_no_frameworks(self):
        d = MarketDispatcher()
        p = MarketPipeline("R", "M", "N", MarketWorkflowType.MARKET_OVERVIEW)
        r = _make_request()
        result = d.dispatch(p, r)
        assert result is p
        assert d.statistics()["dispatch_count"] == 1

    def test_dispatch_calls_policy_framework(self):
        d    = MarketDispatcher()
        called = []
        d.register_policy_framework(lambda p, r: called.append(True))
        p = MarketPipeline("R", "M", "N", MarketWorkflowType.MARKET_OVERVIEW)
        d.dispatch(p, _make_request())
        assert called == [True]

    def test_dispatch_calls_analytics_framework(self):
        d    = MarketDispatcher()
        called = []
        d.register_analytics_framework(lambda p, r: called.append(True))
        p = MarketPipeline("R", "M", "N", MarketWorkflowType.MARKET_OVERVIEW)
        d.dispatch(p, _make_request())
        assert called == [True]

    def test_failing_policy_framework_raises(self):
        d = MarketDispatcher()
        d.register_policy_framework(lambda p, r: (_ for _ in ()).throw(RuntimeError("boom")))
        p = MarketPipeline("R", "M", "N", MarketWorkflowType.MARKET_OVERVIEW)
        with pytest.raises(MarketDispatchError):
            d.dispatch(p, _make_request())

    def test_determine_next_state_analysis(self):
        d = MarketDispatcher()
        for wt in ANALYSIS_WORKFLOWS:
            assert d.determine_next_state(wt) == EngineState.ANALYZING

    def test_determine_next_state_monitoring(self):
        d = MarketDispatcher()
        for wt in MONITORING_WORKFLOWS:
            assert d.determine_next_state(wt) == EngineState.MONITORING

    def test_statistics_failure_count(self):
        d = MarketDispatcher()
        d.register_policy_framework(lambda p, r: (_ for _ in ()).throw(RuntimeError("x")))
        p = MarketPipeline("R", "M", "N", MarketWorkflowType.MARKET_OVERVIEW)
        with pytest.raises(MarketDispatchError):
            d.dispatch(p, _make_request())
        assert d.statistics()["failure_count"] == 1


# ============================================================================
# 10  REGISTRY
# ============================================================================

class TestMarketRegistry:
    def _make_pipeline(self, pid: str = "P1") -> MarketPipeline:
        p = MarketPipeline(f"REQ-{pid}", "MKT-001", "NSE", MarketWorkflowType.MARKET_OVERVIEW,
                           pipeline_id=pid)
        return p

    def test_register_and_get(self):
        reg = MarketEngineRegistry()
        p   = self._make_pipeline()
        reg.register_pipeline(p)
        assert reg.get_pipeline(p.pipeline_id) is p

    def test_capacity_limit(self):
        reg = MarketEngineRegistry(max_pipelines=1)
        reg.register_pipeline(self._make_pipeline("P1"))
        with pytest.raises(MarketEngineCapacityError):
            reg.register_pipeline(self._make_pipeline("P2"))

    def test_archive(self):
        reg = MarketEngineRegistry()
        p   = self._make_pipeline()
        reg.register_pipeline(p)
        reg.archive_pipeline(p)
        assert reg.active_pipeline_count()   == 0
        assert reg.archived_pipeline_count() == 1
        assert reg.get_pipeline(p.pipeline_id) is p

    def test_archive_evicts_oldest(self):
        reg = MarketEngineRegistry(max_archived=2)
        for i in range(3):
            p = self._make_pipeline(f"P{i}")
            reg.register_pipeline(p)
            reg.archive_pipeline(p)
        assert reg.archived_pipeline_count() == 2

    def test_query_by_exchange(self):
        reg = MarketEngineRegistry()
        p1  = MarketPipeline("R1", "M1", "NSE", MarketWorkflowType.MARKET_OVERVIEW, pipeline_id="P1")
        p2  = MarketPipeline("R2", "M2", "BSE", MarketWorkflowType.MARKET_OVERVIEW, pipeline_id="P2")
        reg.register_pipeline(p1)
        reg.register_pipeline(p2)
        result = reg.query(exchange="NSE")
        assert len(result) == 1
        assert result[0].exchange == "NSE"

    def test_register_and_get_request(self):
        reg = MarketEngineRegistry()
        r   = _make_request()
        reg.register_request(r)
        assert reg.get_request(r.request_id) is r

    def test_register_and_get_response(self):
        reg  = MarketEngineRegistry()
        resp = MarketResponse.create_success("R1", "M", "N", MarketWorkflowType.MARKET_OVERVIEW)
        reg.register_response(resp)
        assert reg.get_response("R1") is resp

    def test_statistics(self):
        reg = MarketEngineRegistry()
        p   = self._make_pipeline()
        reg.register_pipeline(p)
        st  = reg.statistics()
        assert st["active_pipelines"] == 1

    def test_is_ready(self):
        reg = MarketEngineRegistry(max_pipelines=2)
        assert reg.is_ready()
        reg.register_pipeline(self._make_pipeline("P1"))
        reg.register_pipeline(self._make_pipeline("P2"))
        assert not reg.is_ready()

    def test_clear(self):
        reg = MarketEngineRegistry()
        reg.register_pipeline(self._make_pipeline())
        reg.clear()
        assert reg.active_pipeline_count() == 0

    def test_thread_safe(self):
        reg    = MarketEngineRegistry(max_pipelines=500)
        errors: List[str] = []

        def worker(i: int):
            try:
                p = self._make_pipeline(f"P{i}")
                reg.register_pipeline(p)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert reg.active_pipeline_count() == 100


# ============================================================================
# 11  VALIDATION
# ============================================================================

class TestMarketValidation:
    def test_valid_request_passes_all(self):
        v   = MarketEngineValidator()
        r   = _make_request()
        res = v.validate_request(r)
        assert res.is_valid
        assert len(res.checks) == 6

    def test_empty_analysis_id_fails(self):
        v = MarketEngineValidator()
        r = MarketRequest.create("", "NSE")
        # context will have same empty id; check identifier_consistency
        res = v.validate_request(r)
        assert not res.is_valid
        assert "identifier_consistency" in res.failed_checks

    def test_empty_exchange_fails(self):
        v = MarketEngineValidator()
        r = MarketRequest.create("MKT-001", "")
        res = v.validate_request(r)
        assert not res.is_valid

    def test_validate_or_raise_valid(self):
        v = MarketEngineValidator()
        v.validate_or_raise(_make_request())  # must not raise

    def test_validate_or_raise_invalid(self):
        v = MarketEngineValidator()
        r = MarketRequest.create("", "NSE")
        with pytest.raises(MarketEngineValidationError):
            v.validate_or_raise(r)

    def test_lifecycle_readiness_check(self):
        v   = MarketEngineValidator(max_sessions=1, active_count_fn=lambda: 0)
        res = v.validate_request(_make_request())
        assert res.is_valid

    def test_lifecycle_readiness_at_limit(self):
        v   = MarketEngineValidator(max_sessions=1, active_count_fn=lambda: 1)
        res = v.validate_request(_make_request())
        assert not res.is_valid
        assert "lifecycle_readiness" in res.failed_checks

    def test_error_messages_empty_when_valid(self):
        v   = MarketEngineValidator()
        res = v.validate_request(_make_request())
        assert res.error_messages == []

    def test_failed_checks_list(self):
        v   = MarketEngineValidator()
        r   = MarketRequest.create("", "NSE")
        res = v.validate_request(r)
        assert isinstance(res.failed_checks, list)


# ============================================================================
# 12  STATISTICS
# ============================================================================

class TestMarketEngineStatistics:
    def test_initial_all_zero(self):
        s    = MarketEngineStatistics()
        snap = s.snapshot()
        for k in ("sessions_created", "sessions_completed", "sessions_failed",
                  "requests_submitted", "requests_completed", "requests_failed",
                  "pipelines_started", "pipelines_completed", "pipelines_failed",
                  "snapshots_published"):
            assert snap[k] == 0

    def test_record_session_created(self):
        s = MarketEngineStatistics()
        s.record_session_created()
        assert s.snapshot()["sessions_created"] == 1

    def test_record_pipeline_completed_updates_mean(self):
        s = MarketEngineStatistics()
        s.record_pipeline_completed(elapsed_s=10.0)
        assert s.snapshot()["avg_analysis_time_s"] == pytest.approx(10.0)

    def test_record_snapshot_published(self):
        s = MarketEngineStatistics()
        s.record_snapshot_published()
        assert s.snapshot()["snapshots_published"] == 1

    def test_throughput_per_min_increments(self):
        s = MarketEngineStatistics()
        for _ in range(3):
            s.record_pipeline_completed(elapsed_s=0.1)
        assert s.snapshot()["throughput_per_min"] == 3

    def test_reset(self):
        s = MarketEngineStatistics()
        s.record_session_created()
        s.record_pipeline_failed()
        s.reset()
        snap = s.snapshot()
        assert snap["sessions_created"]  == 0
        assert snap["pipelines_failed"]  == 0

    def test_thread_safe(self):
        s = MarketEngineStatistics()

        def worker():
            for _ in range(200):
                s.record_request_submitted()

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert s.snapshot()["requests_submitted"] == 1000


# ============================================================================
# 13  HISTORY
# ============================================================================

class TestMarketEngineHistory:
    def test_record_and_retrieve_event(self):
        h = MarketEngineHistory()
        e = make_market_engine_initialized("M", "N", "S")
        h.record_event(e)
        assert h.counts()["events"] == 1
        assert h.recent_events(1)[0] is e

    def test_record_request(self):
        h = MarketEngineHistory()
        r = _make_request()
        h.record_request(r)
        assert h.counts()["requests"] == 1

    def test_record_response(self):
        h    = MarketEngineHistory()
        resp = MarketResponse.create_success("R1", "M", "N", MarketWorkflowType.MARKET_OVERVIEW)
        h.record_response(resp)
        assert h.counts()["responses"] == 1

    def test_record_pipeline(self):
        h = MarketEngineHistory()
        p = MarketPipeline("R", "M", "N", MarketWorkflowType.MARKET_OVERVIEW)
        h.record_pipeline(p)
        assert h.counts()["pipelines"] == 1

    def test_bounded(self):
        h = MarketEngineHistory(max_events=3)
        for i in range(5):
            h.record_event(make_market_engine_initialized(f"M{i}", "N", "S"))
        assert h.counts()["events"] == 3

    def test_clear(self):
        h = MarketEngineHistory()
        h.record_event(make_market_engine_initialized("M", "N", "S"))
        h.clear()
        assert h.counts()["events"] == 0

    def test_recent_n_limit(self):
        h = MarketEngineHistory()
        for i in range(10):
            h.record_event(make_market_engine_initialized(f"M{i}", "N", "S"))
        recent = h.recent_events(3)
        assert len(recent) == 3


# ============================================================================
# 14  FACTORY
# ============================================================================

class TestMarketEngineFactory:
    def test_create_context(self):
        f   = MarketEngineFactory()
        ctx = f.create_context("M", "N", MarketWorkflowType.MARKET_OVERVIEW)
        assert ctx.market_analysis_id == "M"
        assert ctx.exchange           == "N"

    def test_create_request(self):
        f = MarketEngineFactory()
        r = f.create_request("M", "N")
        assert r.market_analysis_id == "M"
        assert r.exchange           == "N"

    def test_create_pipeline(self):
        f   = MarketEngineFactory()
        r   = f.create_request("M", "N")
        p   = f.create_pipeline(r)
        assert p.market_analysis_id == "M"
        assert p.exchange           == "N"
        assert p.request_id         == r.request_id

    def test_create_snapshot(self):
        f    = MarketEngineFactory()
        snap = f.create_snapshot(
            "M", "N", "S",
            MarketWorkflowType.MARKET_OVERVIEW,
            EngineState.PUBLISHING,
        )
        assert snap.market_analysis_id == "M"
        assert snap.exchange           == "N"

    def test_create_success_response(self):
        f    = MarketEngineFactory()
        r    = f.create_request("M", "N")
        resp = f.create_success_response(r)
        assert resp.is_success

    def test_create_failure_response(self):
        f    = MarketEngineFactory()
        r    = f.create_request("M", "N")
        resp = f.create_failure_response(r, error_message="boom")
        assert resp.is_failure
        assert resp.error_message == "boom"


# ============================================================================
# 15  HEALTH
# ============================================================================

class TestMarketEngineHealth:
    def test_healthy_report(self):
        h     = MarketEngineHealth(max_sessions=10)
        sm    = MarketSessionManager()
        sm.start()
        d     = MarketDispatcher()
        report = h.report(sm, d)
        assert report["overall"] == "healthy"
        sm.stop()

    def test_degraded_when_at_capacity(self):
        # Simulate a session manager returning max count
        mock_sm = MagicMock()
        mock_sm.active_session_count.return_value = 10
        h      = MarketEngineHealth(max_sessions=10)
        d      = MarketDispatcher()
        report = h.report(mock_sm, d)
        assert report["overall"] == "degraded"

    def test_report_contains_checked_at(self):
        h  = MarketEngineHealth()
        sm = MarketSessionManager()
        sm.start()
        d  = MarketDispatcher()
        r  = h.report(sm, d)
        assert "checked_at" in r
        sm.stop()


# ============================================================================
# 16  STATUS
# ============================================================================

class TestMarketEngineStatus:
    def test_to_dict(self):
        st = MarketEngineStatus(
            engine_id     = ENGINE_SYSTEM_ID,
            state         = "running",
            engine_state  = EngineState.IDLE,
            session_count = 0,
            pipeline_count = 0,
        )
        d = st.to_dict()
        assert d["engine_id"]    == ENGINE_SYSTEM_ID
        assert d["state"]        == "running"
        assert d["engine_state"] == "idle"

    def test_is_frozen(self):
        st = MarketEngineStatus(
            engine_id="X", state="running",
            engine_state=EngineState.IDLE,
            session_count=0, pipeline_count=0,
        )
        with pytest.raises((AttributeError, TypeError)):
            st.state = "stopped"  # type: ignore[misc]


# ============================================================================
# 17  ENGINE — initialization
# ============================================================================

class TestEngineInitialization:
    def test_create_default(self):
        e = MarketEngine()
        assert e is not None

    def test_initial_not_running(self):
        e = MarketEngine()
        assert e.lifecycle_state().value != "running"

    def test_start_transitions_to_running(self):
        e = MarketEngine()
        e.start()
        assert e.lifecycle_state().value == "running"
        e.stop()

    def test_stop_transitions_out_of_running(self):
        e = _started_engine()
        e.stop()
        assert e.lifecycle_state().value != "running"

    def test_submit_before_start_raises(self):
        e = MarketEngine()
        with pytest.raises(MarketEngineNotRunningError):
            e.submit(_make_request())


# ============================================================================
# 18  ENGINE — happy path workflows
# ============================================================================

class TestEngineWorkflows:
    def test_submit_returns_success(self):
        e    = _started_engine()
        resp = e.submit(_make_request())
        assert resp.is_success
        e.stop()

    def test_initialize_market(self):
        e    = _started_engine()
        resp = e.initialize_market("MKT-001", "NSE")
        assert resp.is_success
        assert resp.market_analysis_id == "MKT-001"
        assert resp.exchange           == "NSE"
        e.stop()

    def test_start_analysis(self):
        e    = _started_engine()
        resp = e.start_analysis("MKT-001", "NSE")
        assert resp.is_success
        assert resp.workflow_type == MarketWorkflowType.MARKET_OVERVIEW
        e.stop()

    def test_stop_analysis(self):
        e    = _started_engine()
        resp = e.stop_analysis("MKT-001", "NSE")
        assert resp.is_success
        assert resp.workflow_type == MarketWorkflowType.EOD_REVIEW
        e.stop()

    def test_dispatch(self):
        e    = _started_engine()
        resp = e.dispatch("MKT-001", "NSE")
        assert resp.is_success
        assert resp.workflow_type == MarketWorkflowType.INTRADAY_MONITORING
        e.stop()

    def test_publish(self):
        e    = _started_engine()
        resp = e.publish("MKT-001", "NSE")
        assert resp.is_success
        e.stop()

    def test_collect_with_inputs(self):
        e    = _started_engine()
        resp = e.collect("MKT-001", "NSE", inputs={"market_feed": {}})
        assert resp.is_success
        e.stop()

    def test_all_workflow_types(self):
        e = _started_engine()
        for i, wt in enumerate(MarketWorkflowType):
            resp = e.initialize_market(f"MKT-{i}", "NSE", workflow_type=wt)
            assert resp.is_success, f"workflow {wt} failed: {resp.error_message}"
        e.stop()

    def test_response_has_snapshot(self):
        e    = _started_engine()
        resp = e.initialize_market("MKT-001", "NSE")
        assert resp.has_snapshot
        e.stop()

    def test_statistics_after_submit(self):
        e = _started_engine()
        e.initialize_market("MKT-001", "NSE")
        e.initialize_market("MKT-002", "BSE")
        snap = e.statistics()
        assert snap["requests_submitted"]  == 2
        assert snap["pipelines_completed"] == 2
        assert snap["snapshots_published"] == 2
        e.stop()


# ============================================================================
# 19  ENGINE — query & validate
# ============================================================================

class TestEngineQueryValidate:
    def test_query_empty(self):
        e = _started_engine()
        assert e.query() == []
        e.stop()

    def test_validate_valid_request(self):
        e   = _started_engine()
        r   = _make_request()
        res = e.validate(r)
        assert res.is_valid
        e.stop()

    def test_validate_before_start_raises(self):
        e = MarketEngine()
        with pytest.raises(MarketEngineNotRunningError):
            e.validate(_make_request())


# ============================================================================
# 20  ENGINE — observability
# ============================================================================

class TestEngineObservability:
    def test_health_returns_dict(self):
        e = _started_engine()
        h = e.health()
        assert "overall" in h
        e.stop()

    def test_status_returns_status(self):
        e  = _started_engine()
        st = e.status()
        assert isinstance(st, MarketEngineStatus)
        assert st.state == "running"
        e.stop()

    def test_statistics_returns_dict(self):
        e    = _started_engine()
        snap = e.statistics()
        assert isinstance(snap, dict)
        assert "requests_submitted" in snap
        e.stop()

    def test_status_engine_state_idle_at_start(self):
        e  = _started_engine()
        st = e.status()
        assert st.engine_state == EngineState.IDLE
        e.stop()


# ============================================================================
# 21  ENGINE — listeners
# ============================================================================

class TestEngineListeners:
    def test_listener_receives_events(self):
        events: List[MarketEngineEvent] = []
        e = _started_engine()
        e.add_listener(events.append)
        e.initialize_market("MKT-001", "NSE")
        assert len(events) >= 2
        e.stop()

    def test_remove_listener(self):
        events: List[MarketEngineEvent] = []
        e = _started_engine()
        e.add_listener(events.append)
        e.remove_listener(events.append)
        e.initialize_market("MKT-001", "NSE")
        assert events == []
        e.stop()

    def test_faulty_listener_does_not_crash(self):
        def bad(evt):
            raise RuntimeError("crash")

        e = _started_engine()
        e.add_listener(bad)
        e.initialize_market("MKT-001", "NSE")  # must not raise
        e.stop()

    def test_all_event_types_emitted_in_happy_path(self):
        emitted: List[MarketEngineEventType] = []
        e = _started_engine()
        e.add_listener(lambda ev: emitted.append(ev.event_type))
        e.initialize_market("MKT-001", "NSE")
        expected = {
            MarketEngineEventType.MARKET_STARTED,
            MarketEngineEventType.MARKET_INITIALIZED,
            MarketEngineEventType.MARKET_COLLECTED,
            MarketEngineEventType.MARKET_DISPATCHED,
            MarketEngineEventType.MARKET_ANALYSIS_STARTED,
            MarketEngineEventType.MARKET_PUBLISHED,
            MarketEngineEventType.MARKET_COMPLETED,
        }
        assert expected.issubset(set(emitted))
        e.stop()

    def test_stopped_event_on_stop(self):
        emitted: List[MarketEngineEventType] = []
        e = _started_engine()
        e.add_listener(lambda ev: emitted.append(ev.event_type))
        e.stop()
        assert MarketEngineEventType.MARKET_STOPPED in emitted


# ============================================================================
# 22  ENGINE — framework registration
# ============================================================================

class TestEngineFrameworkRegistration:
    def test_register_policy_framework(self):
        e = _started_engine()
        e.register_policy_framework(lambda p, r: None)
        assert e._dispatcher.has_policy_framework
        e.stop()

    def test_register_analytics_framework(self):
        e = _started_engine()
        e.register_analytics_framework(lambda p, r: None)
        assert e._dispatcher.has_analytics_framework
        e.stop()

    def test_workflow_runs_with_policy_framework(self):
        e = _started_engine()
        called = []
        e.register_policy_framework(lambda p, r: called.append(r.market_analysis_id))
        resp = e.initialize_market("MKT-001", "NSE")
        assert resp.is_success
        assert "MKT-001" in called
        e.stop()

    def test_workflow_runs_with_analytics_framework(self):
        e = _started_engine()
        called = []
        e.register_analytics_framework(lambda p, r: called.append(r.exchange))
        resp = e.initialize_market("MKT-001", "NSE")
        assert resp.is_success
        assert "NSE" in called
        e.stop()

    def test_failing_policy_framework_returns_failure(self):
        e = _started_engine()
        e.register_policy_framework(
            lambda p, r: (_ for _ in ()).throw(RuntimeError("policy error"))
        )
        resp = e.initialize_market("MKT-001", "NSE")
        assert resp.is_failure
        e.stop()


# ============================================================================
# 23  CONCURRENCY
# ============================================================================

class TestConcurrency:
    def test_concurrent_submissions(self):
        e      = _started_engine()
        errors: List[str] = []
        lock   = threading.Lock()
        responses: List[MarketResponse] = []

        def worker(i: int):
            try:
                resp = e.initialize_market(f"MKT-{i}", "NSE")
                with lock:
                    responses.append(resp)
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        e.stop()
        assert errors == []
        assert len(responses) == 30
        assert all(r.is_success for r in responses)

    def test_concurrent_statistics(self):
        s      = MarketEngineStatistics()
        errors: List[str] = []

        def worker():
            for _ in range(100):
                s.record_request_submitted()

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert s.snapshot()["requests_submitted"] == 1000
        assert errors == []

    def test_concurrent_scheduler(self):
        sched  = MarketScheduler(max_queue_size=500)
        errors: List[str] = []

        def worker(i: int):
            try:
                sched.schedule(_make_request(f"MKT-{i}"))
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert sched.pending_count() == 100


# ============================================================================
# 24  STRESS
# ============================================================================

class TestStress:
    def test_hundred_sequential_workflows(self):
        e = _started_engine()
        for i in range(100):
            resp = e.initialize_market(f"MKT-{i:03d}", "NSE")
            assert resp.is_success
        snap = e.statistics()
        assert snap["requests_completed"]  == 100
        assert snap["pipelines_completed"] == 100
        e.stop()

    def test_all_workflow_types_many_times(self):
        e = _started_engine()
        for _ in range(5):
            for i, wt in enumerate(MarketWorkflowType):
                resp = e.initialize_market(f"MKT-{i}", "NSE", workflow_type=wt)
                assert resp.is_success
        e.stop()


# ============================================================================
# 25  REGRESSION
# ============================================================================

class TestRegression:
    def test_full_happy_path_returns_snapshot(self):
        e    = _started_engine()
        resp = e.initialize_market("MKT-001", "NSE")
        assert resp.is_success
        assert resp.has_snapshot
        snap = resp.snapshot
        assert snap.market_analysis_id == "MKT-001"
        assert snap.exchange           == "NSE"
        e.stop()

    def test_multiple_engines_independent(self):
        e1 = _started_engine()
        e2 = _started_engine()
        r1 = e1.initialize_market("E1-MKT", "NSE")
        r2 = e2.initialize_market("E2-MKT", "BSE")
        assert r1.is_success
        assert r2.is_success
        assert e1.statistics()["requests_completed"] == 1
        assert e2.statistics()["requests_completed"] == 1
        e1.stop()
        e2.stop()

    def test_failure_response_no_snapshot(self):
        e = _started_engine()
        e.register_policy_framework(
            lambda p, r: (_ for _ in ()).throw(RuntimeError("forced fail"))
        )
        resp = e.initialize_market("MKT-001", "NSE")
        assert resp.is_failure
        assert not resp.has_snapshot
        assert e.statistics()["pipelines_failed"] == 1
        e.stop()

    def test_history_records_requests_and_responses(self):
        e = _started_engine()
        e.initialize_market("MKT-001", "NSE")
        e.initialize_market("MKT-002", "BSE")
        counts = e._history.counts()
        assert counts["requests"]  >= 2
        assert counts["responses"] >= 2
        e.stop()

    def test_scheduler_statistics_after_workflow(self):
        e = _started_engine()
        e.initialize_market("MKT-001", "NSE")
        st = e._scheduler.statistics()
        assert st["scheduled"] >= 1
        e.stop()

    def test_snapshot_has_correct_workflow_type(self):
        e    = _started_engine()
        resp = e.initialize_market(
            "MKT-001", "NSE",
            workflow_type=MarketWorkflowType.SECTOR_ANALYSIS,
        )
        assert resp.snapshot.workflow_type == MarketWorkflowType.SECTOR_ANALYSIS
        e.stop()

    def test_start_stop_start(self):
        e = MarketEngine()
        e.start()
        e.stop()
        e.start()
        resp = e.initialize_market("MKT-001", "NSE")
        assert resp.is_success
        e.stop()
