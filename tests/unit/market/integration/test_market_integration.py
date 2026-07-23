"""
test_market_integration.py — tests/unit/market/integration
===========================================================
Comprehensive test suite for iios.market.integration (C12 M6).

Coverage targets: ≥ 95%

Test categories:
  1  Constants
  2  Exceptions
  3  MarketIntegrationContext
  4  MarketIntegrationRequest
  5  MarketIntegrationResponse
  6  MarketIntegrationSnapshot (integration-level)
  7  MarketIntegrationValidation
  8  MarketIntegrationHealth
  9  MarketIntegrationStatus
 10  MarketIntegrationStatistics
 11  MarketIntegrationHistory
 12  MarketIntegrationEvents
 13  MarketIntegrationRegistry
 14  MarketComponentRegistry
 15  MarketComponentFactory (unit, no subsystem start)
 16  MarketIntegrationEngine — lifecycle
 17  MarketIntegrationEngine — submit workflow
 18  MarketIntegrationEngine — public API
 19  MarketIntegrationEngine — concurrency
 20  Public surface (__all__)
 21  Regression: no internal subsystem exposed
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from iios.market.integration import (
    # Primary
    MarketIntegrationEngine,
    # Requests
    MarketIntegrationContext,
    MarketIntegrationRequest,
    # Responses
    MarketIntegrationResponse,
    MarketIntegrationSnapshot,
    MarketIntegrationStatus,
    # Validation
    IntegrationCheckResult,
    MarketIntegrationValidation,
    MarketIntegrationValidationResult,
    # Infrastructure
    MarketIntegrationHealth,
    MarketIntegrationHistory,
    MarketIntegrationRegistry,
    MarketIntegrationStatistics,
    # Components
    MarketComponentFactory,
    MarketComponentRegistry,
    # Events
    MarketIntegrationEvent,
    market_completed_event,
    market_failed_event,
    market_integration_started_event,
    market_integration_stopped_event,
    market_request_received_event,
    market_snapshot_published_event,
    market_validated_event,
    # Exceptions
    MarketIntegrationCapacityError,
    MarketIntegrationConfigurationError,
    MarketIntegrationError,
    MarketIntegrationHistoryError,
    MarketIntegrationNotFoundError,
    MarketIntegrationNotRunningError,
    MarketIntegrationRequestError,
    MarketIntegrationSnapshotError,
    MarketIntegrationSubsystemError,
    MarketIntegrationValidationError,
    # Enumerations
    ComponentStatus,
    IntegrationEventType,
    IntegrationPriority,
    IntegrationRequestType,
    IntegrationStatus,
    IntegrationValidationCode,
    # Version / IDs
    INTEGRATION_SYSTEM_ID,
    VERSION,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _request(
    exchange:     str = "NSE",
    request_type: IntegrationRequestType = IntegrationRequestType.MARKET_OVERVIEW,
    **kwargs: Any,
) -> MarketIntegrationRequest:
    return MarketIntegrationRequest.create(exchange, request_type, **kwargs)


def _engine_no_components() -> MarketIntegrationEngine:
    """Engine that does NOT create subsystem instances (faster tests)."""
    e = MarketIntegrationEngine()
    e.initialize(create_components=False)
    e.start()
    return e


def _engine_no_components_stopped() -> MarketIntegrationEngine:
    """Initialized but not started."""
    e = MarketIntegrationEngine()
    e.initialize(create_components=False)
    return e


# ===========================================================================
# 1. Constants
# ===========================================================================

class TestConstants:
    def test_version(self):
        assert VERSION == "1.0.0"

    def test_integration_system_id(self):
        assert "integration" in INTEGRATION_SYSTEM_ID

    def test_request_type_count(self):
        assert len(IntegrationRequestType) == 10

    def test_status_values(self):
        assert IntegrationStatus.COMPLETED.value == "completed"
        assert IntegrationStatus.FAILED.value    == "failed"
        assert IntegrationStatus.REJECTED.value  == "rejected"

    def test_event_type_count(self):
        assert len(IntegrationEventType) == 7

    def test_validation_code_count(self):
        assert len(IntegrationValidationCode) == 6

    def test_priority_values(self):
        assert IntegrationPriority.NORMAL.value == "normal"
        assert IntegrationPriority.HIGH.value   == "high"

    def test_component_status_values(self):
        assert ComponentStatus.AVAILABLE.value   == "available"
        assert ComponentStatus.UNAVAILABLE.value == "unavailable"
        assert ComponentStatus.UNKNOWN.value     == "unknown"


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(MarketIntegrationError, IIOSError)

    def test_not_running_error(self):
        e = MarketIntegrationNotRunningError()
        assert "MI-001" in e.error_code

    def test_request_error(self):
        e = MarketIntegrationRequestError("bad", request_id="r1")
        assert e.request_id == "r1"
        assert "MI-002" in e.error_code

    def test_validation_error(self):
        e = MarketIntegrationValidationError("fail", request_id="r1")
        assert e.request_id == "r1"
        assert "MI-003" in e.error_code

    def test_not_found_error(self):
        e = MarketIntegrationNotFoundError("id-1")
        assert e.integration_id == "id-1"
        assert "MI-004" in e.error_code

    def test_subsystem_error(self):
        e = MarketIntegrationSubsystemError("fail", subsystem="engine")
        assert e.subsystem == "engine"
        assert "MI-005" in e.error_code

    def test_capacity_error(self):
        e = MarketIntegrationCapacityError(limit=1000)
        assert e.limit == 1000
        assert "MI-006" in e.error_code

    def test_configuration_error(self):
        assert "MI-007" in MarketIntegrationConfigurationError("x").error_code

    def test_snapshot_error(self):
        assert "MI-008" in MarketIntegrationSnapshotError("x").error_code

    def test_history_error(self):
        assert "MI-009" in MarketIntegrationHistoryError("x").error_code


# ===========================================================================
# 3. MarketIntegrationContext
# ===========================================================================

class TestMarketIntegrationContext:
    def test_create_defaults(self):
        ctx = MarketIntegrationContext.create("NSE")
        assert ctx.exchange          == "NSE"
        assert ctx.market_type       == "equity"
        assert ctx.enable_analytics  is True
        assert ctx.enable_policy     is True
        assert ctx.priority          == IntegrationPriority.NORMAL
        assert ctx.timeout_s         == 60.0

    def test_create_custom(self):
        ctx = MarketIntegrationContext.create(
            "BSE",
            request_type  = IntegrationRequestType.REGIME_ANALYSIS
                            if hasattr(IntegrationRequestType, "REGIME_ANALYSIS")
                            else IntegrationRequestType.MARKET_REGIME_ANALYSIS,
            priority      = IntegrationPriority.HIGH,
            enable_policy = False,
            timeout_s     = 30.0,
        )
        assert ctx.exchange       == "BSE"
        assert ctx.priority       == IntegrationPriority.HIGH
        assert ctx.enable_policy  is False

    def test_to_dict_keys(self):
        d = MarketIntegrationContext.create("NSE").to_dict()
        for k in ("context_id", "exchange", "request_type", "priority",
                  "enable_analytics", "enable_policy", "timeout_s"):
            assert k in d

    def test_immutable(self):
        ctx = MarketIntegrationContext.create("NSE")
        with pytest.raises((AttributeError, TypeError)):
            ctx.exchange = "BSE"  # type: ignore[misc]


# ===========================================================================
# 4. MarketIntegrationRequest
# ===========================================================================

class TestMarketIntegrationRequest:
    def test_create(self):
        req = _request()
        assert req.exchange     == "NSE"
        assert req.request_type == IntegrationRequestType.MARKET_OVERVIEW
        assert req.request_id   != ""
        assert req.framework_version == VERSION

    def test_convenience_constructors(self):
        types = [
            ("market_overview",      IntegrationRequestType.MARKET_OVERVIEW),
            ("regime_analysis",      IntegrationRequestType.MARKET_REGIME_ANALYSIS),
            ("sector_analysis",      IntegrationRequestType.SECTOR_ANALYSIS),
            ("breadth_analysis",     IntegrationRequestType.BREADTH_ANALYSIS),
            ("volatility_analysis",  IntegrationRequestType.VOLATILITY_ANALYSIS),
            ("liquidity_analysis",   IntegrationRequestType.LIQUIDITY_ANALYSIS),
            ("correlation_analysis", IntegrationRequestType.CORRELATION_ANALYSIS),
            ("forecast_request",     IntegrationRequestType.FORECAST_REQUEST),
            ("snapshot_request",     IntegrationRequestType.MARKET_SNAPSHOT_REQUEST),
            ("history_request",      IntegrationRequestType.MARKET_HISTORY_REQUEST),
        ]
        for method_name, expected_type in types:
            method = getattr(MarketIntegrationRequest, method_name)
            req    = method("NSE")
            assert req.request_type == expected_type, f"Failed for {method_name}"

    def test_with_inputs(self):
        req  = _request()
        req2 = req.with_inputs({"index_prices": {"NIFTY": [100.0, 101.0]}})
        assert "index_prices" in req2.inputs
        assert req.inputs == {}  # original unchanged

    def test_to_dict(self):
        d = _request().to_dict()
        for k in ("request_id", "integration_id", "exchange",
                  "request_type", "priority", "framework_version"):
            assert k in d

    def test_auto_market_analysis_id(self):
        req = _request()
        assert len(req.market_analysis_id) > 0

    def test_custom_market_analysis_id(self):
        req = _request(market_analysis_id="ma-custom")
        assert req.market_analysis_id == "ma-custom"

    def test_immutable(self):
        req = _request()
        with pytest.raises((AttributeError, TypeError)):
            req.exchange = "BSE"  # type: ignore[misc]


# ===========================================================================
# 5. MarketIntegrationResponse
# ===========================================================================

class TestMarketIntegrationResponse:
    def test_create_success(self):
        r = MarketIntegrationResponse.create_success(
            request_id     = "req-1",
            integration_id = "int-1",
            exchange       = "NSE",
            request_type   = IntegrationRequestType.MARKET_OVERVIEW,
            snapshot_id    = "snap-1",
            elapsed_s      = 0.15,
        )
        assert r.is_successful is True
        assert r.is_failed     is False
        assert r.is_rejected   is False
        assert r.has_snapshot  is True
        assert r.snapshot_id   == "snap-1"

    def test_create_failure(self):
        r = MarketIntegrationResponse.create_failure(
            request_id     = "req-1",
            integration_id = "int-1",
            exchange       = "NSE",
            request_type   = IntegrationRequestType.MARKET_OVERVIEW,
            error_message  = "timeout",
        )
        assert r.is_failed      is True
        assert r.is_successful  is False
        assert r.error_message  == "timeout"

    def test_create_rejected(self):
        r = MarketIntegrationResponse.create_rejected(
            request_id     = "req-1",
            integration_id = "int-1",
            exchange       = "NSE",
            request_type   = IntegrationRequestType.MARKET_OVERVIEW,
            reason         = "validation failed",
        )
        assert r.is_rejected  is True
        assert r.error_message == "validation failed"

    def test_to_dict(self):
        r = MarketIntegrationResponse.create_success(
            request_id     = "r",
            integration_id = "i",
            exchange       = "NSE",
            request_type   = IntegrationRequestType.MARKET_OVERVIEW,
        )
        d = r.to_dict()
        for k in ("response_id", "exchange", "status", "is_successful",
                  "elapsed_s", "framework_version"):
            assert k in d

    def test_immutable(self):
        r = MarketIntegrationResponse.create_success(
            request_id="r", integration_id="i", exchange="NSE",
            request_type=IntegrationRequestType.MARKET_OVERVIEW,
        )
        with pytest.raises((AttributeError, TypeError)):
            r.exchange = "BSE"  # type: ignore[misc]


# ===========================================================================
# 6. MarketIntegrationSnapshot (integration-level)
# ===========================================================================

class TestMarketIntegrationSnapshot:
    def test_create_defaults(self):
        s = MarketIntegrationSnapshot.create()
        assert s.lifecycle_state == "stopped"
        assert s.snapshot_id     != ""
        assert s.availability_rate == 1.0
        assert s.has_market_snapshot is False

    def test_create_with_data(self):
        s = MarketIntegrationSnapshot.create(
            integration_id     = "int-1",
            exchange           = "NSE",
            request_count      = 10,
            success_count      = 9,
            failure_count      = 1,
            market_snapshot_id = "ms-001",
        )
        assert s.availability_rate   == 0.9
        assert s.has_market_snapshot is True
        assert s.market_snapshot_id  == "ms-001"

    def test_overall_health(self):
        s = MarketIntegrationSnapshot.create(health={"overall": "healthy"})
        assert s.overall_health == "healthy"

    def test_to_dict(self):
        d = MarketIntegrationSnapshot.create(exchange="NSE").to_dict()
        for k in ("snapshot_id", "exchange", "lifecycle_state",
                  "request_count", "availability_rate", "overall_health"):
            assert k in d

    def test_immutable(self):
        s = MarketIntegrationSnapshot.create()
        with pytest.raises((AttributeError, TypeError)):
            s.exchange = "NSE"  # type: ignore[misc]


# ===========================================================================
# 7. MarketIntegrationValidation
# ===========================================================================

class TestMarketIntegrationValidation:
    def setup_method(self):
        self.v = MarketIntegrationValidation(is_running_fn=lambda: True)

    def test_valid_request_passes_all(self):
        req    = _request()
        result = self.v.validate(req)
        assert result.is_valid is True
        assert len(result.failed_checks) == 0
        assert len(result.passed_checks) == 6

    def test_empty_exchange_fails(self):
        import dataclasses
        req    = _request()
        bad    = dataclasses.replace(req, exchange="")
        result = self.v.validate(bad)
        assert result.is_valid is False
        codes  = [c.code for c in result.failed_checks]
        assert IntegrationValidationCode.LIFECYCLE_CONSISTENCY in codes

    def test_engine_not_running_fails(self):
        v      = MarketIntegrationValidation(is_running_fn=lambda: False)
        result = v.validate(_request())
        assert result.is_valid is False
        codes  = [c.code for c in result.failed_checks]
        assert IntegrationValidationCode.SUBSYSTEM_AVAILABILITY in codes

    def test_invalid_request_type_fails(self):
        import dataclasses
        req = _request()
        # Force an invalid request_type
        bad = dataclasses.replace(req, request_type="INVALID")  # type: ignore
        result = self.v.validate(bad)
        assert result.is_valid is False

    def test_validate_or_raise_valid(self):
        self.v.validate_or_raise(_request())  # should not raise

    def test_validate_or_raise_invalid(self):
        import dataclasses
        req = _request()
        bad = dataclasses.replace(req, exchange="")
        with pytest.raises(MarketIntegrationValidationError):
            self.v.validate_or_raise(bad)

    def test_failure_messages_non_empty(self):
        import dataclasses
        req    = _request()
        bad    = dataclasses.replace(req, exchange="")
        result = self.v.validate(bad)
        assert len(result.failure_messages) > 0


# ===========================================================================
# 8. MarketIntegrationHealth
# ===========================================================================

class TestMarketIntegrationHealth:
    def test_empty_registry_reports_healthy(self):
        h = MarketIntegrationHealth()
        report = h.report()
        assert report["overall"] == "healthy"
        assert "checked_at" in report

    def test_healthy_probe(self):
        h = MarketIntegrationHealth(
            component_probes={"engine": lambda: {"overall": "healthy"}}
        )
        assert h.is_healthy() is True
        assert h.report()["overall"] == "healthy"

    def test_degraded_probe_makes_overall_degraded(self):
        h = MarketIntegrationHealth(
            component_probes={"engine": lambda: {"overall": "degraded"}}
        )
        assert h.report()["overall"] == "degraded"

    def test_unhealthy_probe_makes_overall_unhealthy(self):
        h = MarketIntegrationHealth(
            component_probes={"engine": lambda: {"overall": "unhealthy"}}
        )
        assert h.report()["overall"] == "unhealthy"

    def test_probe_raises_marks_unhealthy(self):
        def bad_probe():
            raise RuntimeError("boom")
        h = MarketIntegrationHealth(component_probes={"engine": bad_probe})
        assert h.report()["overall"] == "unhealthy"

    def test_register_probe(self):
        h = MarketIntegrationHealth()
        h.register_probe("new", lambda: {"overall": "healthy"})
        assert h.component_status("new") == "healthy"

    def test_unknown_component_returns_unknown(self):
        h = MarketIntegrationHealth()
        assert h.component_status("ghost") == "unknown"

    def test_multiple_probes_mixed(self):
        h = MarketIntegrationHealth(
            component_probes={
                "a": lambda: {"overall": "healthy"},
                "b": lambda: {"overall": "degraded"},
            }
        )
        assert h.report()["overall"] == "degraded"


# ===========================================================================
# 9. MarketIntegrationStatus
# ===========================================================================

class TestMarketIntegrationStatus:
    def _make_status(self, **kwargs) -> MarketIntegrationStatus:
        defaults = dict(
            engine_id             = INTEGRATION_SYSTEM_ID,
            lifecycle_state       = "running",
            request_count         = 10,
            success_count         = 9,
            failure_count         = 1,
            rejection_count       = 0,
            snapshot_publications = 5,
            subsystem_states      = {"engine": "available"},
            health                = {"overall": "healthy"},
            statistics            = {},
            started_at            = time.time() - 100,
            captured_at           = time.time(),
            framework_version     = VERSION,
        )
        defaults.update(kwargs)
        return MarketIntegrationStatus(**defaults)

    def test_is_running_true(self):
        s = self._make_status(lifecycle_state="running")
        assert s.is_running is True

    def test_is_running_false(self):
        s = self._make_status(lifecycle_state="stopped")
        assert s.is_running is False

    def test_availability_rate(self):
        s = self._make_status(request_count=10, success_count=8)
        assert s.availability_rate == 0.8

    def test_availability_rate_no_requests(self):
        s = self._make_status(request_count=0)
        assert s.availability_rate == 1.0

    def test_overall_health(self):
        s = self._make_status(health={"overall": "degraded"})
        assert s.overall_health == "degraded"

    def test_to_dict(self):
        d = self._make_status().to_dict()
        for k in ("engine_id", "lifecycle_state", "request_count",
                  "availability_rate", "overall_health", "framework_version"):
            assert k in d


# ===========================================================================
# 10. MarketIntegrationStatistics
# ===========================================================================

class TestMarketIntegrationStatistics:
    def test_initial_zeros(self):
        s = MarketIntegrationStatistics()
        snap = s.snapshot()
        assert snap["requests_processed"] == 0

    def test_increment_counters(self):
        s = MarketIntegrationStatistics()
        s.record_request_received()
        s.record_request_received()
        s.record_request_succeeded()
        s.record_request_failed()
        s.record_request_rejected()
        s.record_snapshot_published()
        s.record_validation_failure()
        snap = s.snapshot()
        assert snap["requests_processed"]    == 2
        assert snap["successful_requests"]   == 1
        assert snap["failed_requests"]       == 1
        assert snap["rejected_requests"]     == 1
        assert snap["snapshot_publications"] == 1
        assert snap["validation_failures"]   == 1

    def test_elapsed_average(self):
        s = MarketIntegrationStatistics()
        s.record_elapsed(0.1)
        s.record_elapsed(0.3)
        assert abs(s.snapshot()["average_processing_s"] - 0.2) < 0.01

    def test_api_utilization(self):
        s = MarketIntegrationStatistics()
        s.record_api_call("submit")
        s.record_api_call("submit")
        s.record_api_call("status")
        snap = s.snapshot()
        assert snap["api_utilization"]["submit"] == 2
        assert snap["api_utilization"]["status"] == 1

    def test_availability_rate(self):
        s = MarketIntegrationStatistics()
        for _ in range(3):
            s.record_request_received()
            s.record_request_succeeded()
        s.record_request_received()
        s.record_request_failed()
        snap = s.snapshot()
        assert abs(snap["subsystem_availability"] - 0.75) < 0.01

    def test_reset(self):
        s = MarketIntegrationStatistics()
        s.record_request_received()
        s.reset()
        assert s.snapshot()["requests_processed"] == 0


# ===========================================================================
# 11. MarketIntegrationHistory
# ===========================================================================

class TestMarketIntegrationHistory:
    def test_record_and_retrieve(self):
        h = MarketIntegrationHistory()
        h.record_request("req1")
        h.record_response("res1")
        h.record_event("ev1")
        h.record_error("err1")
        counts = h.counts()
        assert counts["requests"]  == 1
        assert counts["responses"] == 1
        assert counts["events"]    == 1
        assert counts["errors"]    == 1

    def test_bounded_capacity(self):
        h = MarketIntegrationHistory(max_entries=3)
        for i in range(10):
            h.record_request(i)
        assert h.counts()["requests"] == 3

    def test_recent_n(self):
        h = MarketIntegrationHistory()
        for i in range(20):
            h.record_request(i)
        assert len(h.recent_requests(5)) == 5

    def test_clear(self):
        h = MarketIntegrationHistory()
        h.record_request("x")
        h.clear()
        assert all(v == 0 for v in h.counts().values())


# ===========================================================================
# 12. Events
# ===========================================================================

class TestMarketIntegrationEvents:
    _kwargs = dict(integration_id="int-1", exchange="NSE", actor="test")

    def test_started_event(self):
        ev = market_integration_started_event(**self._kwargs)
        assert ev.event_type  == IntegrationEventType.MARKET_INTEGRATION_STARTED
        assert ev.exchange    == "NSE"
        assert ev.event_id    != ""

    def test_all_factories(self):
        factories = [
            market_request_received_event,
            market_validated_event,
            market_snapshot_published_event,
            market_completed_event,
            market_failed_event,
            market_integration_stopped_event,
        ]
        for fn in factories:
            ev = fn(**self._kwargs)
            assert isinstance(ev, MarketIntegrationEvent)

    def test_event_payload(self):
        ev = market_failed_event(**self._kwargs, reason="timeout")
        assert ev.payload.get("reason") == "timeout"

    def test_event_to_dict(self):
        ev = market_completed_event(**self._kwargs)
        d  = ev.to_dict()
        assert "event_id"   in d
        assert "event_type" in d
        assert "source"     in d
        assert INTEGRATION_SYSTEM_ID in d["source"]

    def test_event_immutable(self):
        ev = market_completed_event(**self._kwargs)
        with pytest.raises((AttributeError, TypeError)):
            ev.exchange = "BSE"  # type: ignore[misc]


# ===========================================================================
# 13. MarketIntegrationRegistry
# ===========================================================================

class TestMarketIntegrationRegistry:
    def _response(self, suffix: str = "1") -> MarketIntegrationResponse:
        return MarketIntegrationResponse.create_success(
            request_id     = f"req-{suffix}",
            integration_id = f"int-{suffix}",
            exchange       = "NSE",
            request_type   = IntegrationRequestType.MARKET_OVERVIEW,
        )

    def test_register_and_get(self):
        reg = MarketIntegrationRegistry()
        r   = self._response()
        reg.register(r)
        assert reg.get(r.response_id) is r

    def test_get_or_raise_missing(self):
        reg = MarketIntegrationRegistry()
        with pytest.raises(MarketIntegrationNotFoundError):
            reg.get_or_raise("ghost")

    def test_evicts_oldest_at_capacity(self):
        reg = MarketIntegrationRegistry(max_entries=2)
        r1, r2, r3 = [self._response(str(i)) for i in range(3)]
        reg.register(r1)
        reg.register(r2)
        reg.register(r3)
        assert reg.get(r1.response_id) is None
        assert reg.get(r3.response_id) is r3

    def test_by_exchange(self):
        reg = MarketIntegrationRegistry()
        reg.register(self._response("1"))
        reg.register(self._response("2"))
        results = reg.by_exchange("NSE")
        assert len(results) == 2

    def test_by_status(self):
        reg = MarketIntegrationRegistry()
        reg.register(self._response("a"))
        f = MarketIntegrationResponse.create_failure(
            request_id="req-b", integration_id="int-b",
            exchange="NSE", request_type=IntegrationRequestType.MARKET_OVERVIEW,
        )
        reg.register(f)
        assert len(reg.by_status(IntegrationStatus.COMPLETED)) == 1
        assert len(reg.by_status(IntegrationStatus.FAILED))    == 1

    def test_latest_for_exchange(self):
        reg = MarketIntegrationRegistry()
        r1  = self._response("1")
        r2  = self._response("2")
        reg.register(r1)
        reg.register(r2)
        assert reg.latest_for_exchange("NSE") is r2

    def test_remove(self):
        reg = MarketIntegrationRegistry()
        r   = self._response()
        reg.register(r)
        assert reg.remove(r.response_id) is True
        assert reg.count() == 0

    def test_query_predicate(self):
        reg = MarketIntegrationRegistry()
        reg.register(self._response("1"))
        results = reg.query(lambda r: r.exchange == "NSE")
        assert len(results) == 1

    def test_clear(self):
        reg = MarketIntegrationRegistry()
        reg.register(self._response())
        reg.clear()
        assert reg.count() == 0

    def test_exists(self):
        reg = MarketIntegrationRegistry()
        r   = self._response()
        reg.register(r)
        assert reg.exists(r.response_id) is True
        assert reg.exists("ghost")       is False


# ===========================================================================
# 14. MarketComponentRegistry
# ===========================================================================

class TestMarketComponentRegistry:
    def test_register_and_get(self):
        reg = MarketComponentRegistry()
        obj = object()
        reg.register("engine", obj)
        assert reg.get("engine") is obj

    def test_is_registered(self):
        reg = MarketComponentRegistry()
        assert reg.is_registered("x") is False
        reg.register("x", object())
        assert reg.is_registered("x") is True

    def test_is_available(self):
        reg = MarketComponentRegistry()
        reg.register("engine", object())
        assert reg.is_available("engine") is True

    def test_set_status(self):
        reg = MarketComponentRegistry()
        reg.register("engine", object())
        reg.set_status("engine", ComponentStatus.DEGRADED)
        assert reg.status("engine") == ComponentStatus.DEGRADED
        assert reg.is_available("engine") is False

    def test_unknown_component_returns_unknown(self):
        reg = MarketComponentRegistry()
        assert reg.status("ghost") == ComponentStatus.UNKNOWN

    def test_unregister(self):
        reg = MarketComponentRegistry()
        reg.register("x", object())
        assert reg.unregister("x") is True
        assert reg.is_registered("x") is False

    def test_unregister_missing(self):
        assert MarketComponentRegistry().unregister("ghost") is False

    def test_health_summary(self):
        reg = MarketComponentRegistry()
        reg.register("a", object())
        reg.register("b", object())
        reg.set_status("b", ComponentStatus.DEGRADED)
        h = reg.health_summary()
        assert h["a"] == "available"
        assert h["b"] == "degraded"

    def test_all_names(self):
        reg = MarketComponentRegistry()
        reg.register("x", object())
        reg.register("y", object())
        assert set(reg.all_names()) == {"x", "y"}

    def test_count(self):
        reg = MarketComponentRegistry()
        reg.register("a", object())
        assert reg.count() == 1

    def test_clear(self):
        reg = MarketComponentRegistry()
        reg.register("a", object())
        reg.clear()
        assert reg.count() == 0


# ===========================================================================
# 15. MarketComponentFactory (unit, no subsystem start)
# ===========================================================================

class TestMarketComponentFactory:
    def test_create_snapshot_registry(self):
        factory = MarketComponentFactory()
        sr = factory.create_snapshot_registry()
        from iios.market.snapshot import MarketSnapshotRegistry
        assert isinstance(sr, MarketSnapshotRegistry)

    def test_create_snapshot_store(self):
        factory = MarketComponentFactory()
        ss = factory.create_snapshot_store()
        from iios.market.snapshot import MarketSnapshotStore
        assert isinstance(ss, MarketSnapshotStore)

    def test_create_snapshot_cache(self):
        factory = MarketComponentFactory()
        sc = factory.create_snapshot_cache()
        from iios.market.snapshot import MarketSnapshotCache
        assert isinstance(sc, MarketSnapshotCache)

    def test_create_snapshot_history(self):
        factory = MarketComponentFactory()
        sh = factory.create_snapshot_history()
        from iios.market.snapshot import MarketSnapshotHistory
        assert isinstance(sh, MarketSnapshotHistory)

    def test_create_lifecycle(self):
        factory = MarketComponentFactory()
        lc = factory.create_lifecycle()
        from iios.market.lifecycle import MarketLifecycle
        assert isinstance(lc, MarketLifecycle)

    def test_create_engine(self):
        factory = MarketComponentFactory()
        e = factory.create_engine()
        from iios.market.engine import MarketEngine
        assert isinstance(e, MarketEngine)


# ===========================================================================
# 16. MarketIntegrationEngine — lifecycle
# ===========================================================================

class TestMarketIntegrationEngineLifecycle:
    def test_initial_state_stopped(self):
        e = MarketIntegrationEngine()
        # Before start(), lifecycle state is "created" (LifecycleAwareMixin initial state)
        assert e.lifecycle_state().value in ("stopped", "created")

    def test_initialize_and_start(self):
        e = _engine_no_components()
        assert e.lifecycle_state().value == "running"
        e.stop()

    def test_stop(self):
        e = _engine_no_components()
        e.stop()
        assert e.lifecycle_state().value == "stopped"

    def test_restart(self):
        e = _engine_no_components()
        e.restart()
        assert e.lifecycle_state().value == "running"
        e.stop()

    def test_submit_raises_when_not_running(self):
        e = _engine_no_components_stopped()
        with pytest.raises(MarketIntegrationNotRunningError):
            e.submit(_request())

    def test_start_registers_no_components_without_create(self):
        e = MarketIntegrationEngine()
        e.initialize(create_components=False)
        e.start()
        assert e._components.count() == 0
        e.stop()


# ===========================================================================
# 17. MarketIntegrationEngine — submit workflow
# ===========================================================================

class TestMarketIntegrationEngineSubmit:
    def test_submit_returns_response(self):
        e = _engine_no_components()
        req  = _request()
        resp = e.submit(req)
        assert isinstance(resp, MarketIntegrationResponse)
        e.stop()

    def test_submit_with_empty_exchange_returns_rejected(self):
        e   = _engine_no_components()
        import dataclasses
        req = _request()
        bad = dataclasses.replace(req, exchange="")
        resp = e.submit(bad)
        assert resp.is_rejected is True
        e.stop()

    def test_submit_records_statistics(self):
        e   = _engine_no_components()
        e.submit(_request())
        stats = e.statistics()
        assert stats["requests_processed"] >= 1
        e.stop()

    def test_submit_records_history(self):
        e    = _engine_no_components()
        e.submit(_request())
        hist = e.history()
        assert len(hist["requests"])  >= 1
        assert len(hist["responses"]) >= 1
        e.stop()

    def test_submit_registers_response(self):
        e    = _engine_no_components()
        resp = e.submit(_request("NSE"))
        results = e.query(exchange="NSE")
        assert any(r.response_id == resp.response_id for r in results)
        e.stop()

    def test_multiple_exchanges(self):
        e = _engine_no_components()
        e.submit(_request("NSE"))
        e.submit(_request("BSE"))
        nse_results = e.query(exchange="NSE")
        bse_results = e.query(exchange="BSE")
        assert len(nse_results) >= 1
        assert len(bse_results) >= 1
        e.stop()


# ===========================================================================
# 18. MarketIntegrationEngine — public API
# ===========================================================================

class TestMarketIntegrationEnginePublicAPI:
    def setup_method(self):
        self.engine = _engine_no_components()

    def teardown_method(self):
        if self.engine.lifecycle_state().value == "running":
            self.engine.stop()

    def test_health_returns_dict(self):
        h = self.engine.health()
        assert isinstance(h, dict)
        assert "overall" in h

    def test_status_returns_status_object(self):
        s = self.engine.status()
        assert isinstance(s, MarketIntegrationStatus)
        assert s.is_running is True

    def test_statistics_returns_dict(self):
        stats = self.engine.statistics()
        assert isinstance(stats, dict)
        assert "requests_processed" in stats

    def test_snapshot_returns_integration_snapshot(self):
        s = self.engine.snapshot()
        assert isinstance(s, MarketIntegrationSnapshot)

    def test_snapshot_exchange_arg(self):
        s = self.engine.snapshot("NSE")
        assert isinstance(s, MarketIntegrationSnapshot)

    def test_history_structure(self):
        hist = self.engine.history()
        assert "requests"  in hist
        assert "responses" in hist
        assert "events"    in hist
        assert "errors"    in hist

    def test_validate_returns_result(self):
        req    = _request()
        result = self.engine.validate(req)
        assert isinstance(result, MarketIntegrationValidationResult)

    def test_query_default(self):
        result = self.engine.query()
        assert isinstance(result, list)

    def test_query_by_status(self):
        result = self.engine.query(status=IntegrationStatus.COMPLETED)
        assert isinstance(result, list)

    def test_get_market_snapshot_none_when_empty(self):
        # No components registered — snapshot cache not wired
        snap = self.engine.get_market_snapshot("NSE")
        assert snap is None

    def test_listener_receives_event(self):
        received = []
        self.engine.add_listener(received.append)
        self.engine.submit(_request())
        assert len(received) > 0
        self.engine.remove_listener(received.append)

    def test_remove_listener(self):
        received = []
        self.engine.add_listener(received.append)
        self.engine.remove_listener(received.append)
        prev = len(received)
        self.engine.submit(_request())
        assert len(received) == prev  # no new events after removal


# ===========================================================================
# 19. Concurrency
# ===========================================================================

class TestMarketIntegrationConcurrency:
    def test_concurrent_submits(self):
        e = _engine_no_components()
        errors = []

        def _submit():
            try:
                e.submit(_request())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_submit) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent submit errors: {errors}"
        stats = e.statistics()
        assert stats["requests_processed"] == 20
        e.stop()

    def test_concurrent_status_and_submit(self):
        e = _engine_no_components()
        errors = []

        def _work():
            try:
                e.submit(_request())
                e.status()
                e.statistics()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_work) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errors: {errors}"
        e.stop()


# ===========================================================================
# 20. Public surface
# ===========================================================================

class TestPublicSurface:
    def test_all_exports_importable(self):
        import iios.market.integration as pkg
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"Missing: {name}"

    def test_version_exported(self):
        from iios.market.integration import VERSION
        assert VERSION == "1.0.0"

    def test_integration_system_id_exported(self):
        from iios.market.integration import INTEGRATION_SYSTEM_ID
        assert "integration" in INTEGRATION_SYSTEM_ID


# ===========================================================================
# 21. Regression: no internal subsystem exposed
# ===========================================================================

class TestNoInternalSubsystemExposed:
    def test_public_api_does_not_export_lifecycle_module(self):
        import iios.market.integration as pkg
        for name in pkg.__all__:
            # M1-M4 core classes must NOT be in the public integration API
            assert name not in (
                "MarketLifecycle", "MarketEngine",
                "MarketPolicyEngine", "MarketAnalyticsEngine",
            ), f"Internal class {name!r} exposed in integration public API"

    def test_engine_exposes_integration_snapshot_not_engine_snapshot(self):
        e    = _engine_no_components()
        snap = e.snapshot()
        # Must return MarketIntegrationSnapshot, not MarketEngineSnapshot
        assert isinstance(snap, MarketIntegrationSnapshot)
        e.stop()

    def test_market_snapshot_only_via_get_market_snapshot(self):
        """The only path to a MarketSnapshot is via get_market_snapshot()."""
        e = _engine_no_components()
        # Engine public API should not directly expose MarketEngine
        assert not hasattr(e, "market_engine_public_expose"), \
            "MarketEngine must not be a public attribute"
        e.stop()
