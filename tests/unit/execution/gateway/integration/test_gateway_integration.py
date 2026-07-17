"""tests/unit/execution/gateway/integration/test_gateway_integration.py
==============================================================
Unit tests for C6 Phase 5 M6 — Execution Gateway Integration.

~200+ tests across 16 test classes.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import List
from unittest.mock import MagicMock

import pytest

from iios.execution.gateway.integration import (
    ACTIVE_REQUEST_STATUSES,
    INTEGRATION_SYSTEM_ID,
    TERMINAL_REQUEST_STATUSES,
    VERSION,
    ComponentHealth,
    ComponentHealthRecord,
    ComponentNotRegisteredError,
    ComponentType,
    ExecutionGatewayIntegrationEngine,
    GatewayComponentFactory,
    GatewayComponentRegistry,
    GatewayIntegrationContext,
    GatewayIntegrationError,
    GatewayIntegrationHealthMonitor,
    GatewayIntegrationHistory,
    GatewayIntegrationRegistry,
    GatewayIntegrationRequest,
    GatewayIntegrationResponse,
    GatewayIntegrationSnapshot,
    GatewayIntegrationStatistics,
    GatewayIntegrationStatus,
    GatewayIntegrationValidationResult,
    GatewayIntegrationValidator,
    IntegrationCapacityError,
    IntegrationEvent,
    IntegrationEventType,
    IntegrationHealthReport,
    IntegrationNotRunningError,
    IntegrationOutcome,
    IntegrationRequestNotFoundError,
    IntegrationRequestStatus,
    IntegrationRequestValidationError,
    IntegrationWorkflowError,
    SubsystemNotInitializedError,
    make_health_updated_event,
    make_integration_context,
    make_integration_request,
    make_request_completed_event,
    make_request_failed_event,
    make_request_received_event,
    make_subsystem_initialized_event,
    make_subsystem_started_event,
    make_subsystem_stopped_event,
)
from iios.execution.gateway.integration.gateway_integration_manager import (
    GatewayIntegrationManager,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ctx(**kwargs) -> GatewayIntegrationContext:
    return make_integration_context(
        kwargs.pop("execution_id",  "exec-test"),
        kwargs.pop("order_id",      "ord-test"),
        kwargs.pop("portfolio_id",  "port-test"),
        kwargs.pop("strategy_id",   "strat-test"),
        symbol=kwargs.pop("symbol",   "RELIANCE"),
        side=kwargs.pop("side",       "BUY"),
        quantity=kwargs.pop("quantity", 50.0),
        price=kwargs.pop("price",       2500.0),
        **kwargs,
    )


def _request(
    engine_id: str = "integ-test",
    **kwargs,
) -> GatewayIntegrationRequest:
    return make_integration_request(_ctx(**kwargs), integration_id=engine_id)


def _started_engine(**kwargs) -> ExecutionGatewayIntegrationEngine:
    e = ExecutionGatewayIntegrationEngine(**kwargs)
    e.initialize()
    e.start()
    return e


# ─────────────────────────────────────────────────────────────────────────────
# TestConstants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version(self):
        assert VERSION == "1.0.0"

    def test_system_id(self):
        assert INTEGRATION_SYSTEM_ID.startswith("iios:execution:gateway")

    def test_terminal_statuses(self):
        assert IntegrationRequestStatus.COMPLETED in TERMINAL_REQUEST_STATUSES
        assert IntegrationRequestStatus.FAILED    in TERMINAL_REQUEST_STATUSES
        assert IntegrationRequestStatus.CANCELLED in TERMINAL_REQUEST_STATUSES

    def test_active_statuses_disjoint_from_terminal(self):
        for s in TERMINAL_REQUEST_STATUSES:
            assert s not in ACTIVE_REQUEST_STATUSES

    def test_component_types(self):
        types = {ct.value for ct in ComponentType}
        assert "LIFECYCLE"      in types
        assert "ENGINE"         in types
        assert "ROUTING_ENGINE" in types
        assert "BROKER_LAYER"   in types
        assert "SNAPSHOT_STORE" in types

    def test_integration_outcomes(self):
        assert IntegrationOutcome.SUCCESS.value        == "SUCCESS"
        assert IntegrationOutcome.ROUTING_FAILED.value == "ROUTING_FAILED"
        assert IntegrationOutcome.VALIDATION_FAILED.value == "VALIDATION_FAILED"

    def test_component_health_values(self):
        assert ComponentHealth.HEALTHY.value  == "HEALTHY"
        assert ComponentHealth.OFFLINE.value  == "OFFLINE"
        assert ComponentHealth.DEGRADED.value == "DEGRADED"

    def test_event_type_values(self):
        assert IntegrationEventType.SUBSYSTEM_STARTED.value  == "SUBSYSTEM_STARTED"
        assert IntegrationEventType.GATEWAY_REQUEST_COMPLETED.value == "GATEWAY_REQUEST_COMPLETED"


# ─────────────────────────────────────────────────────────────────────────────
# TestExceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_error(self):
        e = GatewayIntegrationError("base")
        assert isinstance(e, Exception)
        assert e.error_code == "GI-000"

    def test_not_running_error(self):
        e = IntegrationNotRunningError()
        assert e.error_code == "GI-001"

    def test_validation_error_carries_errors(self):
        e = IntegrationRequestValidationError("bad", errors=("e1", "e2"))
        assert e.error_code == "GI-002"
        assert e.errors == ("e1", "e2")

    def test_not_found_error(self):
        e = IntegrationRequestNotFoundError("req-1")
        assert e.error_code == "GI-003"
        assert "req-1" in str(e)

    def test_component_not_registered_error(self):
        e = ComponentNotRegisteredError("ENGINE")
        assert e.error_code == "GI-004"
        assert "ENGINE" in str(e)

    def test_capacity_error(self):
        e = IntegrationCapacityError(500)
        assert e.error_code == "GI-006"
        assert "500" in str(e)

    def test_workflow_error(self):
        e = IntegrationWorkflowError("validate", "missing field")
        assert e.error_code == "GI-007"
        assert "validate" in str(e)

    def test_subsystem_not_initialized_error(self):
        e = SubsystemNotInitializedError()
        assert e.error_code == "GI-008"

    def test_all_inherit_base(self):
        errors = [
            IntegrationNotRunningError(),
            IntegrationRequestValidationError("x"),
            IntegrationRequestNotFoundError("x"),
            ComponentNotRegisteredError("x"),
            IntegrationCapacityError(1),
            IntegrationWorkflowError("x"),
            SubsystemNotInitializedError(),
        ]
        for err in errors:
            assert isinstance(err, GatewayIntegrationError)


# ─────────────────────────────────────────────────────────────────────────────
# TestContext
# ─────────────────────────────────────────────────────────────────────────────

class TestContext:
    def test_create_minimal(self):
        ctx = _ctx()
        assert ctx.execution_id == "exec-test"
        assert ctx.order_id     == "ord-test"

    def test_is_frozen(self):
        ctx = _ctx()
        with pytest.raises((TypeError, AttributeError)):
            ctx.execution_id = "modified"  # type: ignore

    def test_is_buy(self):
        assert _ctx(side="BUY").is_buy is True
        assert _ctx(side="SELL").is_buy is False

    def test_is_market_order(self):
        ctx = make_integration_context("e", "o", "p", "s", order_type="MARKET")
        assert ctx.is_market_order is True

    def test_has_preferred_broker(self):
        ctx = make_integration_context("e", "o", "p", "s",
                                       preferred_broker_id="broker-1")
        assert ctx.has_preferred_broker is True

    def test_no_preferred_broker(self):
        ctx = _ctx()
        assert ctx.has_preferred_broker is False

    def test_has_risk_snapshot(self):
        ctx = make_integration_context("e", "o", "p", "s",
                                       risk_snapshot={"x": 1})
        assert ctx.has_risk_snapshot is True

    def test_to_dict_keys(self):
        d = _ctx().to_dict()
        for key in ("execution_id", "order_id", "portfolio_id", "strategy_id",
                    "symbol", "side", "quantity", "price", "created_at"):
            assert key in d, f"Missing key: {key}"


# ─────────────────────────────────────────────────────────────────────────────
# TestRequest
# ─────────────────────────────────────────────────────────────────────────────

class TestRequest:
    def test_create(self):
        req = _request()
        uuid.UUID(req.request_id)  # no raise
        assert req.status == IntegrationRequestStatus.PENDING

    def test_is_frozen(self):
        req = _request()
        with pytest.raises((TypeError, AttributeError)):
            req.request_id = "modified"  # type: ignore

    def test_passthrough_properties(self):
        req = _request()
        assert req.execution_id  == req.context.execution_id
        assert req.order_id      == req.context.order_id
        assert req.portfolio_id  == req.context.portfolio_id
        assert req.strategy_id   == req.context.strategy_id

    def test_is_pending(self):
        assert _request().is_pending is True

    def test_is_terminal_false_for_pending(self):
        assert _request().is_terminal is False

    def test_to_dict_keys(self):
        d = _request().to_dict()
        assert "request_id"    in d
        assert "status"        in d
        assert "integration_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestResponse
# ─────────────────────────────────────────────────────────────────────────────

class TestResponse:
    def _make(self, **kwargs) -> GatewayIntegrationResponse:
        defaults = dict(
            response_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            integration_id="integ-1",
            status=IntegrationRequestStatus.COMPLETED,
            outcome=IntegrationOutcome.SUCCESS,
            execution_id="exec-1",
            order_id="ord-1",
            portfolio_id="port-1",
            strategy_id="strat-1",
            gateway_snapshot_id=str(uuid.uuid4()),
            routing_decision_id=str(uuid.uuid4()),
            selected_broker_id="broker-1",
            selected_broker_name="Zerodha",
            failure_reason=None,
            processing_duration_ms=42.0,
        )
        defaults.update(kwargs)
        return GatewayIntegrationResponse(**defaults)

    def test_is_success(self):
        assert self._make(outcome=IntegrationOutcome.SUCCESS).is_success is True
        assert self._make(outcome=IntegrationOutcome.ROUTING_FAILED).is_success is False

    def test_is_failed(self):
        r = self._make(status=IntegrationRequestStatus.FAILED)
        assert r.is_failed is True

    def test_is_routed(self):
        assert self._make(selected_broker_id="b").is_routed is True
        assert self._make(selected_broker_id=None).is_routed is False

    def test_has_snapshot(self):
        assert self._make(gateway_snapshot_id="snap").has_snapshot is True
        assert self._make(gateway_snapshot_id=None).has_snapshot is False

    def test_is_frozen(self):
        r = self._make()
        with pytest.raises((TypeError, AttributeError)):
            r.response_id = "x"  # type: ignore

    def test_to_dict_keys(self):
        d = self._make().to_dict()
        for key in ("response_id", "request_id", "status", "outcome",
                    "execution_id", "is_success", "is_failed"):
            assert key in d


# ─────────────────────────────────────────────────────────────────────────────
# TestIntegrationSnapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationSnapshot:
    def _snap(self, **kwargs) -> GatewayIntegrationSnapshot:
        defaults = dict(
            snapshot_id=str(uuid.uuid4()),
            integration_id="integ-1",
            lifecycle_state="RUNNING",
            engine_state="RUNNING",
            routing_state="RUNNING",
            broker_layer_state="RUNNING",
            snapshot_store_state="RUNNING",
            overall_health=ComponentHealth.HEALTHY,
            component_health={},
            pending_requests=0,
            completed_requests=5,
            failed_requests=1,
            total_requests=6,
        )
        defaults.update(kwargs)
        return GatewayIntegrationSnapshot(**defaults)

    def test_is_frozen(self):
        s = self._snap()
        with pytest.raises((TypeError, AttributeError)):
            s.integration_id = "x"  # type: ignore

    def test_is_healthy(self):
        assert self._snap(overall_health=ComponentHealth.HEALTHY).is_healthy is True
        assert self._snap(overall_health=ComponentHealth.OFFLINE).is_healthy is False

    def test_has_active_requests(self):
        assert self._snap(pending_requests=1).has_active_requests is True
        assert self._snap(pending_requests=0).has_active_requests is False

    def test_success_rate(self):
        s = self._snap(completed_requests=8, failed_requests=2, total_requests=10)
        assert s.success_rate == pytest.approx(0.8)

    def test_success_rate_zero_division(self):
        assert self._snap(completed_requests=0, failed_requests=0,
                          total_requests=0).success_rate == 0.0

    def test_to_dict_keys(self):
        d = self._snap().to_dict()
        for key in ("snapshot_id", "integration_id", "overall_health",
                    "completed_requests", "is_healthy"):
            assert key in d


# ─────────────────────────────────────────────────────────────────────────────
# TestEvents
# ─────────────────────────────────────────────────────────────────────────────

class TestEvents:
    def test_make_initialized_event(self):
        ev = make_subsystem_initialized_event("integ-1")
        assert ev.event_type == IntegrationEventType.SUBSYSTEM_INITIALIZED
        assert ev.integration_id == "integ-1"

    def test_make_started_event(self):
        ev = make_subsystem_started_event("integ-1")
        assert ev.event_type == IntegrationEventType.SUBSYSTEM_STARTED

    def test_make_stopped_event(self):
        ev = make_subsystem_stopped_event("integ-1")
        assert ev.event_type == IntegrationEventType.SUBSYSTEM_STOPPED

    def test_make_received_event(self):
        ev = make_request_received_event("integ-1", "req-1")
        assert ev.event_type == IntegrationEventType.GATEWAY_REQUEST_RECEIVED
        assert ev.request_id == "req-1"

    def test_make_completed_event(self):
        ev = make_request_completed_event("integ-1", "req-1")
        assert ev.event_type == IntegrationEventType.GATEWAY_REQUEST_COMPLETED

    def test_make_failed_event(self):
        ev = make_request_failed_event("integ-1", "req-1")
        assert ev.event_type == IntegrationEventType.GATEWAY_REQUEST_FAILED

    def test_event_is_frozen(self):
        ev = make_subsystem_started_event("integ-1")
        with pytest.raises((TypeError, AttributeError)):
            ev.integration_id = "x"  # type: ignore

    def test_event_has_unique_id(self):
        ev1 = make_request_received_event("integ-1", "req-1")
        ev2 = make_request_received_event("integ-1", "req-1")
        assert ev1.event_id != ev2.event_id

    def test_event_occurred_at_positive(self):
        ev = make_subsystem_started_event("integ-1")
        assert ev.occurred_at > 0


# ─────────────────────────────────────────────────────────────────────────────
# TestStatistics
# ─────────────────────────────────────────────────────────────────────────────

class TestStatistics:
    def test_initial_zeros(self):
        s = GatewayIntegrationStatistics()
        assert s.requests_received   == 0
        assert s.requests_completed  == 0

    def test_record_received(self):
        s = GatewayIntegrationStatistics()
        s.record_received()
        assert s.requests_received == 1

    def test_record_completed(self):
        s = GatewayIntegrationStatistics()
        s.record_completed(100.0)
        assert s.requests_completed == 1
        assert s.total_processing_ms == pytest.approx(100.0)

    def test_record_failed(self):
        s = GatewayIntegrationStatistics()
        s.record_failed()
        assert s.requests_failed == 1

    def test_success_rate(self):
        s = GatewayIntegrationStatistics()
        s.record_completed()
        s.record_completed()
        s.record_failed()
        assert s.success_rate == pytest.approx(2 / 3)

    def test_success_rate_zero_division(self):
        assert GatewayIntegrationStatistics().success_rate == 0.0

    def test_average_processing_ms(self):
        s = GatewayIntegrationStatistics()
        s.record_completed(100.0)
        s.record_completed(200.0)
        assert s.average_processing_ms == pytest.approx(150.0)

    def test_average_routing_ms(self):
        s = GatewayIntegrationStatistics()
        s.record_routed(50.0)
        s.record_routed(150.0)
        assert s.average_routing_ms == pytest.approx(100.0)

    def test_copy_independence(self):
        s = GatewayIntegrationStatistics()
        s.record_received()
        c = s.copy()
        c.record_received()
        assert s.requests_received == 1
        assert c.requests_received == 2

    def test_reset(self):
        s = GatewayIntegrationStatistics()
        s.record_completed()
        s.reset()
        assert s.requests_completed == 0

    def test_to_dict_keys(self):
        d = GatewayIntegrationStatistics().to_dict()
        assert "requests_completed" in d
        assert "success_rate"       in d
        assert "average_processing_ms" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestHistory:
    def test_append_request(self):
        h = GatewayIntegrationHistory(max_requests=10)
        h.append_request(_request())
        assert h.request_count == 1

    def test_latest_request(self):
        h = GatewayIntegrationHistory(max_requests=10)
        r1 = _request()
        r2 = _request()
        h.append_request(r1)
        h.append_request(r2)
        assert h.latest_request() is r2

    def test_bounded_requests(self):
        h = GatewayIntegrationHistory(max_requests=3)
        for _ in range(5):
            h.append_request(_request())
        assert h.request_count == 3

    def test_by_execution_id(self):
        h = GatewayIntegrationHistory(max_requests=10)
        r = _request(execution_id="exec-X")
        h.append_request(r)
        h.append_request(_request(execution_id="exec-Y"))
        result = h.by_execution_id("exec-X")
        assert len(result) == 1

    def test_append_event(self):
        h = GatewayIntegrationHistory(max_events=10)
        ev = make_subsystem_started_event("integ-1")
        h.append_event(ev)
        assert h.event_count == 1

    def test_latest_event(self):
        h = GatewayIntegrationHistory(max_events=10)
        h.append_event(make_subsystem_started_event("integ-1"))
        ev2 = make_subsystem_stopped_event("integ-1")
        h.append_event(ev2)
        assert h.latest_event() is ev2

    def test_clear(self):
        h = GatewayIntegrationHistory(max_requests=10, max_events=10)
        h.append_request(_request())
        h.append_event(make_subsystem_started_event("integ-1"))
        h.clear()
        assert h.request_count == 0
        assert h.event_count   == 0


# ─────────────────────────────────────────────────────────────────────────────
# TestValidation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:
    def test_valid_request_passes(self):
        v = GatewayIntegrationValidator()
        result = v.validate_request(_request())
        assert result.is_valid is True

    def test_empty_execution_id_fails(self):
        v = GatewayIntegrationValidator()
        ctx = make_integration_context("", "ord", "port", "strat")
        req = make_integration_request(ctx, "integ-1")
        result = v.validate_request(req)
        assert result.is_valid is False
        assert any("execution_id" in e for e in result.errors)

    def test_negative_quantity_fails(self):
        v = GatewayIntegrationValidator()
        ctx = make_integration_context("e", "o", "p", "s", quantity=-1.0)
        req = make_integration_request(ctx, "integ-1")
        result = v.validate_request(req)
        assert result.is_valid is False

    def test_zero_quantity_warning(self):
        v = GatewayIntegrationValidator()
        ctx = make_integration_context("e", "o", "p", "s", quantity=0.0)
        req = make_integration_request(ctx, "integ-1")
        result = v.validate_request(req)
        assert result.is_valid is True
        assert result.has_warnings is True

    def test_empty_symbol_warning(self):
        v = GatewayIntegrationValidator()
        ctx = make_integration_context("e", "o", "p", "s", symbol="")
        req = make_integration_request(ctx, "integ-1")
        result = v.validate_context(ctx)
        assert result.has_warnings is True

    def test_validation_result_frozen(self):
        r = GatewayIntegrationValidationResult(is_valid=True, errors=(), warnings=())
        with pytest.raises((TypeError, AttributeError)):
            r.is_valid = False  # type: ignore

    def test_raise_if_invalid_raises(self):
        v = GatewayIntegrationValidator()
        bad = GatewayIntegrationValidationResult(
            is_valid=False, errors=("err",), warnings=()
        )
        with pytest.raises(IntegrationRequestValidationError):
            v.raise_if_invalid(bad)

    def test_raise_if_valid_does_not_raise(self):
        v = GatewayIntegrationValidator()
        ok = GatewayIntegrationValidationResult(
            is_valid=True, errors=(), warnings=()
        )
        v.raise_if_invalid(ok)  # no raise

    def test_to_dict_keys(self):
        r = GatewayIntegrationValidationResult(
            is_valid=True, errors=(), warnings=("w",)
        )
        d = r.to_dict()
        assert "is_valid"  in d
        assert "errors"    in d
        assert "warnings"  in d


# ─────────────────────────────────────────────────────────────────────────────
# TestHealth
# ─────────────────────────────────────────────────────────────────────────────

class TestHealth:
    def _running_registry(self) -> GatewayComponentRegistry:
        reg = GatewayComponentFactory.create_all()
        reg.start_all()
        return reg

    def _stopped_registry(self) -> GatewayComponentRegistry:
        return GatewayComponentFactory.create_all()

    def test_health_all_running(self):
        reg = self._running_registry()
        monitor = GatewayIntegrationHealthMonitor()
        report  = monitor.check(reg)
        assert report.overall_health == ComponentHealth.HEALTHY
        reg.stop_all()

    def test_health_degraded_when_stopped(self):
        reg = self._stopped_registry()
        monitor = GatewayIntegrationHealthMonitor()
        report  = monitor.check(reg)
        # stopped components are DEGRADED, not OFFLINE (they exist)
        assert report.overall_health in (ComponentHealth.DEGRADED, ComponentHealth.OFFLINE)

    def test_health_has_five_components(self):
        reg = self._running_registry()
        monitor = GatewayIntegrationHealthMonitor()
        report  = monitor.check(reg)
        assert len(report.components) == 5
        reg.stop_all()

    def test_health_report_is_frozen(self):
        reg = self._running_registry()
        monitor = GatewayIntegrationHealthMonitor()
        report  = monitor.check(reg)
        with pytest.raises((TypeError, AttributeError)):
            report.overall_health = ComponentHealth.OFFLINE  # type: ignore
        reg.stop_all()

    def test_unhealthy_components_empty_when_all_healthy(self):
        reg = self._running_registry()
        monitor = GatewayIntegrationHealthMonitor()
        report  = monitor.check(reg)
        assert len(report.unhealthy_components) == 0
        reg.stop_all()

    def test_component_health_map(self):
        reg = self._running_registry()
        monitor = GatewayIntegrationHealthMonitor()
        report  = monitor.check(reg)
        m = report.component_health_map
        for ct in ComponentType:
            assert ct.value in m
        reg.stop_all()

    def test_health_report_to_dict(self):
        reg = self._running_registry()
        monitor = GatewayIntegrationHealthMonitor()
        d = monitor.check(reg).to_dict()
        assert "overall_health" in d
        assert "components"     in d
        reg.stop_all()


# ─────────────────────────────────────────────────────────────────────────────
# TestRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_store_and_get_request(self):
        reg = GatewayIntegrationRegistry(max_requests=100)
        req = _request()
        reg.store_request(req)
        assert reg.get_request(req.request_id) is req

    def test_get_unknown_raises(self):
        reg = GatewayIntegrationRegistry()
        with pytest.raises(IntegrationRequestNotFoundError):
            reg.get_request("non-existent")

    def test_capacity_error(self):
        reg = GatewayIntegrationRegistry(max_requests=1)
        reg.store_request(_request())
        with pytest.raises(IntegrationCapacityError):
            reg.store_request(_request())

    def test_store_and_get_response(self):
        reg = GatewayIntegrationRegistry()
        req = _request()
        reg.store_request(req)
        resp = GatewayIntegrationResponse(
            response_id=str(uuid.uuid4()),
            request_id=req.request_id,
            integration_id="integ-1",
            status=IntegrationRequestStatus.COMPLETED,
            outcome=IntegrationOutcome.SUCCESS,
            execution_id="e",
            order_id="o",
            portfolio_id="p",
            strategy_id="s",
            gateway_snapshot_id=None,
            routing_decision_id=None,
            selected_broker_id=None,
            selected_broker_name=None,
            failure_reason=None,
            processing_duration_ms=10.0,
        )
        reg.store_response(resp)
        assert reg.get_response(req.request_id) is resp

    def test_completed_count(self):
        reg = GatewayIntegrationRegistry()
        req = _request()
        reg.store_request(req)
        resp = GatewayIntegrationResponse(
            response_id=str(uuid.uuid4()),
            request_id=req.request_id,
            integration_id="i",
            status=IntegrationRequestStatus.COMPLETED,
            outcome=IntegrationOutcome.SUCCESS,
            execution_id="e", order_id="o", portfolio_id="p", strategy_id="s",
            gateway_snapshot_id=None, routing_decision_id=None,
            selected_broker_id=None, selected_broker_name=None,
            failure_reason=None, processing_duration_ms=1.0,
        )
        reg.store_response(resp)
        assert reg.completed_count == 1

    def test_responses_for_execution(self):
        eng = _started_engine()
        req = make_integration_request(_ctx(execution_id="exec-Q"), eng.integration_id)
        eng.submit(req)
        responses = eng.query("exec-Q")
        assert len(responses) >= 1
        eng.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TestComponentRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestComponentRegistry:
    def test_unregistered_lifecycle_raises(self):
        reg = GatewayComponentRegistry()
        with pytest.raises(ComponentNotRegisteredError):
            _ = reg.lifecycle

    def test_register_and_access_lifecycle(self):
        from iios.execution.gateway.lifecycle import GatewayLifecycle
        reg  = GatewayComponentRegistry()
        lc   = GatewayLifecycle()
        reg.register_lifecycle(lc)
        assert reg.lifecycle is lc

    def test_all_registered_false_when_empty(self):
        assert GatewayComponentRegistry().all_registered is False

    def test_all_registered_true_when_full(self):
        reg = GatewayComponentFactory.create_all()
        assert reg.all_registered is True

    def test_start_all_starts_components(self):
        from iios.investment.workflow.engine_lifecycle import EngineState
        reg = GatewayComponentFactory.create_all()
        reg.start_all()
        assert reg.lifecycle.lifecycle_state()     == EngineState.RUNNING
        assert reg.engine.lifecycle_state()        == EngineState.RUNNING
        assert reg.routing_engine.lifecycle_state() == EngineState.RUNNING
        reg.stop_all()

    def test_stop_all_stops_components(self):
        from iios.investment.workflow.engine_lifecycle import EngineState
        reg = GatewayComponentFactory.create_all()
        reg.start_all()
        reg.stop_all()
        assert reg.lifecycle.lifecycle_state()     == EngineState.STOPPED
        assert reg.engine.lifecycle_state()        == EngineState.STOPPED
        assert reg.routing_engine.lifecycle_state() == EngineState.STOPPED


# ─────────────────────────────────────────────────────────────────────────────
# TestComponentFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestComponentFactory:
    def test_create_lifecycle(self):
        from iios.execution.gateway.lifecycle import GatewayLifecycle
        assert isinstance(GatewayComponentFactory.create_lifecycle(), GatewayLifecycle)

    def test_create_engine(self):
        from iios.execution.gateway.engine import ExecutionGatewayEngine
        assert isinstance(GatewayComponentFactory.create_engine(), ExecutionGatewayEngine)

    def test_create_broker_manager(self):
        from iios.execution.gateway.brokers import BrokerManager
        assert isinstance(GatewayComponentFactory.create_broker_manager(), BrokerManager)

    def test_create_routing_engine(self):
        from iios.execution.gateway.routing import RoutingEngine
        assert isinstance(GatewayComponentFactory.create_routing_engine(), RoutingEngine)

    def test_create_snapshot_store(self):
        from iios.execution.gateway.snapshot import GatewaySnapshotStore
        assert isinstance(GatewayComponentFactory.create_snapshot_store(), GatewaySnapshotStore)

    def test_create_all_returns_registry(self):
        reg = GatewayComponentFactory.create_all()
        assert isinstance(reg, GatewayComponentRegistry)
        assert reg.all_registered

    def test_create_all_components_not_started(self):
        from iios.investment.workflow.engine_lifecycle import EngineState
        reg = GatewayComponentFactory.create_all()
        assert reg.lifecycle.lifecycle_state() != EngineState.RUNNING


# ─────────────────────────────────────────────────────────────────────────────
# TestIntegrationEngine  (subsystem integration tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationEngine:
    def test_initialize_and_start(self):
        e = ExecutionGatewayIntegrationEngine()
        e.initialize()
        e.start()
        assert e.lifecycle_state().value in ("RUNNING", "running")
        e.stop()

    def test_submit_not_running_raises(self):
        e = ExecutionGatewayIntegrationEngine()
        e.initialize()
        with pytest.raises(IntegrationNotRunningError):
            e.submit(_request())

    def test_submit_returns_response(self):
        e = _started_engine()
        resp = e.submit(_request(engine_id=e.integration_id))
        assert isinstance(resp, GatewayIntegrationResponse)
        e.stop()

    def test_submit_completes_with_outcome(self):
        e = _started_engine()
        resp = e.submit(_request(engine_id=e.integration_id))
        assert resp.status == IntegrationRequestStatus.COMPLETED
        assert resp.outcome in (IntegrationOutcome.SUCCESS,
                                IntegrationOutcome.ROUTING_FAILED)
        e.stop()

    def test_submit_publishes_snapshot(self):
        e = _started_engine()
        resp = e.submit(_request(engine_id=e.integration_id))
        assert resp.gateway_snapshot_id is not None
        e.stop()

    def test_validate_without_submit(self):
        e = _started_engine()
        req = _request(engine_id=e.integration_id)
        result = e.validate(req)
        assert result.is_valid is True
        e.stop()

    def test_validate_bad_request(self):
        e = _started_engine()
        ctx = make_integration_context("", "o", "p", "s")
        req = make_integration_request(ctx, e.integration_id)
        result = e.validate(req)
        assert result.is_valid is False
        e.stop()

    def test_health_returns_report(self):
        e = _started_engine()
        report = e.health()
        assert isinstance(report, IntegrationHealthReport)
        assert report.overall_health == ComponentHealth.HEALTHY
        e.stop()

    def test_health_before_initialize(self):
        e = ExecutionGatewayIntegrationEngine()
        report = e.health()
        assert report.overall_health == ComponentHealth.OFFLINE

    def test_status_returns_status(self):
        e = _started_engine()
        s = e.status()
        assert isinstance(s, GatewayIntegrationStatus)
        assert s.is_running is True
        e.stop()

    def test_snapshot_returns_snapshot(self):
        e = _started_engine()
        snap = e.snapshot()
        assert isinstance(snap, GatewayIntegrationSnapshot)
        assert snap.is_healthy is True
        e.stop()

    def test_statistics_after_submit(self):
        e = _started_engine()
        e.submit(_request(engine_id=e.integration_id))
        stats = e.statistics()
        assert stats.requests_received   >= 1
        assert stats.requests_completed  >= 1
        e.stop()

    def test_statistics_is_copy(self):
        e = _started_engine()
        stats1 = e.statistics()
        e.submit(_request(engine_id=e.integration_id))
        stats2 = e.statistics()
        assert stats1.requests_received == 0
        assert stats2.requests_received == 1
        e.stop()

    def test_history_records_request(self):
        e = _started_engine()
        e.submit(_request(engine_id=e.integration_id))
        h = e.history()
        assert h.request_count >= 1
        e.stop()

    def test_query_by_execution_id(self):
        e = _started_engine()
        ctx = _ctx(execution_id="exec-QUERY")
        req = make_integration_request(ctx, e.integration_id)
        e.submit(req)
        responses = e.query("exec-QUERY")
        assert len(responses) == 1
        e.stop()

    def test_event_listener_fires(self):
        e = _started_engine()
        received: List[IntegrationEvent] = []
        e.add_event_listener(received.append)
        e.submit(_request(engine_id=e.integration_id))
        assert any(
            ev.event_type == IntegrationEventType.GATEWAY_REQUEST_COMPLETED
            for ev in received
        )
        e.stop()

    def test_remove_event_listener(self):
        e = _started_engine()
        received: List[IntegrationEvent] = []
        e.add_event_listener(received.append)
        e.remove_event_listener(received.append)
        e.submit(_request(engine_id=e.integration_id))
        assert len(received) == 0
        e.stop()

    def test_stop_and_restart(self):
        e = ExecutionGatewayIntegrationEngine()
        e.initialize()
        e.start()
        e.stop()
        e.start()
        resp = e.submit(_request(engine_id=e.integration_id))
        assert resp.status == IntegrationRequestStatus.COMPLETED
        e.stop()

    def test_integration_id_is_uuid(self):
        e = ExecutionGatewayIntegrationEngine()
        uuid.UUID(e.integration_id)

    def test_register_component_after_initialize(self):
        from iios.execution.gateway.lifecycle import GatewayLifecycle
        e = ExecutionGatewayIntegrationEngine()
        e.initialize()
        lc = GatewayLifecycle()
        e.register_lifecycle(lc)
        assert e._components.lifecycle is lc

    def test_register_before_initialize_raises(self):
        from iios.execution.gateway.lifecycle import GatewayLifecycle
        e = ExecutionGatewayIntegrationEngine()
        with pytest.raises(SubsystemNotInitializedError):
            e.register_lifecycle(GatewayLifecycle())

    def test_snapshot_includes_component_states(self):
        e = _started_engine()
        snap = e.snapshot()
        running = ("RUNNING", "running")
        assert snap.lifecycle_state     in running
        assert snap.engine_state        in running
        assert snap.routing_state       in running
        assert snap.broker_layer_state  in running
        assert snap.snapshot_store_state in running
        e.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TestWorkflow  (end-to-end orchestration)
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflow:
    def test_full_cycle(self):
        e = _started_engine()
        ctx  = _ctx(symbol="NIFTY50", side="BUY", quantity=100, price=22000.0)
        req  = make_integration_request(ctx, e.integration_id)
        resp = e.submit(req)

        assert resp.request_id  == req.request_id
        assert resp.execution_id == ctx.execution_id
        assert resp.order_id     == ctx.order_id
        assert resp.portfolio_id == ctx.portfolio_id
        assert resp.strategy_id  == ctx.strategy_id
        assert resp.processing_duration_ms >= 0
        e.stop()

    def test_multiple_requests_same_execution(self):
        e = _started_engine()
        for i in range(3):
            ctx  = _ctx(execution_id="exec-MULTI", order_id=f"ord-{i}")
            req  = make_integration_request(ctx, e.integration_id)
            resp = e.submit(req)
            assert resp.status == IntegrationRequestStatus.COMPLETED

        responses = e.query("exec-MULTI")
        assert len(responses) == 3
        e.stop()

    def test_invalid_request_returns_failed_response(self):
        e = _started_engine()
        ctx = make_integration_context("", "o", "p", "s")  # empty execution_id
        req = make_integration_request(ctx, e.integration_id)
        resp = e.submit(req)
        assert resp.status  == IntegrationRequestStatus.FAILED
        assert resp.outcome == IntegrationOutcome.VALIDATION_FAILED
        assert resp.failure_reason is not None
        e.stop()

    def test_failed_response_has_no_snapshot(self):
        e = _started_engine()
        ctx  = make_integration_context("", "o", "p", "s")
        req  = make_integration_request(ctx, e.integration_id)
        resp = e.submit(req)
        assert resp.gateway_snapshot_id is None
        e.stop()

    def test_response_stored_in_history(self):
        e = _started_engine()
        req  = _request(engine_id=e.integration_id)
        e.submit(req)
        h = e.history()
        assert h.response_count >= 1
        e.stop()

    def test_events_emitted_in_order(self):
        e = _started_engine()
        received: List[IntegrationEvent] = []
        e.add_event_listener(received.append)
        e.submit(_request(engine_id=e.integration_id))

        event_types = [ev.event_type for ev in received]
        assert IntegrationEventType.GATEWAY_REQUEST_RECEIVED  in event_types
        assert IntegrationEventType.GATEWAY_REQUEST_VALIDATED in event_types
        assert IntegrationEventType.GATEWAY_REQUEST_COMPLETED in event_types
        e.stop()

    def test_statistics_track_failed_requests(self):
        e = _started_engine()
        ctx  = make_integration_context("", "o", "p", "s")
        req  = make_integration_request(ctx, e.integration_id)
        e.submit(req)
        stats = e.statistics()
        assert stats.requests_failed >= 1
        e.stop()

    def test_status_tracks_completed(self):
        e = _started_engine()
        req = _request(engine_id=e.integration_id)
        e.submit(req)
        s = e.status()
        assert s.completed_requests >= 1
        e.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TestConcurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_submits(self):
        e = _started_engine(max_requests=200)
        errors: List[Exception] = []

        def worker():
            try:
                for _ in range(5):
                    resp = e.submit(_request(engine_id=e.integration_id))
                    assert resp.status in (
                        IntegrationRequestStatus.COMPLETED,
                        IntegrationRequestStatus.FAILED,
                    )
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert not errors, f"Concurrent submits raised: {errors[:3]}"
        e.stop()

    def test_concurrent_health_checks(self):
        e = _started_engine()
        errors: List[Exception] = []

        def checker():
            try:
                for _ in range(10):
                    report = e.health()
                    assert report.overall_health is not None
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=checker) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        e.stop()

    def test_concurrent_statistics_reads(self):
        e = _started_engine()
        errors: List[Exception] = []

        def reader():
            try:
                for _ in range(20):
                    s = e.statistics()
                    assert s.requests_received >= 0
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        e.stop()

    def test_history_concurrent_appends(self):
        h = GatewayIntegrationHistory(max_requests=200)
        errors: List[Exception] = []

        def appender():
            try:
                for _ in range(20):
                    h.append_request(_request())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=appender) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors


# ─────────────────────────────────────────────────────────────────────────────
# TestRegressionEdgeCases
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressionEdgeCases:
    def test_submit_with_optional_ids(self):
        e = _started_engine()
        ctx = make_integration_context(
            "exec-1", "ord-1", "port-1", "strat-1",
            position_id="pos-1",
            workflow_id="wf-1",
            decision_id="dec-1",
        )
        req  = make_integration_request(ctx, e.integration_id)
        resp = e.submit(req)
        assert resp.status == IntegrationRequestStatus.COMPLETED
        e.stop()

    def test_submit_with_upstream_snapshots(self):
        e = _started_engine()
        ctx = make_integration_context(
            "exec-1", "ord-1", "port-1", "strat-1",
            risk_snapshot={"max_dd": 0.05},
            position_snapshot={"net": 100},
        )
        req  = make_integration_request(ctx, e.integration_id)
        resp = e.submit(req)
        assert resp.status == IntegrationRequestStatus.COMPLETED
        e.stop()

    def test_auto_initialize_on_start(self):
        e = ExecutionGatewayIntegrationEngine()
        # do NOT call initialize()
        e.start()
        resp = e.submit(_request(engine_id=e.integration_id))
        assert resp.status == IntegrationRequestStatus.COMPLETED
        e.stop()

    def test_custom_component_registry(self):
        reg = GatewayComponentFactory.create_all()
        e   = ExecutionGatewayIntegrationEngine()
        e.initialize(components=reg)
        e.start()
        resp = e.submit(_request(engine_id=e.integration_id))
        assert resp.status == IntegrationRequestStatus.COMPLETED
        e.stop()

    def test_history_bounded(self):
        h = GatewayIntegrationHistory(max_requests=3)
        for _ in range(5):
            h.append_request(_request())
        assert h.request_count == 3

    def test_registry_pending_count(self):
        reg = GatewayIntegrationRegistry(max_requests=100)
        req = _request()
        reg.store_request(req)
        # status is PENDING (terminal=False)
        assert reg.pending_count == 1

    def test_status_uninitialized_not_running(self):
        e = ExecutionGatewayIntegrationEngine()
        s = e.status()
        assert s.is_running       is False
        assert s.is_initialized   is False

    def test_multiple_submit_same_request_id_recorded_once(self):
        """The registry records only the latest response per request_id."""
        reg = GatewayIntegrationRegistry(max_requests=100)
        req = _request()
        reg.store_request(req)
        resp1 = GatewayIntegrationResponse(
            response_id=str(uuid.uuid4()),
            request_id=req.request_id,
            integration_id="i",
            status=IntegrationRequestStatus.COMPLETED,
            outcome=IntegrationOutcome.SUCCESS,
            execution_id="e", order_id="o", portfolio_id="p", strategy_id="s",
            gateway_snapshot_id=None, routing_decision_id=None,
            selected_broker_id=None, selected_broker_name=None,
            failure_reason=None, processing_duration_ms=1.0,
        )
        resp2 = GatewayIntegrationResponse(
            response_id=str(uuid.uuid4()),
            request_id=req.request_id,   # same request_id
            integration_id="i",
            status=IntegrationRequestStatus.COMPLETED,
            outcome=IntegrationOutcome.SUCCESS,
            execution_id="e", order_id="o", portfolio_id="p", strategy_id="s",
            gateway_snapshot_id=None, routing_decision_id=None,
            selected_broker_id=None, selected_broker_name=None,
            failure_reason=None, processing_duration_ms=2.0,
        )
        reg.store_response(resp1)
        reg.store_response(resp2)
        # second overrides first
        assert reg.get_response(req.request_id).processing_duration_ms == pytest.approx(2.0)
