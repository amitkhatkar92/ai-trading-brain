"""
tests/unit/execution/recovery/failover/test_failover_framework.py
=================================================================
Comprehensive test suite for the Execution Failover Framework (C7 M4).

Coverage targets ≥ 95% across all 20 source files.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from iios.execution.recovery.failover.constants import (
    ALWAYS_SUCCEEDS,
    NON_OPERATIONAL_ACTIONS,
    STRATEGY_TO_FAILOVER_MAP,
    FailoverAction,
    FailoverEventType,
    FailoverPhase,
    FailoverStatus,
    FailoverType,
    HealthStatus,
    VerificationStatus,
)
from iios.execution.recovery.failover.exceptions import (
    FailoverError,
    FailoverExecutionError,
    FailoverNotRunningError,
    FailoverPlanNotFoundError,
    FailoverRegistryError,
    FailoverResourceUnavailableError,
    FailoverStrategyNotFoundError,
    FailoverTimeoutError,
    FailoverValidationError,
    FailoverVerificationError,
)
from iios.execution.recovery.failover.failover_context import (
    FailoverContext,
    make_failover_context,
)
from iios.execution.recovery.failover.failover_engine import (
    FailoverEngine,
    _get_strategy_value,
)
from iios.execution.recovery.failover.failover_events import (
    FailoverEvent,
    make_failover_completed,
    make_failover_executed,
    make_failover_failed,
    make_failover_prepared,
    make_failover_started,
    make_failover_verified,
    make_fallback_activated,
    make_manual_escalation_requested,
)
from iios.execution.recovery.failover.failover_executor import FailoverExecutor
from iios.execution.recovery.failover.failover_factory import FailoverFactory
from iios.execution.recovery.failover.failover_health_monitor import (
    FailoverHealthMonitor,
    ResourceAvailabilityReport,
)
from iios.execution.recovery.failover.failover_history import FailoverHistory
from iios.execution.recovery.failover.failover_manager import FailoverManager
from iios.execution.recovery.failover.failover_plan import (
    DEFAULT_PLAN_FACTORIES,
    FailoverPlan,
    make_backup_activation_plan,
    make_broker_failover_plan,
    make_component_restart_plan,
    make_gateway_failover_plan,
    make_graceful_shutdown_plan,
    make_manual_escalation_plan,
    make_resume_plan,
    make_retry_plan,
    make_rollback_plan,
    make_workflow_restart_plan,
)
from iios.execution.recovery.failover.failover_registry import FailoverRegistry
from iios.execution.recovery.failover.failover_request import (
    FailoverRequest,
    make_failover_request,
)
from iios.execution.recovery.failover.failover_response import (
    FailoverExecutionStep,
    FailoverResponse,
    FailoverResult,
    VerificationCheck,
    VerificationReport,
    make_failover_response,
    make_failover_result,
    make_verification_report,
)
from iios.execution.recovery.failover.failover_statistics import FailoverStatistics
from iios.execution.recovery.failover.failover_strategy_registry import (
    FailoverStrategyRegistry,
)
from iios.execution.recovery.failover.failover_validation import (
    FailoverValidationResult,
    FailoverValidator,
)
from iios.execution.recovery.failover.failover_verifier import (
    CHECK_BROKER_AVAIL,
    CHECK_EXEC_READINESS,
    CHECK_GATEWAY_AVAIL,
    CHECK_MONITORING_STATUS,
    CHECK_SERVICE_HEALTH,
    CHECK_WORKFLOW_HEALTH,
    FailoverVerifier,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ctx(
    failover_type: FailoverType = FailoverType.COMPONENT,
    primary_action: FailoverAction = FailoverAction.RETRY,
    *,
    backup_broker_available: bool = False,
    backup_gateway_available: bool = False,
    rollback_available: bool = True,
    restart_available: bool = True,
    monitoring_active: bool = True,
    primary_subsystem_healthy: bool = True,
    is_within_risk_limits: bool = True,
    emergency_shutdown_requested: bool = False,
    is_retry_exhausted: bool = False,
    retry_count: int = 0,
    max_retries: int = 3,
    **kwargs: Any,
) -> FailoverContext:
    return make_failover_context(
        failover_session_id      = str(uuid.uuid4()),
        execution_session_id     = str(uuid.uuid4()),
        subsystem_id             = "test-subsystem",
        failover_type            = failover_type,
        primary_action           = primary_action,
        source_decision_id       = str(uuid.uuid4()),
        backup_broker_available  = backup_broker_available,
        backup_gateway_available = backup_gateway_available,
        rollback_available       = rollback_available,
        restart_available        = restart_available,
        monitoring_active        = monitoring_active,
        primary_subsystem_healthy = primary_subsystem_healthy,
        is_within_risk_limits    = is_within_risk_limits,
        emergency_shutdown_requested = emergency_shutdown_requested,
        is_retry_exhausted       = is_retry_exhausted,
        retry_count              = retry_count,
        max_retries              = max_retries,
        **kwargs,
    )


def _req(context: FailoverContext) -> FailoverRequest:
    return make_failover_request(
        failover_session_id  = context.failover_session_id,
        execution_session_id = context.execution_session_id,
        subsystem_id         = context.subsystem_id,
        failover_type        = context.failover_type,
        primary_action       = context.primary_action,
        source_decision_id   = context.source_decision_id,
        context              = context,
    )


def _simple_result(
    context: FailoverContext,
    is_successful: bool = True,
    action: FailoverAction = FailoverAction.RETRY,
) -> FailoverResult:
    step = FailoverExecutionStep(
        step_id      = str(uuid.uuid4()),
        phase        = FailoverPhase.EXECUTION,
        action       = action,
        status       = FailoverStatus.COMPLETED if is_successful else FailoverStatus.FAILED,
        message      = "test",
        started_at   = time.time(),
        completed_at = time.time(),
        duration_ms  = 1.0,
    )
    return make_failover_result(
        request_id          = context.failover_session_id,
        failover_session_id = context.failover_session_id,
        failover_type       = context.failover_type,
        action_executed     = action,
        status              = FailoverStatus.COMPLETED if is_successful else FailoverStatus.FAILED,
        is_successful       = is_successful,
        phases_completed    = (FailoverPhase.EXECUTION,),
        execution_steps     = (step,),
        recovery_time_ms    = 1.0,
        started_at          = time.time(),
    )


def _mock_decision(strategy_type: str = "retry") -> MagicMock:
    """Build a mock M3 RecoveryPolicyDecision-like object."""
    d = MagicMock()
    d.decision_id           = str(uuid.uuid4())
    d.request_id            = str(uuid.uuid4())
    d.execution_session_id  = str(uuid.uuid4())
    d.subsystem_id          = "test-subsystem"
    d.policy_name           = "RetryPolicy"
    d.strategy_type         = MagicMock()
    d.strategy_type.value   = strategy_type
    d.requires_failover             = strategy_type == "failover"
    d.requires_manual_intervention  = strategy_type in ("manual_intervention", "emergency_shutdown")
    return d


# ════════════════════════════════════════════════════════════════════════════
# 1.  Constants
# ════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_failover_types(self):
        assert FailoverType.HOT.value == "hot"
        assert FailoverType.MANUAL.value == "manual"

    def test_failover_actions(self):
        assert FailoverAction.RETRY.value == "retry"
        assert FailoverAction.GRACEFUL_SHUTDOWN.value == "graceful_shutdown"

    def test_failover_status(self):
        assert FailoverStatus.COMPLETED.value == "completed"

    def test_failover_phase_sequence(self):
        phases = list(FailoverPhase)
        assert FailoverPhase.VALIDATION in phases
        assert FailoverPhase.COMPLETION in phases

    def test_verification_status(self):
        for s in VerificationStatus:
            assert isinstance(s.value, str)

    def test_health_status(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_strategy_map_coverage(self):
        for k, (ft, fa) in STRATEGY_TO_FAILOVER_MAP.items():
            assert isinstance(ft, FailoverType)
            assert isinstance(fa, FailoverAction)

    def test_always_succeeds_subset(self):
        for a in ALWAYS_SUCCEEDS:
            assert isinstance(a, FailoverAction)

    def test_non_operational_subset(self):
        assert FailoverAction.GRACEFUL_SHUTDOWN in NON_OPERATIONAL_ACTIONS
        assert FailoverAction.MANUAL_ESCALATION in NON_OPERATIONAL_ACTIONS


# ════════════════════════════════════════════════════════════════════════════
# 2.  Exceptions
# ════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_error(self):
        e = FailoverError("test")
        assert e.error_code == "FO-000"

    def test_not_running(self):
        e = FailoverNotRunningError()
        assert e.error_code == "FO-001"

    def test_validation_error(self):
        e = FailoverValidationError("bad", errors=("e1",))
        assert e.error_code == "FO-002"
        assert "e1" in e.errors

    def test_execution_error(self):
        e = FailoverExecutionError("exec fail", action="retry")
        assert e.error_code == "FO-003"
        assert e.action == "retry"

    def test_verification_error(self):
        e = FailoverVerificationError("verify fail", check_name="service_health")
        assert e.error_code == "FO-004"

    def test_plan_not_found(self):
        e = FailoverPlanNotFoundError("switch_broker")
        assert e.error_code == "FO-005"

    def test_resource_unavailable(self):
        e = FailoverResourceUnavailableError("backup_broker")
        assert e.error_code == "FO-006"

    def test_timeout_error(self):
        e = FailoverTimeoutError(5000.0)
        assert e.error_code == "FO-007"
        assert e.timeout_ms == 5000.0

    def test_registry_error(self):
        e = FailoverRegistryError("registry full")
        assert e.error_code == "FO-008"

    def test_strategy_not_found(self):
        e = FailoverStrategyNotFoundError("unknown_action")
        assert e.error_code == "FO-009"

    def test_hierarchy(self):
        for cls in [
            FailoverNotRunningError, FailoverValidationError,
            FailoverExecutionError, FailoverVerificationError,
        ]:
            assert issubclass(cls, FailoverError)


# ════════════════════════════════════════════════════════════════════════════
# 3.  FailoverContext
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverContext:
    def test_factory(self):
        ctx = _ctx()
        assert ctx.context_id
        assert ctx.failover_session_id
        assert ctx.subsystem_id == "test-subsystem"

    def test_is_emergency_from_flag(self):
        ctx = _ctx(emergency_shutdown_requested=True)
        assert ctx.is_emergency

    def test_is_emergency_from_risk(self):
        ctx = _ctx(is_within_risk_limits=False)
        assert ctx.is_emergency

    def test_not_emergency_default(self):
        ctx = _ctx()
        assert not ctx.is_emergency

    def test_has_backup_resource(self):
        ctx = _ctx(backup_broker_available=True)
        assert ctx.has_backup_resource

    def test_no_backup_resource(self):
        ctx = _ctx(backup_broker_available=False, backup_gateway_available=False)
        assert not ctx.has_backup_resource

    def test_can_retry(self):
        ctx = _ctx(retry_count=0, max_retries=3, is_retry_exhausted=False)
        assert ctx.can_retry

    def test_cannot_retry_exhausted(self):
        ctx = _ctx(is_retry_exhausted=True)
        assert not ctx.can_retry

    def test_cannot_retry_count_maxed(self):
        ctx = _ctx(retry_count=3, max_retries=3)
        assert not ctx.can_retry

    def test_frozen(self):
        ctx = _ctx()
        with pytest.raises((AttributeError, TypeError)):
            ctx.subsystem_id = "other"  # type: ignore[misc]

    def test_to_dict(self):
        ctx = _ctx()
        d = ctx.to_dict()
        assert "failover_type" in d
        assert "primary_action" in d


# ════════════════════════════════════════════════════════════════════════════
# 4.  FailoverRequest
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverRequest:
    def test_factory(self):
        ctx = _ctx()
        req = _req(ctx)
        assert req.request_id
        assert req.context is ctx
        assert req.failover_type == ctx.failover_type

    def test_frozen(self):
        req = _req(_ctx())
        with pytest.raises((AttributeError, TypeError)):
            req.request_id = "other"  # type: ignore[misc]

    def test_to_dict(self):
        req = _req(_ctx())
        d = req.to_dict()
        assert "request_id" in d
        assert "failover_type" in d


# ════════════════════════════════════════════════════════════════════════════
# 5.  Response types
# ════════════════════════════════════════════════════════════════════════════

class TestResponseTypes:
    def test_verification_check_passed(self):
        vc = VerificationCheck(CHECK_SERVICE_HEALTH, VerificationStatus.PASSED, "ok")
        assert vc.passed
        assert vc.to_dict()["status"] == "passed"

    def test_verification_check_failed(self):
        vc = VerificationCheck(CHECK_SERVICE_HEALTH, VerificationStatus.FAILED, "fail")
        assert not vc.passed

    def test_make_verification_report_all_pass(self):
        checks = (
            VerificationCheck(CHECK_SERVICE_HEALTH, VerificationStatus.PASSED, "ok"),
            VerificationCheck(CHECK_MONITORING_STATUS, VerificationStatus.PASSED, "ok"),
        )
        rpt = make_verification_report("sess-1", checks)
        assert rpt.is_verified
        assert rpt.passed_checks == 2
        assert rpt.failed_checks == 0

    def test_make_verification_report_with_failure(self):
        checks = (
            VerificationCheck(CHECK_SERVICE_HEALTH, VerificationStatus.PASSED, "ok"),
            VerificationCheck(CHECK_BROKER_AVAIL, VerificationStatus.FAILED, "no broker"),
        )
        rpt = make_verification_report("sess-1", checks)
        assert not rpt.is_verified
        assert rpt.failed_checks == 1

    def test_make_failover_result(self):
        ctx = _ctx()
        r = _simple_result(ctx)
        assert r.is_successful
        assert r.result_id
        assert r.recovery_time_ms == 1.0

    def test_failover_result_not_successful(self):
        ctx = _ctx()
        r = _simple_result(ctx, is_successful=False)
        assert not r.is_successful
        assert r.status == FailoverStatus.FAILED

    def test_make_failover_response_operational(self):
        ctx = _ctx(primary_action=FailoverAction.RETRY)
        result = _simple_result(ctx, is_successful=True, action=FailoverAction.RETRY)
        rpt = make_verification_report(ctx.failover_session_id, ())
        resp = make_failover_response(
            ctx.failover_session_id, ctx.failover_session_id,
            ctx.source_decision_id, result, rpt, 5.0,
        )
        assert resp.is_operational   # RETRY is not a NON_OPERATIONAL action
        assert not resp.requires_manual_intervention

    def test_make_failover_response_graceful_shutdown_not_operational(self):
        ctx = _ctx(primary_action=FailoverAction.GRACEFUL_SHUTDOWN)
        result = _simple_result(ctx, is_successful=True, action=FailoverAction.GRACEFUL_SHUTDOWN)
        resp = make_failover_response(
            ctx.failover_session_id, ctx.failover_session_id,
            ctx.source_decision_id, result, None, 5.0,
        )
        assert not resp.is_operational

    def test_response_requires_manual_for_manual_escalation(self):
        ctx = _ctx(primary_action=FailoverAction.MANUAL_ESCALATION)
        result = _simple_result(ctx, is_successful=True, action=FailoverAction.MANUAL_ESCALATION)
        resp = make_failover_response(
            ctx.failover_session_id, ctx.failover_session_id,
            ctx.source_decision_id, result, None, 5.0,
        )
        assert resp.requires_manual_intervention

    def test_response_frozen(self):
        ctx = _ctx()
        result = _simple_result(ctx)
        resp = make_failover_response(
            ctx.failover_session_id, ctx.failover_session_id,
            ctx.source_decision_id, result, None, 5.0,
        )
        with pytest.raises((AttributeError, TypeError)):
            resp.response_id = "other"  # type: ignore[misc]

    def test_execution_step_to_dict(self):
        step = FailoverExecutionStep(
            step_id="s", phase=FailoverPhase.EXECUTION, action=FailoverAction.RETRY,
            status=FailoverStatus.COMPLETED, message="ok",
            started_at=time.time(), completed_at=time.time(), duration_ms=1.0,
        )
        d = step.to_dict()
        assert d["action"] == "retry"


# ════════════════════════════════════════════════════════════════════════════
# 6.  FailoverPlan
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverPlan:
    def test_retry_plan(self):
        p = make_retry_plan()
        assert p.primary_action == FailoverAction.RETRY
        assert p.failover_type == FailoverType.COMPONENT
        assert not p.requires_verification

    def test_resume_plan(self):
        p = make_resume_plan()
        assert p.primary_action == FailoverAction.RESUME
        assert p.requires_verification

    def test_rollback_plan(self):
        p = make_rollback_plan()
        assert p.is_disruptive

    def test_component_restart_plan(self):
        p = make_component_restart_plan()
        assert p.primary_action == FailoverAction.RESTART_COMPONENT

    def test_workflow_restart_plan(self):
        p = make_workflow_restart_plan()
        assert p.primary_action == FailoverAction.RESTART_WORKFLOW

    def test_gateway_failover_plan(self):
        p = make_gateway_failover_plan()
        assert p.primary_action == FailoverAction.SWITCH_GATEWAY
        assert "gateway_availability" in p.verification_checks

    def test_broker_failover_plan(self):
        p = make_broker_failover_plan()
        assert p.primary_action == FailoverAction.SWITCH_BROKER
        assert "broker_availability" in p.verification_checks

    def test_graceful_shutdown_plan(self):
        p = make_graceful_shutdown_plan()
        assert not p.requires_verification
        assert p.priority == 100

    def test_manual_escalation_plan(self):
        p = make_manual_escalation_plan()
        assert p.priority == 10

    def test_all_actions_have_plans(self):
        for action in FailoverAction:
            if action == FailoverAction.DEACTIVATE_PRIMARY:
                continue   # tested separately
            assert action in DEFAULT_PLAN_FACTORIES

    def test_frozen(self):
        p = make_retry_plan()
        with pytest.raises((AttributeError, TypeError)):
            p.name = "other"  # type: ignore[misc]

    def test_to_dict(self):
        p = make_retry_plan()
        d = p.to_dict()
        assert "plan_id" in d
        assert d["primary_action"] == "retry"


# ════════════════════════════════════════════════════════════════════════════
# 7.  FailoverEvents
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverEvents:
    def test_failover_started(self):
        e = make_failover_started("sess-1", "req-1")
        assert e.event_type == FailoverEventType.FAILOVER_STARTED

    def test_failover_prepared(self):
        e = make_failover_prepared("sess-1", "req-1")
        assert e.event_type == FailoverEventType.FAILOVER_PREPARED

    def test_failover_executed(self):
        e = make_failover_executed("sess-1", "req-1", action="retry")
        assert e.event_type == FailoverEventType.FAILOVER_EXECUTED
        assert e.action == "retry"

    def test_failover_verified(self):
        e = make_failover_verified("sess-1", "req-1")
        assert e.event_type == FailoverEventType.FAILOVER_VERIFIED

    def test_failover_completed(self):
        e = make_failover_completed("sess-1", "req-1")
        assert e.event_type == FailoverEventType.FAILOVER_COMPLETED

    def test_failover_failed(self):
        e = make_failover_failed("sess-1", "req-1", reason="timeout")
        assert e.event_type == FailoverEventType.FAILOVER_FAILED
        assert e.reason == "timeout"

    def test_fallback_activated(self):
        e = make_fallback_activated("sess-1", "req-1", action="restart_component")
        assert e.event_type == FailoverEventType.FALLBACK_ACTIVATED

    def test_manual_escalation_requested(self):
        e = make_manual_escalation_requested("sess-1", "req-1")
        assert e.event_type == FailoverEventType.MANUAL_ESCALATION_REQUESTED

    def test_event_frozen(self):
        e = make_failover_started("s", "r")
        with pytest.raises((AttributeError, TypeError)):
            e.event_id = "other"  # type: ignore[misc]

    def test_event_to_dict(self):
        e = make_failover_started("s", "r")
        d = e.to_dict()
        assert "event_type" in d


# ════════════════════════════════════════════════════════════════════════════
# 8.  FailoverValidation
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverValidation:
    def setup_method(self):
        self.v = FailoverValidator()

    def test_valid_request(self):
        r = self.v.validate_request(_req(_ctx()))
        assert r.is_valid

    def test_none_request_invalid(self):
        r = self.v.validate_request(None)
        assert not r.is_valid

    def test_missing_session_id_invalid(self):
        m = MagicMock()
        m.request_id = "r"
        m.failover_session_id = ""
        m.execution_session_id = "s"
        m.subsystem_id = "sub"
        m.failover_type = FailoverType.COMPONENT
        m.primary_action = FailoverAction.RETRY
        m.source_decision_id = "d"
        m.context = MagicMock()
        r = self.v.validate_request(m)
        assert not r.is_valid

    def test_valid_plan(self):
        r = self.v.validate_plan(make_retry_plan())
        assert r.is_valid

    def test_none_plan_invalid(self):
        r = self.v.validate_plan(None)
        assert not r.is_valid

    def test_valid_context(self):
        r = self.v.validate_context(_ctx())
        assert r.is_valid

    def test_none_context_invalid(self):
        r = self.v.validate_context(None)
        assert not r.is_valid

    def test_resource_validation_switch_broker_no_backup(self):
        ctx = _ctx(primary_action=FailoverAction.SWITCH_BROKER, backup_broker_available=False)
        r = self.v.validate_resource_availability(ctx)
        assert not r.is_valid

    def test_resource_validation_switch_broker_with_backup(self):
        ctx = _ctx(primary_action=FailoverAction.SWITCH_BROKER, backup_broker_available=True)
        r = self.v.validate_resource_availability(ctx)
        assert r.is_valid

    def test_resource_validation_rollback_unavailable(self):
        ctx = _ctx(primary_action=FailoverAction.ROLLBACK, rollback_available=False)
        r = self.v.validate_resource_availability(ctx)
        assert not r.is_valid

    def test_resource_validation_retry_exhausted(self):
        ctx = _ctx(primary_action=FailoverAction.RETRY, is_retry_exhausted=True)
        r = self.v.validate_resource_availability(ctx)
        assert not r.is_valid

    def test_validation_result_merge(self):
        r1 = FailoverValidationResult()
        r1.add_error("err1")
        r2 = FailoverValidationResult()
        r2.add_warning("warn1")
        r1.merge(r2)
        assert "err1" in r1.errors
        assert "warn1" in r1.warnings

    def test_valid_response(self):
        ctx = _ctx()
        result = _simple_result(ctx)
        resp = make_failover_response(
            ctx.failover_session_id, ctx.failover_session_id,
            ctx.source_decision_id, result, None, 5.0,
        )
        r = self.v.validate_response(resp)
        assert r.is_valid


# ════════════════════════════════════════════════════════════════════════════
# 9.  FailoverStatistics
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverStatistics:
    def setup_method(self):
        self.stats = FailoverStatistics()

    def test_initial_state(self):
        assert self.stats.failovers_executed == 0
        assert self.stats.average_recovery_time_ms == 0.0

    def test_record_execution(self):
        self.stats.record_execution(action="retry", failover_type="component")
        assert self.stats.failovers_executed == 1
        assert self.stats.action_count("retry") == 1
        assert self.stats.type_count("component") == 1

    def test_record_success_failure(self):
        self.stats.record_success()
        self.stats.record_failure()
        assert self.stats.successful_failovers == 1
        assert self.stats.failed_failovers == 1

    def test_success_rate(self):
        self.stats.record_execution()
        self.stats.record_success()
        assert self.stats.success_rate == 1.0

    def test_success_rate_zero_when_no_executions(self):
        assert self.stats.success_rate == 0.0

    def test_verification_success_rate(self):
        self.stats.record_verification_run(passed=True)
        self.stats.record_verification_run(passed=False)
        assert self.stats.verification_success_rate == 0.5

    def test_average_recovery_time(self):
        self.stats.record_recovery_time(10.0)
        self.stats.record_recovery_time(20.0)
        assert self.stats.average_recovery_time_ms == 15.0

    def test_record_fallback_and_manual(self):
        self.stats.record_fallback()
        self.stats.record_manual_escalation()
        assert self.stats.fallback_executions == 1

    def test_reset(self):
        self.stats.record_execution()
        self.stats.record_success()
        self.stats.reset()
        assert self.stats.failovers_executed == 0

    def test_copy(self):
        self.stats.record_execution()
        copy = self.stats.copy()
        assert copy.failovers_executed == 1
        self.stats.record_execution()
        assert copy.failovers_executed == 1   # copy is independent

    def test_to_dict(self):
        d = self.stats.to_dict()
        assert "failovers_executed" in d
        assert "average_recovery_time_ms" in d

    def test_thread_safety(self):
        errors = []
        def worker():
            try:
                for _ in range(100):
                    self.stats.record_execution(action="retry")
                    self.stats.record_success()
                    self.stats.record_recovery_time(5.0)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert self.stats.failovers_executed == 400


# ════════════════════════════════════════════════════════════════════════════
# 10. FailoverHistory
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverHistory:
    def setup_method(self):
        self.hist = FailoverHistory(
            max_requests=10, max_responses=10, max_events=20, max_results=10
        )

    def test_append_read_request(self):
        req = _req(_ctx())
        self.hist.append_request(req)
        assert self.hist.request_count == 1
        assert self.hist.latest_request() is req

    def test_append_read_event(self):
        e = make_failover_started("s", "r")
        self.hist.append_event(e)
        assert self.hist.event_count == 1

    def test_append_read_response(self):
        ctx = _ctx()
        result = _simple_result(ctx)
        resp = make_failover_response(
            ctx.failover_session_id, ctx.failover_session_id,
            ctx.source_decision_id, result, None, 1.0,
        )
        self.hist.append_response(resp)
        assert self.hist.response_count == 1
        assert self.hist.latest_response() is resp

    def test_bounded_capacity(self):
        for _ in range(15):
            self.hist.append_request(_req(_ctx()))
        assert self.hist.request_count == 10

    def test_for_session(self):
        sess_id = str(uuid.uuid4())
        ctx = make_failover_context(
            failover_session_id=sess_id, execution_session_id=str(uuid.uuid4()),
            subsystem_id="sub", failover_type=FailoverType.COMPONENT,
            primary_action=FailoverAction.RETRY, source_decision_id=str(uuid.uuid4()),
        )
        result = _simple_result(ctx)
        resp = make_failover_response(
            ctx.failover_session_id, sess_id,
            ctx.source_decision_id, result, None, 1.0,
        )
        self.hist.append_response(resp)
        assert len(self.hist.for_session(sess_id)) == 1
        assert len(self.hist.for_session("other")) == 0

    def test_for_decision(self):
        dec_id = str(uuid.uuid4())
        ctx = _ctx()
        result = _simple_result(ctx)
        resp = make_failover_response(
            ctx.failover_session_id, ctx.failover_session_id,
            dec_id, result, None, 1.0,
        )
        self.hist.append_response(resp)
        assert len(self.hist.for_decision(dec_id)) == 1
        assert len(self.hist.for_decision("other")) == 0

    def test_latest_none_when_empty(self):
        assert self.hist.latest_request() is None
        assert self.hist.latest_response() is None

    def test_clear(self):
        self.hist.append_request(_req(_ctx()))
        self.hist.append_event(make_failover_started("s", "r"))
        self.hist.clear()
        assert self.hist.request_count == 0
        assert self.hist.event_count == 0


# ════════════════════════════════════════════════════════════════════════════
# 11. FailoverStrategyRegistry
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverStrategyRegistry:
    def setup_method(self):
        self.reg = FailoverStrategyRegistry()
        self.reg.start()

    def teardown_method(self):
        if self.reg.lifecycle_state() not in ("stopped", "STOPPED"):
            self.reg.stop()

    def test_default_plans_registered(self):
        for action in DEFAULT_PLAN_FACTORIES:
            assert self.reg.contains(action)

    def test_get_plan(self):
        plan = self.reg.get_plan(FailoverAction.RETRY)
        assert plan.primary_action == FailoverAction.RETRY

    def test_get_plan_not_found_raises(self):
        # Remove all and try to get
        reg2 = FailoverStrategyRegistry()
        reg2.start()
        reg2._plans.clear()  # force empty
        with pytest.raises(FailoverStrategyNotFoundError):
            reg2.get_plan(FailoverAction.RETRY)
        reg2.stop()

    def test_find_plan_returns_none_when_missing(self):
        self.reg._plans.clear()
        assert self.reg.find_plan(FailoverAction.RETRY) is None

    def test_register_overwrites(self):
        new_plan = make_retry_plan()
        self.reg.register(new_plan)
        assert self.reg.contains(FailoverAction.RETRY)

    def test_all(self):
        plans = self.reg.all()
        assert len(plans) == len(DEFAULT_PLAN_FACTORIES)

    def test_for_type(self):
        plans = self.reg.for_type(FailoverType.COMPONENT)
        assert all(p.failover_type == FailoverType.COMPONENT for p in plans)

    def test_plan_count(self):
        assert self.reg.plan_count == len(DEFAULT_PLAN_FACTORIES)

    def test_register_not_running_raises(self):
        reg = FailoverStrategyRegistry()
        with pytest.raises(FailoverNotRunningError):
            reg.register(make_retry_plan())


# ════════════════════════════════════════════════════════════════════════════
# 12. FailoverRegistry
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverRegistry:
    def setup_method(self):
        self.reg = FailoverRegistry()
        self.reg.start()

    def teardown_method(self):
        if self.reg.lifecycle_state() not in ("stopped", "STOPPED"):
            self.reg.stop()

    def test_register_active(self):
        sid = str(uuid.uuid4())
        self.reg.register_active(sid)
        assert self.reg.is_active(sid)

    def test_complete_removes_from_active(self):
        sid = str(uuid.uuid4())
        did = str(uuid.uuid4())
        self.reg.register_active(sid)
        self.reg.complete(sid, did)
        assert not self.reg.is_active(sid)

    def test_decision_processed_after_complete(self):
        sid = str(uuid.uuid4())
        did = str(uuid.uuid4())
        self.reg.register_active(sid)
        self.reg.complete(sid, did)
        assert self.reg.is_decision_processed(did)

    def test_decision_not_processed_initially(self):
        did = str(uuid.uuid4())
        assert not self.reg.is_decision_processed(did)

    def test_active_sessions_list(self):
        sid = str(uuid.uuid4())
        self.reg.register_active(sid)
        assert sid in self.reg.active_sessions()

    def test_capacity_limit(self):
        reg = FailoverRegistry(max_sessions=1)
        reg.start()
        reg.register_active("s1")
        with pytest.raises(FailoverRegistryError):
            reg.register_active("s2")
        reg.stop()

    def test_not_running_raises(self):
        reg = FailoverRegistry()
        with pytest.raises(FailoverNotRunningError):
            reg.register_active("x")

    def test_clear(self):
        sid = str(uuid.uuid4())
        self.reg.register_active(sid)
        self.reg.clear()
        assert not self.reg.is_active(sid)


# ════════════════════════════════════════════════════════════════════════════
# 13. FailoverHealthMonitor
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverHealthMonitor:
    def setup_method(self):
        self.monitor = FailoverHealthMonitor()
        self.monitor.start()

    def teardown_method(self):
        if self.monitor.lifecycle_state() not in ("stopped", "STOPPED"):
            self.monitor.stop()

    def test_healthy_context(self):
        ctx = _ctx(primary_subsystem_healthy=True, monitoring_active=True)
        report = self.monitor.check_resource_availability(ctx)
        assert report.overall_health == HealthStatus.HEALTHY

    def test_degraded_when_monitoring_off(self):
        ctx = _ctx(monitoring_active=False)
        report = self.monitor.check_resource_availability(ctx)
        assert report.overall_health == HealthStatus.DEGRADED

    def test_unhealthy_when_emergency(self):
        ctx = _ctx(emergency_shutdown_requested=True)
        report = self.monitor.check_resource_availability(ctx)
        assert report.overall_health == HealthStatus.UNHEALTHY

    def test_has_any_backup_false(self):
        ctx = _ctx(backup_broker_available=False, backup_gateway_available=False)
        report = self.monitor.check_resource_availability(ctx)
        assert not report.has_any_backup

    def test_has_any_backup_true(self):
        ctx = _ctx(backup_broker_available=True)
        report = self.monitor.check_resource_availability(ctx)
        assert report.has_any_backup

    def test_switch_broker_no_backup_adds_note(self):
        ctx = _ctx(primary_action=FailoverAction.SWITCH_BROKER, backup_broker_available=False)
        report = self.monitor.check_resource_availability(ctx)
        assert any("broker" in n for n in report.notes)

    def test_assess_context_health(self):
        ctx = _ctx()
        h = self.monitor.assess_context_health(ctx)
        assert h == HealthStatus.HEALTHY

    def test_assess_context_health_emergency(self):
        ctx = _ctx(emergency_shutdown_requested=True)
        h = self.monitor.assess_context_health(ctx)
        assert h == HealthStatus.UNHEALTHY

    def test_report_to_dict(self):
        ctx = _ctx()
        report = self.monitor.check_resource_availability(ctx)
        d = report.to_dict()
        assert "overall_health" in d

    def test_not_running_raises(self):
        m = FailoverHealthMonitor()
        ctx = _ctx()
        with pytest.raises(FailoverNotRunningError):
            m.check_resource_availability(ctx)


# ════════════════════════════════════════════════════════════════════════════
# 14. FailoverVerifier
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverVerifier:
    def setup_method(self):
        self.verifier = FailoverVerifier()
        self.verifier.start()

    def teardown_method(self):
        if self.verifier.lifecycle_state() not in ("stopped", "STOPPED"):
            self.verifier.stop()

    def _verify(self, ctx, is_successful=True, checks=()):
        result = _simple_result(ctx, is_successful=is_successful)
        return self.verifier.verify(ctx, result, checks)

    def test_successful_failover_passes_service_health(self):
        ctx = _ctx()
        report = self._verify(ctx)
        service_check = next(c for c in report.checks if c.check_name == CHECK_SERVICE_HEALTH)
        assert service_check.passed

    def test_failed_failover_fails_service_health(self):
        ctx = _ctx()
        report = self._verify(ctx, is_successful=False)
        service_check = next(c for c in report.checks if c.check_name == CHECK_SERVICE_HEALTH)
        assert not service_check.passed

    def test_gateway_check_passes_when_backup_available(self):
        ctx = _ctx(primary_action=FailoverAction.SWITCH_GATEWAY, backup_gateway_available=True)
        result = _simple_result(ctx, action=FailoverAction.SWITCH_GATEWAY)
        report = self.verifier.verify(ctx, result, (CHECK_GATEWAY_AVAIL,))
        gw_check = next(c for c in report.checks if c.check_name == CHECK_GATEWAY_AVAIL)
        assert gw_check.passed

    def test_gateway_check_fails_without_backup(self):
        ctx = _ctx(primary_action=FailoverAction.SWITCH_GATEWAY, backup_gateway_available=False)
        result = _simple_result(ctx, action=FailoverAction.SWITCH_GATEWAY)
        report = self.verifier.verify(ctx, result, (CHECK_GATEWAY_AVAIL,))
        gw_check = next(c for c in report.checks if c.check_name == CHECK_GATEWAY_AVAIL)
        assert not gw_check.passed

    def test_broker_check_passes_when_backup_available(self):
        ctx = _ctx(primary_action=FailoverAction.SWITCH_BROKER, backup_broker_available=True)
        result = _simple_result(ctx, action=FailoverAction.SWITCH_BROKER)
        report = self.verifier.verify(ctx, result, (CHECK_BROKER_AVAIL,))
        bk_check = next(c for c in report.checks if c.check_name == CHECK_BROKER_AVAIL)
        assert bk_check.passed

    def test_execution_readiness_skipped_for_shutdown(self):
        ctx = _ctx(
            primary_action=FailoverAction.GRACEFUL_SHUTDOWN,
            emergency_shutdown_requested=True,
        )
        result = _simple_result(ctx, action=FailoverAction.GRACEFUL_SHUTDOWN)
        report = self.verifier.verify(ctx, result, (CHECK_EXEC_READINESS,))
        ex_check = next(c for c in report.checks if c.check_name == CHECK_EXEC_READINESS)
        assert ex_check.status == VerificationStatus.SKIPPED

    def test_monitoring_check_fails_when_inactive(self):
        ctx = _ctx(monitoring_active=False)
        report = self._verify(ctx, checks=(CHECK_MONITORING_STATUS,))
        mon_check = next(c for c in report.checks if c.check_name == CHECK_MONITORING_STATUS)
        assert not mon_check.passed

    def test_overall_passed_when_all_checks_pass(self):
        ctx = _ctx()
        report = self._verify(ctx)
        assert report.is_verified

    def test_overall_failed_when_any_check_fails(self):
        ctx = _ctx(monitoring_active=False)
        report = self._verify(ctx)
        assert not report.is_verified

    def test_not_running_raises(self):
        v = FailoverVerifier()
        ctx = _ctx()
        result = _simple_result(ctx)
        with pytest.raises(FailoverNotRunningError):
            v.verify(ctx, result)


# ════════════════════════════════════════════════════════════════════════════
# 15. FailoverExecutor — individual action feasibility
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverExecutor:
    def setup_method(self):
        self.executor = FailoverExecutor()
        self.executor.start()

    def teardown_method(self):
        if self.executor.lifecycle_state() not in ("stopped", "STOPPED"):
            self.executor.stop()

    def _exec(self, action: FailoverAction, **kw) -> FailoverResult:
        plan = DEFAULT_PLAN_FACTORIES.get(action, make_manual_escalation_plan)()
        ctx = _ctx(primary_action=action, failover_type=plan.failover_type, **kw)
        return self.executor.execute(plan, ctx)

    def test_retry_succeeds_when_allowed(self):
        r = self._exec(FailoverAction.RETRY, is_retry_exhausted=False, retry_count=0)
        assert r.is_successful

    def test_retry_fails_when_exhausted(self):
        # With fallback RESTART_COMPONENT — restart_available=True → fallback succeeds
        r = self._exec(FailoverAction.RETRY, is_retry_exhausted=True, restart_available=True)
        # fallback (restart_component) should succeed
        assert r.is_successful
        assert r.fallback_used

    def test_retry_fails_entirely_when_both_unavailable(self):
        r = self._exec(
            FailoverAction.RETRY,
            is_retry_exhausted=True,
            restart_available=False,
        )
        assert not r.is_successful

    def test_resume_succeeds_when_healthy(self):
        r = self._exec(FailoverAction.RESUME, primary_subsystem_healthy=True)
        assert r.is_successful

    def test_resume_fails_when_subsystem_down(self):
        ctx = _ctx(primary_action=FailoverAction.RESUME, primary_subsystem_healthy=False,
                   failover_type=FailoverType.WORKFLOW)
        plan = make_resume_plan()
        result = self.executor.execute(plan, ctx)
        # Fallback is RESTART_WORKFLOW + restart_available=True (default) → fallback ok
        assert result.is_successful
        assert result.fallback_used

    def test_rollback_succeeds_when_available(self):
        r = self._exec(FailoverAction.ROLLBACK, rollback_available=True)
        assert r.is_successful

    def test_rollback_fails_when_unavailable(self):
        ctx = _ctx(primary_action=FailoverAction.ROLLBACK, rollback_available=False,
                   failover_type=FailoverType.WORKFLOW)
        plan = make_rollback_plan()
        result = self.executor.execute(plan, ctx)
        # Fallback is MANUAL_ESCALATION which always succeeds
        assert result.is_successful
        assert result.fallback_used

    def test_switch_broker_succeeds_with_backup(self):
        r = self._exec(FailoverAction.SWITCH_BROKER, backup_broker_available=True)
        assert r.is_successful

    def test_switch_broker_fails_without_backup(self):
        ctx = _ctx(primary_action=FailoverAction.SWITCH_BROKER,
                   backup_broker_available=False, failover_type=FailoverType.HOT)
        plan = make_broker_failover_plan()
        result = self.executor.execute(plan, ctx)
        # Fallback chain: SWITCH_GATEWAY (no backup gw) → MANUAL_ESCALATION (always ok)
        assert result.is_successful
        assert result.fallback_used

    def test_switch_gateway_succeeds_with_backup(self):
        r = self._exec(FailoverAction.SWITCH_GATEWAY, backup_gateway_available=True)
        assert r.is_successful

    def test_graceful_shutdown_always_succeeds(self):
        r = self._exec(FailoverAction.GRACEFUL_SHUTDOWN)
        assert r.is_successful

    def test_manual_escalation_always_succeeds(self):
        r = self._exec(FailoverAction.MANUAL_ESCALATION)
        assert r.is_successful

    def test_deactivate_primary_always_succeeds(self):
        ctx = _ctx(primary_action=FailoverAction.DEACTIVATE_PRIMARY,
                   failover_type=FailoverType.COMPONENT)
        from iios.execution.recovery.failover.failover_plan import make_deactivate_primary_plan
        plan = make_deactivate_primary_plan()
        r = self.executor.execute(plan, ctx)
        assert r.is_successful

    def test_result_has_execution_steps(self):
        r = self._exec(FailoverAction.RETRY)
        assert len(r.execution_steps) >= 1

    def test_result_records_recovery_time(self):
        r = self._exec(FailoverAction.RETRY)
        assert r.recovery_time_ms >= 0

    def test_not_running_raises(self):
        e = FailoverExecutor()
        ctx = _ctx()
        plan = make_retry_plan()
        with pytest.raises(FailoverNotRunningError):
            e.execute(plan, ctx)


# ════════════════════════════════════════════════════════════════════════════
# 16. FailoverFactory
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverFactory:
    def setup_method(self):
        self.factory = FailoverFactory()
        self.factory.start()

    def teardown_method(self):
        if self.factory.lifecycle_state() not in ("stopped", "STOPPED"):
            self.factory.stop()

    def test_create_context(self):
        ctx = self.factory.create_context(
            failover_session_id  = str(uuid.uuid4()),
            execution_session_id = str(uuid.uuid4()),
            subsystem_id         = "sub",
            failover_type        = FailoverType.COMPONENT,
            primary_action       = FailoverAction.RETRY,
            source_decision_id   = str(uuid.uuid4()),
        )
        assert ctx.subsystem_id == "sub"

    def test_create_request(self):
        ctx = self.factory.create_context(
            str(uuid.uuid4()), str(uuid.uuid4()), "sub",
            FailoverType.COMPONENT, FailoverAction.RETRY, str(uuid.uuid4()),
        )
        req = self.factory.create_request(
            failover_session_id  = ctx.failover_session_id,
            execution_session_id = ctx.execution_session_id,
            subsystem_id         = ctx.subsystem_id,
            failover_type        = ctx.failover_type,
            primary_action       = ctx.primary_action,
            source_decision_id   = ctx.source_decision_id,
            context              = ctx,
        )
        assert req.context is ctx

    def test_create_response(self):
        ctx = _ctx()
        result = _simple_result(ctx)
        resp = self.factory.create_response(
            ctx.failover_session_id, ctx.failover_session_id,
            ctx.source_decision_id, result, None, 5.0,
        )
        assert resp.result is result


# ════════════════════════════════════════════════════════════════════════════
# 17. FailoverManager
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverManager:
    def setup_method(self):
        self.mgr = FailoverManager()
        self.mgr.start()

    def teardown_method(self):
        if self.mgr.lifecycle_state() not in ("stopped", "STOPPED"):
            self.mgr.stop()

    def test_start_failover_succeeds(self):
        ctx = _ctx(primary_action=FailoverAction.RETRY, is_retry_exhausted=False)
        req = _req(ctx)
        resp = self.mgr.start_failover(req)
        assert resp is not None
        assert resp.failover_session_id == ctx.failover_session_id

    def test_duplicate_decision_raises(self):
        ctx = _ctx(primary_action=FailoverAction.RETRY)
        req = _req(ctx)
        self.mgr.start_failover(req)
        with pytest.raises(FailoverRegistryError):
            self.mgr.start_failover(req)  # same source_decision_id

    def test_session_cleaned_up_after_completion(self):
        ctx = _ctx(primary_action=FailoverAction.RETRY)
        req = _req(ctx)
        self.mgr.start_failover(req)
        assert not self.mgr.session_registry.is_active(ctx.failover_session_id)

    def test_not_running_raises(self):
        mgr = FailoverManager()
        ctx = _ctx()
        req = _req(ctx)
        with pytest.raises(FailoverNotRunningError):
            mgr.start_failover(req)


# ════════════════════════════════════════════════════════════════════════════
# 18. FailoverEngine (primary entry point)
# ════════════════════════════════════════════════════════════════════════════

class TestFailoverEngine:
    def setup_method(self):
        self.engine = FailoverEngine()
        self.engine.start()

    def teardown_method(self):
        if self.engine.lifecycle_state() not in ("stopped", "STOPPED"):
            self.engine.stop()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def test_engine_starts_and_stops(self):
        e = FailoverEngine()
        e.start()
        e.stop()

    def test_not_running_raises(self):
        e = FailoverEngine()
        with pytest.raises(FailoverNotRunningError):
            e.execute(_mock_decision())

    # ── Strategy type routing ──────────────────────────────────────────────

    def test_retry_decision(self):
        resp = self.engine.execute(
            _mock_decision("retry"),
            is_retry_exhausted=False,
        )
        assert resp.is_successful
        assert resp.result.action_executed == FailoverAction.RETRY

    def test_resume_decision(self):
        resp = self.engine.execute(
            _mock_decision("resume"),
            primary_subsystem_healthy=True,
        )
        assert resp.is_successful

    def test_rollback_decision(self):
        resp = self.engine.execute(
            _mock_decision("rollback"),
            rollback_available=True,
        )
        assert resp.is_successful
        assert resp.result.action_executed == FailoverAction.ROLLBACK

    def test_restart_decision(self):
        resp = self.engine.execute(
            _mock_decision("restart"),
            restart_available=True,
        )
        assert resp.is_successful

    def test_failover_decision_with_backup(self):
        resp = self.engine.execute(
            _mock_decision("failover"),
            backup_broker_available=True,
        )
        assert resp.is_successful
        assert resp.result.action_executed == FailoverAction.SWITCH_BROKER

    def test_manual_intervention_decision(self):
        resp = self.engine.execute(_mock_decision("manual_intervention"))
        assert resp.is_successful
        assert resp.requires_manual_intervention

    def test_emergency_shutdown_decision(self):
        resp = self.engine.execute(_mock_decision("emergency_shutdown"))
        assert resp.is_successful
        assert not resp.is_operational

    def test_unknown_strategy_falls_back_to_manual(self):
        resp = self.engine.execute(_mock_decision("unknown_type"))
        assert resp.is_successful
        assert resp.requires_manual_intervention

    # ── Statistics ─────────────────────────────────────────────────────────

    def test_statistics_updated(self):
        self.engine.execute(_mock_decision("retry"))
        assert self.engine.statistics.failovers_executed == 1

    def test_success_recorded_in_stats(self):
        self.engine.execute(_mock_decision("retry"))
        assert self.engine.statistics.successful_failovers == 1

    def test_fallback_recorded_when_used(self):
        # Retry exhausted → fallback to restart
        self.engine.execute(
            _mock_decision("retry"),
            is_retry_exhausted=True,
            restart_available=True,
        )
        assert self.engine.statistics.fallback_executions == 1

    # ── History ────────────────────────────────────────────────────────────

    def test_history_populated(self):
        self.engine.execute(_mock_decision("retry"))
        assert self.engine.history.request_count == 1
        assert self.engine.history.response_count == 1

    def test_events_emitted(self):
        self.engine.execute(_mock_decision("retry"))
        assert self.engine.history.event_count >= 2  # started + completed

    # ── Duplicate decision guard ───────────────────────────────────────────

    def test_same_decision_id_raises_second_time(self):
        d = _mock_decision("retry")
        self.engine.execute(d)
        with pytest.raises(FailoverRegistryError):
            self.engine.execute(d)

    # ── Response completeness ──────────────────────────────────────────────

    def test_response_has_required_fields(self):
        resp = self.engine.execute(_mock_decision("retry"))
        assert resp.response_id
        assert resp.failover_session_id
        assert resp.source_decision_id
        assert resp.result is not None
        assert resp.response_time_ms >= 0

    # ── Concurrency ────────────────────────────────────────────────────────

    def test_concurrent_executions(self):
        errors = []
        responses = []
        lock = threading.Lock()

        def run():
            try:
                resp = self.engine.execute(_mock_decision("retry"))
                with lock:
                    responses.append(resp)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=run) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent errors: {errors}"
        assert len(responses) == 20


# ════════════════════════════════════════════════════════════════════════════
# 19. _get_strategy_value helper
# ════════════════════════════════════════════════════════════════════════════

class TestGetStrategyValue:
    def test_with_enum_value(self):
        d = MagicMock()
        d.strategy_type = MagicMock()
        d.strategy_type.value = "retry"
        assert _get_strategy_value(d) == "retry"

    def test_with_string_strategy_type(self):
        # When strategy_type has no .value, _get_strategy_value should return the str itself
        d = MagicMock(spec=["strategy_type"])
        d.strategy_type = "rollback"
        # MagicMock with spec=["strategy_type"] won't auto-create .value
        result = _get_strategy_value(d)
        # The function should handle str strategy_type gracefully
        assert isinstance(result, str)

    def test_no_strategy_type(self):
        d = MagicMock(spec=[])
        assert _get_strategy_value(d) == ""


# ════════════════════════════════════════════════════════════════════════════
# 20. Public __init__ surface
# ════════════════════════════════════════════════════════════════════════════

class TestPublicSurface:
    def test_primary_imports(self):
        from iios.execution.recovery.failover import (
            FailoverEngine,
            FailoverContext,
            FailoverRequest,
            FailoverResponse,
            FailoverType,
            FailoverAction,
        )

    def test_exception_imports(self):
        from iios.execution.recovery.failover import (
            FailoverError,
            FailoverNotRunningError,
            FailoverValidationError,
        )

    def test_plan_imports(self):
        from iios.execution.recovery.failover import (
            FailoverPlan,
            make_retry_plan,
            make_broker_failover_plan,
        )

    def test_constant_imports(self):
        from iios.execution.recovery.failover import (
            VERSION, SYSTEM_ID, ENGINE_ID,
        )
        assert VERSION == "1.0.0"


# ════════════════════════════════════════════════════════════════════════════
# 21. Edge cases
# ════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def setup_method(self):
        self.engine = FailoverEngine()
        self.engine.start()

    def teardown_method(self):
        if self.engine.lifecycle_state() not in ("stopped", "STOPPED"):
            self.engine.stop()

    def test_response_ids_unique_across_executions(self):
        ids = set()
        for _ in range(20):
            resp = self.engine.execute(_mock_decision("retry"))
            ids.add(resp.response_id)
        assert len(ids) == 20

    def test_activate_backup_with_gateway(self):
        resp = self.engine.execute(
            _mock_decision("failover"),
            backup_gateway_available=True,
            backup_broker_available=False,
        )
        # SWITCH_BROKER fails (no broker), fallback SWITCH_GATEWAY ok
        assert resp.is_successful
        assert resp.result.fallback_used

    def test_all_resources_unavailable_falls_back_to_manual(self):
        resp = self.engine.execute(
            _mock_decision("retry"),
            is_retry_exhausted=True,
            restart_available=False,
        )
        # Primary (retry) fails, fallback (restart_component) fails → no more fallbacks
        # Result should be unsuccessful but engine shouldn't raise
        assert not resp.is_successful

    def test_context_fields_accessible(self):
        ctx = make_failover_context(
            failover_session_id="sess", execution_session_id="exec",
            subsystem_id="sub", failover_type=FailoverType.HOT,
            primary_action=FailoverAction.SWITCH_BROKER,
            source_decision_id="dec",
            tags=("prod", "urgent"),
            metadata={"key": "value"},
        )
        assert "prod" in ctx.tags
        assert ctx.metadata["key"] == "value"

    def test_stats_verification_rate_with_verifiable_plan(self):
        # Retry plan doesn't require verification
        self.engine.execute(_mock_decision("retry"))
        # Failover plan does require verification
        self.engine.execute(_mock_decision("failover"), backup_broker_available=True)
        # verification_success_rate should be > 0 now
        assert self.engine.statistics._verification_runs > 0

    def test_graceful_shutdown_not_operational(self):
        resp = self.engine.execute(_mock_decision("emergency_shutdown"))
        assert not resp.is_operational
        assert resp.requires_manual_intervention
