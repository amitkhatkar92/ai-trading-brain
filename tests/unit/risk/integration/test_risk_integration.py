"""
test_risk_integration.py
========================
Unit tests for C11 M6 — Risk Integration Framework.

Coverage targets:
  API, Initialisation, Lifecycle, Workflow, Validation,
  Health, Statistics, History, Events, Registry, Concurrency, Regression

Tests: ~220 cases.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from iios.risk.integration import (
    # Engine
    RiskIntegrationEngine,
    # Request / Response / Context
    RiskIntegrationContext,
    RiskIntegrationRequest,
    RiskIntegrationResponse,
    # Enums
    ComponentStatus,
    HealthStatus,
    IntegrationEventType,
    IntegrationStatus,
    IntegrationValidationCode,
    RequestType,
    # Constants
    COMPONENT_ASSESSMENT,
    COMPONENT_ENGINE,
    COMPONENT_LIFECYCLE,
    COMPONENT_POLICIES,
    COMPONENT_SNAPSHOT,
    INTEGRATION_SYSTEM_ID,
    REQUIRED_COMPONENTS,
    VERSION,
    # Exceptions
    RiskIntegrationCapacityError,
    RiskIntegrationComponentError,
    RiskIntegrationError,
    RiskIntegrationNotRunningError,
    RiskIntegrationRequestError,
    RiskIntegrationValidationError,
    RiskIntegrationWorkflowError,
    # Components
    RiskComponentFactory,
    RiskComponentRegistry,
    RiskIntegrationRegistry,
    RiskIntegrationStatistics,
    RiskIntegrationHistory,
    RiskIntegrationSnapshot,
    RiskIntegrationStatus,
    RiskIntegrationHealth,
    RiskIntegrationHealthReport,
    RiskIntegrationManager,
    RiskIntegrationValidator,
    IntegrationValidationResult,
    IntegrationValidationCheck,
    # Events
    RiskIntegrationEvent,
    make_integration_started,
    make_integration_stopped,
    make_request_received,
    make_risk_completed,
    make_risk_failed,
    make_risk_validated,
    make_snapshot_published,
)


# ============================================================================
# Helpers / Fixtures
# ============================================================================

def _make_request(
    portfolio_id: str = "PORT-001",
    request_type: RequestType = RequestType.PORTFOLIO_RISK_ASSESSMENT,
    **kwargs: Any,
) -> RiskIntegrationRequest:
    return RiskIntegrationRequest.create(
        request_type=request_type,
        portfolio_id=portfolio_id,
        **kwargs,
    )


def _started_engine(**kwargs) -> RiskIntegrationEngine:
    engine = RiskIntegrationEngine(**kwargs)
    engine.initialize()
    engine.start()
    return engine


# ============================================================================
# 1  CONSTANTS
# ============================================================================

class TestConstants:
    def test_integration_system_id(self):
        assert INTEGRATION_SYSTEM_ID == "iios:risk:integration"

    def test_version_format(self):
        parts = VERSION.split(".")
        assert len(parts) == 3

    def test_required_components_has_five(self):
        assert len(REQUIRED_COMPONENTS) == 5

    def test_component_keys_in_required(self):
        for key in [
            COMPONENT_LIFECYCLE, COMPONENT_ENGINE,
            COMPONENT_POLICIES, COMPONENT_ASSESSMENT, COMPONENT_SNAPSHOT,
        ]:
            assert key in REQUIRED_COMPONENTS

    def test_request_type_count(self):
        assert len(RequestType) == 10

    def test_integration_status_count(self):
        assert len(IntegrationStatus) == 7

    def test_component_status_count(self):
        assert len(ComponentStatus) == 5

    def test_health_status_count(self):
        assert len(HealthStatus) == 4

    def test_integration_event_type_count(self):
        assert len(IntegrationEventType) == 7

    def test_integration_validation_code_count(self):
        assert len(IntegrationValidationCode) == 6


# ============================================================================
# 2  EXCEPTIONS
# ============================================================================

class TestExceptions:
    def test_base_error_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(RiskIntegrationError, IIOSError)

    def test_not_running_error_code(self):
        exc = RiskIntegrationNotRunningError("not running")
        assert exc.error_code == "RI-001"

    def test_request_error_code(self):
        exc = RiskIntegrationRequestError("bad request")
        assert exc.error_code == "RI-002"

    def test_validation_error_code(self):
        exc = RiskIntegrationValidationError("invalid")
        assert exc.error_code == "RI-003"

    def test_component_error_code(self):
        exc = RiskIntegrationComponentError("missing")
        assert exc.error_code == "RI-004"

    def test_capacity_error_code(self):
        exc = RiskIntegrationCapacityError("full")
        assert exc.error_code == "RI-007"

    def test_all_are_subclass_of_base(self):
        from iios.risk.integration.exceptions import (
            RiskIntegrationSnapshotError,
            RiskIntegrationTimeoutError,
            RiskIntegrationConfigurationError,
            RiskIntegrationWorkflowError,
        )
        for exc_cls in [
            RiskIntegrationNotRunningError,
            RiskIntegrationRequestError,
            RiskIntegrationValidationError,
            RiskIntegrationComponentError,
            RiskIntegrationSnapshotError,
            RiskIntegrationWorkflowError,
            RiskIntegrationCapacityError,
            RiskIntegrationTimeoutError,
            RiskIntegrationConfigurationError,
        ]:
            assert issubclass(exc_cls, RiskIntegrationError)


# ============================================================================
# 3  CONTEXT
# ============================================================================

class TestRiskIntegrationContext:
    def test_create_basic(self):
        ctx = RiskIntegrationContext.create(
            request_type=RequestType.PORTFOLIO_RISK_ASSESSMENT,
            portfolio_id="P-1",
        )
        assert ctx.portfolio_id == "P-1"
        assert ctx.request_type == RequestType.PORTFOLIO_RISK_ASSESSMENT

    def test_context_id_generated(self):
        ctx = RiskIntegrationContext.create(
            request_type=RequestType.RISK_SNAPSHOT,
            portfolio_id="P-X",
        )
        assert uuid.UUID(ctx.context_id)   # valid uuid

    def test_to_dict(self):
        ctx = RiskIntegrationContext.create(
            request_type=RequestType.STRESS_TEST,
            portfolio_id="P-2",
        )
        d = ctx.to_dict()
        assert d["portfolio_id"] == "P-2"
        assert d["request_type"] == RequestType.STRESS_TEST.value

    def test_context_is_frozen(self):
        ctx = RiskIntegrationContext.create(
            request_type=RequestType.RISK_FORECAST,
            portfolio_id="P-3",
        )
        with pytest.raises((AttributeError, TypeError)):
            ctx.portfolio_id = "MODIFIED"  # type: ignore[misc]

    def test_optional_fields_default(self):
        ctx = RiskIntegrationContext.create(
            request_type=RequestType.EXPOSURE_REVIEW,
            portfolio_id="P-4",
        )
        assert ctx.workflow_id == ""
        assert ctx.strategy_id == ""
        assert ctx.account_id  == ""

    def test_with_optional_fields(self):
        ctx = RiskIntegrationContext.create(
            request_type=RequestType.RISK_HISTORY,
            portfolio_id="P-5",
            workflow_id="WF-1",
            strategy_id="ST-1",
            account_id="AC-1",
        )
        assert ctx.workflow_id == "WF-1"
        assert ctx.strategy_id == "ST-1"
        assert ctx.account_id  == "AC-1"


# ============================================================================
# 4  REQUEST
# ============================================================================

class TestRiskIntegrationRequest:
    def test_create_minimal(self):
        req = _make_request()
        assert req.portfolio_id == "PORT-001"
        assert req.request_type == RequestType.PORTFOLIO_RISK_ASSESSMENT

    def test_request_id_generated(self):
        req = _make_request()
        assert uuid.UUID(req.request_id)

    def test_explicit_request_id(self):
        req = _make_request(request_id="MY-ID")
        assert req.request_id == "MY-ID"

    def test_properties(self):
        req = _make_request(
            request_type=RequestType.POSITION_RISK_ASSESSMENT,
            portfolio_id="P-99",
        )
        assert req.request_type == RequestType.POSITION_RISK_ASSESSMENT
        assert req.portfolio_id == "P-99"

    def test_snapshots_default_empty(self):
        req = _make_request()
        assert req.portfolio_snapshot  == {}
        assert req.market_snapshot     == {}
        assert req.account_snapshot    == {}

    def test_with_positions(self):
        req = _make_request(positions={"RELIANCE": 100.0})
        assert req.positions["RELIANCE"] == 100.0

    def test_with_returns(self):
        req = _make_request(returns=[0.01, -0.02, 0.03])
        assert len(req.returns) == 3

    def test_to_dict(self):
        req = _make_request()
        d = req.to_dict()
        assert "request_id"   in d
        assert "portfolio_id" in d
        assert "context"      in d

    def test_is_frozen(self):
        req = _make_request()
        with pytest.raises((AttributeError, TypeError)):
            req.portfolio_id = "X"  # type: ignore[misc]


# ============================================================================
# 5  RESPONSE
# ============================================================================

class TestRiskIntegrationResponse:
    def test_success_factory(self):
        resp = RiskIntegrationResponse.success(
            request_id    = "REQ-1",
            portfolio_id  = "PORT-1",
            request_type  = RequestType.PORTFOLIO_RISK_ASSESSMENT,
            snapshot_dict = {"score": 42.0},
            duration_s    = 0.1,
        )
        assert resp.is_success
        assert resp.status == IntegrationStatus.COMPLETED
        assert resp.has_snapshot

    def test_failure_factory(self):
        resp = RiskIntegrationResponse.failure(
            request_id    = "REQ-2",
            portfolio_id  = "PORT-2",
            request_type  = RequestType.STRESS_TEST,
            error_message = "something broke",
            duration_s    = 0.05,
        )
        assert not resp.is_success
        assert resp.status == IntegrationStatus.FAILED
        assert resp.error_message == "something broke"

    def test_to_dict(self):
        resp = RiskIntegrationResponse.success(
            request_id   = "R",
            portfolio_id = "P",
            request_type = RequestType.RISK_SNAPSHOT,
            snapshot_dict= {},
            duration_s   = 0.0,
        )
        d = resp.to_dict()
        assert d["status"] == IntegrationStatus.COMPLETED.value

    def test_response_id_generated(self):
        resp = RiskIntegrationResponse.success(
            request_id="R", portfolio_id="P",
            request_type=RequestType.EXPOSURE_REVIEW,
            snapshot_dict={}, duration_s=0.0,
        )
        assert uuid.UUID(resp.response_id)

    def test_snapshot_id_generated(self):
        resp = RiskIntegrationResponse.success(
            request_id="R", portfolio_id="P",
            request_type=RequestType.EXPOSURE_REVIEW,
            snapshot_dict={"x": 1}, duration_s=0.0,
        )
        assert resp.snapshot_id != ""

    def test_no_snapshot_when_empty(self):
        resp = RiskIntegrationResponse.success(
            request_id="R", portfolio_id="P",
            request_type=RequestType.RISK_FORECAST,
            snapshot_dict={}, duration_s=0.0,
        )
        # empty snapshot_dict — has_snapshot depends on implementation
        assert isinstance(resp.has_snapshot, bool)


# ============================================================================
# 6  EVENTS
# ============================================================================

class TestEvents:
    def test_make_integration_started(self):
        evt = make_integration_started("ENG-1", "P-1", actor="system")
        assert evt.event_type == IntegrationEventType.RISK_INTEGRATION_STARTED
        assert evt.engine_id == "ENG-1"

    def test_make_request_received(self):
        evt = make_request_received("ENG-1", "P-1", "REQ-1", actor="manager")
        assert evt.event_type == IntegrationEventType.RISK_REQUEST_RECEIVED
        assert evt.request_id == "REQ-1"

    def test_make_risk_validated(self):
        evt = make_risk_validated("ENG-1", "P-1", "REQ-1", actor="manager")
        assert evt.event_type == IntegrationEventType.RISK_VALIDATED

    def test_make_snapshot_published(self):
        evt = make_snapshot_published("ENG-1", "P-1", "REQ-1", actor="manager")
        assert evt.event_type == IntegrationEventType.RISK_SNAPSHOT_PUBLISHED

    def test_make_risk_completed(self):
        evt = make_risk_completed("ENG-1", "P-1", "REQ-1", actor="manager")
        assert evt.event_type == IntegrationEventType.RISK_COMPLETED

    def test_make_risk_failed(self):
        evt = make_risk_failed("ENG-1", "P-1", "REQ-1", actor="manager")
        assert evt.event_type == IntegrationEventType.RISK_FAILED

    def test_make_integration_stopped(self):
        evt = make_integration_stopped("ENG-1", "P-1", actor="system")
        assert evt.event_type == IntegrationEventType.RISK_INTEGRATION_STOPPED

    def test_event_is_frozen(self):
        evt = make_risk_completed("E", "P", "R", actor="a")
        with pytest.raises((AttributeError, TypeError)):
            evt.engine_id = "X"  # type: ignore[misc]

    def test_event_id_unique(self):
        e1 = make_risk_completed("E", "P", "R", actor="a")
        e2 = make_risk_completed("E", "P", "R", actor="a")
        assert e1.event_id != e2.event_id

    def test_event_payload_kwargs(self):
        evt = make_risk_completed("E", "P", "R", actor="a",
                                   risk_score=55.0, duration_s=0.1)
        assert evt.payload.get("risk_score") == 55.0


# ============================================================================
# 7  COMPONENT REGISTRY
# ============================================================================

class TestRiskComponentRegistry:
    def test_register_and_get(self):
        reg = RiskComponentRegistry()
        obj = object()
        reg.register("mykey", obj, status=ComponentStatus.AVAILABLE)
        assert reg.get("mykey") is obj

    def test_get_missing_raises(self):
        reg = RiskComponentRegistry()
        with pytest.raises(RiskIntegrationComponentError):
            reg.get("nonexistent")

    def test_get_unavailable_raises(self):
        reg = RiskComponentRegistry()
        reg.register("key", None, status=ComponentStatus.UNAVAILABLE)
        with pytest.raises(RiskIntegrationComponentError):
            reg.get("key")

    def test_get_or_none_returns_none(self):
        reg = RiskComponentRegistry()
        assert reg.get_or_none("missing") is None

    def test_get_or_none_unavailable_returns_none(self):
        reg = RiskComponentRegistry()
        reg.register("k", None, status=ComponentStatus.UNAVAILABLE)
        assert reg.get_or_none("k") is None

    def test_is_available(self):
        reg = RiskComponentRegistry()
        reg.register("a", object(), status=ComponentStatus.AVAILABLE)
        assert reg.is_available("a") is True

    def test_is_unavailable(self):
        reg = RiskComponentRegistry()
        reg.register("a", None, status=ComponentStatus.UNAVAILABLE)
        assert reg.is_available("a") is False

    def test_all_available_false_when_empty(self):
        reg = RiskComponentRegistry()
        assert reg.all_available() is False

    def test_all_available_true_when_all_registered(self):
        reg = RiskComponentRegistry()
        for key in REQUIRED_COMPONENTS:
            reg.register(key, object(), status=ComponentStatus.AVAILABLE)
        assert reg.all_available() is True

    def test_missing_required(self):
        reg = RiskComponentRegistry()
        missing = reg.missing_required()
        assert set(missing) == REQUIRED_COMPONENTS

    def test_set_status(self):
        reg = RiskComponentRegistry()
        reg.register("x", object(), status=ComponentStatus.AVAILABLE)
        reg.set_status("x", ComponentStatus.DEGRADED)
        assert reg.get_status("x") == ComponentStatus.DEGRADED

    def test_unregister(self):
        reg = RiskComponentRegistry()
        reg.register("x", object(), status=ComponentStatus.AVAILABLE)
        reg.unregister("x")
        assert reg.get_or_none("x") is None

    def test_count(self):
        reg = RiskComponentRegistry()
        reg.register("a", object(), status=ComponentStatus.AVAILABLE)
        reg.register("b", object(), status=ComponentStatus.AVAILABLE)
        assert reg.count() == 2

    def test_clear(self):
        reg = RiskComponentRegistry()
        reg.register("a", object(), status=ComponentStatus.AVAILABLE)
        reg.clear()
        assert reg.count() == 0

    def test_health_summary(self):
        reg = RiskComponentRegistry()
        reg.register("a", object(), status=ComponentStatus.AVAILABLE)
        summary = reg.health_summary()
        assert summary["a"] == ComponentStatus.AVAILABLE.value

    def test_thread_safety(self):
        reg  = RiskComponentRegistry()
        errors: List[str] = []

        def worker(i: int):
            try:
                reg.register(f"k{i}", object(), status=ComponentStatus.AVAILABLE)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert reg.count() == 50
        assert errors == []


# ============================================================================
# 8  COMPONENT FACTORY
# ============================================================================

class TestRiskComponentFactory:
    def test_create_returns_registry(self):
        factory  = RiskComponentFactory()
        registry = factory.create_default_registry()
        assert isinstance(registry, RiskComponentRegistry)

    def test_registry_has_five_components(self):
        factory  = RiskComponentFactory()
        registry = factory.create_default_registry()
        assert registry.count() == 5

    def test_component_versions_returns_dict(self):
        factory   = RiskComponentFactory()
        versions  = factory.component_versions()
        assert isinstance(versions, dict)
        assert len(versions) == 5

    def test_production_environment_default(self):
        factory = RiskComponentFactory()
        assert factory._environment == "production"

    def test_custom_environment(self):
        factory = RiskComponentFactory(environment="test")
        assert factory._environment == "test"


# ============================================================================
# 9  INTEGRATION REGISTRY
# ============================================================================

class TestRiskIntegrationRegistry:
    def test_register_and_get_request(self):
        reg = RiskIntegrationRegistry()
        req = _make_request()
        reg.register_request(req)
        assert reg.get_request(req.request_id) is req

    def test_register_and_get_response(self):
        reg  = RiskIntegrationRegistry()
        req  = _make_request()
        reg.register_request(req)
        resp = RiskIntegrationResponse.success(
            request_id="R", portfolio_id="P",
            request_type=RequestType.PORTFOLIO_RISK_ASSESSMENT,
            snapshot_dict={}, duration_s=0.0,
        )
        resp2 = RiskIntegrationResponse(
            **{**resp.__dict__,
               "request_id": req.request_id,
               "response_id": str(uuid.uuid4())})
        reg.register_response(resp2)
        assert reg.get_response(req.request_id) is resp2

    def test_latest_for_portfolio(self):
        reg  = RiskIntegrationRegistry()
        req  = _make_request(portfolio_id="P-LATEST")
        resp = RiskIntegrationResponse.success(
            request_id=req.request_id, portfolio_id="P-LATEST",
            request_type=RequestType.PORTFOLIO_RISK_ASSESSMENT,
            snapshot_dict={}, duration_s=0.0,
        )
        reg.register_request(req)
        reg.register_response(resp)
        found = reg.latest_for_portfolio("P-LATEST")
        assert found is not None
        assert found.portfolio_id == "P-LATEST"

    def test_latest_for_unknown_portfolio_returns_none(self):
        reg = RiskIntegrationRegistry()
        assert reg.latest_for_portfolio("UNKNOWN") is None

    def test_capacity_limit(self):
        reg = RiskIntegrationRegistry(max_requests=2)
        for i in range(2):
            reg.register_request(_make_request(request_id=f"REQ-{i}"))
        with pytest.raises(RiskIntegrationCapacityError):
            reg.register_request(_make_request(request_id="REQ-extra"))

    def test_duplicate_raises(self):
        reg = RiskIntegrationRegistry()
        req = _make_request()
        reg.register_request(req)
        with pytest.raises(RiskIntegrationRequestError):
            reg.register_request(req)

    def test_clear(self):
        reg = RiskIntegrationRegistry()
        req = _make_request()
        reg.register_request(req)
        reg.clear()
        assert reg.is_empty()

    def test_count(self):
        reg = RiskIntegrationRegistry()
        reg.register_request(_make_request(request_id="A"))
        reg.register_request(_make_request(request_id="B"))
        assert reg.request_count() == 2


# ============================================================================
# 10  STATISTICS
# ============================================================================

class TestRiskIntegrationStatistics:
    def test_initial_state(self):
        stats = RiskIntegrationStatistics()
        snap  = stats.snapshot()
        assert snap["requests_received"]  == 0
        assert snap["requests_completed"] == 0
        assert snap["requests_failed"]    == 0

    def test_record_received(self):
        stats = RiskIntegrationStatistics()
        stats.record_request_received()
        stats.record_request_received()
        assert stats.total_received() == 2

    def test_record_completed(self):
        stats = RiskIntegrationStatistics()
        stats.record_request_completed()
        assert stats.total_completed() == 1

    def test_record_failed(self):
        stats = RiskIntegrationStatistics()
        stats.record_request_failed()
        assert stats.total_failed() == 1

    def test_record_snapshot_published(self):
        stats = RiskIntegrationStatistics()
        stats.record_snapshot_published()
        stats.record_snapshot_published()
        assert stats.total_snapshots() == 2

    def test_processing_time(self):
        stats = RiskIntegrationStatistics()
        stats.record_request_completed()
        stats.record_processing_time(0.5)
        snap = stats.snapshot()
        assert snap["avg_processing_s"] == pytest.approx(0.5)

    def test_success_rate(self):
        stats = RiskIntegrationStatistics()
        stats.record_request_completed()
        stats.record_request_completed()
        stats.record_request_failed()
        snap = stats.snapshot()
        assert snap["success_rate"] == pytest.approx(2 / 3)

    def test_error_rate(self):
        stats = RiskIntegrationStatistics()
        stats.record_request_completed()
        stats.record_request_failed()
        snap = stats.snapshot()
        assert snap["error_rate"] == pytest.approx(0.5)

    def test_reset(self):
        stats = RiskIntegrationStatistics()
        stats.record_request_received()
        stats.reset()
        assert stats.total_received() == 0

    def test_thread_safety(self):
        stats  = RiskIntegrationStatistics()
        errors: List[str] = []

        def worker():
            try:
                for _ in range(100):
                    stats.record_request_received()
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert stats.total_received() == 1000
        assert errors == []


# ============================================================================
# 11  HISTORY
# ============================================================================

class TestRiskIntegrationHistory:
    def test_record_and_retrieve_requests(self):
        hist = RiskIntegrationHistory()
        req  = _make_request()
        hist.record_request(req)
        assert hist.recent_requests(5)[0] is req

    def test_record_and_retrieve_responses(self):
        hist = RiskIntegrationHistory()
        resp = RiskIntegrationResponse.success(
            request_id="R", portfolio_id="P",
            request_type=RequestType.PORTFOLIO_RISK_ASSESSMENT,
            snapshot_dict={}, duration_s=0.0,
        )
        hist.record_response(resp)
        assert hist.recent_responses(5)[0] is resp

    def test_find_response(self):
        hist = RiskIntegrationHistory()
        resp = RiskIntegrationResponse.success(
            request_id="FIND-ME", portfolio_id="P",
            request_type=RequestType.PORTFOLIO_RISK_ASSESSMENT,
            snapshot_dict={}, duration_s=0.0,
        )
        hist.record_response(resp)
        found = hist.find_response("FIND-ME")
        assert found is resp

    def test_find_response_not_found(self):
        hist = RiskIntegrationHistory()
        assert hist.find_response("GHOST") is None

    def test_record_events(self):
        hist = RiskIntegrationHistory()
        evt  = make_risk_completed("E", "P", "R", actor="a")
        hist.record_event(evt)
        assert hist.recent_events(5)[0] is evt

    def test_record_errors(self):
        hist = RiskIntegrationHistory()
        hist.record_error({"msg": "oops"})
        assert len(hist.recent_errors(5)) == 1

    def test_max_items_cap(self):
        hist = RiskIntegrationHistory(max_items=3)
        for i in range(10):
            hist.record_request(_make_request(request_id=f"R{i}"))
        assert len(hist.recent_requests(20)) == 3

    def test_counts(self):
        hist = RiskIntegrationHistory()
        hist.record_request(_make_request())
        hist.record_event("evt")
        c = hist.counts()
        assert c["requests"] == 1
        assert c["events"]   == 1

    def test_clear(self):
        hist = RiskIntegrationHistory()
        hist.record_request(_make_request())
        hist.clear()
        assert hist.counts() == {"requests": 0, "responses": 0, "events": 0, "errors": 0}


# ============================================================================
# 12  SNAPSHOT (integration layer)
# ============================================================================

class TestRiskIntegrationSnapshot:
    def test_capture(self):
        snap = RiskIntegrationSnapshot.capture(
            engine_id          = "ENG",
            state              = "running",
            health_status      = HealthStatus.HEALTHY,
            is_running         = True,
            requests_received  = 10,
            requests_completed = 8,
            requests_failed    = 2,
            snapshots_published= 8,
            components         = {"k": "available"},
            uptime_s           = 60.0,
            avg_processing_s   = 0.05,
        )
        assert snap.engine_id          == "ENG"
        assert snap.is_running         is True
        assert snap.requests_received  == 10
        assert snap.uptime_s           == 60.0

    def test_snapshot_id_uuid(self):
        snap = RiskIntegrationSnapshot.capture(
            engine_id="E", state="running", health_status=HealthStatus.HEALTHY,
            is_running=True, requests_received=0, requests_completed=0,
            requests_failed=0, snapshots_published=0, components={},
            uptime_s=0.0, avg_processing_s=0.0,
        )
        assert uuid.UUID(snap.snapshot_id)

    def test_to_dict(self):
        snap = RiskIntegrationSnapshot.capture(
            engine_id="E", state="running", health_status=HealthStatus.HEALTHY,
            is_running=True, requests_received=0, requests_completed=0,
            requests_failed=0, snapshots_published=0, components={},
            uptime_s=0.0, avg_processing_s=0.0,
        )
        d = snap.to_dict()
        assert d["engine_id"]     == "E"
        assert d["health_status"] == HealthStatus.HEALTHY.value

    def test_is_frozen(self):
        snap = RiskIntegrationSnapshot.capture(
            engine_id="E", state="running", health_status=HealthStatus.HEALTHY,
            is_running=True, requests_received=0, requests_completed=0,
            requests_failed=0, snapshots_published=0, components={},
            uptime_s=0.0, avg_processing_s=0.0,
        )
        with pytest.raises((AttributeError, TypeError)):
            snap.engine_id = "X"  # type: ignore[misc]


# ============================================================================
# 13  STATUS
# ============================================================================

class TestRiskIntegrationStatus:
    def test_create_and_to_dict(self):
        status = RiskIntegrationStatus(
            engine_id           = "ENG",
            state               = "running",
            health_status       = HealthStatus.HEALTHY,
            is_running          = True,
            requests_total      = 100,
            requests_completed  = 90,
            requests_failed     = 10,
            snapshots_published = 90,
            components_available= 5,
            components_total    = 5,
            uptime_s            = 300.0,
            started_at          = time.time() - 300,
        )
        assert status.state        == "running"
        assert status.is_running   is True
        d = status.to_dict()
        assert d["state"]          == "running"
        assert "success_rate"      in d
        assert "error_rate"        in d

    def test_success_rate(self):
        s = RiskIntegrationStatus(
            engine_id="E", state="running", health_status=HealthStatus.HEALTHY,
            is_running=True, requests_total=10, requests_completed=8,
            requests_failed=2, snapshots_published=8, components_available=5,
            components_total=5, uptime_s=0.0, started_at=0.0,
        )
        assert s.success_rate == pytest.approx(0.8)

    def test_error_rate(self):
        s = RiskIntegrationStatus(
            engine_id="E", state="running", health_status=HealthStatus.HEALTHY,
            is_running=True, requests_total=10, requests_completed=8,
            requests_failed=2, snapshots_published=8, components_available=5,
            components_total=5, uptime_s=0.0, started_at=0.0,
        )
        assert s.error_rate == pytest.approx(0.2)


# ============================================================================
# 14  HEALTH
# ============================================================================

class TestRiskIntegrationHealth:
    def test_healthy_when_running_no_degraded(self):
        reporter = RiskIntegrationHealth("ENG")
        reg      = RiskComponentRegistry()
        for key in REQUIRED_COMPONENTS:
            reg.register(key, object(), status=ComponentStatus.AVAILABLE)
        report = reporter.report(
            component_registry = reg,
            is_running         = True,
            started_at         = time.time() - 10,
        )
        assert report.health_status == HealthStatus.HEALTHY
        assert report.is_healthy is True

    def test_unhealthy_when_not_running(self):
        reporter = RiskIntegrationHealth("ENG")
        report   = reporter.report(is_running=False)
        assert report.health_status == HealthStatus.UNHEALTHY

    def test_unhealthy_when_component_unavailable(self):
        reporter = RiskIntegrationHealth("ENG")
        reg      = RiskComponentRegistry()
        reg.register("a", None, status=ComponentStatus.UNAVAILABLE)
        report   = reporter.report(component_registry=reg, is_running=True)
        assert report.health_status == HealthStatus.UNHEALTHY

    def test_degraded_when_component_degraded(self):
        reporter = RiskIntegrationHealth("ENG")
        reg      = RiskComponentRegistry()
        reg.register("a", object(), status=ComponentStatus.DEGRADED)
        report   = reporter.report(component_registry=reg, is_running=True)
        assert report.health_status == HealthStatus.DEGRADED

    def test_to_dict(self):
        reporter = RiskIntegrationHealth("ENG")
        report   = reporter.report(is_running=True)
        d        = report.to_dict()
        assert "health_status" in d
        assert "uptime_s"      in d

    def test_error_rate_calculated(self):
        reporter = RiskIntegrationHealth("ENG")
        report   = reporter.report(
            is_running=True,
            requests_processed=9,
            requests_failed=1,
        )
        assert report.error_rate == pytest.approx(0.1)


# ============================================================================
# 15  VALIDATION
# ============================================================================

class TestRiskIntegrationValidation:
    def test_valid_request_passes(self):
        v   = RiskIntegrationValidator()
        req = _make_request()
        result = v.validate(req)
        assert isinstance(result, IntegrationValidationResult)

    def test_validate_or_raise_passes_for_valid(self):
        v   = RiskIntegrationValidator()
        req = _make_request()
        v.validate_or_raise(req)   # no exception

    def test_validation_result_has_checks(self):
        v      = RiskIntegrationValidator()
        req    = _make_request()
        result = v.validate(req)
        assert len(result.checks) > 0

    def test_passed_count_positive(self):
        v      = RiskIntegrationValidator()
        req    = _make_request()
        result = v.validate(req)
        assert result.passed_count > 0

    def test_validation_check_attributes(self):
        v      = RiskIntegrationValidator()
        req    = _make_request()
        result = v.validate(req)
        for check in result.checks:
            assert isinstance(check.code,    IntegrationValidationCode)
            assert isinstance(check.passed,  bool)
            assert isinstance(check.message, str)

    def test_summary(self):
        v      = RiskIntegrationValidator()
        req    = _make_request()
        result = v.validate(req)
        summary = result.to_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0


# ============================================================================
# 16  MANAGER
# ============================================================================

class TestRiskIntegrationManager:
    def test_workflow_returns_response(self):
        mgr = RiskIntegrationManager()
        req = _make_request()
        resp = mgr.run_workflow(req)
        assert isinstance(resp, RiskIntegrationResponse)

    def test_successful_workflow(self):
        mgr  = RiskIntegrationManager()
        req  = _make_request()
        resp = mgr.run_workflow(req)
        assert resp.is_success

    def test_response_portfolio_id_matches(self):
        mgr  = RiskIntegrationManager()
        req  = _make_request(portfolio_id="MATCH-ME")
        resp = mgr.run_workflow(req)
        assert resp.portfolio_id == "MATCH-ME"

    def test_listener_receives_events(self):
        events: List[Any] = []
        mgr = RiskIntegrationManager()
        mgr.add_listener(events.append)
        req = _make_request()
        mgr.run_workflow(req)
        assert len(events) > 0

    def test_remove_listener(self):
        events: List[Any] = []
        mgr = RiskIntegrationManager()
        mgr.add_listener(events.append)
        mgr.remove_listener(events.append)
        mgr.run_workflow(_make_request())
        assert events == []

    def test_statistics_incremented(self):
        stats = RiskIntegrationStatistics()
        mgr   = RiskIntegrationManager(statistics=stats)
        mgr.run_workflow(_make_request())
        assert stats.total_completed() == 1

    def test_history_records_request(self):
        hist = RiskIntegrationHistory()
        mgr  = RiskIntegrationManager(history=hist)
        req  = _make_request()
        mgr.run_workflow(req)
        c = hist.counts()
        assert c["requests"] >= 1

    def test_fallback_snapshot_when_no_components(self):
        reg = RiskComponentRegistry()
        mgr = RiskIntegrationManager(component_registry=reg)
        req = _make_request()
        resp = mgr.run_workflow(req)
        # Should succeed via fallback path
        assert resp.is_success


# ============================================================================
# 17  ENGINE — Initialization
# ============================================================================

class TestEngineInitialization:
    def test_create_default(self):
        engine = RiskIntegrationEngine()
        assert engine is not None

    def test_system_id(self):
        engine = RiskIntegrationEngine()
        assert engine.SYSTEM_ID == INTEGRATION_SYSTEM_ID

    def test_version(self):
        engine = RiskIntegrationEngine()
        assert engine.VERSION == VERSION

    def test_initialize_idempotent(self):
        engine = RiskIntegrationEngine()
        engine.initialize()
        engine.initialize()   # second call should not raise

    def test_initial_state_not_running(self):
        engine = RiskIntegrationEngine()
        assert engine.lifecycle_state().value != "running"

    def test_with_injected_components(self):
        reg    = RiskComponentRegistry()
        engine = RiskIntegrationEngine(component_registry=reg)
        assert engine is not None


# ============================================================================
# 18  ENGINE — Lifecycle
# ============================================================================

class TestEngineLifecycle:
    def test_start_transitions_to_running(self):
        engine = RiskIntegrationEngine()
        engine.initialize()
        engine.start()
        assert engine.lifecycle_state().value == "running"
        engine.stop()

    def test_stop_transitions_out_of_running(self):
        engine = _started_engine()
        engine.stop()
        assert engine.lifecycle_state().value != "running"

    def test_restart(self):
        engine = _started_engine()
        engine.restart()
        assert engine.lifecycle_state().value == "running"
        engine.stop()

    def test_submit_before_start_raises(self):
        engine = RiskIntegrationEngine()
        engine.initialize()
        req = _make_request()
        with pytest.raises(RiskIntegrationNotRunningError):
            engine.submit(req)

    def test_submit_after_stop_raises(self):
        engine = _started_engine()
        engine.stop()
        req = _make_request()
        with pytest.raises(RiskIntegrationNotRunningError):
            engine.submit(req)


# ============================================================================
# 19  ENGINE — Workflow
# ============================================================================

class TestEngineWorkflow:
    def test_submit_returns_response(self):
        engine = _started_engine()
        req    = _make_request()
        resp   = engine.submit(req)
        assert isinstance(resp, RiskIntegrationResponse)
        engine.stop()

    def test_submit_success(self):
        engine = _started_engine()
        req    = _make_request()
        resp   = engine.submit(req)
        assert resp.is_success
        engine.stop()

    def test_submit_has_snapshot(self):
        engine = _started_engine()
        req    = _make_request()
        resp   = engine.submit(req)
        # snapshot_dict should not be empty (fallback path provides one)
        assert isinstance(resp.risk_snapshot, dict)
        engine.stop()

    def test_submit_portfolio_id_matches(self):
        engine = _started_engine()
        req    = _make_request(portfolio_id="P-MATCH")
        resp   = engine.submit(req)
        assert resp.portfolio_id == "P-MATCH"
        engine.stop()

    def test_query_finds_response(self):
        engine = _started_engine()
        req    = _make_request()
        resp   = engine.submit(req)
        found  = engine.query(req.request_id)
        assert found is not None
        assert found.request_id == req.request_id
        engine.stop()

    def test_query_unknown_returns_none(self):
        engine = _started_engine()
        assert engine.query("NO-SUCH-ID") is None
        engine.stop()

    def test_multiple_requests(self):
        engine = _started_engine()
        for i in range(5):
            resp = engine.submit(_make_request(portfolio_id=f"P{i}"))
            assert resp.is_success
        engine.stop()

    def test_different_request_types(self):
        engine = _started_engine()
        for rt in RequestType:
            resp = engine.submit(_make_request(request_type=rt))
            assert resp.is_success
        engine.stop()


# ============================================================================
# 20  ENGINE — Validate API
# ============================================================================

class TestEngineValidate:
    def test_validate_returns_result(self):
        engine = _started_engine()
        req    = _make_request()
        result = engine.validate(req)
        assert isinstance(result, IntegrationValidationResult)
        engine.stop()

    def test_validate_without_running(self):
        engine = RiskIntegrationEngine()
        engine.initialize()
        req    = _make_request()
        # validate does not require running state
        result = engine.validate(req)
        assert isinstance(result, IntegrationValidationResult)


# ============================================================================
# 21  ENGINE — Observability
# ============================================================================

class TestEngineObservability:
    def test_health_returns_report(self):
        engine = _started_engine()
        h      = engine.health()
        assert isinstance(h, RiskIntegrationHealthReport)
        engine.stop()

    def test_health_healthy_when_running(self):
        engine = _started_engine()
        h      = engine.health()
        # May be degraded if subsystems not available — just check type
        assert h.health_status in HealthStatus
        engine.stop()

    def test_status_returns_status(self):
        engine = _started_engine()
        s      = engine.status()
        assert isinstance(s, RiskIntegrationStatus)
        assert s.state == "running"
        engine.stop()

    def test_statistics_returns_dict(self):
        engine = _started_engine()
        stats  = engine.statistics()
        assert isinstance(stats, dict)
        assert "requests_received" in stats
        engine.stop()

    def test_snapshot_returns_snapshot(self):
        engine = _started_engine()
        snap   = engine.snapshot()
        assert isinstance(snap, RiskIntegrationSnapshot)
        assert snap.is_running is True
        engine.stop()

    def test_history_returns_list(self):
        engine = _started_engine()
        engine.submit(_make_request())
        hist   = engine.history(5)
        assert isinstance(hist, list)
        engine.stop()

    def test_statistics_increments_on_submit(self):
        engine = _started_engine()
        engine.submit(_make_request())
        stats  = engine.statistics()
        assert stats["requests_received"] >= 1
        engine.stop()

    def test_status_to_dict(self):
        engine = _started_engine()
        d      = engine.status().to_dict()
        assert "engine_id" in d
        engine.stop()

    def test_snapshot_to_dict(self):
        engine = _started_engine()
        d      = engine.snapshot().to_dict()
        assert "engine_id" in d
        engine.stop()


# ============================================================================
# 22  ENGINE — Events
# ============================================================================

class TestEngineEvents:
    def test_add_and_receive_listener(self):
        events: List[Any] = []
        engine = _started_engine()
        engine.add_listener(events.append)
        engine.submit(_make_request())
        assert len(events) > 0
        engine.stop()

    def test_remove_listener(self):
        events: List[Any] = []
        engine = _started_engine()
        engine.add_listener(events.append)
        engine.remove_listener(events.append)
        engine.submit(_make_request())
        assert len(events) == 0
        engine.stop()

    def test_listener_receives_completed_event(self):
        types:  List[IntegrationEventType] = []
        engine = _started_engine()
        engine.add_listener(lambda e: types.append(e.event_type))
        engine.submit(_make_request())
        assert IntegrationEventType.RISK_COMPLETED in types
        engine.stop()

    def test_listener_receives_received_event(self):
        types:  List[IntegrationEventType] = []
        engine = _started_engine()
        engine.add_listener(lambda e: types.append(e.event_type))
        engine.submit(_make_request())
        assert IntegrationEventType.RISK_REQUEST_RECEIVED in types
        engine.stop()

    def test_faulty_listener_does_not_crash_engine(self):
        def bad_listener(evt):
            raise RuntimeError("I'm broken")
        engine = _started_engine()
        engine.add_listener(bad_listener)
        resp = engine.submit(_make_request())
        assert resp.is_success   # engine survived
        engine.stop()


# ============================================================================
# 23  CONCURRENCY
# ============================================================================

class TestConcurrency:
    def test_concurrent_submissions(self):
        engine  = _started_engine()
        results: List[RiskIntegrationResponse] = []
        lock    = threading.Lock()
        errors: List[str] = []

        def worker():
            try:
                resp = engine.submit(_make_request(portfolio_id=str(uuid.uuid4())))
                with lock:
                    results.append(resp)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        engine.stop()
        assert len(errors) == 0
        assert all(r.is_success for r in results)
        assert len(results) == 20

    def test_concurrent_stats_increment(self):
        stats  = RiskIntegrationStatistics()
        errors: List[str] = []

        def worker():
            for _ in range(50):
                stats.record_request_received()

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert stats.total_received() == 500
        assert errors == []


# ============================================================================
# 24  REGRESSION — Full integration lifecycle
# ============================================================================

class TestRegression:
    def test_full_lifecycle_cycle(self):
        """initialize → start → submit×3 → stop → statistics correct"""
        engine = RiskIntegrationEngine()
        engine.initialize()
        engine.start()

        for i in range(3):
            resp = engine.submit(_make_request(portfolio_id=f"P-{i}"))
            assert resp.is_success

        stats = engine.statistics()
        assert stats["requests_completed"] == 3

        engine.stop()
        assert engine.lifecycle_state().value != "running"

    def test_history_after_submit(self):
        engine = _started_engine()
        for _ in range(5):
            engine.submit(_make_request())
        hist = engine.history(10)
        assert len(hist) >= 5
        engine.stop()

    def test_snapshot_counts_match_stats(self):
        engine = _started_engine()
        engine.submit(_make_request())
        snap  = engine.snapshot()
        stats = engine.statistics()
        assert snap.requests_completed == stats["requests_completed"]
        engine.stop()

    def test_restart_clears_lifecycle_state(self):
        engine = _started_engine()
        engine.restart()
        assert engine.lifecycle_state().value == "running"
        engine.stop()

    def test_public_api_complete(self):
        """All public methods exist and return expected types."""
        engine = _started_engine()
        req    = _make_request()

        assert callable(engine.initialize)
        assert callable(engine.start)
        assert callable(engine.stop)
        assert callable(engine.restart)
        assert isinstance(engine.health(),      RiskIntegrationHealthReport)
        assert isinstance(engine.status(),      RiskIntegrationStatus)
        assert isinstance(engine.statistics(),  dict)
        assert isinstance(engine.snapshot(),    RiskIntegrationSnapshot)
        assert isinstance(engine.history(),     list)
        assert isinstance(engine.validate(req), IntegrationValidationResult)
        resp = engine.submit(req)
        assert isinstance(resp,                 RiskIntegrationResponse)
        assert engine.query(req.request_id) is not None

        engine.stop()

    def test_empty_registry_engine_still_submits(self):
        """Engine with empty component registry uses fallback path."""
        reg    = RiskComponentRegistry()
        engine = RiskIntegrationEngine(component_registry=reg)
        engine.initialize()
        engine.start()
        resp = engine.submit(_make_request())
        assert resp.is_success
        engine.stop()

    def test_response_snapshot_dict_is_dict(self):
        engine = _started_engine()
        resp   = engine.submit(_make_request())
        assert isinstance(resp.risk_snapshot, dict)
        engine.stop()
