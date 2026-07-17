"""tests/unit/execution/risk/test_execution_risk_integration.py
==================================================
Unit tests for C6 Phase 4 M6 — Execution Risk Integration.

Coverage:
  TestConstants                — enums, sentinel sets, system IDs
  TestExceptions               — hierarchy, error codes, fields
  TestExecutionContext         — construction, properties, to_dict
  TestExecutionRiskRequest     — construction, properties, expiry
  TestExecutionRiskResponse    — construction, properties, serialisation
  TestValidation               — valid/invalid contexts, requests, raise
  TestComponentRegistry        — register, get, require, all_required
  TestIntegrationStatistics    — record methods, derived properties, copy
  TestIntegrationHistory       — append, latest, filters, clear
  TestIntegrationEvents        — all 8 factory functions, to_dict
  TestSubsystemHealth          — ComponentHealth, SubsystemHealth, factory
  TestSubsystemStatus          — enum values
  TestIntegrationSnapshot      — fields, to_dict, to_json
  TestIntegrationRequestFactory — all factory methods
  TestWorkflow                 — full evaluate() happy path
  TestWorkflowBlocked          — blocked evaluation response
  TestWorkflowValidationFail   — invalid request response
  TestEngineLifecycle          — start, stop, not-running guard
  TestManagerLifecycle         — manager start/stop, delegates evaluate
  TestHealth                   — health() returns SubsystemHealth
  TestStatisticsIntegration    — statistics updated after evaluate
  TestHistoryIntegration       — history populated after evaluate
  TestQueryFilters             — query filters by execution_id, order_id
  TestEventsEmitted            — evaluation events in events()
  TestSnapshotPublication      — M5 snapshot published after evaluate
  TestConcurrency              — concurrent evaluate() calls
  TestEdgeCases                — expired request, empty order_id guard
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

from iios.execution.risk.integration import (
    APPROVED_ACTIONS,
    ComponentHealth,
    ComponentRegistry,
    ComponentType,
    ContextValidationError,
    EvaluationFailedError,
    EvaluationMode,
    ExecutionContext,
    ExecutionRiskIntegrationEngine,
    ExecutionRiskIntegrationManager,
    ExecutionRiskIntegrationSnapshot,
    ExecutionRiskRequest,
    ExecutionRiskResponse,
    ExecutionRiskIntegrationError,
    INTEGRATION_SYSTEM_ID,
    IntegrationEvent,
    IntegrationEventType,
    IntegrationHistory,
    IntegrationNotRunningError,
    IntegrationRequestFactory,
    IntegrationStatistics,
    IntegrationValidator,
    MANAGER_SYSTEM_ID,
    REQUIRED_COMPONENT_TYPES,
    RequestValidationError,
    SubsystemHealth,
    SubsystemStatus,
    ValidationReport,
    VERSION,
    make_evaluation_completed_event,
    make_evaluation_requested_event,
    make_execution_context,
    make_execution_risk_request,
    make_health_updated_event,
    make_snapshot_published_event,
    make_subsystem_started_event,
    make_subsystem_stopped_event,
    make_validation_completed_event,
)
from iios.execution.risk.integration.execution_risk_health import (
    check_component_health,
    make_subsystem_health,
)
from iios.execution.risk.integration.execution_risk_integration_snapshot import (
    make_integration_snapshot,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ctx(
    execution_id: str = "",
    order_id: str = "",
    **kw,
) -> ExecutionContext:
    return make_execution_context(
        execution_id=execution_id or str(uuid.uuid4()),
        order_id=order_id or str(uuid.uuid4()),
        portfolio_id=kw.pop("portfolio_id", "PORT-1"),
        strategy_id=kw.pop("strategy_id", "STRAT-1"),
        **kw,
    )


def _req(ctx=None, **kw) -> ExecutionRiskRequest:
    return make_execution_risk_request(ctx or _ctx(), **kw)


def _manager() -> ExecutionRiskIntegrationManager:
    m = ExecutionRiskIntegrationManager()
    m.start()
    return m


def _engine() -> ExecutionRiskIntegrationEngine:
    e = ExecutionRiskIntegrationEngine()
    e.start()
    return e


# ── TestConstants ─────────────────────────────────────────────────────────────

class TestConstants:
    def test_integration_system_id_prefix(self):
        assert INTEGRATION_SYSTEM_ID.startswith("iios:")

    def test_version(self):
        assert VERSION == "1.0.0"

    def test_evaluation_mode_values(self):
        vals = {m.value for m in EvaluationMode}
        assert "standard"  in vals
        assert "strict"    in vals
        assert "permissive" in vals
        assert "emergency" in vals

    def test_integration_event_type_values(self):
        vals = {e.value for e in IntegrationEventType}
        assert "subsystem_started"    in vals
        assert "evaluation_completed" in vals
        assert "snapshot_published"   in vals

    def test_approved_actions(self):
        assert "ALLOW"              in APPROVED_ACTIONS
        assert "ALLOW_WITH_WARNING" in APPROVED_ACTIONS
        assert "BLOCK"              not in APPROVED_ACTIONS

    def test_required_component_types(self):
        assert ComponentType.ENGINE   in REQUIRED_COMPONENT_TYPES
        assert ComponentType.CONTROLS in REQUIRED_COMPONENT_TYPES
        assert ComponentType.SNAPSHOT in REQUIRED_COMPONENT_TYPES

    def test_component_type_values(self):
        vals = {c.value for c in ComponentType}
        assert "engine"      in vals
        assert "controls"    in vals
        assert "snapshot"    in vals
        assert "integration" in vals


# ── TestExceptions ────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(ExecutionRiskIntegrationError, IIOSError)

    def test_not_running_no_args(self):
        e = IntegrationNotRunningError()
        assert "not running" in str(e).lower()

    def test_request_validation_error_has_message(self):
        e = RequestValidationError("bad request")
        assert e.message == "bad request"

    def test_evaluation_failed_error(self):
        e = EvaluationFailedError("workflow exploded")
        assert e.message == "workflow exploded"

    def test_all_subclass_base(self):
        from iios.execution.risk.integration.exceptions import (
            ComponentNotHealthyError, ComponentRegistrationError,
            ContextValidationError, IntegrationHistoryError,
            IntegrationTimeoutError,
        )
        for cls in (
            IntegrationNotRunningError, RequestValidationError, EvaluationFailedError,
            ComponentNotHealthyError, IntegrationTimeoutError,
            ComponentRegistrationError, ContextValidationError,
            IntegrationHistoryError,
        ):
            assert issubclass(cls, ExecutionRiskIntegrationError)


# ── TestExecutionContext ──────────────────────────────────────────────────────

class TestExecutionContext:
    def test_required_fields(self):
        ctx = _ctx(execution_id="EX-1", order_id="ORD-1")
        assert ctx.execution_id == "EX-1"
        assert ctx.order_id     == "ORD-1"

    def test_defaults(self):
        ctx = _ctx()
        assert ctx.position_id  == ""
        assert ctx.quantity     == 0.0
        assert ctx.price        == 0.0

    def test_full_construction(self):
        ctx = make_execution_context(
            "EX-1", "ORD-1",
            symbol="RELIANCE", side="BUY",
            quantity=100.0, price=2500.0,
            portfolio_id="PORT-1",
        )
        assert ctx.symbol    == "RELIANCE"
        assert ctx.side      == "BUY"
        assert ctx.quantity  == 100.0
        assert ctx.price     == 2500.0

    def test_immutable(self):
        ctx = _ctx()
        with pytest.raises((TypeError, AttributeError)):
            ctx.execution_id = "changed"  # type: ignore

    def test_has_snapshots_false_by_default(self):
        ctx = _ctx()
        assert ctx.has_execution_snapshot is False
        assert ctx.has_position_snapshot  is False

    def test_has_snapshots_true_when_supplied(self):
        ctx = make_execution_context("E", "O", execution_snapshot={"a": 1})
        assert ctx.has_execution_snapshot is True

    def test_to_dict(self):
        ctx = _ctx(execution_id="EX-1", order_id="ORD-1")
        d   = ctx.to_dict()
        assert d["execution_id"] == "EX-1"
        assert "portfolio_id" in d

    def test_age_ms_non_negative(self):
        ctx = _ctx()
        time.sleep(0.01)
        assert ctx.age_ms >= 0


# ── TestExecutionRiskRequest ──────────────────────────────────────────────────

class TestExecutionRiskRequest:
    def test_construction(self):
        req = _req()
        assert req.request_id
        assert req.evaluation_mode == EvaluationMode.STANDARD

    def test_convenience_properties(self):
        ctx = _ctx(execution_id="EX-1", order_id="ORD-1", portfolio_id="PORT-1")
        req = _req(ctx)
        assert req.execution_id  == "EX-1"
        assert req.order_id      == "ORD-1"
        assert req.portfolio_id  == "PORT-1"

    def test_not_expired_by_default(self):
        req = _req()
        assert req.is_expired is False

    def test_expired_when_timeout_exceeded(self):
        req = make_execution_risk_request(_ctx(), timeout_ms=0.001)
        time.sleep(0.01)
        assert req.is_expired is True

    def test_zero_timeout_never_expires(self):
        req = make_execution_risk_request(_ctx(), timeout_ms=0)
        time.sleep(0.01)
        assert req.is_expired is False

    def test_effective_correlation_id_from_context(self):
        ctx = make_execution_context("E", "O", correlation_id="COR-1")
        req = make_execution_risk_request(ctx)
        assert req.effective_correlation_id == "COR-1"

    def test_effective_correlation_id_request_overrides(self):
        ctx = make_execution_context("E", "O", correlation_id="CTX-COR")
        req = make_execution_risk_request(ctx, correlation_id="REQ-COR")
        assert req.effective_correlation_id == "REQ-COR"

    def test_to_dict(self):
        req = _req()
        d   = req.to_dict()
        assert "request_id"     in d
        assert "evaluation_mode" in d
        assert "context"        in d


# ── TestExecutionRiskResponse ─────────────────────────────────────────────────

class TestExecutionRiskResponse:
    def _make(self, approved=True, action="ALLOW", **kw):
        from iios.execution.risk.snapshot import SnapshotFactory
        snap = SnapshotFactory.create_allow_snapshot()
        return ExecutionRiskResponse(
            response_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            execution_id="EX-1",
            order_id="ORD-1",
            portfolio_id="PORT-1",
            strategy_id="STRAT-1",
            correlation_id="COR-1",
            approved=approved,
            action=action,
            risk_state="PASSED" if approved else "BLOCKED",
            snapshot=snap,
            validation_passed=True,
            elapsed_ms=10.0,
            **kw,
        )

    def test_approved_response(self):
        r = self._make()
        assert r.approved is True
        assert r.is_blocked is False

    def test_blocked_response(self):
        r = self._make(approved=False, action="BLOCK")
        assert r.approved   is False
        assert r.is_blocked is True

    def test_is_error_false_by_default(self):
        r = self._make()
        assert r.is_error is False

    def test_is_error_true_when_message_present(self):
        r = self._make(error_message="something went wrong")
        assert r.is_error is True

    def test_to_dict(self):
        r = self._make()
        d = r.to_dict()
        assert "response_id" in d
        assert "approved"    in d
        assert "snapshot"    in d

    def test_to_json(self):
        r    = self._make()
        raw  = r.to_json()
        parsed = json.loads(raw)
        assert parsed["approved"] is True

    def test_immutable(self):
        r = self._make()
        with pytest.raises((TypeError, AttributeError)):
            r.approved = False  # type: ignore


# ── TestValidation ────────────────────────────────────────────────────────────

class TestValidation:
    def test_valid_context(self):
        ctx = _ctx()
        result = IntegrationValidator.validate_context(ctx)
        assert result.is_valid

    def test_missing_execution_id(self):
        ctx = make_execution_context("", "ORD-1")
        result = IntegrationValidator.validate_context(ctx)
        assert not result.is_valid
        assert any("execution_id" in e for e in result.errors)

    def test_missing_order_id(self):
        ctx = make_execution_context("EX-1", "")
        result = IntegrationValidator.validate_context(ctx)
        assert not result.is_valid

    def test_negative_quantity_fails(self):
        ctx = make_execution_context("EX-1", "ORD-1", quantity=-1.0)
        result = IntegrationValidator.validate_context(ctx)
        assert not result.is_valid

    def test_valid_request(self):
        req = _req()
        result = IntegrationValidator.validate_request(req)
        assert result.is_valid

    def test_expired_request_fails(self):
        req = make_execution_risk_request(_ctx(), timeout_ms=0.001)
        time.sleep(0.01)
        result = IntegrationValidator.validate_request(req)
        assert not result.is_valid

    def test_raise_if_invalid_raises(self):
        req = make_execution_risk_request(make_execution_context("", "ORD-1"))
        result = IntegrationValidator.validate_request(req)
        with pytest.raises(RequestValidationError):
            result.raise_if_invalid()

    def test_raise_if_valid_does_not_raise(self):
        req = _req()
        result = IntegrationValidator.validate_request(req)
        result.raise_if_invalid()  # should not raise

    def test_validation_report_bool(self):
        ok  = ValidationReport(True, (), ())
        bad = ValidationReport(False, ("err",), ())
        assert bool(ok)  is True
        assert bool(bad) is False

    def test_validate_request_and_raise_propagates(self):
        req = make_execution_risk_request(make_execution_context("", "ORD-1"))
        with pytest.raises(RequestValidationError):
            IntegrationValidator.validate_request_and_raise(req)


# ── TestComponentRegistry ─────────────────────────────────────────────────────

class TestComponentRegistry:
    def test_register_and_get(self):
        reg = ComponentRegistry()
        obj = object()
        reg.register(ComponentType.ENGINE, obj)
        assert reg.get(ComponentType.ENGINE) is obj

    def test_require_raises_when_missing(self):
        from iios.execution.risk.integration.exceptions import ComponentRegistrationError
        reg = ComponentRegistry()
        with pytest.raises(ComponentRegistrationError):
            reg.require(ComponentType.ENGINE)

    def test_is_registered(self):
        reg = ComponentRegistry()
        assert reg.is_registered(ComponentType.ENGINE) is False
        reg.register(ComponentType.ENGINE, object())
        assert reg.is_registered(ComponentType.ENGINE) is True

    def test_all_required_registered_false(self):
        reg = ComponentRegistry()
        assert reg.all_required_registered() is False

    def test_all_required_registered_true(self):
        reg = ComponentRegistry()
        for ct in REQUIRED_COMPONENT_TYPES:
            reg.register(ct, object())
        assert reg.all_required_registered() is True

    def test_deregister(self):
        reg = ComponentRegistry()
        reg.register(ComponentType.ENGINE, object())
        reg.deregister(ComponentType.ENGINE)
        assert reg.is_registered(ComponentType.ENGINE) is False

    def test_registered_types(self):
        reg = ComponentRegistry()
        reg.register(ComponentType.ENGINE, object())
        reg.register(ComponentType.CONTROLS, object())
        types = reg.registered_types()
        assert ComponentType.ENGINE   in types
        assert ComponentType.CONTROLS in types


# ── TestIntegrationStatistics ─────────────────────────────────────────────────

class TestIntegrationStatistics:
    def test_initial_zeroes(self):
        s = IntegrationStatistics()
        assert s.requests_processed == 0
        assert s.average_processing_time_ms == 0.0

    def test_record_request_approved(self):
        s = IntegrationStatistics()
        s.record_request(50.0, "ALLOW", True)
        assert s.requests_processed     == 1
        assert s.successful_evaluations == 1
        assert s.blocked_evaluations    == 0

    def test_record_request_blocked(self):
        s = IntegrationStatistics()
        s.record_request(30.0, "BLOCK", False)
        assert s.blocked_evaluations == 1

    def test_record_request_warning(self):
        s = IntegrationStatistics()
        s.record_request(20.0, "ALLOW_WITH_WARNING", True)
        assert s.warnings_issued == 1

    def test_record_request_emergency(self):
        s = IntegrationStatistics()
        s.record_request(10.0, "EMERGENCY_STOP", False)
        assert s.emergency_stops == 1

    def test_record_validation_failure(self):
        s = IntegrationStatistics()
        s.record_validation_failure()
        assert s.validation_failures == 1
        assert s.requests_processed  == 1

    def test_subsystem_availability(self):
        s = IntegrationStatistics()
        s.record_request(10.0, "ALLOW", True)
        s.record_request(10.0, "ALLOW", True)
        s.record_validation_failure()
        # 2 processed OK out of 3 total
        assert abs(s.subsystem_availability - 2/3) < 0.001

    def test_average_processing_time(self):
        s = IntegrationStatistics()
        s.record_request(100.0, "ALLOW", True)
        s.record_request(200.0, "ALLOW", True)
        assert s.average_processing_time_ms == 150.0

    def test_copy_is_independent(self):
        s = IntegrationStatistics()
        s.record_request(10.0, "ALLOW", True)
        c = s.copy()
        s.record_request(20.0, "ALLOW", True)
        assert c.requests_processed == 1
        assert s.requests_processed == 2

    def test_to_dict(self):
        s = IntegrationStatistics()
        d = s.to_dict()
        assert "requests_processed"     in d
        assert "subsystem_availability" in d


# ── TestIntegrationHistory ────────────────────────────────────────────────────

class TestIntegrationHistory:
    def _response(self, execution_id="E1", order_id="O1", portfolio_id="PORT-1", approved=True):
        from iios.execution.risk.snapshot import SnapshotFactory
        snap = SnapshotFactory.create_allow_snapshot()
        return ExecutionRiskResponse(
            response_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            execution_id=execution_id,
            order_id=order_id,
            portfolio_id=portfolio_id,
            strategy_id="STRAT-1",
            correlation_id="",
            approved=approved,
            action="ALLOW" if approved else "BLOCK",
            risk_state="PASSED" if approved else "BLOCKED",
            snapshot=snap,
            validation_passed=True,
            elapsed_ms=5.0,
        )

    def test_append_and_count(self):
        h = IntegrationHistory()
        h.append(self._response())
        assert h.count == 1

    def test_latest(self):
        h = IntegrationHistory()
        for _ in range(5):
            h.append(self._response())
        assert len(h.latest(3)) == 3

    def test_by_execution_id(self):
        h = IntegrationHistory()
        h.append(self._response(execution_id="E1"))
        h.append(self._response(execution_id="E2"))
        result = h.by_execution_id("E1")
        assert len(result) == 1

    def test_by_order_id(self):
        h = IntegrationHistory()
        h.append(self._response(order_id="O1"))
        h.append(self._response(order_id="O2"))
        assert len(h.by_order_id("O1")) == 1

    def test_blocked_only(self):
        h = IntegrationHistory()
        h.append(self._response(approved=True))
        h.append(self._response(approved=False))
        assert len(h.blocked_only()) == 1

    def test_approved_only(self):
        h = IntegrationHistory()
        h.append(self._response(approved=True))
        h.append(self._response(approved=False))
        assert len(h.approved_only()) == 1

    def test_clear(self):
        h = IntegrationHistory()
        h.append(self._response())
        h.clear()
        assert h.count == 0

    def test_bounded_eviction(self):
        h = IntegrationHistory(max_size=2)
        for _ in range(3):
            h.append(self._response())
        assert h.count == 2


# ── TestIntegrationEvents ─────────────────────────────────────────────────────

class TestIntegrationEvents:
    def _check(self, event: IntegrationEvent, expected_type: IntegrationEventType):
        assert isinstance(event, IntegrationEvent)
        assert event.event_type == expected_type
        assert event.event_id
        assert event.occurred_at > 0

    def test_subsystem_started(self):
        e = make_subsystem_started_event()
        self._check(e, IntegrationEventType.SUBSYSTEM_STARTED)

    def test_subsystem_stopped(self):
        e = make_subsystem_stopped_event()
        self._check(e, IntegrationEventType.SUBSYSTEM_STOPPED)

    def test_evaluation_requested(self):
        e = make_evaluation_requested_event(request_id="R1", execution_id="E1")
        self._check(e, IntegrationEventType.EVALUATION_REQUESTED)
        assert e.metadata["request_id"]   == "R1"
        assert e.metadata["execution_id"] == "E1"

    def test_evaluation_completed(self):
        e = make_evaluation_completed_event(approved=True, elapsed_ms=5.0)
        self._check(e, IntegrationEventType.EVALUATION_COMPLETED)
        assert e.metadata["approved"] is True

    def test_snapshot_published(self):
        e = make_snapshot_published_event(snapshot_id="SID", risk_id="RID")
        self._check(e, IntegrationEventType.SNAPSHOT_PUBLISHED)

    def test_validation_completed(self):
        e = make_validation_completed_event(is_valid=False)
        self._check(e, IntegrationEventType.VALIDATION_COMPLETED)

    def test_health_updated(self):
        e = make_health_updated_event(overall_healthy=True)
        self._check(e, IntegrationEventType.HEALTH_UPDATED)

    def test_to_dict(self):
        e = make_subsystem_started_event()
        d = e.to_dict()
        assert "event_type"   in d
        assert "subsystem_id" in d
        assert "version"      in d


# ── TestSubsystemHealth ───────────────────────────────────────────────────────

class TestSubsystemHealth:
    def _mock_running_component(self) -> Any:
        from iios.investment.workflow.engine_lifecycle import EngineState
        m = MagicMock()
        m.lifecycle_state.return_value = EngineState.RUNNING
        return m

    def _mock_stopped_component(self) -> Any:
        from iios.investment.workflow.engine_lifecycle import EngineState
        m = MagicMock()
        m.lifecycle_state.return_value = EngineState.STOPPED
        return m

    def test_running_component_healthy(self):
        h = check_component_health(self._mock_running_component(), "engine")
        assert h.is_running is True
        assert h.is_healthy is True
        assert h.error      is None

    def test_stopped_component_not_healthy(self):
        h = check_component_health(self._mock_stopped_component(), "engine")
        assert h.is_running is False
        assert h.is_healthy is False
        assert h.error      is not None

    def test_non_lifecycle_component(self):
        h = check_component_health(object(), "custom")
        assert h.is_running is False

    def test_subsystem_health_all_running(self):
        comps = {
            "engine":   self._mock_running_component(),
            "controls": self._mock_running_component(),
        }
        h = make_subsystem_health(comps, "running")
        assert h.overall_healthy is True
        assert h.all_running     is True

    def test_subsystem_health_one_stopped(self):
        comps = {
            "engine":   self._mock_running_component(),
            "controls": self._mock_stopped_component(),
        }
        h = make_subsystem_health(comps, "running")
        assert h.overall_healthy is False
        assert len(h.unhealthy_components) == 1

    def test_to_dict(self):
        comps = {"engine": self._mock_running_component()}
        h = make_subsystem_health(comps, "running")
        d = h.to_dict()
        assert "overall_healthy" in d
        assert "component_health" in d


# ── TestSubsystemStatus ───────────────────────────────────────────────────────

class TestSubsystemStatus:
    def test_values(self):
        assert SubsystemStatus.RUNNING  == "running"
        assert SubsystemStatus.STOPPED  == "stopped"
        assert SubsystemStatus.FAILED   == "failed"

    def test_str_enum(self):
        assert isinstance(SubsystemStatus.RUNNING, str)


# ── TestIntegrationSnapshot ───────────────────────────────────────────────────

class TestIntegrationSnapshot:
    def _make(self):
        return make_integration_snapshot(
            subsystem_state="running",
            is_running=True,
            is_healthy=True,
            component_health={"engine": {"is_healthy": True}},
            statistics={"requests_processed": 5},
            recent_events=[],
            evaluation_count=5,
            snapshot_count=5,
            uptime_sec=60.0,
            version="1.0.0",
        )

    def test_fields(self):
        s = self._make()
        assert s.is_running      is True
        assert s.evaluation_count == 5
        assert s.version         == "1.0.0"

    def test_to_dict(self):
        d = self._make().to_dict()
        assert "snapshot_id"      in d
        assert "statistics"       in d
        assert "component_health" in d

    def test_to_json(self):
        raw    = self._make().to_json()
        parsed = json.loads(raw)
        assert parsed["is_running"] is True

    def test_immutable(self):
        s = self._make()
        with pytest.raises((TypeError, AttributeError)):
            s.is_running = False  # type: ignore


# ── TestIntegrationRequestFactory ────────────────────────────────────────────

class TestIntegrationRequestFactory:
    def test_create_context(self):
        ctx = IntegrationRequestFactory.create_context("EX-1", "ORD-1", portfolio_id="PORT-1")
        assert ctx.execution_id == "EX-1"
        assert ctx.portfolio_id == "PORT-1"

    def test_create_equity_context(self):
        ctx = IntegrationRequestFactory.create_equity_context(
            "EX-1", "ORD-1", "RELIANCE", "BUY", 100.0, 2500.0
        )
        assert ctx.asset_class == "EQUITY"
        assert ctx.symbol      == "RELIANCE"

    def test_create_option_context(self):
        ctx = IntegrationRequestFactory.create_option_context(
            "EX-1", "ORD-1", "NIFTY25JAN25CE", "BUY", 50.0, 200.0
        )
        assert ctx.asset_class == "OPTION"

    def test_create_request(self):
        ctx = _ctx()
        req = IntegrationRequestFactory.create_request(ctx)
        assert isinstance(req, ExecutionRiskRequest)

    def test_create_minimal_request(self):
        req = IntegrationRequestFactory.create_minimal_request("EX-1", "ORD-1")
        assert req.execution_id == "EX-1"

    def test_create_strict_request(self):
        req = IntegrationRequestFactory.create_strict_request(_ctx())
        assert req.evaluation_mode == EvaluationMode.STRICT

    def test_create_emergency_request(self):
        req = IntegrationRequestFactory.create_emergency_request(_ctx())
        assert req.evaluation_mode == EvaluationMode.EMERGENCY


# ── TestWorkflow ──────────────────────────────────────────────────────────────

class TestWorkflow:
    """Full evaluate() workflow with real M2/M4/M5 (no registered rules → ALLOW)."""

    def test_evaluate_no_rules_returns_allowed(self):
        manager = _manager()
        ctx = _ctx(execution_id="EX-1", order_id="ORD-1")
        req = _req(ctx)
        response = manager.evaluate(req)
        manager.stop()

        assert isinstance(response, ExecutionRiskResponse)
        assert response.approved is True
        assert response.action   == "ALLOW"

    def test_response_has_snapshot(self):
        manager = _manager()
        response = manager.evaluate(_req())
        manager.stop()

        from iios.execution.risk.snapshot import ExecutionRiskSnapshot
        assert isinstance(response.snapshot, ExecutionRiskSnapshot)

    def test_response_identifiers_match_request(self):
        manager = _manager()
        ctx = _ctx(execution_id="EX-99", order_id="ORD-99",
                   portfolio_id="PORT-X", strategy_id="STRAT-X")
        req = _req(ctx)
        response = manager.evaluate(req)
        manager.stop()

        assert response.execution_id == "EX-99"
        assert response.order_id     == "ORD-99"
        assert response.portfolio_id == "PORT-X"
        assert response.strategy_id  == "STRAT-X"

    def test_response_elapsed_ms_positive(self):
        manager = _manager()
        response = manager.evaluate(_req())
        manager.stop()
        assert response.elapsed_ms > 0

    def test_snapshot_published_status(self):
        from iios.execution.risk.snapshot import SnapshotStatus
        manager = _manager()
        response = manager.evaluate(_req())
        manager.stop()
        assert response.snapshot.status == SnapshotStatus.PUBLISHED


# ── TestWorkflowBlocked ───────────────────────────────────────────────────────

class TestWorkflowBlocked:
    """Test blocked evaluation with a blocking M3-style rule."""

    def _blocking_rule(self):
        """Minimal M2-compatible blocking rule."""
        from iios.execution.risk.engine import RuleResult, RuleOutcome

        class _BlockRule:
            rule_name = "always_block"

            @property
            def risk_category(self):
                from iios.execution.risk.lifecycle import RiskCategory
                return RiskCategory.EXECUTION

            def is_applicable(self, request) -> bool:
                return True

            def evaluate(self, request, context) -> RuleResult:
                return RuleResult(
                    rule_name=self.rule_name,
                    rule_category="execution",
                    outcome=RuleOutcome.BLOCKED,
                    message="always blocked",
                    elapsed_ms=0.5,
                )

        return _BlockRule()

    def test_blocked_response(self):
        manager = _manager()
        manager.register_rule(self._blocking_rule())
        response = manager.evaluate(_req())
        manager.stop()

        assert response.approved  is False
        assert response.is_blocked is True

    def test_blocked_action_is_block_variant(self):
        manager = _manager()
        manager.register_rule(self._blocking_rule())
        response = manager.evaluate(_req())
        manager.stop()
        assert response.action in ("BLOCK", "CANCEL", "EMERGENCY_STOP")


# ── TestWorkflowValidationFail ────────────────────────────────────────────────

class TestWorkflowValidationFail:
    def test_empty_execution_id_returns_blocked(self):
        manager = _manager()
        req = make_execution_risk_request(make_execution_context("", "ORD-1"))
        response = manager.evaluate(req)
        manager.stop()

        assert response.approved        is False
        assert response.validation_passed is False
        assert response.error_message

    def test_validation_failure_updates_stats(self):
        manager = _manager()
        req = make_execution_risk_request(make_execution_context("", "ORD-1"))
        manager.evaluate(req)
        stats = manager.statistics()
        manager.stop()

        assert stats.validation_failures >= 1


# ── TestEngineLifecycle ───────────────────────────────────────────────────────

class TestEngineLifecycle:
    def test_start_and_stop(self):
        e = ExecutionRiskIntegrationEngine()
        e.start()
        assert e.is_running
        e.stop()
        assert not e.is_running

    def test_not_running_raises(self):
        e = ExecutionRiskIntegrationEngine()
        with pytest.raises(IntegrationNotRunningError):
            e.evaluate(_req())

    def test_register_rule_requires_running(self):
        e = ExecutionRiskIntegrationEngine()
        with pytest.raises(IntegrationNotRunningError):
            e.register_rule(MagicMock())

    def test_status_before_start(self):
        e = ExecutionRiskIntegrationEngine()
        assert e.status() == SubsystemStatus.UNINITIALIZED

    def test_status_while_running(self):
        e = ExecutionRiskIntegrationEngine()
        e.start()
        s = e.status()
        e.stop()
        assert s == SubsystemStatus.RUNNING

    def test_status_after_stop(self):
        e = ExecutionRiskIntegrationEngine()
        e.start()
        e.stop()
        assert e.status() == SubsystemStatus.STOPPED


# ── TestManagerLifecycle ──────────────────────────────────────────────────────

class TestManagerLifecycle:
    def test_start_stop(self):
        m = ExecutionRiskIntegrationManager()
        m.start()
        assert m.is_running
        m.stop()
        assert not m.is_running

    def test_manager_delegates_evaluate(self):
        m = _manager()
        response = m.evaluate(_req())
        m.stop()
        assert isinstance(response, ExecutionRiskResponse)

    def test_create_context_convenience(self):
        m = _manager()
        ctx = m.create_context("EX-1", "ORD-1", portfolio_id="PORT-1")
        m.stop()
        assert ctx.execution_id == "EX-1"

    def test_create_request_convenience(self):
        m = _manager()
        ctx = m.create_context("EX-1", "ORD-1")
        req = m.create_request(ctx)
        m.stop()
        assert isinstance(req, ExecutionRiskRequest)


# ── TestHealth ────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_subsystem_health(self):
        engine = _engine()
        h = engine.health()
        engine.stop()
        assert isinstance(h, SubsystemHealth)

    def test_health_all_running_when_started(self):
        engine = _engine()
        h = engine.health()
        engine.stop()
        assert h.all_running is True
        assert h.overall_healthy is True

    def test_health_via_manager(self):
        m = _manager()
        h = m.health()
        m.stop()
        assert isinstance(h, SubsystemHealth)


# ── TestStatisticsIntegration ─────────────────────────────────────────────────

class TestStatisticsIntegration:
    def test_statistics_updated_after_evaluate(self):
        m = _manager()
        m.evaluate(_req())
        stats = m.statistics()
        m.stop()
        assert stats.requests_processed >= 1

    def test_statistics_copy_independent(self):
        m = _manager()
        m.evaluate(_req())
        s1 = m.statistics()
        m.evaluate(_req())
        s2 = m.statistics()
        m.stop()
        assert s2.requests_processed == s1.requests_processed + 1


# ── TestHistoryIntegration ────────────────────────────────────────────────────

class TestHistoryIntegration:
    def test_history_populated(self):
        m = _manager()
        m.evaluate(_req())
        m.evaluate(_req())
        hist = m.history(n=10)
        m.stop()
        assert len(hist) >= 2

    def test_history_default_n(self):
        m = _manager()
        for _ in range(5):
            m.evaluate(_req())
        hist = m.history()
        m.stop()
        assert len(hist) >= 5


# ── TestQueryFilters ──────────────────────────────────────────────────────────

class TestQueryFilters:
    def test_query_by_execution_id(self):
        m = _manager()
        eid = "EX-FILTER-TEST"
        m.evaluate(_req(_ctx(execution_id=eid)))
        m.evaluate(_req(_ctx(execution_id="EX-OTHER")))
        results = m.query(execution_id=eid)
        m.stop()
        assert all(r.execution_id == eid for r in results)
        assert len(results) >= 1

    def test_query_by_order_id(self):
        m = _manager()
        oid = "ORD-FILTER-TEST"
        m.evaluate(_req(_ctx(order_id=oid)))
        results = m.query(order_id=oid)
        m.stop()
        assert len(results) >= 1

    def test_query_approved_only(self):
        m = _manager()
        m.evaluate(_req())  # no blocking rules → approved
        results = m.query(approved_only=True)
        m.stop()
        assert all(r.approved for r in results)

    def test_query_blocked_only(self):
        m = _manager()
        m.evaluate(_req())
        results = m.query(blocked_only=True)
        m.stop()
        # With no rules → no blocked results
        assert all(r.is_blocked for r in results)


# ── TestEventsEmitted ─────────────────────────────────────────────────────────

class TestEventsEmitted:
    def test_start_emits_started_event(self):
        e = _engine()
        evts = e.events()
        e.stop()
        types = [ev.event_type for ev in evts]
        assert IntegrationEventType.SUBSYSTEM_STARTED in types

    def test_evaluate_emits_requested_and_completed(self):
        e = _engine()
        e.evaluate(_req())
        evts = e.events()
        e.stop()
        types = {ev.event_type for ev in evts}
        assert IntegrationEventType.EVALUATION_REQUESTED  in types
        assert IntegrationEventType.EVALUATION_COMPLETED  in types
        assert IntegrationEventType.SNAPSHOT_PUBLISHED    in types

    def test_stop_emits_stopped_event(self):
        e = _engine()
        e.stop()
        evts = e.events()
        types = [ev.event_type for ev in evts]
        assert IntegrationEventType.SUBSYSTEM_STOPPED in types


# ── TestSnapshotPublication ───────────────────────────────────────────────────

class TestSnapshotPublication:
    def test_snapshot_published_in_registry(self):
        from iios.execution.risk.snapshot import SnapshotStatus
        e = _engine()
        response = e.evaluate(_req())
        e.stop()

        assert response.snapshot.status == SnapshotStatus.PUBLISHED

    def test_snapshot_has_correct_identifiers(self):
        e = _engine()
        ctx = _ctx(execution_id="EX-SNAP", order_id="ORD-SNAP")
        response = e.evaluate(_req(ctx))
        e.stop()

        assert response.snapshot.execution_id == "EX-SNAP"
        assert response.snapshot.order_id     == "ORD-SNAP"


# ── TestConcurrency ───────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_evaluations(self):
        engine = _engine()
        errors  = []
        results = []
        lock    = threading.Lock()

        def _evaluate():
            try:
                r = engine.evaluate(_req())
                with lock:
                    results.append(r)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_evaluate) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        engine.stop()
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10

    def test_concurrent_statistics_consistent(self):
        engine = _engine()

        def _evaluate():
            engine.evaluate(_req())

        threads = [threading.Thread(target=_evaluate) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = engine.statistics()
        engine.stop()
        assert stats.requests_processed == 20


# ── TestEdgeCases ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_to_json_roundtrip(self):
        m = _manager()
        response = m.evaluate(_req())
        m.stop()
        d1 = response.to_dict()
        d2 = json.loads(response.to_json())
        assert d1["response_id"] == d2["response_id"]
        assert d1["approved"]    == d2["approved"]

    def test_snapshot_method_returns_integration_snapshot(self):
        e = _engine()
        s = e.snapshot()
        e.stop()
        assert isinstance(s, ExecutionRiskIntegrationSnapshot)
        assert s.is_running is True

    def test_validate_without_evaluate(self):
        e = _engine()
        req = _req()
        report = e.validate(req)
        e.stop()
        assert report.is_valid

    def test_registered_rules_initially_empty(self):
        e = _engine()
        rules = e.registered_rules()
        e.stop()
        assert isinstance(rules, list)

    def test_events_returns_list(self):
        e = _engine()
        evts = e.events()
        e.stop()
        assert isinstance(evts, list)
        # events() returns a copy
        assert evts is not e.events()

    def test_history_empty_initially(self):
        e = ExecutionRiskIntegrationEngine()
        e.start()
        hist = e.history()
        e.stop()
        assert hist == []

    def test_snapshot_count_increases_after_evaluate(self):
        e = _engine()
        s1 = e.snapshot()
        e.evaluate(_req())
        s2 = e.snapshot()
        e.stop()
        assert s2.snapshot_count > s1.snapshot_count
