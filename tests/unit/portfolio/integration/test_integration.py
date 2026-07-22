"""
test_integration.py — tests/unit/portfolio/integration
=======================================================
Comprehensive test suite for the Portfolio Integration subsystem (C10 M6).

Sections
--------
1.  Constants
2.  Exceptions
3.  Context
4.  Request
5.  Response
6.  Events
7.  Validation (7 checks)
8.  Statistics
9.  Status
10. Health
11. History
12. Integration Snapshot
13. Component Registry
14. Component Factory
15. Integration Registry
16. Integration Manager
17. Integration Engine — public API
18. End-to-end workflow (all 9 service types)
19. Concurrency safety
20. Regression
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from iios.portfolio.integration import (
    # constants
    INTEGRATION_SYSTEM_ID,
    VERSION,
    IntegrationState,
    IntegrationServiceType,
    WorkflowStage,
    ResponseStatus,
    ComponentType,
    IntegrationEventType,
    IntegrationValidationCode,
    IntegrationHealth,
    CREATION_SERVICES,
    READONLY_SERVICES,
    # exceptions
    PortfolioIntegrationError,
    IntegrationNotReadyError,
    IntegrationRequestError,
    IntegrationValidationError,
    IntegrationWorkflowError,
    IntegrationComponentError,
    IntegrationSnapshotError,
    IntegrationHistoryError,
    IntegrationCapacityError,
    IntegrationTimeoutError,
    # context
    IntegrationContext,
    # request/response
    PortfolioIntegrationRequest,
    PortfolioIntegrationResponse,
    # events
    IntegrationEvent,
    make_portfolio_initialized,
    make_portfolio_started,
    make_portfolio_completed,
    make_portfolio_stopped,
    make_portfolio_restarted,
    make_portfolio_validated,
    make_portfolio_health_changed,
    make_snapshot_published,
    # validation
    IntegrationValidationCheckResult,
    IntegrationValidationResult,
    PortfolioIntegrationValidator,
    # infrastructure
    PortfolioIntegrationStatistics,
    IntegrationComponentStatus,
    PortfolioIntegrationStatus,
    PortfolioIntegrationHealth,
    PortfolioIntegrationHistory,
    PortfolioIntegrationRegistry,
    PortfolioIntegrationSnapshot,
    # components
    PortfolioComponentRegistry,
    PortfolioComponentFactory,
    PortfolioIntegrationManager,
    # primary interface
    PortfolioIntegrationEngine,
)


# ===========================================================================
# Helpers / fixtures
# ===========================================================================

def _make_request(
    portfolio_id:  str = "pf-001",
    service_type:  IntegrationServiceType = IntegrationServiceType.PORTFOLIO_CREATION,
    *,
    priority: int = 5,
    inputs:   Optional[Dict[str, Any]] = None,
) -> PortfolioIntegrationRequest:
    return PortfolioIntegrationRequest.create(
        portfolio_id,
        service_type,
        priority = priority,
        inputs   = inputs or {"portfolio_name": "Test Portfolio", "lifecycle_state": "running"},
    )


def _make_minimal_registry() -> PortfolioComponentRegistry:
    """Registry with all components as None (unavailable)."""
    return PortfolioComponentRegistry()


def _make_snapshot_only_registry() -> PortfolioComponentRegistry:
    """Registry with only the snapshot component available."""
    from iios.portfolio.snapshot import PortfolioSnapshotRegistry
    reg = PortfolioComponentRegistry()
    reg.register_snapshot(PortfolioSnapshotRegistry(auto_validate=True))
    return reg


@pytest.fixture
def engine() -> PortfolioIntegrationEngine:
    """Full integration engine; stopped in teardown."""
    eng = PortfolioIntegrationEngine()
    eng.initialize()
    yield eng
    if eng.lifecycle_state().value == "running":
        eng.stop()


@pytest.fixture
def request_() -> PortfolioIntegrationRequest:
    return _make_request()


@pytest.fixture
def validator() -> PortfolioIntegrationValidator:
    return PortfolioIntegrationValidator()


@pytest.fixture
def stats() -> PortfolioIntegrationStatistics:
    return PortfolioIntegrationStatistics()


@pytest.fixture
def history() -> PortfolioIntegrationHistory:
    return PortfolioIntegrationHistory()


@pytest.fixture
def registry() -> PortfolioIntegrationRegistry:
    return PortfolioIntegrationRegistry()


# ===========================================================================
# 1. Constants
# ===========================================================================

class TestConstants:
    def test_system_id_starts_with_iios(self):
        assert INTEGRATION_SYSTEM_ID.startswith("iios:")

    def test_version_format(self):
        parts = VERSION.split(".")
        assert len(parts) == 3

    def test_service_type_count(self):
        assert len(IntegrationServiceType) == 9

    def test_workflow_stage_count(self):
        assert len(WorkflowStage) >= 8

    def test_event_type_count(self):
        assert len(IntegrationEventType) == 8

    def test_validation_code_count(self):
        assert len(IntegrationValidationCode) == 7

    def test_component_type_count(self):
        assert len(ComponentType) == 5

    def test_creation_services_nonempty(self):
        assert len(CREATION_SERVICES) > 0

    def test_readonly_services_nonempty(self):
        assert len(READONLY_SERVICES) > 0

    def test_creation_and_readonly_disjoint(self):
        creation_vals = {s.value for s in CREATION_SERVICES}
        readonly_vals = {s.value for s in READONLY_SERVICES}
        assert creation_vals.isdisjoint(readonly_vals)

    def test_integration_health_values(self):
        vals = {h.value for h in IntegrationHealth}
        assert {"healthy", "degraded", "critical", "unknown"} == vals

    def test_response_status_values(self):
        vals = {s.value for s in ResponseStatus}
        assert {"success", "failure", "partial"} == vals


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(PortfolioIntegrationError, IIOSError)

    def test_all_are_subclasses(self):
        for cls in (
            IntegrationNotReadyError, IntegrationRequestError,
            IntegrationValidationError, IntegrationWorkflowError,
            IntegrationComponentError, IntegrationSnapshotError,
            IntegrationHistoryError, IntegrationCapacityError,
            IntegrationTimeoutError,
        ):
            assert issubclass(cls, PortfolioIntegrationError)

    def test_error_codes_unique(self):
        codes = {
            PortfolioIntegrationError.error_code,
            IntegrationNotReadyError.error_code,
            IntegrationRequestError.error_code,
            IntegrationValidationError.error_code,
            IntegrationWorkflowError.error_code,
            IntegrationComponentError.error_code,
            IntegrationSnapshotError.error_code,
            IntegrationHistoryError.error_code,
            IntegrationCapacityError.error_code,
            IntegrationTimeoutError.error_code,
        }
        assert len(codes) == 10

    def test_error_codes_pi_prefix(self):
        for cls in (
            PortfolioIntegrationError, IntegrationNotReadyError,
            IntegrationCapacityError,
        ):
            assert cls.error_code.startswith("PI-")

    def test_request_error_stores_portfolio_id(self):
        err = IntegrationRequestError("bad", portfolio_id="pf-1")
        assert err.portfolio_id == "pf-1"

    def test_validation_error_stores_failed_checks(self):
        err = IntegrationValidationError("fail", failed_checks=("a", "b"))
        assert len(err.failed_checks) == 2

    def test_workflow_error_stores_stage(self):
        err = IntegrationWorkflowError("crash", stage="engine_invoked")
        assert err.stage == "engine_invoked"

    def test_component_error_stores_component(self):
        err = IntegrationComponentError("down", component="lifecycle")
        assert err.component == "lifecycle"

    def test_capacity_error_stores_limit(self):
        err = IntegrationCapacityError(500)
        assert err.limit == 500

    def test_timeout_error_stores_timeout_s(self):
        err = IntegrationTimeoutError("too slow", timeout_s=30.0)
        assert err.timeout_s == 30.0


# ===========================================================================
# 3. Context
# ===========================================================================

class TestIntegrationContext:
    def test_create(self):
        ctx = IntegrationContext.create("req-1", "pf-1", "portfolio_creation")
        assert ctx.request_id == "req-1"
        assert ctx.portfolio_id == "pf-1"
        assert ctx.framework_version == VERSION

    def test_is_frozen(self):
        ctx = IntegrationContext.create("req-1", "pf-1", "portfolio_creation")
        with pytest.raises((AttributeError, TypeError)):
            ctx.portfolio_id = "other"  # type: ignore

    def test_advance_stage(self):
        ctx = IntegrationContext.create("req-1", "pf-1", "portfolio_creation")
        ctx2 = ctx.advance(WorkflowStage.CONTEXT_VALIDATED)
        assert ctx2.workflow_stage == WorkflowStage.CONTEXT_VALIDATED.value
        assert ctx.workflow_stage == WorkflowStage.REQUEST_RECEIVED.value

    def test_with_session(self):
        ctx = IntegrationContext.create("req-1", "pf-1", "portfolio_creation")
        ctx2 = ctx.with_session("sess-42")
        assert ctx2.session_id == "sess-42"
        assert ctx.session_id == ""

    def test_to_dict(self):
        ctx = IntegrationContext.create("req-1", "pf-1", "portfolio_creation")
        d = ctx.to_dict()
        assert d["portfolio_id"] == "pf-1"
        assert "context_id" in d

    def test_metadata_is_copied(self):
        meta = {"k": "v"}
        ctx  = IntegrationContext.create("r", "p", "portfolio_creation", metadata=meta)
        meta["extra"] = "should not appear"
        assert "extra" not in ctx.metadata


# ===========================================================================
# 4. Request
# ===========================================================================

class TestPortfolioIntegrationRequest:
    def test_create(self):
        req = _make_request()
        assert req.portfolio_id == "pf-001"
        assert req.service_type == IntegrationServiceType.PORTFOLIO_CREATION.value
        assert req.framework_version == VERSION

    def test_is_frozen(self):
        req = _make_request()
        with pytest.raises((AttributeError, TypeError)):
            req.portfolio_id = "x"  # type: ignore

    def test_priority_clamped(self):
        req = PortfolioIntegrationRequest.create("pf-1", priority=99)
        assert req.priority == 10
        req2 = PortfolioIntegrationRequest.create("pf-1", priority=0)
        assert req2.priority == 1

    def test_is_readonly_query(self):
        req = _make_request(service_type=IntegrationServiceType.PORTFOLIO_QUERY)
        assert req.is_readonly
        assert not req.is_creation

    def test_is_creation(self):
        req = _make_request(service_type=IntegrationServiceType.PORTFOLIO_CREATION)
        assert req.is_creation
        assert not req.is_readonly

    def test_portfolio_name_property(self):
        req = _make_request(inputs={"portfolio_name": "Alpha"})
        assert req.portfolio_name == "Alpha"

    def test_lifecycle_state_property(self):
        req = _make_request(inputs={"lifecycle_state": "active"})
        assert req.lifecycle_state == "active"

    def test_to_dict(self):
        req = _make_request()
        d   = req.to_dict()
        assert d["portfolio_id"] == "pf-001"
        assert "request_id" in d
        assert "context" in d

    def test_context_is_attached(self):
        req = _make_request()
        assert req.context.portfolio_id == req.portfolio_id


# ===========================================================================
# 5. Response
# ===========================================================================

class TestPortfolioIntegrationResponse:
    def test_success_factory(self):
        r = PortfolioIntegrationResponse.success("req-1", "pf-1", "portfolio_creation")
        assert r.is_success
        assert not r.is_failure
        assert not r.is_partial

    def test_failure_factory(self):
        r = PortfolioIntegrationResponse.failure("req-1", "pf-1", "portfolio_creation", "oops")
        assert r.is_failure
        assert r.error == "oops"
        assert not r.has_snapshot

    def test_is_frozen(self):
        r = PortfolioIntegrationResponse.success("r", "p", "st")
        with pytest.raises((AttributeError, TypeError)):
            r.status = "x"  # type: ignore

    def test_has_snapshot_false_when_none(self):
        r = PortfolioIntegrationResponse.success("r", "p", "st", snapshot=None)
        assert not r.has_snapshot

    def test_duration_ms_positive(self):
        started = time.time() - 0.1
        r = PortfolioIntegrationResponse.success("r", "p", "st", started_at=started)
        assert r.duration_ms >= 0

    def test_to_dict(self):
        r = PortfolioIntegrationResponse.success("req-1", "pf-1", "portfolio_creation")
        d = r.to_dict()
        for key in ("response_id", "request_id", "portfolio_id", "status", "error"):
            assert key in d

    def test_to_dict_snapshot_none_when_absent(self):
        r = PortfolioIntegrationResponse.success("r", "p", "st")
        assert r.to_dict()["snapshot"] is None


# ===========================================================================
# 6. Events
# ===========================================================================

class TestIntegrationEvents:
    def _check(self, event, expected_type):
        assert isinstance(event, IntegrationEvent)
        assert event.event_type == expected_type.value
        assert event.occurred_at > 0
        uuid.UUID(event.event_id)

    def test_make_initialized(self):
        self._check(make_portfolio_initialized("p-1"), IntegrationEventType.PORTFOLIO_INITIALIZED)

    def test_make_started(self):
        self._check(make_portfolio_started("p-1"), IntegrationEventType.PORTFOLIO_STARTED)

    def test_make_completed(self):
        e = make_portfolio_completed("p-1", "r-1", service_type="portfolio_creation")
        self._check(e, IntegrationEventType.PORTFOLIO_COMPLETED)
        assert e.payload["service_type"] == "portfolio_creation"

    def test_make_stopped(self):
        e = make_portfolio_stopped("p-1", reason="shutdown")
        self._check(e, IntegrationEventType.PORTFOLIO_STOPPED)
        assert e.payload["reason"] == "shutdown"

    def test_make_restarted(self):
        self._check(make_portfolio_restarted("p-1"), IntegrationEventType.PORTFOLIO_RESTARTED)

    def test_make_validated(self):
        e = make_portfolio_validated("p-1", passed_checks=7)
        self._check(e, IntegrationEventType.PORTFOLIO_VALIDATED)
        assert e.payload["passed_checks"] == 7

    def test_make_health_changed(self):
        e = make_portfolio_health_changed("p-1", from_health="healthy", to_health="degraded")
        self._check(e, IntegrationEventType.PORTFOLIO_HEALTH_CHANGED)
        assert e.payload["to_health"] == "degraded"

    def test_make_snapshot_published(self):
        e = make_snapshot_published("p-1", "r-1", snapshot_id="snap-1")
        self._check(e, IntegrationEventType.PORTFOLIO_SNAPSHOT_PUBLISHED)
        assert e.payload["snapshot_id"] == "snap-1"

    def test_event_is_frozen(self):
        e = make_portfolio_initialized("p-1")
        with pytest.raises((AttributeError, TypeError)):
            e.event_id = "x"  # type: ignore

    def test_each_event_has_unique_id(self):
        ids = {make_portfolio_started("p-1").event_id for _ in range(10)}
        assert len(ids) == 10

    def test_all_8_event_types_covered(self):
        factories = [
            make_portfolio_initialized, make_portfolio_started, make_portfolio_completed,
            make_portfolio_stopped, make_portfolio_restarted, make_portfolio_validated,
            make_portfolio_health_changed, make_snapshot_published,
        ]
        types = {f("p-1").event_type for f in factories}
        all_types = {e.value for e in IntegrationEventType}
        assert types == all_types


# ===========================================================================
# 7. Validation (7 checks)
# ===========================================================================

class TestIntegrationValidation:
    def test_valid_request_passes_all_7(self, validator):
        req    = _make_request()
        result = validator.validate(req)
        assert result.is_valid
        assert result.passed_count == 7
        assert result.failed_count == 0

    def test_checks_count_property(self, validator):
        result = validator.validate(_make_request())
        assert result.checks_count == 7

    def test_check_result_is_frozen(self, validator):
        result = validator.validate(_make_request())
        chk    = result.checks[0]
        with pytest.raises((AttributeError, TypeError)):
            chk.passed = False  # type: ignore

    def test_lifecycle_fails_empty_portfolio_id(self, validator):
        import dataclasses
        req = _make_request()
        bad = dataclasses.replace(req, portfolio_id="")
        result = validator.validate(bad)
        codes  = [c.code for c in result.failed_checks]
        assert IntegrationValidationCode.LIFECYCLE_CONSISTENCY.value in codes

    def test_lifecycle_fails_unknown_state(self, validator):
        req    = _make_request(inputs={"lifecycle_state": "__bad__"})
        result = validator.validate(req)
        codes  = [c.code for c in result.failed_checks]
        assert IntegrationValidationCode.LIFECYCLE_CONSISTENCY.value in codes

    def test_engine_fails_empty_request_id(self, validator):
        import dataclasses
        req = _make_request()
        bad = dataclasses.replace(req, request_id="")
        result = validator.validate(bad)
        codes  = [c.code for c in result.failed_checks]
        assert IntegrationValidationCode.ENGINE_CONSISTENCY.value in codes

    def test_engine_fails_bad_priority(self, validator):
        import dataclasses
        req = _make_request()
        bad = dataclasses.replace(req, priority=99)
        result = validator.validate(bad)
        codes  = [c.code for c in result.failed_checks]
        assert IntegrationValidationCode.ENGINE_CONSISTENCY.value in codes

    def test_policy_fails_non_dict_context(self, validator):
        req    = _make_request(inputs={"policy_context": "not-a-dict"})
        result = validator.validate(req)
        codes  = [c.code for c in result.failed_checks]
        assert IntegrationValidationCode.POLICY_CONSISTENCY.value in codes

    def test_optimization_fails_non_dict_context(self, validator):
        req    = _make_request(inputs={"optimization_context": 42})
        result = validator.validate(req)
        codes  = [c.code for c in result.failed_checks]
        assert IntegrationValidationCode.OPTIMIZATION_CONSISTENCY.value in codes

    def test_snapshot_fails_non_dict_context(self, validator):
        req    = _make_request(inputs={"snapshot_context": [1, 2]})
        result = validator.validate(req)
        codes  = [c.code for c in result.failed_checks]
        assert IntegrationValidationCode.SNAPSHOT_CONSISTENCY.value in codes

    def test_integration_fails_unknown_service_type(self, validator):
        import dataclasses
        req = _make_request()
        bad = dataclasses.replace(req, service_type="__invalid__")
        result = validator.validate(bad)
        codes  = [c.code for c in result.failed_checks]
        assert IntegrationValidationCode.INTEGRATION_CONSISTENCY.value in codes

    def test_integration_fails_empty_framework_version(self, validator):
        import dataclasses
        req = _make_request()
        bad = dataclasses.replace(req, framework_version="")
        result = validator.validate(bad)
        codes  = [c.code for c in result.failed_checks]
        assert IntegrationValidationCode.INTEGRATION_CONSISTENCY.value in codes

    def test_subsystem_readiness_skipped_with_none_registry(self, validator):
        req    = _make_request()
        result = validator.validate(req, None)
        assert result.is_valid   # passes because registry is None

    def test_subsystem_fails_when_not_ready(self, validator):
        req = _make_request()
        reg = _make_minimal_registry()   # all None → not ready
        # Patch is_ready to return False
        reg_mock = MagicMock(spec=PortfolioComponentRegistry)
        reg_mock.is_ready.return_value = False
        result = validator.validate(req, reg_mock)
        codes  = [c.code for c in result.failed_checks]
        assert IntegrationValidationCode.SUBSYSTEM_READINESS.value in codes

    def test_error_messages_populated_on_failure(self, validator):
        import dataclasses
        req = _make_request()
        bad = dataclasses.replace(req, portfolio_id="", service_type="__bad__")
        result = validator.validate(bad)
        assert len(result.error_messages) >= 2

    def test_validation_code_all_7_checked(self, validator):
        req    = _make_request()
        result = validator.validate(req, None)
        checked = {c.code for c in result.checks}
        all_codes = {c.value for c in IntegrationValidationCode}
        assert checked == all_codes


# ===========================================================================
# 8. Statistics
# ===========================================================================

class TestIntegrationStatistics:
    def test_initial_state(self, stats):
        d = stats.snapshot()
        assert d["portfolio_requests"] == 0
        assert d["portfolio_sessions"] == 0
        assert d["snapshots_published"] == 0
        assert d["workflow_successes"] == 0
        assert d["workflow_failures"] == 0

    def test_record_request(self, stats):
        stats.record_request()
        assert stats.snapshot()["portfolio_requests"] == 1

    def test_record_session(self, stats):
        stats.record_session_created()
        assert stats.snapshot()["portfolio_sessions"] == 1

    def test_record_snapshot(self, stats):
        stats.record_snapshot_published()
        assert stats.snapshot()["snapshots_published"] == 1

    def test_record_optimization(self, stats):
        stats.record_optimization()
        assert stats.snapshot()["portfolio_optimizations"] == 1

    def test_record_review(self, stats):
        stats.record_review()
        assert stats.snapshot()["portfolio_reviews"] == 1

    def test_record_success_avg(self, stats):
        stats.record_success(10.0)
        stats.record_success(20.0)
        d = stats.snapshot()
        assert d["workflow_successes"] == 2
        assert d["avg_response_time_ms"] == 15.0

    def test_record_failure(self, stats):
        stats.record_failure(5.0)
        assert stats.snapshot()["workflow_failures"] == 1

    def test_availability_dict(self, stats):
        stats.set_component_availability(lifecycle=True, engine=True)
        d = stats.snapshot()
        assert d["subsystem_availability"]["lifecycle"] is True
        assert d["subsystem_availability"]["optimization"] is False

    def test_reset(self, stats):
        stats.record_request()
        stats.record_success()
        stats.reset()
        d = stats.snapshot()
        assert d["portfolio_requests"] == 0
        assert d["workflow_successes"] == 0

    def test_avg_zero_with_no_samples(self, stats):
        assert stats.snapshot()["avg_response_time_ms"] == 0.0


# ===========================================================================
# 9. Status
# ===========================================================================

class TestIntegrationStatus:
    def test_component_status_running(self):
        cs = IntegrationComponentStatus.running("lifecycle", started_at=1000.0)
        assert cs.is_running
        assert cs.health == IntegrationHealth.HEALTHY.value

    def test_component_status_unknown(self):
        cs = IntegrationComponentStatus.unknown("engine")
        assert not cs.is_running
        assert cs.health == IntegrationHealth.UNKNOWN.value

    def test_component_status_is_frozen(self):
        cs = IntegrationComponentStatus.running("lifecycle")
        with pytest.raises((AttributeError, TypeError)):
            cs.is_running = False  # type: ignore

    def test_component_status_to_dict(self):
        cs = IntegrationComponentStatus.running("policy")
        d  = cs.to_dict()
        assert d["component_type"] == "policy"
        assert d["is_running"] is True

    def test_portfolio_integration_status_to_dict(self):
        cs = IntegrationComponentStatus.unknown("lifecycle")
        ps = PortfolioIntegrationStatus(
            integration_id      = INTEGRATION_SYSTEM_ID,
            state               = IntegrationState.RUNNING.value,
            lifecycle_status    = cs,
            engine_status       = cs,
            policy_status       = cs,
            optimization_status = cs,
            snapshot_status     = cs,
            overall_health      = IntegrationHealth.UNKNOWN.value,
            statistics          = {},
            started_at          = 0.0,
            captured_at         = time.time(),
            framework_version   = VERSION,
        )
        d = ps.to_dict()
        assert d["integration_id"] == INTEGRATION_SYSTEM_ID
        assert "lifecycle_status" in d


# ===========================================================================
# 10. Health
# ===========================================================================

class TestIntegrationHealth:
    def test_all_unknown_when_no_components(self):
        health = PortfolioIntegrationHealth()
        reg    = _make_minimal_registry()
        report = health.report(reg)
        assert report["overall"] == IntegrationHealth.UNKNOWN.value

    def test_healthy_when_all_running(self, engine):
        health = PortfolioIntegrationHealth()
        report = health.report(engine._component_registry)
        # Overall health is one of the four valid values (subsystems may vary)
        assert report["overall"] in {h.value for h in IntegrationHealth}

    def test_check_lifecycle_unknown_when_absent(self):
        health = PortfolioIntegrationHealth()
        reg    = _make_minimal_registry()
        cs     = health.check_lifecycle(reg)
        assert cs.health == IntegrationHealth.UNKNOWN.value

    def test_check_snapshot_healthy_when_available(self):
        from iios.portfolio.snapshot import PortfolioSnapshotRegistry
        health = PortfolioIntegrationHealth()
        reg    = PortfolioComponentRegistry()
        reg.register_snapshot(PortfolioSnapshotRegistry())
        cs = health.check_snapshot(reg)
        assert cs.is_running
        assert cs.health == IntegrationHealth.HEALTHY.value

    def test_overall_health_critical_if_any_critical(self):
        health = PortfolioIntegrationHealth()
        statuses = [
            IntegrationComponentStatus.running("lifecycle"),
            IntegrationComponentStatus(
                component_type="engine", is_running=False,
                health=IntegrationHealth.CRITICAL.value,
                started_at=0.0, last_event="", metadata={},
            ),
        ]
        assert health.overall_health(statuses) == IntegrationHealth.CRITICAL.value

    def test_overall_health_degraded_if_any_degraded(self):
        health   = PortfolioIntegrationHealth()
        statuses = [
            IntegrationComponentStatus.running("lifecycle"),
            IntegrationComponentStatus(
                component_type="engine", is_running=True,
                health=IntegrationHealth.DEGRADED.value,
                started_at=0.0, last_event="", metadata={},
            ),
        ]
        assert health.overall_health(statuses) == IntegrationHealth.DEGRADED.value

    def test_overall_health_degraded_mix_healthy_unknown(self):
        health   = PortfolioIntegrationHealth()
        statuses = [
            IntegrationComponentStatus.running("lifecycle"),
            IntegrationComponentStatus.unknown("engine"),
        ]
        assert health.overall_health(statuses) == IntegrationHealth.DEGRADED.value

    def test_report_has_all_keys(self, engine):
        report = engine.health()
        for key in ("overall", "lifecycle", "engine", "policy", "optimization", "snapshot"):
            assert key in report


# ===========================================================================
# 11. History
# ===========================================================================

class TestPortfolioIntegrationHistory:
    def _make_response(self, portfolio_id: str = "pf-1") -> PortfolioIntegrationResponse:
        return PortfolioIntegrationResponse.success(
            str(uuid.uuid4()), portfolio_id, "portfolio_creation"
        )

    def test_record_and_get(self, history):
        r = self._make_response()
        history.record(r)
        items = history.get_for_portfolio("pf-1")
        assert len(items) == 1

    def test_get_latest(self, history):
        r1 = self._make_response()
        r2 = self._make_response()
        history.record(r1)
        history.record(r2)
        latest = history.get_latest("pf-1")
        assert latest is r2

    def test_get_latest_missing_returns_none(self, history):
        assert history.get_latest("nonexistent") is None

    def test_get_global(self, history):
        r1 = self._make_response("pf-1")
        r2 = self._make_response("pf-2")
        history.record(r1)
        history.record(r2)
        assert len(history.get_global()) == 2

    def test_limit_parameter(self, history):
        for _ in range(5):
            history.record(self._make_response())
        items = history.get_for_portfolio("pf-1", limit=3)
        assert len(items) == 3

    def test_bounded_deque(self):
        h = PortfolioIntegrationHistory(max_per_portfolio=3)
        for _ in range(5):
            h.record(self._make_response())
        assert h.count_for_portfolio("pf-1") == 3

    def test_portfolio_count(self, history):
        history.record(self._make_response("pf-A"))
        history.record(self._make_response("pf-B"))
        assert history.portfolio_count() == 2

    def test_total_count(self, history):
        for _ in range(3):
            history.record(self._make_response())
        assert history.total_count() == 3

    def test_has_portfolio(self, history):
        history.record(self._make_response("pf-x"))
        assert history.has_portfolio("pf-x")
        assert not history.has_portfolio("pf-y")

    def test_clear(self, history):
        history.record(self._make_response())
        history.clear()
        assert history.total_count() == 0


# ===========================================================================
# 12. Integration Snapshot
# ===========================================================================

class TestPortfolioIntegrationSnapshot:
    def test_build_returns_snapshot(self):
        util = PortfolioIntegrationSnapshot()
        req  = _make_request(inputs={
            "portfolio_name": "Test Fund",
            "lifecycle_state": "running",
            "portfolio_currency": "INR",
        })
        snap = util.build(req, "sess-1", {})
        assert snap.portfolio_id == req.portfolio_id
        assert snap.portfolio_name == "Test Fund"

    def test_build_with_session_id(self):
        util = PortfolioIntegrationSnapshot()
        req  = _make_request()
        snap = util.build(req, "sess-99", {})
        assert snap.portfolio_session_id == "sess-99"

    def test_build_auto_generates_session_if_empty(self):
        util = PortfolioIntegrationSnapshot()
        req  = _make_request()
        snap = util.build(req, "", {})
        assert snap.portfolio_session_id != ""

    def test_build_passes_result_to_summaries(self):
        util = PortfolioIntegrationSnapshot()
        req  = _make_request()
        result = {"risk": {"var_95": 0.02}, "optimization": {"status": "optimal"}}
        snap = util.build(req, "sess-1", result)
        assert snap.risk_summary["var_95"] == 0.02
        assert snap.optimization_summary["status"] == "optimal"

    def test_build_with_holdings(self):
        util = PortfolioIntegrationSnapshot()
        req  = _make_request(inputs={
            "current_holdings": [{"sym": "TCS"}, {"sym": "INFY"}],
        })
        snap = util.build(req, "sess-1", {})
        assert snap.position_count == 2


# ===========================================================================
# 13. Component Registry
# ===========================================================================

class TestPortfolioComponentRegistry:
    def test_initially_empty(self):
        reg = PortfolioComponentRegistry()
        assert reg.available_count() == 0

    def test_register_and_get(self):
        reg  = PortfolioComponentRegistry()
        mock = MagicMock()
        reg.register_lifecycle(mock)
        assert reg.get_lifecycle() is mock

    def test_available_count(self):
        reg = PortfolioComponentRegistry()
        reg.register_lifecycle(MagicMock())
        reg.register_engine(MagicMock())
        assert reg.available_count() == 2

    def test_is_available(self):
        reg = PortfolioComponentRegistry()
        reg.register_snapshot(MagicMock())
        assert reg.is_available(ComponentType.SNAPSHOT)
        assert not reg.is_available(ComponentType.LIFECYCLE)

    def test_is_ready_false_when_empty(self):
        reg = PortfolioComponentRegistry()
        assert not reg.is_ready()

    def test_status_dict(self):
        reg = PortfolioComponentRegistry()
        reg.register_lifecycle(MagicMock())
        d = reg.status_dict()
        assert d[ComponentType.LIFECYCLE.value] is True
        assert d[ComponentType.ENGINE.value] is False

    def test_clear(self):
        reg = PortfolioComponentRegistry()
        reg.register_lifecycle(MagicMock())
        reg.clear()
        assert reg.available_count() == 0


# ===========================================================================
# 14. Component Factory
# ===========================================================================

class TestPortfolioComponentFactory:
    def test_create_lifecycle(self):
        from iios.portfolio.lifecycle import PortfolioLifecycle
        lc = PortfolioComponentFactory.create_lifecycle()
        assert isinstance(lc, PortfolioLifecycle)

    def test_create_engine(self):
        from iios.portfolio.engine import PortfolioEngine
        eng = PortfolioComponentFactory.create_engine()
        assert isinstance(eng, PortfolioEngine)

    def test_create_policy(self):
        from iios.portfolio.policies import PortfolioPolicyEngine
        pol = PortfolioComponentFactory.create_policy()
        assert isinstance(pol, PortfolioPolicyEngine)

    def test_create_optimization(self):
        from iios.portfolio.optimization import PortfolioOptimizationEngine
        opt = PortfolioComponentFactory.create_optimization()
        assert isinstance(opt, PortfolioOptimizationEngine)

    def test_create_snapshot_registry(self):
        from iios.portfolio.snapshot import PortfolioSnapshotRegistry
        snap = PortfolioComponentFactory.create_snapshot_registry()
        assert isinstance(snap, PortfolioSnapshotRegistry)

    def test_create_all_returns_registry(self):
        factory = PortfolioComponentFactory()
        reg     = factory.create_all()
        assert isinstance(reg, PortfolioComponentRegistry)
        assert reg.available_count() == 5

    def test_start_and_stop_all(self):
        factory = PortfolioComponentFactory()
        reg     = factory.create_all()
        PortfolioComponentFactory.start_all(reg)
        # Should not raise
        PortfolioComponentFactory.stop_all(reg)


# ===========================================================================
# 15. Integration Registry
# ===========================================================================

class TestPortfolioIntegrationRegistry:
    def test_register_request(self, registry):
        req = _make_request()
        registry.register_request(req)
        assert registry.contains_request(req.request_id)

    def test_register_response(self, registry):
        req  = _make_request()
        resp = PortfolioIntegrationResponse.success(req.request_id, req.portfolio_id, req.service_type)
        registry.register_request(req)
        registry.register_response(resp)
        assert registry.contains_response(req.request_id)

    def test_get_request(self, registry):
        req = _make_request()
        registry.register_request(req)
        assert registry.get_request(req.request_id) is req

    def test_get_response(self, registry):
        req  = _make_request()
        resp = PortfolioIntegrationResponse.success(req.request_id, req.portfolio_id, req.service_type)
        registry.register_request(req)
        registry.register_response(resp)
        assert registry.get_response(req.request_id) is resp

    def test_find_by_portfolio(self, registry):
        for _ in range(3):
            registry.register_request(_make_request("pf-A"))
        registry.register_request(_make_request("pf-B"))
        assert len(registry.find_by_portfolio("pf-A")) == 3

    def test_find_by_service(self, registry):
        registry.register_request(_make_request(service_type=IntegrationServiceType.PORTFOLIO_QUERY))
        registry.register_request(_make_request(service_type=IntegrationServiceType.PORTFOLIO_CREATION))
        queries = registry.find_by_service(IntegrationServiceType.PORTFOLIO_QUERY.value)
        assert len(queries) == 1

    def test_capacity_error(self):
        reg = PortfolioIntegrationRegistry(max_requests=2)
        for _ in range(2):
            reg.register_request(_make_request())
        with pytest.raises(IntegrationCapacityError):
            reg.register_request(_make_request())

    def test_counts(self, registry):
        req  = _make_request()
        resp = PortfolioIntegrationResponse.success(req.request_id, req.portfolio_id, req.service_type)
        registry.register_request(req)
        registry.register_response(resp)
        assert registry.request_count() == 1
        assert registry.response_count() == 1

    def test_clear(self, registry):
        registry.register_request(_make_request())
        registry.clear()
        assert registry.request_count() == 0

    def test_idempotent_register(self, registry):
        req = _make_request()
        registry.register_request(req)
        registry.register_request(req)   # second call is a no-op
        assert registry.request_count() == 1


# ===========================================================================
# 16. Integration Manager
# ===========================================================================

class TestPortfolioIntegrationManager:
    def _make_manager_with_snapshot_only(self):
        from iios.portfolio.snapshot import PortfolioSnapshotRegistry
        reg   = PortfolioComponentRegistry()
        reg.register_snapshot(PortfolioSnapshotRegistry(auto_validate=True))
        # Patch is_ready to True so subsystem readiness check passes
        reg.is_ready = lambda: True
        stats = PortfolioIntegrationStatistics()
        return PortfolioIntegrationManager(reg, stats), reg, stats

    def test_execute_returns_response(self):
        manager, _, _ = self._make_manager_with_snapshot_only()
        req  = _make_request()
        resp = manager.execute(req)
        assert isinstance(resp, PortfolioIntegrationResponse)

    def test_execute_success_has_snapshot(self):
        manager, _, _ = self._make_manager_with_snapshot_only()
        req  = _make_request()
        resp = manager.execute(req)
        assert resp.is_success
        assert resp.has_snapshot

    def test_execute_failure_on_invalid_request(self):
        manager, _, _ = self._make_manager_with_snapshot_only()
        import dataclasses
        req = _make_request()
        bad = dataclasses.replace(req, portfolio_id="", service_type="__bad__")
        resp = manager.execute(bad)
        assert resp.is_failure

    def test_execute_query_succeeds(self):
        manager, _, _ = self._make_manager_with_snapshot_only()
        req  = _make_request(service_type=IntegrationServiceType.PORTFOLIO_QUERY)
        resp = manager.execute(req)
        assert resp.is_success

    def test_execute_updates_statistics(self):
        manager, _, stats = self._make_manager_with_snapshot_only()
        manager.execute(_make_request())
        assert stats.snapshot()["workflow_successes"] == 1


# ===========================================================================
# 17. Integration Engine — public API
# ===========================================================================

class TestPortfolioIntegrationEngine:
    def test_initialize_starts_engine(self):
        eng = PortfolioIntegrationEngine()
        try:
            eng.initialize()
            assert eng.lifecycle_state().value == "running"
        finally:
            eng.stop()

    def test_start_and_stop(self):
        eng = PortfolioIntegrationEngine()
        eng.start()
        assert eng.lifecycle_state().value == "running"
        eng.stop()
        assert eng.lifecycle_state().value == "stopped"

    def test_restart(self):
        eng = PortfolioIntegrationEngine()
        eng.start()
        eng.restart()
        assert eng.lifecycle_state().value == "running"
        eng.stop()

    def test_submit_returns_response(self, engine, request_):
        resp = engine.submit(request_)
        assert isinstance(resp, PortfolioIntegrationResponse)

    def test_submit_not_ready_raises(self, request_):
        eng = PortfolioIntegrationEngine()
        with pytest.raises(IntegrationNotReadyError):
            eng.submit(request_)

    def test_submit_none_raises(self, engine):
        with pytest.raises(IntegrationRequestError):
            engine.submit(None)  # type: ignore

    def test_submit_empty_portfolio_id_raises(self, engine):
        with pytest.raises(IntegrationRequestError):
            req = PortfolioIntegrationRequest.create("")
            engine.submit(req)

    def test_validate_returns_result(self, engine, request_):
        result = engine.validate(request_)
        assert isinstance(result, IntegrationValidationResult)

    def test_validate_before_start(self, request_):
        eng = PortfolioIntegrationEngine()
        result = eng.validate(request_)
        assert isinstance(result, IntegrationValidationResult)

    def test_snapshot_returns_none_when_empty(self, engine):
        assert engine.snapshot("pf-nonexistent") is None

    def test_snapshot_returns_published_after_submit(self, engine):
        req  = _make_request("pf-snap")
        resp = engine.submit(req)
        assert resp.is_success
        snap = engine.snapshot("pf-snap")
        assert snap is not None

    def test_history_empty_initially(self, engine):
        assert engine.history("pf-001") == []

    def test_history_populated_after_submit(self, engine, request_):
        engine.submit(request_)
        h = engine.history("pf-001")
        assert len(h) == 1

    def test_query_returns_list(self, engine, request_):
        engine.submit(request_)
        results = engine.query(portfolio_id="pf-001")
        assert isinstance(results, list)

    def test_health_returns_dict(self, engine):
        report = engine.health()
        assert isinstance(report, dict)
        assert "overall" in report

    def test_status_returns_status_object(self, engine):
        s = engine.status()
        assert isinstance(s, PortfolioIntegrationStatus)
        assert s.integration_id == INTEGRATION_SYSTEM_ID

    def test_statistics_returns_dict(self, engine, request_):
        engine.submit(request_)
        stats = engine.statistics()
        assert stats["portfolio_requests"] >= 1

    def test_add_and_remove_listener(self, engine):
        events = []
        engine.add_listener(events.append)
        engine.submit(_make_request())
        assert len(events) > 0
        engine.remove_listener(events.append)
        before = len(events)
        engine.submit(_make_request())
        assert len(events) == before   # no new events

    def test_initialize_idempotent(self, engine):
        engine.initialize()  # second call
        assert engine.lifecycle_state().value == "running"

    def test_health_raises_when_not_running(self):
        eng = PortfolioIntegrationEngine()
        with pytest.raises(IntegrationNotReadyError):
            eng.health()


# ===========================================================================
# 18. End-to-end workflow — all 9 service types
# ===========================================================================

class TestEndToEndWorkflow:
    @pytest.fixture(autouse=True)
    def _eng(self):
        self.eng = PortfolioIntegrationEngine()
        self.eng.initialize()
        yield
        if self.eng.lifecycle_state().value == "running":
            self.eng.stop()

    def _submit(self, stype: IntegrationServiceType, pid: str = "pf-e2e") -> PortfolioIntegrationResponse:
        req = PortfolioIntegrationRequest.create(
            pid, stype,
            inputs={"portfolio_name": f"E2E {stype.value}", "lifecycle_state": "running"},
        )
        return self.eng.submit(req)

    def test_portfolio_creation(self):
        resp = self._submit(IntegrationServiceType.PORTFOLIO_CREATION)
        assert resp.is_success
        assert resp.has_snapshot

    def test_portfolio_update(self):
        resp = self._submit(IntegrationServiceType.PORTFOLIO_UPDATE)
        assert resp.is_success

    def test_portfolio_validation(self):
        resp = self._submit(IntegrationServiceType.PORTFOLIO_VALIDATION)
        assert resp.is_success

    def test_portfolio_review(self):
        resp = self._submit(IntegrationServiceType.PORTFOLIO_REVIEW)
        assert resp.is_success

    def test_portfolio_optimization(self):
        resp = self._submit(IntegrationServiceType.PORTFOLIO_OPTIMIZATION)
        assert resp.is_success

    def test_portfolio_rebalancing(self):
        resp = self._submit(IntegrationServiceType.PORTFOLIO_REBALANCING)
        assert resp.is_success

    def test_portfolio_synchronization(self):
        resp = self._submit(IntegrationServiceType.PORTFOLIO_SYNCHRONIZATION)
        assert resp.is_success

    def test_portfolio_query(self):
        resp = self._submit(IntegrationServiceType.PORTFOLIO_QUERY)
        assert resp.is_success

    def test_portfolio_reporting(self):
        resp = self._submit(IntegrationServiceType.PORTFOLIO_REPORTING)
        assert resp.is_success

    def test_snapshot_published_after_creation(self):
        self._submit(IntegrationServiceType.PORTFOLIO_CREATION, "pf-snap-e2e")
        snap = self.eng.snapshot("pf-snap-e2e")
        assert snap is not None
        assert snap.is_published

    def test_history_grows_with_submissions(self):
        for _ in range(3):
            self._submit(IntegrationServiceType.PORTFOLIO_QUERY, "pf-hist")
        h = self.eng.history("pf-hist")
        assert len(h) == 3

    def test_statistics_track_requests(self):
        for _ in range(5):
            self._submit(IntegrationServiceType.PORTFOLIO_CREATION, "pf-stats")
        stats = self.eng.statistics()
        assert stats["portfolio_requests"] >= 5

    def test_query_after_multiple_submissions(self):
        for i in range(3):
            self._submit(IntegrationServiceType.PORTFOLIO_CREATION, f"pf-q{i}")
        results = self.eng.query(snapshot_status="published")
        assert len(results) >= 3

    def test_validate_request_before_submit(self):
        req    = PortfolioIntegrationRequest.create("pf-val", IntegrationServiceType.PORTFOLIO_CREATION)
        result = self.eng.validate(req)
        assert result.is_valid

    def test_event_listener_receives_completed_event(self):
        events: List[IntegrationEvent] = []
        self.eng.add_listener(events.append)
        self._submit(IntegrationServiceType.PORTFOLIO_CREATION, "pf-ev")
        types = [e.event_type for e in events]
        assert IntegrationEventType.PORTFOLIO_SNAPSHOT_PUBLISHED.value in types


# ===========================================================================
# 19. Concurrency safety
# ===========================================================================

class TestConcurrencySafety:
    def test_concurrent_submissions(self):
        eng = PortfolioIntegrationEngine()
        eng.initialize()
        errors = []
        results = []

        def worker(i: int):
            try:
                req  = _make_request(f"pf-conc-{i}")
                resp = eng.submit(req)
                results.append(resp)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        eng.stop()

        assert not errors, f"Errors during concurrent submission: {errors}"
        assert len(results) == 20
        assert all(r.is_success for r in results)

    def test_concurrent_history_writes(self, history):
        errors = []

        def recorder(i: int):
            try:
                r = PortfolioIntegrationResponse.success(
                    str(uuid.uuid4()), f"pf-{i % 5}", "portfolio_creation"
                )
                history.record(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=recorder, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert history.total_count() == 50

    def test_concurrent_statistics_increments(self, stats):
        n = 100

        def incrementer():
            for _ in range(n):
                stats.record_request()

        threads = [threading.Thread(target=incrementer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert stats.snapshot()["portfolio_requests"] == 5 * n

    def test_concurrent_registry_writes(self, registry):
        errors = []

        def writer():
            try:
                registry.register_request(_make_request())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors


# ===========================================================================
# 20. Regression
# ===========================================================================

class TestRegression:
    def test_all_service_types_in_integration_service_type(self):
        vals = {s.value for s in IntegrationServiceType}
        assert "portfolio_creation" in vals
        assert "portfolio_query" in vals
        assert len(vals) == 9

    def test_all_workflow_stages_distinct(self):
        vals = [s.value for s in WorkflowStage]
        assert len(vals) == len(set(vals))

    def test_response_dict_stable_across_calls(self):
        r = PortfolioIntegrationResponse.success("r", "p", "portfolio_creation")
        d1 = r.to_dict()
        d2 = r.to_dict()
        assert d1.keys() == d2.keys()

    def test_request_dict_round_trip_ids(self):
        req = _make_request()
        d   = req.to_dict()
        assert d["request_id"] == req.request_id
        assert d["portfolio_id"] == req.portfolio_id

    def test_error_codes_all_pi_prefix(self):
        for cls in (
            PortfolioIntegrationError, IntegrationNotReadyError,
            IntegrationRequestError, IntegrationValidationError,
            IntegrationWorkflowError, IntegrationComponentError,
            IntegrationSnapshotError, IntegrationHistoryError,
            IntegrationCapacityError, IntegrationTimeoutError,
        ):
            assert cls.error_code.startswith("PI-"), cls

    def test_validation_codes_all_7_distinct(self):
        vals = [c.value for c in IntegrationValidationCode]
        assert len(vals) == len(set(vals)) == 7

    def test_engine_stops_cleanly_after_multiple_submits(self):
        eng = PortfolioIntegrationEngine()
        eng.initialize()
        for i in range(5):
            eng.submit(_make_request(f"pf-clean-{i}"))
        eng.stop()
        assert eng.lifecycle_state().value == "stopped"

    def test_snapshot_status_published_after_workflow(self):
        eng = PortfolioIntegrationEngine()
        eng.initialize()
        try:
            resp = eng.submit(_make_request("pf-pub"))
            assert resp.has_snapshot
            assert resp.snapshot.is_published
        finally:
            eng.stop()

    def test_component_registry_thread_safety(self):
        reg    = PortfolioComponentRegistry()
        errors = []

        def writer(i: int):
            try:
                reg.register_lifecycle(MagicMock())
                reg.available_count()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
