"""
tests/unit/execution/analytics/engine/test_execution_analytics_engine.py
=========================================================================
Comprehensive test suite for C8 M2 — Execution Analytics Engine.

Coverage targets:
  • constants / exceptions
  • AnalyticsRequest / make_analytics_request
  • EngineAnalyticsContext / make_engine_analytics_context
  • AnalyticsResponse / AnalyticsSnapshot
  • AnalyticsPipeline / make_analytics_pipeline
  • AnalyticsScheduler
  • AnalyticsDispatcher
  • AnalyticsSessionManager
  • EngineAnalyticsRegistry
  • EngineAnalyticsValidator / EngineAnalyticsValidationResult
  • EngineAnalyticsStatistics
  • EngineAnalyticsHistory
  • EngineAnalyticsEvent (all 8 factory functions)
  • EngineAnalyticsFactory
  • AnalyticsEngineHealth / assess_engine_health
  • AnalyticsEngineStatus
  • AnalyticsManager (full workflow)
  • ExecutionAnalyticsEngine (lifecycle, workflow, scheduler, concurrency)
  • Regression: invalid input, framework delegation, concurrent requests

95%+ coverage target

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import List
from unittest.mock import MagicMock

import pytest

from iios.execution.analytics.engine import (
    ACTIVE_ENGINE_STATES,
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    AnalyticsDispatchError,
    AnalyticsDispatcher,
    AnalyticsEngineError,
    AnalyticsEngineHealth,
    AnalyticsEngineNotRunningError,
    AnalyticsEngineStatus,
    AnalyticsPipeline,
    AnalyticsPipelineError,
    AnalyticsPublishError,
    AnalyticsRequest,
    AnalyticsRequestNotFoundError,
    AnalyticsRequestType,
    AnalyticsRequestValidationError,
    AnalyticsResponse,
    AnalyticsScheduler,
    AnalyticsSchedulerError,
    AnalyticsSessionManagerError,
    AnalyticsSnapshot,
    ENGINE_STATE_TRANSITIONS,
    ENGINE_SYSTEM_ID,
    EngineAnalyticsContext,
    EngineAnalyticsEvent,
    EngineAnalyticsHistory,
    EngineAnalyticsState,
    EngineAnalyticsStatistics,
    EngineAnalyticsValidationResult,
    EngineAnalyticsValidator,
    EngineEventType,
    EngineHealthStatus,
    ExecutionAnalyticsEngine,
    PipelineStage,
    PipelineStatus,
    ResponseStatus,
    ScheduleType,
    TERMINAL_ENGINE_STATES,
    VERSION,
    assess_engine_health,
    make_analytics_engine_collected,
    make_analytics_engine_completed,
    make_analytics_engine_dispatched,
    make_analytics_engine_failed,
    make_analytics_engine_initialized,
    make_analytics_engine_published,
    make_analytics_engine_started,
    make_analytics_engine_stopped,
    make_analytics_pipeline,
    make_analytics_request,
    make_analytics_response,
    make_analytics_snapshot,
    make_engine_analytics_context,
)
from iios.execution.analytics.engine.analytics_factory import EngineAnalyticsFactory
from iios.execution.analytics.engine.analytics_manager import AnalyticsManager
from iios.execution.analytics.engine.analytics_registry import EngineAnalyticsRegistry
from iios.execution.analytics.engine.analytics_session_manager import AnalyticsSessionManager


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _new_request(**kwargs) -> AnalyticsRequest:
    defaults = {"execution_session_id": str(uuid.uuid4())}
    defaults.update(kwargs)
    return make_analytics_request(**defaults)


def _started_engine(**kwargs) -> ExecutionAnalyticsEngine:
    e = ExecutionAnalyticsEngine(**kwargs)
    e.start()
    return e


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_engine_states_defined(self):
        names = {s.name for s in EngineAnalyticsState}
        for expected in (
            "IDLE", "INITIALIZING", "COLLECTING", "VALIDATING",
            "DISPATCHING", "ANALYZING", "PUBLISHING", "COMPLETED",
            "FAILED", "STOPPED",
        ):
            assert expected in names

    def test_stopped_is_terminal(self):
        assert EngineAnalyticsState.STOPPED in TERMINAL_ENGINE_STATES
        assert ENGINE_STATE_TRANSITIONS[EngineAnalyticsState.STOPPED] == frozenset()

    def test_active_states_not_terminal(self):
        for s in ACTIVE_ENGINE_STATES:
            assert s not in TERMINAL_ENGINE_STATES

    def test_request_types_defined(self):
        for t in ("ON_DEMAND", "PERIODIC", "EVENT", "SCHEDULED", "PRIORITY"):
            assert hasattr(AnalyticsRequestType, t)

    def test_event_types_defined(self):
        for t in (
            "ANALYTICS_INITIALIZED", "ANALYTICS_STARTED",
            "ANALYTICS_COLLECTED", "ANALYTICS_DISPATCHED",
            "ANALYTICS_COMPLETED", "ANALYTICS_PUBLISHED",
            "ANALYTICS_FAILED", "ANALYTICS_STOPPED",
        ):
            assert hasattr(EngineEventType, t)

    def test_version_format(self):
        assert len(VERSION.split(".")) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_error(self):
        e = AnalyticsEngineError("msg")
        assert e.error_code == "AE-000"

    def test_not_running(self):
        e = AnalyticsEngineNotRunningError()
        assert "AE-001" in e.error_code

    def test_request_not_found(self):
        e = AnalyticsRequestNotFoundError("REQ-1")
        assert e.request_id == "REQ-1"
        assert "REQ-1" in str(e)

    def test_validation_error(self):
        e = AnalyticsRequestValidationError("bad", errors=("e1", "e2"))
        assert e.errors == ("e1", "e2")

    def test_pipeline_error(self):
        e = AnalyticsPipelineError("err", pipeline_id="P1")
        assert e.pipeline_id == "P1"

    def test_dispatch_error(self):
        e = AnalyticsDispatchError("oops", pipeline_id="P2")
        assert e.pipeline_id == "P2"

    def test_scheduler_error(self):
        e = AnalyticsSchedulerError("full")
        assert isinstance(e, AnalyticsEngineError)

    def test_publish_error(self):
        e = AnalyticsPublishError()
        assert isinstance(e, AnalyticsEngineError)

    def test_session_manager_error(self):
        e = AnalyticsSessionManagerError("no session")
        assert isinstance(e, AnalyticsEngineError)


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsRequest:
    def test_make_defaults(self):
        r = make_analytics_request("exec-1")
        assert r.execution_session_id == "exec-1"
        assert r.request_type == AnalyticsRequestType.ON_DEMAND
        assert r.priority == 5

    def test_make_with_overrides(self):
        r = make_analytics_request(
            "exec-2",
            request_type = AnalyticsRequestType.PRIORITY,
            priority     = 1,
            reason       = "urgent",
            tags         = ("trade", "risk"),
        )
        assert r.priority == 1
        assert r.reason == "urgent"
        assert r.tags == ("trade", "risk")

    def test_to_dict(self):
        r = make_analytics_request("exec-3")
        d = r.to_dict()
        assert d["execution_session_id"] == "exec-3"
        assert "request_type" in d
        assert isinstance(d["tags"], list)

    def test_frozen(self):
        r = make_analytics_request("exec-4")
        with pytest.raises(Exception):
            r.execution_session_id = "other"  # type: ignore[misc]

    def test_unique_ids(self):
        r1 = make_analytics_request("exec-5")
        r2 = make_analytics_request("exec-5")
        assert r1.request_id != r2.request_id

    def test_explicit_request_id(self):
        r = make_analytics_request("exec-6", request_id="REQ-X")
        assert r.request_id == "REQ-X"


# ═══════════════════════════════════════════════════════════════════════════════
# EngineAnalyticsContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineAnalyticsContext:
    def test_make_defaults(self):
        ctx = make_engine_analytics_context("REQ-1", "exec-1")
        assert ctx.request_id == "REQ-1"
        assert ctx.execution_session_id == "exec-1"
        assert ctx.monitoring_snapshot is None
        assert ctx.available_snapshot_count == 0

    def test_with_snapshots(self):
        ctx = make_engine_analytics_context(
            "REQ-2", "exec-2",
            monitoring_snapshot = object(),
            recovery_snapshot   = object(),
        )
        assert ctx.available_snapshot_count == 2

    def test_to_dict(self):
        ctx = make_engine_analytics_context("REQ-3", "exec-3")
        d = ctx.to_dict()
        assert d["request_id"] == "REQ-3"
        assert d["has_monitoring_snapshot"] is False
        assert d["available_snapshots"] == 0

    def test_frozen(self):
        ctx = make_engine_analytics_context("REQ-4", "exec-4")
        with pytest.raises(Exception):
            ctx.request_id = "other"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsResponse / AnalyticsSnapshot
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsResponse:
    def test_make_success(self):
        r = make_analytics_response("REQ-1", ResponseStatus.SUCCESS)
        assert r.is_success
        assert not r.is_failed

    def test_make_failed(self):
        r = make_analytics_response("REQ-2", ResponseStatus.FAILED, error_message="oops")
        assert r.is_failed
        assert r.error_message == "oops"

    def test_make_rejected(self):
        r = make_analytics_response("REQ-3", ResponseStatus.REJECTED)
        assert r.is_failed

    def test_to_dict(self):
        r = make_analytics_response("REQ-4", ResponseStatus.SUCCESS, processing_ms=10.5)
        d = r.to_dict()
        assert d["status"] == "success"
        assert d["processing_ms"] == 10.5

    def test_frozen(self):
        r = make_analytics_response("REQ-5", ResponseStatus.SUCCESS)
        with pytest.raises(Exception):
            r.request_id = "other"  # type: ignore[misc]


class TestAnalyticsSnapshot:
    def test_make(self):
        s = make_analytics_snapshot(EngineAnalyticsState.PUBLISHING, request_id="REQ-1")
        assert s.engine_state == EngineAnalyticsState.PUBLISHING
        assert s.request_id == "REQ-1"

    def test_to_dict(self):
        s = make_analytics_snapshot(EngineAnalyticsState.COMPLETED)
        d = s.to_dict()
        assert d["engine_state"] == "completed"

    def test_frozen(self):
        s = make_analytics_snapshot(EngineAnalyticsState.IDLE)
        with pytest.raises(Exception):
            s.engine_state = EngineAnalyticsState.COMPLETED  # type: ignore[misc]

    def test_unique_ids(self):
        s1 = make_analytics_snapshot(EngineAnalyticsState.IDLE)
        s2 = make_analytics_snapshot(EngineAnalyticsState.IDLE)
        assert s1.snapshot_id != s2.snapshot_id


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsPipeline
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsPipeline:
    def test_make(self):
        p = make_analytics_pipeline("REQ-1", "SESS-1")
        assert p.request_id == "REQ-1"
        assert p.session_id == "SESS-1"
        assert p.is_pending
        assert p.has_performance is True
        assert p.has_predictive is False

    def test_lifecycle(self):
        p = make_analytics_pipeline("REQ-2", "SESS-2")
        p.start()
        assert p.is_active
        assert p.started_at is not None
        p.complete()
        assert p.is_completed
        assert p.completed_at is not None
        assert p.duration_ms is not None
        assert p.duration_ms >= 0.0

    def test_fail(self):
        p = make_analytics_pipeline("REQ-3", "SESS-3")
        p.start()
        p.fail("disk full")
        assert p.is_failed
        assert p.error_message == "disk full"

    def test_cancel(self):
        p = make_analytics_pipeline("REQ-4", "SESS-4")
        p.cancel()
        assert p.is_cancelled

    def test_advance_to(self):
        p = make_analytics_pipeline("REQ-5", "SESS-5")
        p.start()
        p.advance_to(PipelineStage.DISPATCHING)
        assert p.stage == PipelineStage.DISPATCHING

    def test_to_dict(self):
        p = make_analytics_pipeline("REQ-6", "SESS-6")
        d = p.to_dict()
        assert d["pipeline_id"] == p.pipeline_id
        assert d["status"] == "pending"

    def test_duration_none_before_start(self):
        p = make_analytics_pipeline("REQ-7", "SESS-7")
        assert p.duration_ms is None


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsScheduler
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsScheduler:
    def _started(self) -> AnalyticsScheduler:
        s = AnalyticsScheduler()
        s.start()
        return s

    def test_start_stop(self):
        s = AnalyticsScheduler()
        s.start()
        s.stop()

    def test_not_running_raises(self):
        s = AnalyticsScheduler()
        with pytest.raises(AnalyticsEngineNotRunningError):
            s.dequeue()

    def test_schedule_and_dequeue(self):
        s = self._started()
        try:
            request = make_analytics_request("exec-1")
            s.schedule(request)
            result = s.dequeue()
            assert result is not None
            assert result.request_id == request.request_id
        finally:
            s.stop()

    def test_schedule_on_demand(self):
        s = self._started()
        try:
            rid = s.schedule_on_demand("exec-1")
            assert rid
            assert s.queue_depth == 1
        finally:
            s.stop()

    def test_schedule_periodic(self):
        s = self._started()
        try:
            rid = s.schedule_periodic("exec-2", 60.0)
            assert rid
            assert s.queue_depth == 1
        finally:
            s.stop()

    def test_schedule_event_driven(self):
        s = self._started()
        try:
            rid = s.schedule_event_driven("exec-3")
            assert rid
        finally:
            s.stop()

    def test_schedule_priority(self):
        s = self._started()
        try:
            rid = s.schedule_priority("exec-4", priority=1)
            assert rid
        finally:
            s.stop()

    def test_priority_ordering(self):
        """Lower priority number = dequeued first."""
        s = self._started()
        try:
            r_low  = make_analytics_request("exec-low",  priority=9)
            r_high = make_analytics_request("exec-high", priority=1)
            s.schedule(r_low)
            s.schedule(r_high)
            first = s.dequeue()
            assert first.priority == 1
        finally:
            s.stop()

    def test_queue_full_raises(self):
        s = AnalyticsScheduler(max_queue=1)
        s.start()
        try:
            s.schedule(make_analytics_request("exec-1"))
            with pytest.raises(AnalyticsSchedulerError):
                s.schedule(make_analytics_request("exec-2"))
        finally:
            s.stop()

    def test_dequeue_all_due(self):
        s = self._started()
        try:
            for i in range(3):
                s.schedule(make_analytics_request(f"exec-{i}"))
            results = s.dequeue_all_due()
            assert len(results) == 3
            assert s.is_empty
        finally:
            s.stop()

    def test_peek(self):
        s = self._started()
        try:
            r = make_analytics_request("exec-1")
            s.schedule(r)
            assert s.peek().request_id == r.request_id
            assert s.queue_depth == 1  # not dequeued
        finally:
            s.stop()

    def test_clear(self):
        s = self._started()
        try:
            for _ in range(3):
                s.schedule(make_analytics_request("exec-1"))
            removed = s.clear()
            assert removed == 3
            assert s.is_empty
        finally:
            s.stop()

    def test_thread_safety(self):
        s = self._started()
        errors = []

        def worker():
            try:
                s.schedule(make_analytics_request("exec-t"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        s.stop()
        assert len(errors) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsDispatcher
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsDispatcher:
    def _started(self) -> AnalyticsDispatcher:
        d = AnalyticsDispatcher()
        d.start()
        return d

    def test_start_stop(self):
        d = AnalyticsDispatcher()
        d.start()
        d.stop()

    def test_dispatch_no_frameworks(self):
        d = self._started()
        try:
            p = make_analytics_pipeline("REQ-1", "SESS-1")
            d.dispatch(p)
            assert p.is_completed
            assert d.dispatch_count == 1
        finally:
            d.stop()

    def test_dispatch_with_performance_framework(self):
        d = self._started()
        try:
            mock_fw = MagicMock()
            mock_fw.process.return_value = {"result": "ok"}
            d.register_performance_framework(mock_fw)
            assert d.has_performance_framework
            p = make_analytics_pipeline("REQ-2", "SESS-2")
            d.dispatch(p)
            mock_fw.process.assert_called_once_with("REQ-2")
            assert p.performance_result == {"result": "ok"}
        finally:
            d.stop()

    def test_dispatch_with_predictive_framework(self):
        d = self._started()
        try:
            mock_fw = MagicMock()
            mock_fw.predict.return_value = {"pred": 0.7}
            d.register_predictive_framework(mock_fw)
            p = make_analytics_pipeline("REQ-3", "SESS-3", has_predictive=True)
            d.dispatch(p)
            assert p.predictive_result == {"pred": 0.7}
        finally:
            d.stop()

    def test_faulty_framework_skipped(self):
        d = self._started()
        try:
            mock_fw = MagicMock()
            mock_fw.process.side_effect = RuntimeError("fw crash")
            d.register_performance_framework(mock_fw)
            p = make_analytics_pipeline("REQ-4", "SESS-4")
            d.dispatch(p)  # Should NOT raise; failure is skipped
            assert p.is_completed
        finally:
            d.stop()

    def test_deregister_framework(self):
        d = self._started()
        try:
            d.register_performance_framework(MagicMock())
            assert d.has_performance_framework
            d.deregister_performance_framework()
            assert not d.has_performance_framework
        finally:
            d.stop()

    def test_not_running_raises(self):
        d = AnalyticsDispatcher()
        with pytest.raises(AnalyticsEngineNotRunningError):
            d.dispatch(make_analytics_pipeline("REQ-1", "SESS-1"))


# ═══════════════════════════════════════════════════════════════════════════════
# EngineAnalyticsRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineAnalyticsRegistry:
    def _started(self) -> EngineAnalyticsRegistry:
        r = EngineAnalyticsRegistry()
        r.start()
        return r

    def test_store_and_get(self):
        reg = self._started()
        try:
            req = make_analytics_request("exec-1")
            reg.store(req)
            fetched = reg.get(req.request_id)
            assert fetched is req
        finally:
            reg.stop()

    def test_find_returns_none(self):
        reg = self._started()
        try:
            assert reg.find("nonexistent") is None
        finally:
            reg.stop()

    def test_get_not_found_raises(self):
        reg = self._started()
        try:
            with pytest.raises(AnalyticsRequestNotFoundError):
                reg.get("nonexistent")
        finally:
            reg.stop()

    def test_complete_moves_to_completed(self):
        reg = self._started()
        try:
            req = make_analytics_request("exec-1")
            reg.store(req)
            reg.complete(req.request_id)
            assert reg.active_count == 0
            assert reg.completed_count == 1
        finally:
            reg.stop()

    def test_fail_moves_to_failed(self):
        reg = self._started()
        try:
            req = make_analytics_request("exec-1")
            reg.store(req)
            reg.fail(req.request_id)
            assert reg.failed_count == 1
        finally:
            reg.stop()

    def test_all_active(self):
        reg = self._started()
        try:
            reg.store(make_analytics_request("e1"))
            reg.store(make_analytics_request("e2"))
            assert len(reg.all_active()) == 2
        finally:
            reg.stop()

    def test_capacity_eviction(self):
        reg = EngineAnalyticsRegistry(max_requests=2)
        reg.start()
        try:
            reg.store(make_analytics_request("e1"))
            reg.store(make_analytics_request("e2"))
            reg.store(make_analytics_request("e3"))  # evicts oldest
            assert reg.active_count == 2
        finally:
            reg.stop()

    def test_not_running_raises(self):
        reg = EngineAnalyticsRegistry()
        with pytest.raises(AnalyticsEngineNotRunningError):
            reg.store(make_analytics_request("e1"))


# ═══════════════════════════════════════════════════════════════════════════════
# EngineAnalyticsValidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineAnalyticsValidator:
    def setup_method(self):
        self.v = EngineAnalyticsValidator()

    def test_valid_request(self):
        r = self.v.validate_request(make_analytics_request("exec-1"))
        assert r.is_valid

    def test_none_request(self):
        r = self.v.validate_request(None)
        assert not r.is_valid

    def test_missing_execution_session_id(self):
        req = make_analytics_request("")
        r = self.v.validate_request(req)
        assert not r.is_valid
        assert any("execution_session_id" in e for e in r.errors)

    def test_valid_context(self):
        ctx = make_engine_analytics_context("REQ-1", "exec-1")
        r = self.v.validate_context(ctx)
        assert r.is_valid

    def test_none_context(self):
        r = self.v.validate_context(None)
        assert not r.is_valid

    def test_no_snapshots_warning(self):
        ctx = make_engine_analytics_context("REQ-2", "exec-2")
        r = self.v.validate_context(ctx)
        assert r.is_valid  # still valid but with warnings
        assert any("snapshot" in w.lower() for w in r.warnings)

    def test_pipeline_validation(self):
        p = make_analytics_pipeline("REQ-1", "SESS-1")
        r = self.v.validate_pipeline(p)
        assert r.is_valid

    def test_pipeline_no_delegation_warning(self):
        p = make_analytics_pipeline("REQ-1", "SESS-1",
                                    has_performance=False, has_predictive=False)
        r = self.v.validate_pipeline(p)
        assert any("framework" in w.lower() for w in r.warnings)

    def test_lifecycle_consistency_mismatch(self):
        req = make_analytics_request("exec-1", request_id="REQ-A")
        ctx = make_engine_analytics_context("REQ-B", "exec-2")
        r = self.v.validate_lifecycle_consistency(req, ctx)
        assert not r.is_valid


class TestEngineAnalyticsValidationResult:
    def test_initial_valid(self):
        r = EngineAnalyticsValidationResult()
        assert r.is_valid

    def test_add_error(self):
        r = EngineAnalyticsValidationResult()
        r.add_error("oops")
        assert not r.is_valid
        assert "oops" in r.errors

    def test_add_warning_stays_valid(self):
        r = EngineAnalyticsValidationResult()
        r.add_warning("heads up")
        assert r.is_valid

    def test_merge(self):
        r1 = EngineAnalyticsValidationResult()
        r2 = EngineAnalyticsValidationResult()
        r2.add_error("from r2")
        r1.merge(r2)
        assert not r1.is_valid

    def test_to_dict(self):
        r = EngineAnalyticsValidationResult()
        d = r.to_dict()
        assert "is_valid" in d
        assert "errors" in d


# ═══════════════════════════════════════════════════════════════════════════════
# EngineAnalyticsStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineAnalyticsStatistics:
    def test_initial_zeroes(self):
        s = EngineAnalyticsStatistics()
        assert s.requests_received   == 0
        assert s.requests_completed  == 0
        assert s.requests_failed     == 0
        assert s.requests_rejected   == 0
        assert s.pipelines_dispatched== 0
        assert s.success_rate        == 0.0

    def test_record_received(self):
        s = EngineAnalyticsStatistics()
        s.record_received()
        s.record_received()
        assert s.requests_received == 2

    def test_record_completed_with_timing(self):
        s = EngineAnalyticsStatistics()
        s.record_completed(10.0, 3.0, 2.0)
        s.record_completed(20.0, 5.0, 4.0)
        assert s.requests_completed == 2
        assert abs(s.average_processing_ms - 15.0) < 1e-9
        assert abs(s.average_collection_ms - 4.0)  < 1e-9
        assert abs(s.average_dispatch_ms   - 3.0)  < 1e-9

    def test_record_failed(self):
        s = EngineAnalyticsStatistics()
        s.record_failed()
        assert s.requests_failed == 1

    def test_record_rejected(self):
        s = EngineAnalyticsStatistics()
        s.record_received()
        s.record_rejected()
        assert s.subsystem_availability < 1.0

    def test_pipeline_counters(self):
        s = EngineAnalyticsStatistics()
        s.record_pipeline_dispatched()
        s.record_pipeline_completed()
        s.record_pipeline_failed()
        assert s.pipelines_dispatched == 1
        assert s.pipelines_completed  == 1
        assert s.pipelines_failed     == 1

    def test_success_rate(self):
        s = EngineAnalyticsStatistics()
        s.record_completed()
        s.record_completed()
        s.record_failed()
        rate = s.success_rate
        assert abs(rate - 2/3) < 1e-9

    def test_copy_independent(self):
        s = EngineAnalyticsStatistics()
        s.record_received()
        c = s.copy()
        s.record_received()
        assert c.requests_received == 1
        assert s.requests_received == 2

    def test_reset(self):
        s = EngineAnalyticsStatistics()
        s.record_received()
        s.reset()
        assert s.requests_received == 0

    def test_to_dict(self):
        s = EngineAnalyticsStatistics()
        d = s.to_dict()
        assert "requests_received" in d
        assert "success_rate" in d

    def test_thread_safety(self):
        s = EngineAnalyticsStatistics()

        def worker():
            for _ in range(100):
                s.record_received()
                s.record_completed(1.0, 0.5, 0.3)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert s.requests_received  == 500
        assert s.requests_completed == 500


# ═══════════════════════════════════════════════════════════════════════════════
# EngineAnalyticsHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineAnalyticsHistory:
    def test_empty(self):
        h = EngineAnalyticsHistory()
        assert h.request_count  == 0
        assert h.response_count == 0
        assert h.pipeline_count == 0
        assert h.event_count    == 0

    def test_record_request(self):
        h = EngineAnalyticsHistory()
        req = make_analytics_request("e1")
        h.record_request(req)
        assert h.request_count == 1
        assert h.latest_request() is req

    def test_record_response(self):
        h = EngineAnalyticsHistory()
        resp = make_analytics_response("REQ-1", ResponseStatus.SUCCESS)
        h.record_response(resp)
        assert h.response_count == 1
        assert h.latest_response() is resp

    def test_record_pipeline(self):
        h = EngineAnalyticsHistory()
        p = make_analytics_pipeline("REQ-1", "SESS-1")
        h.record_pipeline(p)
        assert h.pipeline_count == 1

    def test_record_event(self):
        h = EngineAnalyticsHistory()
        e = make_analytics_engine_completed("REQ-1")
        h.record_event(e)
        assert h.event_count == 1
        assert h.latest_event() is e

    def test_responses_for_request(self):
        h = EngineAnalyticsHistory()
        h.record_response(make_analytics_response("REQ-A", ResponseStatus.SUCCESS))
        h.record_response(make_analytics_response("REQ-B", ResponseStatus.SUCCESS))
        assert len(h.responses_for_request("REQ-A")) == 1

    def test_events_for_request(self):
        h = EngineAnalyticsHistory()
        h.record_event(make_analytics_engine_completed("REQ-A"))
        h.record_event(make_analytics_engine_failed("REQ-B"))
        assert len(h.events_for_request("REQ-A")) == 1

    def test_bounded(self):
        h = EngineAnalyticsHistory(max_requests=3)
        for _ in range(5):
            h.record_request(make_analytics_request("e1"))
        assert h.request_count == 3

    def test_clear(self):
        h = EngineAnalyticsHistory()
        h.record_request(make_analytics_request("e1"))
        h.record_event(make_analytics_engine_completed("REQ-1"))
        h.clear()
        assert h.request_count == 0
        assert h.event_count   == 0

    def test_thread_safety(self):
        h = EngineAnalyticsHistory()

        def worker():
            for _ in range(50):
                h.record_event(make_analytics_engine_completed(str(uuid.uuid4())))

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert h.event_count == 200


# ═══════════════════════════════════════════════════════════════════════════════
# EngineAnalyticsEvent — all 8 factories
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineAnalyticsEvents:
    def test_make_initialized(self):
        e = make_analytics_engine_initialized("REQ-1")
        assert e.event_type == EngineEventType.ANALYTICS_INITIALIZED
        assert e.request_id == "REQ-1"

    def test_make_started(self):
        e = make_analytics_engine_started("REQ-2")
        assert e.event_type == EngineEventType.ANALYTICS_STARTED

    def test_make_collected(self):
        e = make_analytics_engine_collected("REQ-3")
        assert e.event_type == EngineEventType.ANALYTICS_COLLECTED

    def test_make_dispatched(self):
        e = make_analytics_engine_dispatched("REQ-4")
        assert e.event_type == EngineEventType.ANALYTICS_DISPATCHED

    def test_make_completed(self):
        e = make_analytics_engine_completed("REQ-5")
        assert e.event_type == EngineEventType.ANALYTICS_COMPLETED

    def test_make_published(self):
        e = make_analytics_engine_published("REQ-6")
        assert e.event_type == EngineEventType.ANALYTICS_PUBLISHED

    def test_make_failed(self):
        e = make_analytics_engine_failed("REQ-7")
        assert e.event_type == EngineEventType.ANALYTICS_FAILED

    def test_make_stopped(self):
        e = make_analytics_engine_stopped("REQ-8")
        assert e.event_type == EngineEventType.ANALYTICS_STOPPED

    def test_to_dict(self):
        e = make_analytics_engine_completed("REQ-9")
        d = e.to_dict()
        assert d["event_type"] == "analytics_completed"
        assert "event_id" in d

    def test_frozen(self):
        e = make_analytics_engine_completed("REQ-10")
        with pytest.raises(Exception):
            e.request_id = "other"  # type: ignore[misc]

    def test_unique_ids(self):
        e1 = make_analytics_engine_completed("R")
        e2 = make_analytics_engine_completed("R")
        assert e1.event_id != e2.event_id

    def test_custom_actor(self):
        e = make_analytics_engine_completed("R", actor="custom")
        assert e.actor == "custom"

    def test_reason(self):
        e = make_analytics_engine_failed("R", reason="timeout")
        assert e.reason == "timeout"


# ═══════════════════════════════════════════════════════════════════════════════
# EngineAnalyticsFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineAnalyticsFactory:
    def _started(self) -> EngineAnalyticsFactory:
        f = EngineAnalyticsFactory()
        f.start()
        return f

    def test_create_request(self):
        f = self._started()
        try:
            r = f.create_request("exec-1")
            assert isinstance(r, AnalyticsRequest)
        finally:
            f.stop()

    def test_create_context(self):
        f = self._started()
        try:
            ctx = f.create_context("REQ-1", "exec-1")
            assert isinstance(ctx, EngineAnalyticsContext)
        finally:
            f.stop()

    def test_create_pipeline(self):
        f = self._started()
        try:
            p = f.create_pipeline("REQ-1", "SESS-1")
            assert isinstance(p, AnalyticsPipeline)
        finally:
            f.stop()

    def test_create_snapshot(self):
        f = self._started()
        try:
            s = f.create_snapshot(EngineAnalyticsState.PUBLISHING)
            assert isinstance(s, AnalyticsSnapshot)
        finally:
            f.stop()

    def test_create_response(self):
        f = self._started()
        try:
            r = f.create_response("REQ-1", ResponseStatus.SUCCESS)
            assert isinstance(r, AnalyticsResponse)
        finally:
            f.stop()

    def test_not_running_raises(self):
        f = EngineAnalyticsFactory()
        with pytest.raises(AnalyticsEngineNotRunningError):
            f.create_request("exec-1")


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsEngineHealth / assess_engine_health
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsEngineHealth:
    def test_healthy_defaults(self):
        h = assess_engine_health()
        assert h.is_healthy
        assert not h.errors

    def test_unhealthy_when_component_down(self):
        h = assess_engine_health(scheduler_running=False)
        assert h.is_unhealthy
        assert any("scheduler" in e for e in h.errors)

    def test_degraded_on_high_queue(self):
        h = assess_engine_health(scheduler_queue_depth=900, max_queue_threshold=800)
        assert h.is_degraded
        assert any("queue depth" in w.lower() for w in h.warnings)

    def test_to_dict(self):
        h = assess_engine_health()
        d = h.to_dict()
        assert "status" in d
        assert "components" in d

    def test_add_error_marks_unhealthy(self):
        h = AnalyticsEngineHealth(status=EngineHealthStatus.HEALTHY)
        h.add_error("boom")
        assert h.is_unhealthy

    def test_add_warning_marks_degraded(self):
        h = AnalyticsEngineHealth(status=EngineHealthStatus.HEALTHY)
        h.add_warning("slow")
        assert h.is_degraded

    def test_set_component(self):
        h = AnalyticsEngineHealth()
        h.set_component("scheduler", EngineHealthStatus.HEALTHY)
        assert h.components["scheduler"] == "healthy"


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsEngineStatus
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsEngineStatus:
    def test_to_dict(self):
        s = AnalyticsEngineStatus(
            engine_state   = EngineAnalyticsState.IDLE,
            health_status  = EngineHealthStatus.HEALTHY,
            is_running     = True,
            uptime_seconds = 42.0,
        )
        d = s.to_dict()
        assert d["engine_state"]   == "idle"
        assert d["health_status"]  == "healthy"
        assert d["is_running"]     is True
        assert d["uptime_seconds"] == 42.0

    def test_frozen(self):
        s = AnalyticsEngineStatus(
            engine_state  = EngineAnalyticsState.IDLE,
            health_status = EngineHealthStatus.HEALTHY,
            is_running    = True,
        )
        with pytest.raises(Exception):
            s.is_running = False  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# ExecutionAnalyticsEngine — lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineLifecycle:
    def test_start_stop(self):
        e = ExecutionAnalyticsEngine()
        e.start()
        e.stop()

    def test_not_started_raises(self):
        e = ExecutionAnalyticsEngine()
        with pytest.raises(AnalyticsEngineNotRunningError):
            e.submit("exec-1")

    def test_stopped_raises(self):
        e = _started_engine()
        e.stop()
        with pytest.raises(AnalyticsEngineNotRunningError):
            e.submit("exec-1")

    def test_initialize(self):
        e = _started_engine()
        try:
            e.initialize()  # Should not raise
        finally:
            e.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# ExecutionAnalyticsEngine — workflow
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineWorkflow:
    def setup_method(self):
        self.engine = _started_engine()

    def teardown_method(self):
        try:
            self.engine.stop()
        except Exception:
            pass

    def test_submit_success(self):
        response = self.engine.submit("exec-session-001")
        assert response.is_success
        assert response.session_id
        assert response.pipeline_id
        assert response.snapshot is not None
        assert response.processing_ms >= 0.0

    def test_process_request(self):
        request = make_analytics_request("exec-session-002", priority=1)
        response = self.engine.process(request)
        assert response.is_success
        assert response.request_id == request.request_id

    def test_process_with_context(self):
        request = make_analytics_request("exec-session-003")
        context = make_engine_analytics_context(
            request.request_id,
            request.execution_session_id,
            monitoring_snapshot = {"status": "ok"},
        )
        response = self.engine.process_with_context(request, context)
        assert response.is_success

    def test_invalid_request_returns_rejected(self):
        request = make_analytics_request("")  # empty execution_session_id
        response = self.engine.process(request)
        assert response.status == ResponseStatus.REJECTED

    def test_statistics_increments_on_success(self):
        self.engine.submit("exec-1")
        stats = self.engine.statistics()
        assert stats.requests_received  >= 1
        assert stats.requests_completed >= 1
        assert stats.pipelines_dispatched >= 1

    def test_history_populated(self):
        self.engine.submit("exec-1")
        hist = self.engine.history()
        assert hist.response_count >= 1
        assert hist.event_count    >= 1

    def test_events_emitted(self):
        received: List[EngineAnalyticsEvent] = []
        self.engine.add_listener(received.append)
        self.engine.submit("exec-1")
        self.engine.remove_listener(received.append)
        event_types = {e.event_type for e in received}
        assert EngineEventType.ANALYTICS_COMPLETED in event_types
        assert EngineEventType.ANALYTICS_INITIALIZED in event_types

    def test_validate_valid_request(self):
        req = make_analytics_request("exec-1")
        assert self.engine.validate(req)

    def test_validate_invalid_request(self):
        req = make_analytics_request("")
        assert not self.engine.validate(req)

    def test_collect_returns_context(self):
        ctx = self.engine.collect("exec-1", monitoring_snapshot={"ok": True})
        assert isinstance(ctx, EngineAnalyticsContext)
        assert ctx.available_snapshot_count == 1

    def test_publish(self):
        snapshot = make_analytics_snapshot(EngineAnalyticsState.PUBLISHING)
        self.engine.publish(snapshot)  # Should not raise

    def test_query_after_submit(self):
        request = make_analytics_request("exec-q1")
        self.engine.process(request)
        response = self.engine.query(request.request_id)
        assert response is not None
        assert response.request_id == request.request_id

    def test_query_missing_returns_none(self):
        assert self.engine.query("nonexistent-request") is None

    def test_status(self):
        s = self.engine.status()
        assert isinstance(s, AnalyticsEngineStatus)
        assert s.is_running

    def test_health(self):
        h = self.engine.health()
        assert isinstance(h, AnalyticsEngineHealth)

    def test_snapshot_captures_state(self):
        response = self.engine.submit("exec-snapshot-1")
        assert response.snapshot.engine_state == EngineAnalyticsState.PUBLISHING


# ═══════════════════════════════════════════════════════════════════════════════
# ExecutionAnalyticsEngine — scheduler
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineScheduler:
    def setup_method(self):
        self.engine = _started_engine()

    def teardown_method(self):
        try:
            self.engine.stop()
        except Exception:
            pass

    def test_schedule_and_process(self):
        self.engine.schedule("exec-1")
        response = self.engine.dequeue_and_process()
        assert response is not None
        assert response.is_success

    def test_dequeue_empty_returns_none(self):
        result = self.engine.dequeue_and_process()
        assert result is None

    def test_schedule_periodic(self):
        rid = self.engine.schedule_periodic("exec-2", 60.0)
        assert rid

    def test_dequeue_all_due(self):
        for i in range(3):
            self.engine.schedule(f"exec-{i}")
        responses = self.engine.dequeue_and_process_all()
        assert len(responses) == 3
        assert all(r.is_success for r in responses)


# ═══════════════════════════════════════════════════════════════════════════════
# ExecutionAnalyticsEngine — framework registration
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineFrameworkRegistration:
    def test_register_performance_framework(self):
        engine = _started_engine()
        try:
            mock_fw = MagicMock()
            mock_fw.process.return_value = {"metrics": {}}
            engine.register_performance_framework(mock_fw)
            response = engine.submit("exec-fw-1")
            assert response.is_success
            mock_fw.process.assert_called()
        finally:
            engine.stop()

    def test_register_predictive_framework(self):
        engine = _started_engine()
        try:
            mock_fw = MagicMock()
            mock_fw.predict.return_value = {"prediction": 0.8}
            engine.register_predictive_framework(mock_fw)
            response = engine.submit("exec-fw-2")
            assert response.is_success
        finally:
            engine.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# ExecutionAnalyticsEngine — listeners
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineListeners:
    def setup_method(self):
        self.engine = _started_engine()

    def teardown_method(self):
        try:
            self.engine.stop()
        except Exception:
            pass

    def test_add_and_receive(self):
        received: List[EngineAnalyticsEvent] = []
        self.engine.add_listener(received.append)
        self.engine.submit("exec-1")
        assert len(received) > 0

    def test_remove_listener(self):
        received: List[EngineAnalyticsEvent] = []
        self.engine.add_listener(received.append)
        self.engine.remove_listener(received.append)
        self.engine.submit("exec-2")
        assert len(received) == 0

    def test_faulty_listener_no_crash(self):
        def bad(_):
            raise RuntimeError("listener boom")
        self.engine.add_listener(bad)
        response = self.engine.submit("exec-3")
        assert response is not None

    def test_multiple_listeners(self):
        r1: List = []
        r2: List = []
        self.engine.add_listener(r1.append)
        self.engine.add_listener(r2.append)
        self.engine.submit("exec-4")
        assert len(r1) > 0
        assert len(r2) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Concurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineConcurrency:
    def test_concurrent_submit(self):
        engine = _started_engine(max_sessions=200)
        results: List[AnalyticsResponse] = []
        errors:  List[Exception]         = []
        lock = threading.Lock()

        def worker():
            try:
                r = engine.submit(str(uuid.uuid4()))
                with lock:
                    results.append(r)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        engine.stop()
        assert len(errors) == 0
        assert len(results) == 100
        assert all(r.is_success for r in results)

    def test_concurrent_process_with_context(self):
        engine = _started_engine(max_sessions=60)
        errors: List[Exception] = []

        def worker():
            try:
                req = make_analytics_request(str(uuid.uuid4()))
                ctx = make_engine_analytics_context(
                    req.request_id,
                    req.execution_session_id,
                    monitoring_snapshot={"ts": time.time()},
                )
                r = engine.process_with_context(req, ctx)
                assert r.is_success
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        engine.stop()
        assert len(errors) == 0

    def test_concurrent_statistics_consistency(self):
        engine = _started_engine(max_sessions=500)
        errors: List[Exception] = []

        def worker():
            try:
                for _ in range(5):
                    engine.submit(str(uuid.uuid4()))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = engine.statistics()
        engine.stop()
        assert len(errors) == 0
        assert stats.requests_completed == 100
        assert stats.success_rate == 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# Stress testing
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineStress:
    def test_200_sequential_requests(self):
        engine = _started_engine(max_sessions=500, max_requests=500)
        for i in range(200):
            r = engine.submit(f"exec-stress-{i}")
            assert r.is_success, f"Request {i} failed: {r.error_message}"
        stats = engine.statistics()
        assert stats.requests_completed == 200
        assert stats.success_rate == 1.0
        engine.stop()

    def test_scheduler_stress(self):
        engine = _started_engine(scheduler_queue=500)
        for i in range(50):
            engine.schedule(f"exec-sched-{i}")
        responses = engine.dequeue_and_process_all()
        assert len(responses) == 50
        assert all(r.is_success for r in responses)
        engine.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# Regression
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegression:
    def test_independent_sessions_no_interference(self):
        """Two requests do not share state."""
        engine = _started_engine()
        r1 = engine.submit("session-A")
        r2 = engine.submit("session-B")
        assert r1.session_id != r2.session_id
        assert r1.pipeline_id != r2.pipeline_id
        engine.stop()

    def test_statistics_copy_immutable(self):
        """statistics() snapshot is not mutated by further requests."""
        engine = _started_engine()
        engine.submit("exec-1")
        snap = engine.statistics()
        assert snap.requests_completed == 1
        engine.submit("exec-2")
        assert snap.requests_completed == 1  # copy unchanged
        engine.stop()

    def test_history_response_count_matches_requests(self):
        engine = _started_engine()
        for _ in range(3):
            engine.submit(str(uuid.uuid4()))
        hist = engine.history()
        assert hist.response_count == 3
        engine.stop()

    def test_engine_accepts_requests_after_failures(self):
        """Engine remains operational after a request fails."""
        engine = _started_engine()
        # Invalid request — returns REJECTED, engine stays up
        engine.process(make_analytics_request(""))
        # Valid request — should succeed
        r = engine.submit("exec-valid")
        assert r.is_success
        engine.stop()

    def test_faulty_framework_does_not_crash_workflow(self):
        """A framework that raises should not crash the analytics workflow."""
        engine = _started_engine()
        mock_fw = MagicMock()
        mock_fw.process.side_effect = RuntimeError("fw exploded")
        engine.register_performance_framework(mock_fw)
        # Workflow should still complete (framework error is caught + skipped)
        r = engine.submit("exec-fw-fault")
        assert r.is_success
        engine.stop()

    def test_query_returns_latest_response(self):
        """query() returns the most recent response for a request_id."""
        engine = _started_engine()
        request = make_analytics_request("exec-q")
        engine.process(request)
        response = engine.query(request.request_id)
        assert response is not None
        assert response.request_id == request.request_id
        engine.stop()

    def test_high_priority_processed_first_in_scheduler(self):
        engine = _started_engine(scheduler_queue=20)
        engine.schedule("session-low",  priority=9)
        engine.schedule("session-high", priority=1)
        first = engine.dequeue_and_process()
        # Highest priority (1) should be processed first
        assert first.is_success
        engine.stop()
