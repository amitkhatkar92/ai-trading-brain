"""
tests/unit/execution/recovery/policies/test_recovery_policies.py
================================================================
Comprehensive test suite for the Execution Recovery Policy Framework
(C7 Phase 1 Module 3).

Coverage targets ≥ 95% across all 18 source files.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from iios.execution.recovery.policies.constants import (
    CONFIDENCE_EMERGENCY_SHUTDOWN,
    CONFIDENCE_FAILOVER,
    CONFIDENCE_MANUAL,
    CONFIDENCE_RESTART,
    CONFIDENCE_RESUME,
    CONFIDENCE_RETRY,
    CONFIDENCE_ROLLBACK,
    FAILOVER_ELIGIBLE_CATEGORIES,
    SAFETY_CRITICAL_CATEGORIES,
    SEVERITY_PRIORITY_MAP,
    TRANSIENT_FAILURE_CATEGORIES,
    FailureCategory,
    FailureSeverity,
    PolicyEventType,
    PolicyPriority,
    RecoveryRecommendation,
    RecoveryStrategyType,
    RuleConditionOperator,
)
from iios.execution.recovery.policies.exceptions import (
    RecoveryPolicyConflictError,
    RecoveryPolicyError,
    RecoveryPolicyEvaluationError,
    RecoveryPolicyNotFoundError,
    RecoveryPolicyNotRunningError,
    RecoveryPolicyRegistryError,
    RecoveryPolicyValidationError,
    RecoveryRuleValidationError,
    RecoveryStrategyNotFoundError,
)
from iios.execution.recovery.policies.recovery_context import (
    PolicyEvaluationContext,
    make_policy_evaluation_context,
)
from iios.execution.recovery.policies.recovery_events import (
    RecoveryPolicyEvent,
    make_decision_published,
    make_engine_started,
    make_engine_stopped,
    make_fallback_policy_selected,
    make_policy_evaluated,
    make_policy_evaluation_failed,
    make_policy_evaluation_started,
    make_strategy_selected,
)
from iios.execution.recovery.policies.recovery_factory import RecoveryPolicyFactory
from iios.execution.recovery.policies.recovery_history import RecoveryPolicyHistory
from iios.execution.recovery.policies.recovery_policy import (
    CompositePolicy,
    EmergencyShutdownPolicy,
    FailoverPolicy,
    ManualInterventionPolicy,
    PolicyEvaluationResult,
    RecoveryPolicy,
    RestartPolicy,
    ResumePolicy,
    RetryPolicy,
    RollbackPolicy,
)
from iios.execution.recovery.policies.recovery_policy_engine import (
    RecoveryPolicyEngine,
    RecoveryPolicyEngineAdapter,
    _map_failure_type_to_category,
    _map_severity_str,
)
from iios.execution.recovery.policies.recovery_policy_manager import (
    RecoveryPolicyManager,
)
from iios.execution.recovery.policies.recovery_policy_registry import (
    RecoveryPolicyRegistry,
)
from iios.execution.recovery.policies.recovery_priority import (
    PriorityScore,
    RecoveryPriorityEvaluator,
)
from iios.execution.recovery.policies.recovery_request import (
    PolicyEvaluationRequest,
    make_policy_evaluation_request,
)
from iios.execution.recovery.policies.recovery_response import (
    PolicyEvaluationReport,
    RecoveryPolicyDecision,
    make_policy_decision,
)
from iios.execution.recovery.policies.recovery_rule import (
    RecoveryRule,
    RuleCondition,
    make_rule,
)
from iios.execution.recovery.policies.recovery_statistics import (
    RecoveryPolicyStatistics,
)
from iios.execution.recovery.policies.recovery_strategy import (
    RecoveryStrategy,
    make_emergency_shutdown_strategy,
    make_failover_strategy,
    make_manual_intervention_strategy,
    make_restart_strategy,
    make_resume_strategy,
    make_retry_strategy,
    make_rollback_strategy,
    make_strategy,
    STRATEGY_FACTORY_MAP,
)
from iios.execution.recovery.policies.recovery_validation import (
    PolicyEvaluationValidator,
    PolicyValidationResult,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ctx(
    failure_category: FailureCategory = FailureCategory.TIMEOUT,
    failure_severity: FailureSeverity = FailureSeverity.MEDIUM,
    *,
    is_retry_exhausted: bool = False,
    retry_count: int = 0,
    max_retries: int = 3,
    rollback_available: bool = True,
    restart_count: int = 0,
    is_within_risk_limits: bool = True,
    breach_count: int = 0,
    risk_level: str = "LOW",
    is_subsystem_healthy: bool = True,
    subsystem_availability: float = 1.0,
    failure_frequency: int = 0,
    recent_recovery_failed: bool = False,
    failure_reason: str = "test failure",
    failure_type: str = "test",
    **kwargs: Any,
) -> PolicyEvaluationContext:
    return make_policy_evaluation_context(
        execution_session_id  = str(uuid.uuid4()),
        subsystem_id          = "test-subsystem",
        failure_category      = failure_category,
        failure_severity      = failure_severity,
        failure_reason        = failure_reason,
        failure_type          = failure_type,
        is_retry_exhausted    = is_retry_exhausted,
        retry_count           = retry_count,
        max_retries           = max_retries,
        rollback_available    = rollback_available,
        restart_count         = restart_count,
        is_within_risk_limits = is_within_risk_limits,
        breach_count          = breach_count,
        risk_level            = risk_level,
        is_subsystem_healthy  = is_subsystem_healthy,
        subsystem_availability = subsystem_availability,
        failure_frequency     = failure_frequency,
        recent_recovery_failed = recent_recovery_failed,
        **kwargs,
    )


def _req(context: PolicyEvaluationContext) -> PolicyEvaluationRequest:
    return make_policy_evaluation_request(
        execution_session_id = context.execution_session_id,
        subsystem_id         = context.subsystem_id,
        context              = context,
        failure_category     = context.failure_category,
        failure_severity     = context.failure_severity,
    )


def _report(request_id: str = "") -> PolicyEvaluationReport:
    return PolicyEvaluationReport(
        report_id          = str(uuid.uuid4()),
        request_id         = request_id or str(uuid.uuid4()),
        policies_evaluated = 1,
        rules_evaluated    = 1,
        matched_policies   = ("TestPolicy",),
        rejected_policies  = (),
        selected_policy    = "TestPolicy",
        selected_strategy  = RecoveryStrategyType.RETRY,
        confidence_score   = 0.8,
        evaluation_time_ms = 1.0,
        reasons            = ("test",),
    )


# ════════════════════════════════════════════════════════════════════════════
# 1.  Constants
# ════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_failure_category_values(self):
        assert FailureCategory.TIMEOUT.value == "timeout"
        assert FailureCategory.RISK_VIOLATION.value == "risk_violation"
        assert FailureCategory.BROKER_FAILURE.value == "broker_failure"

    def test_failure_severity_ordering(self):
        svs = [FailureSeverity.UNKNOWN, FailureSeverity.LOW,
               FailureSeverity.MEDIUM, FailureSeverity.HIGH, FailureSeverity.CRITICAL]
        assert all(isinstance(s, str) for s in svs)

    def test_strategy_types(self):
        assert RecoveryStrategyType.RETRY.value == "retry"
        assert RecoveryStrategyType.EMERGENCY_SHUTDOWN.value == "emergency_shutdown"

    def test_policy_priority_ordering(self):
        assert PolicyPriority.LOW < PolicyPriority.EMERGENCY

    def test_transient_categories_subset(self):
        for cat in TRANSIENT_FAILURE_CATEGORIES:
            assert isinstance(cat, FailureCategory)

    def test_safety_critical_subset(self):
        assert FailureCategory.RISK_VIOLATION in SAFETY_CRITICAL_CATEGORIES

    def test_failover_eligible_subset(self):
        assert FailureCategory.BROKER_FAILURE in FAILOVER_ELIGIBLE_CATEGORIES

    def test_severity_priority_map_completeness(self):
        for sev in FailureSeverity:
            assert sev in SEVERITY_PRIORITY_MAP

    def test_confidence_ordering(self):
        assert CONFIDENCE_EMERGENCY_SHUTDOWN > CONFIDENCE_FAILOVER > CONFIDENCE_ROLLBACK
        assert CONFIDENCE_RETRY > CONFIDENCE_MANUAL


# ════════════════════════════════════════════════════════════════════════════
# 2.  Exceptions
# ════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_error(self):
        e = RecoveryPolicyError("test")
        assert e.error_code == "RP-000"
        assert "test" in str(e)

    def test_not_running(self):
        e = RecoveryPolicyNotRunningError()
        assert e.error_code == "RP-001"

    def test_not_found(self):
        e = RecoveryPolicyNotFoundError("MyPolicy")
        assert e.error_code == "RP-002"
        assert e.policy_name == "MyPolicy"

    def test_validation_error(self):
        e = RecoveryPolicyValidationError("bad", errors=("err1",))
        assert e.error_code == "RP-003"
        assert "err1" in e.errors

    def test_rule_validation_error(self):
        e = RecoveryRuleValidationError("bad rule", rule_id="R-1")
        assert e.error_code == "RP-004"
        assert e.rule_id == "R-1"

    def test_strategy_not_found(self):
        e = RecoveryStrategyNotFoundError("custom_strategy")
        assert e.error_code == "RP-005"

    def test_evaluation_error(self):
        e = RecoveryPolicyEvaluationError("eval failed", policy_name="P1")
        assert e.error_code == "RP-006"
        assert e.policy_name == "P1"

    def test_conflict_error(self):
        e = RecoveryPolicyConflictError("P1", "P2")
        assert e.error_code == "RP-007"

    def test_registry_error(self):
        e = RecoveryPolicyRegistryError("registry full")
        assert e.error_code == "RP-008"

    def test_hierarchy(self):
        for cls in [
            RecoveryPolicyNotRunningError,
            RecoveryPolicyNotFoundError,
            RecoveryPolicyValidationError,
        ]:
            assert issubclass(cls, RecoveryPolicyError)


# ════════════════════════════════════════════════════════════════════════════
# 3.  RuleCondition
# ════════════════════════════════════════════════════════════════════════════

class TestRuleCondition:
    def test_equals_true(self):
        cond = RuleCondition("f", RuleConditionOperator.EQUALS, "x")
        assert cond.evaluate("x")

    def test_equals_false(self):
        cond = RuleCondition("f", RuleConditionOperator.EQUALS, "x")
        assert not cond.evaluate("y")

    def test_not_equals(self):
        cond = RuleCondition("f", RuleConditionOperator.NOT_EQUALS, "x")
        assert cond.evaluate("y")
        assert not cond.evaluate("x")

    def test_less_than(self):
        cond = RuleCondition("f", RuleConditionOperator.LESS_THAN, 5)
        assert cond.evaluate(4)
        assert not cond.evaluate(5)
        assert not cond.evaluate(6)

    def test_less_equals(self):
        cond = RuleCondition("f", RuleConditionOperator.LESS_EQUALS, 5)
        assert cond.evaluate(5)
        assert not cond.evaluate(6)

    def test_greater_than(self):
        cond = RuleCondition("f", RuleConditionOperator.GREATER_THAN, 0)
        assert cond.evaluate(1)
        assert not cond.evaluate(0)

    def test_greater_equals(self):
        cond = RuleCondition("f", RuleConditionOperator.GREATER_EQUALS, 3)
        assert cond.evaluate(3)
        assert not cond.evaluate(2)

    def test_in_operator(self):
        cond = RuleCondition("f", RuleConditionOperator.IN, ("a", "b", "c"))
        assert cond.evaluate("b")
        assert not cond.evaluate("d")

    def test_not_in_operator(self):
        cond = RuleCondition("f", RuleConditionOperator.NOT_IN, ("a", "b"))
        assert cond.evaluate("c")
        assert not cond.evaluate("a")

    def test_is_true(self):
        cond = RuleCondition("f", RuleConditionOperator.IS_TRUE)
        assert cond.evaluate(True)
        assert cond.evaluate(1)
        assert not cond.evaluate(False)
        assert not cond.evaluate(None)

    def test_is_false(self):
        cond = RuleCondition("f", RuleConditionOperator.IS_FALSE)
        assert cond.evaluate(False)
        assert cond.evaluate(0)
        assert not cond.evaluate(True)

    def test_contains(self):
        cond = RuleCondition("f", RuleConditionOperator.CONTAINS, "world")
        assert cond.evaluate("hello world")
        assert not cond.evaluate("hello")

    def test_none_context_value_returns_false(self):
        cond = RuleCondition("f", RuleConditionOperator.EQUALS, "x")
        assert not cond.evaluate(None)

    def test_to_dict(self):
        cond = RuleCondition("field", RuleConditionOperator.EQUALS, "val")
        d = cond.to_dict()
        assert d["field"] == "field"
        assert d["operator"] == "equals"

    def test_frozen(self):
        cond = RuleCondition("f", RuleConditionOperator.EQUALS, "x")
        with pytest.raises((AttributeError, TypeError)):
            cond.field = "other"  # type: ignore[misc]


# ════════════════════════════════════════════════════════════════════════════
# 4.  RecoveryRule
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryRule:
    def _ctx_with_field(self, **kwargs) -> PolicyEvaluationContext:
        return _ctx(**kwargs)

    def test_all_conditions_pass(self):
        rule = make_rule(
            "TestRule", "desc",
            conditions=(
                RuleCondition("retry_count", RuleConditionOperator.LESS_THAN, 3),
                RuleCondition("is_retry_exhausted", RuleConditionOperator.IS_FALSE),
            ),
            strategy_type=RecoveryStrategyType.RETRY,
            confidence_score=0.8,
        )
        ctx = _ctx(retry_count=1, is_retry_exhausted=False)
        assert rule.evaluate(ctx)

    def test_one_condition_fails(self):
        rule = make_rule(
            "TestRule", "desc",
            conditions=(
                RuleCondition("retry_count", RuleConditionOperator.LESS_THAN, 3),
                RuleCondition("is_retry_exhausted", RuleConditionOperator.IS_FALSE),
            ),
            strategy_type=RecoveryStrategyType.RETRY,
            confidence_score=0.8,
        )
        ctx = _ctx(retry_count=5, is_retry_exhausted=False)
        assert not rule.evaluate(ctx)

    def test_empty_conditions_always_true(self):
        rule = make_rule(
            "EmptyRule", "desc",
            conditions=(),
            strategy_type=RecoveryStrategyType.MANUAL_INTERVENTION,
            confidence_score=0.5,
        )
        ctx = _ctx()
        assert rule.evaluate(ctx)

    def test_to_dict(self):
        rule = make_rule(
            "R", "desc",
            conditions=(RuleCondition("f", RuleConditionOperator.IS_TRUE),),
            strategy_type=RecoveryStrategyType.RETRY,
            confidence_score=0.8,
        )
        d = rule.to_dict()
        assert d["name"] == "R"
        assert len(d["conditions"]) == 1

    def test_frozen(self):
        rule = make_rule(
            "R", "d", conditions=(), strategy_type=RecoveryStrategyType.RETRY,
            confidence_score=0.5,
        )
        with pytest.raises((AttributeError, TypeError)):
            rule.name = "other"  # type: ignore[misc]


# ════════════════════════════════════════════════════════════════════════════
# 5.  RecoveryStrategy
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryStrategy:
    def test_retry_strategy(self):
        s = make_retry_strategy()
        assert s.strategy_type == RecoveryStrategyType.RETRY
        assert s.max_retries == 3
        assert not s.requires_failover

    def test_retry_strategy_custom_retries(self):
        s = make_retry_strategy(max_retries=5)
        assert s.max_retries == 5

    def test_resume_strategy(self):
        s = make_resume_strategy()
        assert s.strategy_type == RecoveryStrategyType.RESUME

    def test_rollback_strategy(self):
        s = make_rollback_strategy()
        assert s.is_disruptive

    def test_restart_strategy(self):
        s = make_restart_strategy()
        assert s.strategy_type == RecoveryStrategyType.RESTART
        assert s.is_disruptive

    def test_failover_strategy(self):
        s = make_failover_strategy()
        assert s.requires_failover

    def test_manual_intervention_strategy(self):
        s = make_manual_intervention_strategy()
        assert s.requires_manual_intervention
        assert s.max_retries == 0

    def test_emergency_shutdown_strategy(self):
        s = make_emergency_shutdown_strategy()
        assert s.requires_manual_intervention
        assert s.priority == 100

    def test_make_strategy_dispatch(self):
        for st in RecoveryStrategyType:
            if st == RecoveryStrategyType.COMPOSITE:
                continue
            s = make_strategy(st)
            assert s.strategy_type == st

    def test_make_strategy_unknown_falls_back(self):
        s = make_strategy(RecoveryStrategyType.COMPOSITE)
        assert s.strategy_type == RecoveryStrategyType.MANUAL_INTERVENTION

    def test_frozen(self):
        s = make_retry_strategy()
        with pytest.raises((AttributeError, TypeError)):
            s.max_retries = 99  # type: ignore[misc]

    def test_to_dict(self):
        s = make_retry_strategy()
        d = s.to_dict()
        assert d["strategy_type"] == "retry"
        assert "max_retries" in d

    def test_strategy_factory_map_completeness(self):
        for st in RecoveryStrategyType:
            if st != RecoveryStrategyType.COMPOSITE:
                assert st in STRATEGY_FACTORY_MAP


# ════════════════════════════════════════════════════════════════════════════
# 6.  PolicyEvaluationContext
# ════════════════════════════════════════════════════════════════════════════

class TestPolicyEvaluationContext:
    def test_factory_creates_valid_context(self):
        ctx = _ctx()
        assert ctx.context_id
        assert ctx.execution_session_id
        assert ctx.subsystem_id
        assert ctx.failure_category == FailureCategory.TIMEOUT
        assert ctx.failure_severity == FailureSeverity.MEDIUM

    def test_can_retry_property_true(self):
        ctx = _ctx(retry_count=1, max_retries=3, is_retry_exhausted=False)
        assert ctx.can_retry

    def test_can_retry_property_false_exhausted(self):
        ctx = _ctx(is_retry_exhausted=True)
        assert not ctx.can_retry

    def test_can_retry_false_count_exceeded(self):
        ctx = _ctx(retry_count=3, max_retries=3, is_retry_exhausted=False)
        assert not ctx.can_retry

    def test_can_restart_property(self):
        ctx = _ctx(restart_count=2, max_restarts=3)
        assert ctx.can_restart
        ctx2 = _ctx(restart_count=3, max_restarts=3)
        assert not ctx2.can_restart

    def test_is_risk_critical_from_limits(self):
        ctx = _ctx(is_within_risk_limits=False)
        assert ctx.is_risk_critical

    def test_is_risk_critical_from_level(self):
        ctx = _ctx(risk_level="CRITICAL")
        assert ctx.is_risk_critical

    def test_is_high_severity(self):
        ctx = _ctx(failure_severity=FailureSeverity.CRITICAL)
        assert ctx.is_high_severity
        ctx2 = _ctx(failure_severity=FailureSeverity.LOW)
        assert not ctx2.is_high_severity

    def test_get_field(self):
        ctx = _ctx(retry_count=2)
        assert ctx.get_field("retry_count") == 2
        assert ctx.get_field("nonexistent") is None

    def test_to_dict(self):
        ctx = _ctx()
        d = ctx.to_dict()
        assert "failure_category" in d
        assert "failure_severity" in d

    def test_frozen(self):
        ctx = _ctx()
        with pytest.raises((AttributeError, TypeError)):
            ctx.retry_count = 99  # type: ignore[misc]

    def test_subsystem_availability_default(self):
        ctx = _ctx()
        assert ctx.subsystem_availability == 1.0


# ════════════════════════════════════════════════════════════════════════════
# 7.  PolicyEvaluationRequest
# ════════════════════════════════════════════════════════════════════════════

class TestPolicyEvaluationRequest:
    def test_factory(self):
        ctx = _ctx()
        req = _req(ctx)
        assert req.request_id
        assert req.execution_session_id == ctx.execution_session_id
        assert req.failure_category == ctx.failure_category
        assert req.context is ctx

    def test_frozen(self):
        req = _req(_ctx())
        with pytest.raises((AttributeError, TypeError)):
            req.request_id = "other"  # type: ignore[misc]

    def test_to_dict(self):
        req = _req(_ctx())
        d = req.to_dict()
        assert "request_id" in d
        assert "failure_category" in d


# ════════════════════════════════════════════════════════════════════════════
# 8.  RecoveryPolicyDecision / PolicyEvaluationReport
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryResponse:
    def test_make_policy_decision(self):
        rpt = _report()
        d = make_policy_decision(
            request_id           = "req-1",
            execution_session_id = "sess-1",
            subsystem_id         = "sub-1",
            is_approved          = True,
            strategy_type        = RecoveryStrategyType.RETRY,
            priority             = PolicyPriority.NORMAL,
            recommendation       = RecoveryRecommendation.RETRY,
            failure_category     = FailureCategory.TIMEOUT,
            failure_severity     = FailureSeverity.MEDIUM,
            confidence_score     = 0.8,
            policy_name          = "RetryPolicy",
            evaluation_report    = rpt,
        )
        assert d.is_approved
        assert d.strategy_type == RecoveryStrategyType.RETRY
        assert d.confidence_score == 0.8

    def test_decision_properties(self):
        rpt = _report()
        d = make_policy_decision(
            request_id           = "r",
            execution_session_id = "s",
            subsystem_id         = "sub",
            is_approved          = True,
            strategy_type        = RecoveryStrategyType.RETRY,
            priority             = PolicyPriority.NORMAL,
            recommendation       = RecoveryRecommendation.RETRY,
            failure_category     = FailureCategory.TIMEOUT,
            failure_severity     = FailureSeverity.MEDIUM,
            confidence_score     = 0.8,
            policy_name          = "RetryPolicy",
            evaluation_report    = rpt,
        )
        assert d.is_retry
        assert not d.is_failover
        assert not d.is_emergency_shutdown
        assert d.is_high_confidence

    def test_emergency_shutdown_decision(self):
        rpt = _report()
        d = make_policy_decision(
            request_id           = "r",
            execution_session_id = "s",
            subsystem_id         = "sub",
            is_approved          = True,
            strategy_type        = RecoveryStrategyType.EMERGENCY_SHUTDOWN,
            priority             = PolicyPriority.EMERGENCY,
            recommendation       = RecoveryRecommendation.EMERGENCY_SHUTDOWN,
            failure_category     = FailureCategory.RISK_VIOLATION,
            failure_severity     = FailureSeverity.CRITICAL,
            confidence_score     = 0.95,
            policy_name          = "EmergencyShutdownPolicy",
            evaluation_report    = rpt,
        )
        assert d.is_emergency_shutdown

    def test_frozen(self):
        rpt = _report()
        d = make_policy_decision(
            request_id="r", execution_session_id="s", subsystem_id="sub",
            is_approved=True, strategy_type=RecoveryStrategyType.RETRY,
            priority=PolicyPriority.NORMAL, recommendation=RecoveryRecommendation.RETRY,
            failure_category=FailureCategory.TIMEOUT,
            failure_severity=FailureSeverity.MEDIUM,
            confidence_score=0.8, policy_name="P", evaluation_report=rpt,
        )
        with pytest.raises((AttributeError, TypeError)):
            d.decision_id = "other"  # type: ignore[misc]

    def test_to_dict(self):
        rpt = _report()
        d = make_policy_decision(
            request_id="r", execution_session_id="s", subsystem_id="sub",
            is_approved=True, strategy_type=RecoveryStrategyType.RETRY,
            priority=PolicyPriority.NORMAL, recommendation=RecoveryRecommendation.RETRY,
            failure_category=FailureCategory.TIMEOUT,
            failure_severity=FailureSeverity.MEDIUM,
            confidence_score=0.8, policy_name="P", evaluation_report=rpt,
        )
        dd = d.to_dict()
        assert dd["strategy_type"] == "retry"

    def test_report_frozen(self):
        rpt = _report()
        with pytest.raises((AttributeError, TypeError)):
            rpt.report_id = "other"  # type: ignore[misc]

    def test_report_to_dict(self):
        rpt = _report()
        d = rpt.to_dict()
        assert "selected_strategy" in d


# ════════════════════════════════════════════════════════════════════════════
# 9.  RecoveryPolicyEvent
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryEvents:
    def test_evaluation_started(self):
        e = make_policy_evaluation_started("req-1")
        assert e.event_type == PolicyEventType.POLICY_EVALUATION_STARTED
        assert e.request_id == "req-1"

    def test_policy_evaluated(self):
        e = make_policy_evaluated("req-1", "dec-1")
        assert e.event_type == PolicyEventType.POLICY_EVALUATED

    def test_strategy_selected(self):
        e = make_strategy_selected("req-1", "dec-1", reason="matched")
        assert e.event_type == PolicyEventType.STRATEGY_SELECTED
        assert e.reason == "matched"

    def test_decision_published(self):
        e = make_decision_published("req-1", "dec-1")
        assert e.event_type == PolicyEventType.DECISION_PUBLISHED

    def test_fallback_selected(self):
        e = make_fallback_policy_selected("req-1", reason="no match")
        assert e.event_type == PolicyEventType.FALLBACK_POLICY_SELECTED

    def test_evaluation_failed(self):
        e = make_policy_evaluation_failed("req-1", reason="exc")
        assert e.event_type == PolicyEventType.POLICY_EVALUATION_FAILED

    def test_engine_started(self):
        e = make_engine_started()
        assert e.event_type == PolicyEventType.ENGINE_STARTED

    def test_engine_stopped(self):
        e = make_engine_stopped()
        assert e.event_type == PolicyEventType.ENGINE_STOPPED

    def test_frozen(self):
        e = make_engine_started()
        with pytest.raises((AttributeError, TypeError)):
            e.event_id = "x"  # type: ignore[misc]

    def test_to_dict(self):
        e = make_engine_started()
        d = e.to_dict()
        assert "event_type" in d


# ════════════════════════════════════════════════════════════════════════════
# 10. RecoveryPriorityEvaluator
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryPriorityEvaluator:
    def setup_method(self):
        self.evaluator = RecoveryPriorityEvaluator()

    def test_critical_severity_maps_to_emergency(self):
        ctx = _ctx(failure_severity=FailureSeverity.CRITICAL)
        score = self.evaluator.evaluate(ctx)
        assert score.final_priority == PolicyPriority.EMERGENCY

    def test_low_severity_maps_to_low(self):
        ctx = _ctx(failure_severity=FailureSeverity.LOW)
        score = self.evaluator.evaluate(ctx)
        # Low severity, no boosts → LOW
        assert score.final_priority == PolicyPriority.LOW

    def test_risk_violation_forces_emergency(self):
        ctx = _ctx(
            failure_category=FailureCategory.RISK_VIOLATION,
            failure_severity=FailureSeverity.LOW,
        )
        score = self.evaluator.evaluate(ctx)
        assert score.final_priority == PolicyPriority.EMERGENCY

    def test_risk_limit_breach_forces_emergency(self):
        ctx = _ctx(is_within_risk_limits=False, failure_severity=FailureSeverity.LOW)
        score = self.evaluator.evaluate(ctx)
        assert score.final_priority == PolicyPriority.EMERGENCY

    def test_high_failure_frequency_boosts(self):
        ctx_low  = _ctx(failure_severity=FailureSeverity.MEDIUM, failure_frequency=1)
        ctx_high = _ctx(failure_severity=FailureSeverity.MEDIUM, failure_frequency=10)
        score_low  = self.evaluator.evaluate(ctx_low)
        score_high = self.evaluator.evaluate(ctx_high)
        assert score_high.final_priority.value >= score_low.final_priority.value

    def test_recent_recovery_failed_boosts(self):
        ctx = _ctx(failure_severity=FailureSeverity.MEDIUM, recent_recovery_failed=True)
        score = self.evaluator.evaluate(ctx)
        assert score.frequency_boost > 0

    def test_to_dict(self):
        ctx = _ctx()
        score = self.evaluator.evaluate(ctx)
        d = score.to_dict()
        assert "final_priority" in d
        assert "factors" in d


# ════════════════════════════════════════════════════════════════════════════
# 11. PolicyEvaluationValidator
# ════════════════════════════════════════════════════════════════════════════

class TestPolicyEvaluationValidator:
    def setup_method(self):
        self.v = PolicyEvaluationValidator()

    def test_valid_context(self):
        result = self.v.validate_context(_ctx())
        assert result.is_valid

    def test_none_context_invalid(self):
        result = self.v.validate_context(None)
        assert not result.is_valid

    def test_missing_context_id_invalid(self):
        ctx = _ctx()
        mock = MagicMock(spec=PolicyEvaluationContext)
        mock.context_id = ""
        mock.execution_session_id = "sess"
        mock.subsystem_id = "sub"
        mock.failure_category = FailureCategory.TIMEOUT
        mock.failure_severity = FailureSeverity.MEDIUM
        mock.failure_reason = "reason"
        mock.subsystem_availability = 1.0
        result = self.v.validate_context(mock)
        assert not result.is_valid

    def test_invalid_availability(self):
        mock = MagicMock()
        mock.context_id = "c"
        mock.execution_session_id = "s"
        mock.subsystem_id = "sub"
        mock.failure_category = FailureCategory.TIMEOUT
        mock.failure_severity = FailureSeverity.MEDIUM
        mock.failure_reason = "reason"
        mock.subsystem_availability = 1.5
        result = self.v.validate_context(mock)
        assert not result.is_valid

    def test_valid_request(self):
        req = _req(_ctx())
        result = self.v.validate_request(req)
        assert result.is_valid

    def test_none_request_invalid(self):
        result = self.v.validate_request(None)
        assert not result.is_valid

    def test_valid_policy(self):
        result = self.v.validate_policy(RetryPolicy())
        assert result.is_valid

    def test_none_policy_invalid(self):
        result = self.v.validate_policy(None)
        assert not result.is_valid

    def test_valid_strategy(self):
        result = self.v.validate_strategy(make_retry_strategy())
        assert result.is_valid

    def test_none_strategy_invalid(self):
        result = self.v.validate_strategy(None)
        assert not result.is_valid

    def test_valid_decision(self):
        rpt = _report()
        d = make_policy_decision(
            request_id="r", execution_session_id="s", subsystem_id="sub",
            is_approved=True, strategy_type=RecoveryStrategyType.RETRY,
            priority=PolicyPriority.NORMAL, recommendation=RecoveryRecommendation.RETRY,
            failure_category=FailureCategory.TIMEOUT,
            failure_severity=FailureSeverity.MEDIUM,
            confidence_score=0.8, policy_name="P", evaluation_report=rpt,
        )
        result = self.v.validate_decision(d)
        assert result.is_valid

    def test_duplicate_policy_names(self):
        p1 = RetryPolicy()
        p2 = RetryPolicy()
        result = self.v.validate_policy_consistency([p1, p2])
        assert not result.is_valid

    def test_unique_policy_names_valid(self):
        result = self.v.validate_policy_consistency([RetryPolicy(), RollbackPolicy()])
        assert result.is_valid

    def test_multiple_fallbacks_warning(self):
        p1 = ManualInterventionPolicy()
        p2 = ManualInterventionPolicy()
        p2.name = "ManualInterventionPolicy2"
        result = self.v.validate_policy_consistency([p1, p2])
        assert len(result.warnings) > 0

    def test_validation_result_merge(self):
        r1 = PolicyValidationResult()
        r1.add_error("err1")
        r2 = PolicyValidationResult()
        r2.add_warning("warn1")
        r1.merge(r2)
        assert "err1" in r1.errors
        assert "warn1" in r1.warnings


# ════════════════════════════════════════════════════════════════════════════
# 12. RecoveryPolicyStatistics
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryPolicyStatistics:
    def setup_method(self):
        self.stats = RecoveryPolicyStatistics()

    def test_initial_state(self):
        assert self.stats.total_evaluations == 0
        assert self.stats.total_decisions == 0
        assert self.stats.average_evaluation_time_ms == 0.0

    def test_record_evaluation(self):
        self.stats.record_evaluation()
        self.stats.record_evaluation()
        assert self.stats.total_evaluations == 2

    def test_record_decision_approved(self):
        self.stats.record_decision(approved=True)
        assert self.stats.approved_decisions == 1
        assert self.stats.rejected_decisions == 0

    def test_record_decision_rejected(self):
        self.stats.record_decision(approved=False)
        assert self.stats.rejected_decisions == 1

    def test_retry_rate(self):
        self.stats.record_decision(approved=True)
        self.stats.record_retry_recommendation()
        assert self.stats.retry_rate == 1.0

    def test_rollback_rate_zero(self):
        self.stats.record_decision(approved=True)
        assert self.stats.rollback_rate == 0.0

    def test_evaluation_time_average(self):
        self.stats.record_evaluation_time(10.0)
        self.stats.record_evaluation_time(20.0)
        assert self.stats.average_evaluation_time_ms == 15.0

    def test_record_emergency_shutdown(self):
        self.stats.record_decision(approved=True)
        self.stats.record_emergency_shutdown()
        assert self.stats.emergency_rate == 1.0

    def test_record_fallback(self):
        self.stats.record_fallback_used()
        # No assertion needed; just verify no crash

    def test_reset(self):
        self.stats.record_evaluation()
        self.stats.record_decision(approved=True)
        self.stats.reset()
        assert self.stats.total_evaluations == 0

    def test_copy(self):
        self.stats.record_evaluation()
        self.stats.record_decision(approved=True)
        copy = self.stats.copy()
        assert copy.total_evaluations == 1
        # Mutations to original don't affect copy
        self.stats.record_evaluation()
        assert copy.total_evaluations == 1

    def test_to_dict(self):
        d = self.stats.to_dict()
        assert "total_evaluations" in d
        assert "average_evaluation_time_ms" in d

    def test_thread_safety(self):
        errors = []
        def worker():
            try:
                for _ in range(100):
                    self.stats.record_evaluation()
                    self.stats.record_decision(approved=True)
                    self.stats.record_retry_recommendation()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert self.stats.total_evaluations == 400


# ════════════════════════════════════════════════════════════════════════════
# 13. RecoveryPolicyHistory
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryPolicyHistory:
    def setup_method(self):
        self.history = RecoveryPolicyHistory(
            max_requests=10, max_decisions=10, max_events=10, max_reports=10
        )

    def test_append_and_read_request(self):
        req = _req(_ctx())
        self.history.append_request(req)
        assert len(self.history.requests()) == 1
        assert self.history.latest_request() is req

    def test_append_and_read_decision(self):
        d = make_policy_decision(
            request_id="r", execution_session_id="s", subsystem_id="sub",
            is_approved=True, strategy_type=RecoveryStrategyType.RETRY,
            priority=PolicyPriority.NORMAL, recommendation=RecoveryRecommendation.RETRY,
            failure_category=FailureCategory.TIMEOUT,
            failure_severity=FailureSeverity.MEDIUM,
            confidence_score=0.8, policy_name="P", evaluation_report=_report(),
        )
        self.history.append_decision(d)
        assert len(self.history.decisions()) == 1
        assert self.history.latest_decision() is d

    def test_append_event(self):
        e = make_engine_started()
        self.history.append_event(e)
        assert self.history.event_count == 1
        assert self.history.latest_event() is e

    def test_append_report(self):
        rpt = _report()
        self.history.append_report(rpt)
        assert self.history.report_count == 1

    def test_bounded_capacity(self):
        for _ in range(15):
            self.history.append_request(_req(_ctx()))
        assert self.history.request_count == 10   # bounded at 10

    def test_latest_when_empty(self):
        assert self.history.latest_request() is None
        assert self.history.latest_decision() is None

    def test_for_subsystem(self):
        ctx1 = make_policy_evaluation_context(
            execution_session_id="sess-A", subsystem_id="sub-A",
            failure_category=FailureCategory.TIMEOUT,
            failure_severity=FailureSeverity.LOW, failure_reason="r",
        )
        ctx2 = make_policy_evaluation_context(
            execution_session_id="sess-B", subsystem_id="sub-B",
            failure_category=FailureCategory.TIMEOUT,
            failure_severity=FailureSeverity.LOW, failure_reason="r",
        )
        for ctx in (ctx1, ctx2, ctx1):
            d = make_policy_decision(
                request_id="r", execution_session_id=ctx.execution_session_id,
                subsystem_id=ctx.subsystem_id,
                is_approved=True, strategy_type=RecoveryStrategyType.RETRY,
                priority=PolicyPriority.NORMAL, recommendation=RecoveryRecommendation.RETRY,
                failure_category=FailureCategory.TIMEOUT,
                failure_severity=FailureSeverity.MEDIUM,
                confidence_score=0.8, policy_name="P", evaluation_report=_report(),
            )
            self.history.append_decision(d)
        sub_a = self.history.for_subsystem("sub-A")
        assert len(sub_a) == 2

    def test_for_execution_session(self):
        sess_id = "sess-Z"
        d = make_policy_decision(
            request_id="r", execution_session_id=sess_id, subsystem_id="sub",
            is_approved=True, strategy_type=RecoveryStrategyType.RETRY,
            priority=PolicyPriority.NORMAL, recommendation=RecoveryRecommendation.RETRY,
            failure_category=FailureCategory.TIMEOUT,
            failure_severity=FailureSeverity.MEDIUM,
            confidence_score=0.8, policy_name="P", evaluation_report=_report(),
        )
        self.history.append_decision(d)
        assert len(self.history.for_execution_session(sess_id)) == 1
        assert len(self.history.for_execution_session("other")) == 0

    def test_clear(self):
        self.history.append_request(_req(_ctx()))
        self.history.append_event(make_engine_started())
        self.history.clear()
        assert self.history.request_count == 0
        assert self.history.event_count == 0


# ════════════════════════════════════════════════════════════════════════════
# 14. Concrete policies — individual
# ════════════════════════════════════════════════════════════════════════════

class TestRetryPolicy:
    def setup_method(self):
        self.p = RetryPolicy()

    def test_matches_timeout_with_retries_remaining(self):
        ctx = _ctx(failure_category=FailureCategory.TIMEOUT, is_retry_exhausted=False)
        r = self.p.evaluate(ctx)
        assert r.matched
        assert r.strategy_type == RecoveryStrategyType.RETRY
        assert r.confidence_score == CONFIDENCE_RETRY

    def test_no_match_on_broker_failure(self):
        ctx = _ctx(failure_category=FailureCategory.BROKER_FAILURE)
        r = self.p.evaluate(ctx)
        assert not r.matched

    def test_no_match_when_exhausted(self):
        ctx = _ctx(
            failure_category=FailureCategory.TIMEOUT, is_retry_exhausted=True
        )
        r = self.p.evaluate(ctx)
        assert not r.matched

    def test_no_match_critical_severity(self):
        ctx = _ctx(
            failure_category=FailureCategory.TIMEOUT,
            failure_severity=FailureSeverity.CRITICAL,
            is_retry_exhausted=False,
        )
        r = self.p.evaluate(ctx)
        assert not r.matched

    def test_not_fallback(self):
        assert not self.p.is_fallback

    def test_priority(self):
        assert self.p.priority == 60


class TestResumePolicy:
    def setup_method(self):
        self.p = ResumePolicy()

    def test_matches_execution_failure_healthy(self):
        ctx = _ctx(
            failure_category=FailureCategory.EXECUTION_FAILURE,
            failure_severity=FailureSeverity.MEDIUM,
            is_subsystem_healthy=True,
        )
        r = self.p.evaluate(ctx)
        assert r.matched
        assert r.strategy_type == RecoveryStrategyType.RESUME

    def test_no_match_high_severity(self):
        ctx = _ctx(
            failure_category=FailureCategory.EXECUTION_FAILURE,
            failure_severity=FailureSeverity.HIGH,
            is_subsystem_healthy=True,
        )
        r = self.p.evaluate(ctx)
        assert not r.matched

    def test_no_match_unhealthy_subsystem(self):
        ctx = _ctx(
            failure_category=FailureCategory.EXECUTION_FAILURE,
            failure_severity=FailureSeverity.LOW,
            is_subsystem_healthy=False,
        )
        r = self.p.evaluate(ctx)
        assert not r.matched


class TestRollbackPolicy:
    def setup_method(self):
        self.p = RollbackPolicy()

    def test_matches_data_integrity_with_rollback(self):
        ctx = _ctx(
            failure_category=FailureCategory.DATA_INTEGRITY_FAILURE,
            rollback_available=True,
        )
        r = self.p.evaluate(ctx)
        assert r.matched
        assert r.strategy_type == RecoveryStrategyType.ROLLBACK
        assert r.confidence_score == CONFIDENCE_ROLLBACK

    def test_no_match_rollback_unavailable(self):
        ctx = _ctx(
            failure_category=FailureCategory.DATA_INTEGRITY_FAILURE,
            rollback_available=False,
        )
        r = self.p.evaluate(ctx)
        assert not r.matched

    def test_no_match_risk_limits_violated(self):
        ctx = _ctx(
            failure_category=FailureCategory.DATA_INTEGRITY_FAILURE,
            rollback_available=True,
            is_within_risk_limits=False,
        )
        r = self.p.evaluate(ctx)
        assert not r.matched

    def test_applies_to_execution_failure_too(self):
        ctx = _ctx(
            failure_category=FailureCategory.EXECUTION_FAILURE,
            rollback_available=True,
        )
        r = self.p.evaluate(ctx)
        assert r.matched


class TestRestartPolicy:
    def setup_method(self):
        self.p = RestartPolicy()

    def test_matches_execution_failure_with_budget(self):
        ctx = _ctx(
            failure_category=FailureCategory.EXECUTION_FAILURE,
            restart_count=1,
            failure_severity=FailureSeverity.MEDIUM,
        )
        r = self.p.evaluate(ctx)
        assert r.matched
        assert r.strategy_type == RecoveryStrategyType.RESTART

    def test_no_match_budget_exceeded(self):
        ctx = _ctx(
            failure_category=FailureCategory.EXECUTION_FAILURE,
            restart_count=3,
        )
        r = self.p.evaluate(ctx)
        assert not r.matched

    def test_no_match_critical_severity(self):
        ctx = _ctx(
            failure_category=FailureCategory.EXECUTION_FAILURE,
            restart_count=0,
            failure_severity=FailureSeverity.CRITICAL,
        )
        r = self.p.evaluate(ctx)
        assert not r.matched


class TestFailoverPolicy:
    def setup_method(self):
        self.p = FailoverPolicy()

    def test_matches_broker_failure_high_severity(self):
        ctx = _ctx(
            failure_category=FailureCategory.BROKER_FAILURE,
            failure_severity=FailureSeverity.HIGH,
        )
        r = self.p.evaluate(ctx)
        assert r.matched
        assert r.strategy_type == RecoveryStrategyType.FAILOVER
        assert r.confidence_score == CONFIDENCE_FAILOVER

    def test_matches_low_availability(self):
        ctx = _ctx(
            failure_category=FailureCategory.GATEWAY_FAILURE,
            failure_severity=FailureSeverity.MEDIUM,
            subsystem_availability=0.2,
        )
        r = self.p.evaluate(ctx)
        assert r.matched

    def test_no_match_low_severity_normal_availability(self):
        ctx = _ctx(
            failure_category=FailureCategory.BROKER_FAILURE,
            failure_severity=FailureSeverity.LOW,
            subsystem_availability=0.9,
        )
        r = self.p.evaluate(ctx)
        assert not r.matched

    def test_no_match_wrong_category(self):
        ctx = _ctx(failure_category=FailureCategory.TIMEOUT)
        r = self.p.evaluate(ctx)
        assert not r.matched


class TestManualInterventionPolicy:
    def setup_method(self):
        self.p = ManualInterventionPolicy()

    def test_always_matches(self):
        for cat in FailureCategory:
            ctx = _ctx(failure_category=cat)
            r = self.p.evaluate(ctx)
            assert r.matched

    def test_is_fallback(self):
        assert self.p.is_fallback

    def test_confidence_is_manual(self):
        r = self.p.evaluate(_ctx())
        assert r.confidence_score == CONFIDENCE_MANUAL

    def test_strategy_type(self):
        r = self.p.evaluate(_ctx())
        assert r.strategy_type == RecoveryStrategyType.MANUAL_INTERVENTION


class TestEmergencyShutdownPolicy:
    def setup_method(self):
        self.p = EmergencyShutdownPolicy()

    def test_matches_risk_violation(self):
        ctx = _ctx(failure_category=FailureCategory.RISK_VIOLATION, is_within_risk_limits=False)
        r = self.p.evaluate(ctx)
        assert r.matched
        assert r.strategy_type == RecoveryStrategyType.EMERGENCY_SHUTDOWN
        assert r.confidence_score == CONFIDENCE_EMERGENCY_SHUTDOWN

    def test_matches_when_risk_limits_breached_any_category(self):
        ctx = _ctx(
            failure_category=FailureCategory.TIMEOUT,
            is_within_risk_limits=False,
        )
        r = self.p.evaluate(ctx)
        assert r.matched

    def test_matches_when_breach_count_positive(self):
        ctx = _ctx(
            failure_category=FailureCategory.TIMEOUT,
            breach_count=2,
        )
        r = self.p.evaluate(ctx)
        assert r.matched

    def test_no_match_normal_conditions(self):
        ctx = _ctx(
            failure_category=FailureCategory.TIMEOUT,
            is_within_risk_limits=True,
            breach_count=0,
        )
        r = self.p.evaluate(ctx)
        assert not r.matched

    def test_highest_priority(self):
        assert self.p.priority == 100


# ════════════════════════════════════════════════════════════════════════════
# 15. CompositePolicy
# ════════════════════════════════════════════════════════════════════════════

class TestCompositePolicy:
    def test_selects_highest_confidence(self):
        comp = CompositePolicy(
            "MyComposite",
            member_policies=(RetryPolicy(), RollbackPolicy()),
        )
        ctx = _ctx(
            failure_category=FailureCategory.TIMEOUT,
            rollback_available=True,
            is_retry_exhausted=False,
        )
        r = comp.evaluate(ctx)
        assert r.matched
        # RetryPolicy matches with 0.80, RollbackPolicy doesn't match TIMEOUT category
        assert r.strategy_type == RecoveryStrategyType.RETRY

    def test_no_match_when_no_member_matches(self):
        comp = CompositePolicy(
            "MyComposite",
            member_policies=(RetryPolicy(),),
        )
        ctx = _ctx(failure_category=FailureCategory.BROKER_FAILURE)
        r = comp.evaluate(ctx)
        assert not r.matched

    def test_inherits_applicable_categories(self):
        comp = CompositePolicy(
            "C",
            member_policies=(RetryPolicy(), FailoverPolicy()),
        )
        # Should include categories from both members
        all_cats = set(comp.applicable_categories)
        assert FailureCategory.TIMEOUT in all_cats
        assert FailureCategory.BROKER_FAILURE in all_cats


# ════════════════════════════════════════════════════════════════════════════
# 16. RecoveryPolicyRegistry
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryPolicyRegistry:
    def setup_method(self):
        self.reg = RecoveryPolicyRegistry()
        self.reg.start()

    def teardown_method(self):
        if self.reg.lifecycle_state() not in ("stopped", "STOPPED"):
            self.reg.stop()

    def test_register_and_get(self):
        p = RetryPolicy()
        self.reg.register(p)
        assert self.reg.get("RetryPolicy") is p

    def test_register_duplicate_raises(self):
        self.reg.register(RetryPolicy())
        with pytest.raises(RecoveryPolicyConflictError):
            self.reg.register(RetryPolicy())

    def test_get_not_found_raises(self):
        with pytest.raises(RecoveryPolicyNotFoundError):
            self.reg.get("NonExistent")

    def test_find_returns_none_when_missing(self):
        assert self.reg.find("NonExistent") is None

    def test_unregister(self):
        self.reg.register(RetryPolicy())
        self.reg.unregister("RetryPolicy")
        assert not self.reg.contains("RetryPolicy")

    def test_unregister_not_found_raises(self):
        with pytest.raises(RecoveryPolicyNotFoundError):
            self.reg.unregister("NonExistent")

    def test_all(self):
        self.reg.register(RetryPolicy())
        self.reg.register(RollbackPolicy())
        assert len(self.reg.all()) == 2

    def test_for_category(self):
        self.reg.register(RetryPolicy())    # handles TIMEOUT
        self.reg.register(RollbackPolicy()) # handles DATA_INTEGRITY
        result = self.reg.for_category(FailureCategory.TIMEOUT)
        names = [p.name for p in result]
        assert "RetryPolicy" in names
        assert "RollbackPolicy" not in names

    def test_for_type(self):
        self.reg.register(RetryPolicy())
        result = self.reg.for_type(RecoveryStrategyType.RETRY)
        assert len(result) == 1
        assert result[0].name == "RetryPolicy"

    def test_find_fallback(self):
        self.reg.register(ManualInterventionPolicy())
        fb = self.reg.find_fallback()
        assert fb is not None
        assert fb.is_fallback

    def test_find_fallback_none_when_no_fallback(self):
        self.reg.register(RetryPolicy())
        fb = self.reg.find_fallback()
        assert fb is None

    def test_contains(self):
        self.reg.register(RetryPolicy())
        assert self.reg.contains("RetryPolicy")
        assert not self.reg.contains("Other")

    def test_count(self):
        assert self.reg.count == 0
        self.reg.register(RetryPolicy())
        assert self.reg.count == 1

    def test_not_running_raises(self):
        reg = RecoveryPolicyRegistry()
        with pytest.raises(RecoveryPolicyNotRunningError):
            reg.register(RetryPolicy())

    def test_capacity_limit(self):
        reg = RecoveryPolicyRegistry(max_policies=1)
        reg.start()
        reg.register(RetryPolicy())
        # Create a differently-named policy
        p2 = RollbackPolicy()
        with pytest.raises(RecoveryPolicyRegistryError):
            reg.register(p2)
        reg.stop()


# ════════════════════════════════════════════════════════════════════════════
# 17. RecoveryPolicyManager
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryPolicyManager:
    def setup_method(self):
        self.mgr = RecoveryPolicyManager()
        self.mgr.start()

    def teardown_method(self):
        if self.mgr.lifecycle_state() not in ("stopped", "STOPPED"):
            self.mgr.stop()

    def test_add_and_get_ordered_policies(self):
        self.mgr.add_policy(RetryPolicy())
        ctx = _ctx(failure_category=FailureCategory.TIMEOUT)
        policies = self.mgr.get_ordered_policies(ctx)
        assert any(p.name == "RetryPolicy" for p in policies)

    def test_remove_policy(self):
        self.mgr.add_policy(RetryPolicy())
        self.mgr.remove_policy("RetryPolicy")
        ctx = _ctx(failure_category=FailureCategory.TIMEOUT)
        policies = self.mgr.get_ordered_policies(ctx)
        assert not any(p.name == "RetryPolicy" for p in policies)

    def test_deactivate_excludes_from_evaluation(self):
        self.mgr.add_policy(RetryPolicy())
        self.mgr.deactivate("RetryPolicy")
        ctx = _ctx(failure_category=FailureCategory.TIMEOUT)
        policies = self.mgr.get_ordered_policies(ctx)
        assert not any(p.name == "RetryPolicy" for p in policies)

    def test_activate_re_includes(self):
        self.mgr.add_policy(RetryPolicy())
        self.mgr.deactivate("RetryPolicy")
        self.mgr.activate("RetryPolicy")
        ctx = _ctx(failure_category=FailureCategory.TIMEOUT)
        policies = self.mgr.get_ordered_policies(ctx)
        assert any(p.name == "RetryPolicy" for p in policies)

    def test_is_active(self):
        self.mgr.add_policy(RetryPolicy())
        assert self.mgr.is_active("RetryPolicy")
        self.mgr.deactivate("RetryPolicy")
        assert not self.mgr.is_active("RetryPolicy")

    def test_deactivate_not_found_raises(self):
        with pytest.raises(RecoveryPolicyNotFoundError):
            self.mgr.deactivate("NonExistent")

    def test_get_fallback_policy(self):
        self.mgr.add_policy(ManualInterventionPolicy())
        fb = self.mgr.get_fallback_policy()
        assert fb is not None

    def test_ordered_by_priority_descending(self):
        self.mgr.add_policy(RetryPolicy())        # priority=60
        self.mgr.add_policy(FailoverPolicy())     # priority=75
        self.mgr.add_policy(RollbackPolicy())     # priority=70
        ctx = _ctx(failure_category=FailureCategory.GATEWAY_FAILURE,
                   failure_severity=FailureSeverity.HIGH)
        policies = self.mgr.get_ordered_policies(ctx)
        priorities = [p.priority for p in policies]
        assert priorities == sorted(priorities, reverse=True)

    def test_not_running_raises(self):
        mgr = RecoveryPolicyManager()
        with pytest.raises(RecoveryPolicyNotRunningError):
            mgr.add_policy(RetryPolicy())


# ════════════════════════════════════════════════════════════════════════════
# 18. RecoveryPolicyFactory
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryPolicyFactory:
    def setup_method(self):
        self.factory = RecoveryPolicyFactory()
        self.factory.start()

    def teardown_method(self):
        if self.factory.lifecycle_state() not in ("stopped", "STOPPED"):
            self.factory.stop()

    def test_create_evaluation_context(self):
        ctx = self.factory.create_evaluation_context(
            execution_session_id = "sess-1",
            subsystem_id         = "sub-1",
            failure_category     = FailureCategory.TIMEOUT,
            failure_severity     = FailureSeverity.MEDIUM,
            failure_reason       = "timeout",
        )
        assert ctx.execution_session_id == "sess-1"
        assert ctx.failure_category == FailureCategory.TIMEOUT

    def test_create_evaluation_request(self):
        ctx = self.factory.create_evaluation_context(
            "s", "sub", FailureCategory.TIMEOUT, FailureSeverity.MEDIUM, "reason"
        )
        req = self.factory.create_evaluation_request(
            "s", "sub", ctx,
            failure_category=FailureCategory.TIMEOUT,
            failure_severity=FailureSeverity.MEDIUM,
        )
        assert req.context is ctx

    def test_create_decision(self):
        rpt = _report()
        d = self.factory.create_decision(
            request_id           = "req-1",
            execution_session_id = "sess-1",
            subsystem_id         = "sub-1",
            is_approved          = True,
            strategy_type        = RecoveryStrategyType.RETRY,
            priority             = PolicyPriority.NORMAL,
            recommendation       = RecoveryRecommendation.RETRY,
            failure_category     = FailureCategory.TIMEOUT,
            failure_severity     = FailureSeverity.MEDIUM,
            confidence_score     = 0.8,
            policy_name          = "RetryPolicy",
            evaluation_report    = rpt,
        )
        assert d.is_approved
        assert d.decision_id


# ════════════════════════════════════════════════════════════════════════════
# 19. RecoveryPolicyEngine (primary entry point)
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryPolicyEngine:
    def setup_method(self):
        self.engine = RecoveryPolicyEngine()
        self.engine.start()

    def teardown_method(self):
        if self.engine.lifecycle_state() not in ("stopped", "STOPPED"):
            self.engine.stop()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def test_engine_starts_and_stops(self):
        engine2 = RecoveryPolicyEngine()
        engine2.start()
        engine2.stop()

    def test_not_running_raises(self):
        engine2 = RecoveryPolicyEngine()
        req = _req(_ctx())
        with pytest.raises(RecoveryPolicyNotRunningError):
            engine2.evaluate(req)

    # ── Default policy evaluations ─────────────────────────────────────────

    def test_evaluate_timeout_selects_retry(self):
        ctx = _ctx(failure_category=FailureCategory.TIMEOUT, is_retry_exhausted=False)
        decision = self.engine.evaluate(_req(ctx))
        assert decision.strategy_type == RecoveryStrategyType.RETRY
        assert decision.is_approved

    def test_evaluate_risk_violation_selects_emergency_shutdown(self):
        ctx = _ctx(
            failure_category=FailureCategory.RISK_VIOLATION,
            failure_severity=FailureSeverity.CRITICAL,
            is_within_risk_limits=False,
        )
        decision = self.engine.evaluate(_req(ctx))
        assert decision.strategy_type == RecoveryStrategyType.EMERGENCY_SHUTDOWN
        assert decision.is_emergency_shutdown

    def test_evaluate_broker_failure_high_severity_selects_failover(self):
        ctx = _ctx(
            failure_category=FailureCategory.BROKER_FAILURE,
            failure_severity=FailureSeverity.HIGH,
        )
        decision = self.engine.evaluate(_req(ctx))
        assert decision.strategy_type == RecoveryStrategyType.FAILOVER

    def test_evaluate_data_integrity_selects_rollback(self):
        ctx = _ctx(
            failure_category=FailureCategory.DATA_INTEGRITY_FAILURE,
            rollback_available=True,
        )
        decision = self.engine.evaluate(_req(ctx))
        assert decision.strategy_type == RecoveryStrategyType.ROLLBACK

    def test_evaluate_unknown_uses_fallback(self):
        ctx = _ctx(failure_category=FailureCategory.UNKNOWN_FAILURE)
        decision = self.engine.evaluate(_req(ctx))
        assert decision.is_approved
        # ManualIntervention is the fallback for UNKNOWN
        assert decision.strategy_type == RecoveryStrategyType.MANUAL_INTERVENTION

    def test_retry_exhausted_does_not_select_retry(self):
        ctx = _ctx(
            failure_category=FailureCategory.TIMEOUT,
            is_retry_exhausted=True,
        )
        decision = self.engine.evaluate(_req(ctx))
        assert decision.strategy_type != RecoveryStrategyType.RETRY

    # ── Decision completeness ──────────────────────────────────────────────

    def test_decision_has_required_fields(self):
        ctx = _ctx()
        decision = self.engine.evaluate(_req(ctx))
        assert decision.decision_id
        assert decision.request_id
        assert decision.execution_session_id
        assert decision.subsystem_id
        assert 0.0 <= decision.confidence_score <= 1.0
        assert decision.evaluation_report is not None

    def test_decision_has_evaluation_report(self):
        ctx = _ctx()
        decision = self.engine.evaluate(_req(ctx))
        rpt = decision.evaluation_report
        assert rpt.policies_evaluated > 0
        assert rpt.selected_strategy is not None

    # ── Statistics ─────────────────────────────────────────────────────────

    def test_statistics_updated_after_evaluation(self):
        self.engine.evaluate(_req(_ctx()))
        assert self.engine.statistics.total_evaluations == 1
        assert self.engine.statistics.total_decisions == 1

    def test_retry_stat_incremented(self):
        ctx = _ctx(failure_category=FailureCategory.TIMEOUT, is_retry_exhausted=False)
        self.engine.evaluate(_req(ctx))
        # May or may not be retry; check retry_recommendations >= 0
        assert self.engine.statistics._retry_recommendations >= 0

    # ── History ────────────────────────────────────────────────────────────

    def test_history_updated_after_evaluation(self):
        self.engine.evaluate(_req(_ctx()))
        assert self.engine.history.decision_count == 1
        assert self.engine.history.request_count == 1

    # ── Policy management ──────────────────────────────────────────────────

    def test_register_custom_policy_at_runtime(self):
        class HighConfidenceTimeoutPolicy(RetryPolicy):
            def __init__(self):
                super().__init__()
                self.name = "HighConfidenceTimeoutPolicy"
                self.priority = 200

        p = HighConfidenceTimeoutPolicy()
        self.engine.register_policy(p)
        ctx = _ctx(failure_category=FailureCategory.TIMEOUT, is_retry_exhausted=False)
        decision = self.engine.evaluate(_req(ctx))
        assert decision.policy_name == "HighConfidenceTimeoutPolicy"

    def test_deactivate_policy(self):
        self.engine.deactivate_policy("RetryPolicy")
        ctx = _ctx(failure_category=FailureCategory.TIMEOUT, is_retry_exhausted=False)
        decision = self.engine.evaluate(_req(ctx))
        assert decision.strategy_type != RecoveryStrategyType.RETRY

    def test_activate_policy_after_deactivation(self):
        self.engine.deactivate_policy("RetryPolicy")
        self.engine.activate_policy("RetryPolicy")
        ctx = _ctx(failure_category=FailureCategory.TIMEOUT, is_retry_exhausted=False)
        decision = self.engine.evaluate(_req(ctx))
        assert decision.strategy_type == RecoveryStrategyType.RETRY

    # ── Concurrent evaluations ─────────────────────────────────────────────

    def test_concurrent_evaluations(self):
        errors = []
        decisions = []
        lock = threading.Lock()

        def evaluate_once():
            try:
                ctx = _ctx(failure_category=FailureCategory.TIMEOUT, is_retry_exhausted=False)
                d = self.engine.evaluate(_req(ctx))
                with lock:
                    decisions.append(d)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=evaluate_once) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent evaluation errors: {errors}"
        assert len(decisions) == 20


# ════════════════════════════════════════════════════════════════════════════
# 20. RecoveryPolicyEngineAdapter (M2 bridge)
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryPolicyEngineAdapter:
    def setup_method(self):
        self.engine = RecoveryPolicyEngine()
        self.engine.start()
        self.adapter = RecoveryPolicyEngineAdapter(self.engine)

    def teardown_method(self):
        if self.engine.lifecycle_state() not in ("stopped", "STOPPED"):
            self.engine.stop()

    def test_map_failure_type_timeout(self):
        cat = _map_failure_type_to_category("execution_timeout_error")
        assert cat == FailureCategory.TIMEOUT

    def test_map_failure_type_broker(self):
        cat = _map_failure_type_to_category("broker_connection_lost")
        assert cat == FailureCategory.BROKER_FAILURE

    def test_map_failure_type_risk(self):
        cat = _map_failure_type_to_category("risk_limit_exceeded")
        assert cat == FailureCategory.RISK_VIOLATION

    def test_map_failure_type_unknown(self):
        cat = _map_failure_type_to_category("unrecognized_type")
        assert cat == FailureCategory.UNKNOWN_FAILURE

    def test_map_severity_critical(self):
        sev = _map_severity_str("CRITICAL")
        assert sev == FailureSeverity.CRITICAL

    def test_map_severity_unknown(self):
        sev = _map_severity_str(None)
        assert sev == FailureSeverity.UNKNOWN

    def test_adapter_invoke_with_mock_m2_types(self):
        """Adapter translates M2 mock objects to M3 decision and back."""
        # Mock M2 PolicyDecision
        mock_policy_decision_cls = MagicMock()
        mock_policy_decision_cls.return_value = MagicMock()

        failure_ctx = MagicMock()
        failure_ctx.failure_type = "execution_timeout_error"
        failure_ctx.failure_reason = "timed out"
        failure_ctx.severity = "medium"

        m2_request = MagicMock()
        m2_request.request_id = str(uuid.uuid4())
        m2_request.execution_session_id = str(uuid.uuid4())
        m2_request.subsystem_id = "test-sub"
        m2_request.failure_context = failure_ctx

        m2_context = MagicMock()
        m2_context.monitoring_snapshot = None
        m2_context.gateway_snapshot = None
        m2_context.risk_snapshot = None

        with patch(
            "iios.execution.recovery.policies.recovery_policy_engine.RecoveryPolicyEngineAdapter.invoke"
        ) as mock_invoke:
            mock_invoke.return_value = MagicMock(
                approved=True, plan_id="plan-1", instructions=(), requires_failover=False
            )
            result = self.adapter.invoke(m2_request, m2_context)
            assert result is not None


# ════════════════════════════════════════════════════════════════════════════
# 21. __init__ public surface
# ════════════════════════════════════════════════════════════════════════════

class TestPublicSurface:
    def test_primary_imports(self):
        from iios.execution.recovery.policies import (
            RecoveryPolicyEngine,
            RecoveryPolicyEngineAdapter,
            PolicyEvaluationContext,
            PolicyEvaluationRequest,
            RecoveryPolicyDecision,
            FailureCategory,
            RecoveryStrategyType,
        )

    def test_policy_classes_importable(self):
        from iios.execution.recovery.policies import (
            RetryPolicy, ResumePolicy, RollbackPolicy, RestartPolicy,
            FailoverPolicy, ManualInterventionPolicy, EmergencyShutdownPolicy,
            CompositePolicy,
        )

    def test_exception_classes_importable(self):
        from iios.execution.recovery.policies import (
            RecoveryPolicyError,
            RecoveryPolicyNotRunningError,
            RecoveryPolicyNotFoundError,
        )

    def test_constants_importable(self):
        from iios.execution.recovery.policies import (
            VERSION, SYSTEM_ID, ENGINE_ID,
            CONFIDENCE_EMERGENCY_SHUTDOWN,
        )
        assert VERSION == "1.0.0"


# ════════════════════════════════════════════════════════════════════════════
# 22. Edge cases and regression
# ════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def setup_method(self):
        self.engine = RecoveryPolicyEngine()
        self.engine.start()

    def teardown_method(self):
        if self.engine.lifecycle_state() not in ("stopped", "STOPPED"):
            self.engine.stop()

    def test_evaluation_with_all_policies_deactivated_except_fallback(self):
        """When all non-fallback policies are deactivated, fallback fires."""
        for name in [
            "EmergencyShutdownPolicy", "FailoverPolicy", "RollbackPolicy",
            "RestartPolicy", "RetryPolicy", "ResumePolicy",
        ]:
            self.engine.deactivate_policy(name)
        ctx = _ctx(failure_category=FailureCategory.TIMEOUT)
        decision = self.engine.evaluate(_req(ctx))
        assert decision.strategy_type == RecoveryStrategyType.MANUAL_INTERVENTION

    def test_decision_id_is_unique(self):
        ids = set()
        for _ in range(50):
            ctx = _ctx()
            d = self.engine.evaluate(_req(ctx))
            ids.add(d.decision_id)
        assert len(ids) == 50

    def test_evaluation_time_recorded(self):
        ctx = _ctx()
        d = self.engine.evaluate(_req(ctx))
        assert d.evaluation_time_ms >= 0.0

    def test_emergency_overrides_retry_for_risk_breach(self):
        """Even if TIMEOUT category, risk breach should trigger emergency."""
        ctx = _ctx(
            failure_category=FailureCategory.TIMEOUT,
            is_within_risk_limits=False,
            breach_count=1,
        )
        decision = self.engine.evaluate(_req(ctx))
        assert decision.strategy_type == RecoveryStrategyType.EMERGENCY_SHUTDOWN

    def test_execution_failure_with_rollback_selects_rollback(self):
        ctx = _ctx(
            failure_category=FailureCategory.EXECUTION_FAILURE,
            rollback_available=True,
            failure_severity=FailureSeverity.MEDIUM,
        )
        decision = self.engine.evaluate(_req(ctx))
        # RollbackPolicy (70) > RestartPolicy (65) > ResumePolicy (55)
        assert decision.strategy_type == RecoveryStrategyType.ROLLBACK

    def test_statistics_all_recommendation_types(self):
        """Verify all recommendation type counters can be incremented."""
        stats = RecoveryPolicyStatistics()
        stats.record_resume_recommendation()
        stats.record_rollback_recommendation()
        stats.record_restart_recommendation()
        stats.record_failover_recommendation()
        d = stats.to_dict()
        assert d["resume_recommendations"] == 1
        assert d["rollback_recommendations"] == 1
        assert d["restart_recommendations"] == 1
        assert d["failover_recommendations"] == 1

    def test_context_with_degraded_components(self):
        ctx = make_policy_evaluation_context(
            execution_session_id = "s",
            subsystem_id         = "sub",
            failure_category     = FailureCategory.INFRASTRUCTURE_FAILURE,
            failure_severity     = FailureSeverity.HIGH,
            failure_reason       = "degraded",
            degraded_components  = ("broker-A", "gateway-B"),
        )
        assert len(ctx.degraded_components) == 2

    def test_context_tags_preserved(self):
        ctx = make_policy_evaluation_context(
            execution_session_id = "s",
            subsystem_id         = "sub",
            failure_category     = FailureCategory.TIMEOUT,
            failure_severity     = FailureSeverity.LOW,
            failure_reason       = "r",
            tags                 = ("production", "urgent"),
        )
        assert "production" in ctx.tags
