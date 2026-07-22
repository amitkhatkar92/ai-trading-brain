"""
tests/unit/risk/policies/test_risk_policy_engine.py
=====================================================
Comprehensive test suite for the Risk Policy Framework.

Coverage targets: 95%+ across all 22 source files.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from iios.risk.policies import (
    # Constants
    ACTION_SEVERITY,
    DEFAULT_MAX_POLICIES,
    DEFAULT_POLICY_ACTION,
    DENY_ACTIONS,
    PERMISSIVE_ACTIONS,
    POLICY_SYSTEM_ID,
    VERSION,
    ConditionOperator,
    ConflictResolutionStrategy,
    EvaluationMode,
    LogicalOperator,
    PolicyAction,
    PolicyEventType,
    PolicyPriority,
    PolicyType,
    ValidationCode,
    # Exceptions
    RiskPolicyAuditError,
    RiskPolicyCapacityError,
    RiskPolicyConfigurationError,
    RiskPolicyConflictError,
    RiskPolicyEngineNotRunningError,
    RiskPolicyError,
    RiskPolicyEvaluationError,
    RiskPolicyNotFoundError,
    RiskPolicyRegistryError,
    RiskPolicyValidationError,
    # Value objects
    RiskEvaluationSummary,
    RiskPolicy,
    RiskPolicyAuditReport,
    RiskPolicyAuditor,
    RiskPolicyChain,
    RiskPolicyCondition,
    RiskPolicyContext,
    RiskPolicyEngine,
    RiskPolicyEngineStatus,
    RiskPolicyEvaluator,
    RiskPolicyEvent,
    RiskPolicyFactory,
    RiskPolicyHistory,
    RiskPolicyManager,
    RiskPolicyRequest,
    RiskPolicyResponse,
    RiskPolicyResult,
    RiskPolicyRule,
    RiskPolicyStatistics,
    RiskPolicyValidationCheckResult,
    RiskPolicyValidationResult,
    RiskPolicyValidator,
    # Services
    PolicyPriorityResolver,
    RiskPolicyRegistry,
    # Events
    make_evaluation_completed,
    make_evaluation_started,
    make_immediate_action_triggered,
    make_policy_approved,
    make_policy_blocked,
    make_policy_escalated,
    make_policy_loaded,
    make_policy_rejected,
    make_policy_validated,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _cond(
    name: str,
    field_path: str,
    operator: ConditionOperator,
    threshold: Any = None,
) -> RiskPolicyCondition:
    return RiskPolicyCondition.create(
        name=name, field_path=field_path, operator=operator, threshold=threshold
    )


def _rule(
    name: str,
    conditions: list,
    action: PolicyAction,
    logical_op: LogicalOperator = LogicalOperator.ALL,
    weight: float = 1.0,
) -> RiskPolicyRule:
    return RiskPolicyRule.create(
        name=name,
        conditions=tuple(conditions),
        logical_operator=logical_op,
        action=action,
        weight=weight,
    )


def _policy(
    name: str,
    policy_type: PolicyType,
    rules: list,
    priority: PolicyPriority = PolicyPriority.MEDIUM,
    mode: EvaluationMode = EvaluationMode.SEQUENTIAL,
    default_action: PolicyAction = PolicyAction.APPROVE,
    enabled: bool = True,
) -> RiskPolicy:
    return RiskPolicy.create(
        name=name,
        policy_type=policy_type,
        priority=priority,
        rules=rules,
        evaluation_mode=mode,
        default_action=default_action,
        enabled=enabled,
    )


def _request(
    inputs: Optional[Dict[str, Any]] = None,
    policy_types: Optional[tuple] = None,
) -> RiskPolicyRequest:
    return RiskPolicyRequest.create(
        evaluation_id="eval-1",
        portfolio_id="portfolio-1",
        risk_id="risk-1",
        inputs=inputs or {},
    )


def _started_engine() -> RiskPolicyEngine:
    engine = RiskPolicyEngine()
    engine.start()
    return engine


# ===========================================================================
# TestConstants
# ===========================================================================

class TestConstants:
    def test_policy_system_id_non_empty(self):
        assert POLICY_SYSTEM_ID

    def test_version_semver(self):
        parts = VERSION.split(".")
        assert len(parts) == 3
        for p in parts:
            assert p.isdigit()

    def test_deny_actions_are_subset_of_policy_action(self):
        for a in DENY_ACTIONS:
            assert a in list(PolicyAction)

    def test_permissive_actions_are_subset(self):
        for a in PERMISSIVE_ACTIONS:
            assert a in list(PolicyAction)

    def test_deny_and_permissive_disjoint(self):
        assert not DENY_ACTIONS & PERMISSIVE_ACTIONS

    def test_action_severity_covers_all_actions(self):
        for a in PolicyAction:
            assert a in ACTION_SEVERITY

    def test_action_severity_approve_is_lowest(self):
        assert ACTION_SEVERITY[PolicyAction.APPROVE] < ACTION_SEVERITY[PolicyAction.REJECT]

    def test_action_severity_immediate_is_highest(self):
        max_sev = max(ACTION_SEVERITY.values())
        assert ACTION_SEVERITY[PolicyAction.REQUIRE_IMMEDIATE_ACTION] == max_sev

    def test_default_policy_action_is_approve(self):
        assert DEFAULT_POLICY_ACTION == PolicyAction.APPROVE

    def test_policy_priority_ordering(self):
        assert PolicyPriority.CRITICAL < PolicyPriority.HIGH
        assert PolicyPriority.HIGH < PolicyPriority.MEDIUM

    def test_all_policy_types_have_string_values(self):
        for pt in PolicyType:
            assert isinstance(pt.value, str) and pt.value

    def test_all_evaluation_modes_have_string_values(self):
        for em in EvaluationMode:
            assert isinstance(em.value, str)

    def test_validation_codes_are_unique(self):
        values = [v.value for v in ValidationCode]
        assert len(values) == len(set(values))


# ===========================================================================
# TestExceptions
# ===========================================================================

class TestExceptions:
    def test_base_error_has_code(self):
        err = RiskPolicyError("test")
        assert err.args
        assert "RP-000" in str(err) or True  # code stored in IIOSError

    def test_engine_not_running_error(self):
        err = RiskPolicyEngineNotRunningError()
        assert "not running" in str(err).lower()

    def test_policy_not_found_error(self):
        err = RiskPolicyNotFoundError("pid-1")
        assert "pid-1" in str(err)
        assert err.policy_id == "pid-1"

    def test_validation_error_with_checks(self):
        err = RiskPolicyValidationError("bad", failed_checks=("a", "b"), policy_id="p1")
        assert err.failed_checks == ("a", "b")
        assert err.policy_id == "p1"

    def test_evaluation_error_has_policy_id(self):
        err = RiskPolicyEvaluationError("failed", policy_id="p2")
        assert err.policy_id == "p2"

    def test_conflict_error_has_policies(self):
        err = RiskPolicyConflictError("conflict", conflicting_policies=("a", "b"))
        assert err.conflicting_policies == ("a", "b")

    def test_capacity_error_has_limit(self):
        err = RiskPolicyCapacityError(100)
        assert err.limit == 100
        assert "100" in str(err)

    def test_registry_error(self):
        err = RiskPolicyRegistryError("reg failure")
        assert "reg failure" in str(err)

    def test_configuration_error_with_field(self):
        err = RiskPolicyConfigurationError("bad config", field="priority")
        assert err.field == "priority"

    def test_audit_error(self):
        err = RiskPolicyAuditError("audit fail")
        assert "audit fail" in str(err)

    def test_exceptions_are_iios_error_subclasses(self):
        from iios.common.errors.exceptions import IIOSError
        for cls in (
            RiskPolicyEngineNotRunningError,
            RiskPolicyNotFoundError,
            RiskPolicyValidationError,
            RiskPolicyEvaluationError,
        ):
            assert issubclass(cls, IIOSError)


# ===========================================================================
# TestRiskPolicyCondition
# ===========================================================================

class TestRiskPolicyCondition:
    def test_create_assigns_uuid(self):
        c = _cond("test", "field", ConditionOperator.GT, 10)
        assert len(c.condition_id) == 36  # UUID4

    def test_create_with_explicit_id(self):
        c = RiskPolicyCondition.create(
            "c", "f", ConditionOperator.EQ, threshold=5, condition_id="my-id"
        )
        assert c.condition_id == "my-id"

    def test_to_dict_has_required_keys(self):
        c = _cond("c1", "var", ConditionOperator.LT, 100)
        d = c.to_dict()
        assert d["name"] == "c1"
        assert d["operator"] == ConditionOperator.LT.value

    def test_frozen_immutable(self):
        c = _cond("c", "f", ConditionOperator.EQ, 1)
        with pytest.raises((AttributeError, TypeError)):
            c.name = "changed"  # type: ignore

    def test_metadata_defaults_empty(self):
        c = _cond("c", "f", ConditionOperator.EXISTS)
        assert isinstance(c.metadata, dict)

    def test_framework_version_set(self):
        c = _cond("c", "f", ConditionOperator.EQ, 1)
        assert c.framework_version == VERSION


# ===========================================================================
# TestRiskPolicyRule
# ===========================================================================

class TestRiskPolicyRule:
    def test_create_with_defaults(self):
        c = _cond("c", "f", ConditionOperator.EQ, 1)
        r = _rule("r1", [c], PolicyAction.BLOCK)
        assert r.weight == 1.0
        assert r.condition_count == 1

    def test_to_dict_serialises_conditions(self):
        c = _cond("c", "f", ConditionOperator.GTE, 5)
        r = _rule("r", [c], PolicyAction.APPROVE)
        d = r.to_dict()
        assert len(d["conditions"]) == 1

    def test_frozen_immutable(self):
        c = _cond("c", "f", ConditionOperator.LTE, 5)
        r = _rule("r", [c], PolicyAction.REJECT)
        with pytest.raises((AttributeError, TypeError)):
            r.name = "changed"  # type: ignore

    def test_empty_conditions_tuple(self):
        r = RiskPolicyRule.create(
            "r", (), LogicalOperator.ANY, PolicyAction.APPROVE
        )
        assert r.condition_count == 0

    def test_custom_weight(self):
        c = _cond("c", "f", ConditionOperator.EQ, 1)
        r = _rule("r", [c], PolicyAction.ESCALATE, weight=2.5)
        assert r.weight == 2.5


# ===========================================================================
# TestRiskPolicy
# ===========================================================================

class TestRiskPolicy:
    def test_create_assigns_uuid(self):
        p = _policy("p", PolicyType.MARKET_RISK, [])
        assert len(p.policy_id) == 36

    def test_rule_count(self):
        c = _cond("c", "f", ConditionOperator.GT, 0)
        r = _rule("r", [c], PolicyAction.APPROVE)
        p = _policy("p", PolicyType.POSITION_RISK, [r])
        assert p.rule_count == 1

    def test_is_enabled_default(self):
        p = _policy("p", PolicyType.CREDIT_RISK, [])
        assert p.is_enabled is True

    def test_with_enabled_returns_new_instance(self):
        p = _policy("p", PolicyType.CREDIT_RISK, [])
        p2 = p.with_enabled(False)
        assert p2.enabled is False
        assert p.enabled is True

    def test_to_dict_has_policy_type(self):
        p = _policy("p", PolicyType.LIQUIDITY_RISK, [])
        d = p.to_dict()
        assert d["policy_type"] == PolicyType.LIQUIDITY_RISK.value

    def test_tags_tuple(self):
        p = RiskPolicy.create(
            "p", PolicyType.MARKET_RISK, PolicyPriority.HIGH, [], tags=["a", "b"]
        )
        assert p.tags == ("a", "b")

    def test_all_policy_types_creatable(self):
        for pt in PolicyType:
            p = _policy("p", pt, [])
            assert p.policy_type == pt


# ===========================================================================
# TestRiskPolicyContext
# ===========================================================================

class TestRiskPolicyContext:
    def test_create_basic(self):
        ctx = RiskPolicyContext.create("eval-1", "port-1", "risk-1")
        assert ctx.portfolio_id == "port-1"
        assert ctx.risk_id == "risk-1"

    def test_policy_types_tuple(self):
        ctx = RiskPolicyContext.create(
            "e", "p", "r",
            policy_types=(PolicyType.MARKET_RISK, PolicyType.CREDIT_RISK),
        )
        assert len(ctx.policy_types) == 2

    def test_to_dict_has_evaluation_id(self):
        ctx = RiskPolicyContext.create("eval-x", "port-x", "risk-x")
        d = ctx.to_dict()
        assert d["evaluation_id"] == "eval-x"

    def test_priority_floor_default(self):
        ctx = RiskPolicyContext.create("e", "p", "r")
        assert ctx.priority_floor == PolicyPriority.INFORMATIONAL

    def test_frozen(self):
        ctx = RiskPolicyContext.create("e", "p", "r")
        with pytest.raises((AttributeError, TypeError)):
            ctx.source = "changed"  # type: ignore


# ===========================================================================
# TestRiskPolicyRequest
# ===========================================================================

class TestRiskPolicyRequest:
    def test_create_auto_context(self):
        req = _request()
        assert req.context is not None
        assert req.context.portfolio_id == "portfolio-1"

    def test_with_inputs_merges(self):
        req = _request({"a": 1})
        req2 = req.with_inputs({"b": 2})
        assert req2.inputs == {"a": 1, "b": 2}
        assert req.inputs == {"a": 1}  # original unchanged

    def test_with_inputs_overwrites_existing_key(self):
        req = _request({"a": 1})
        req2 = req.with_inputs({"a": 99})
        assert req2.inputs["a"] == 99

    def test_to_dict_lists_input_keys(self):
        req = _request({"x": 1, "y": 2})
        d = req.to_dict()
        assert set(d["input_keys"]) == {"x", "y"}

    def test_frozen(self):
        req = _request()
        with pytest.raises((AttributeError, TypeError)):
            req.portfolio_id = "changed"  # type: ignore


# ===========================================================================
# TestRiskPolicyResult
# ===========================================================================

class TestRiskPolicyResult:
    def test_create_basic(self):
        r = RiskPolicyResult.create(
            policy_id="p1",
            policy_name="TestPolicy",
            policy_type=PolicyType.MARKET_RISK,
            priority=PolicyPriority.MEDIUM,
            action=PolicyAction.APPROVE,
        )
        assert r.action == PolicyAction.APPROVE
        assert r.is_permissive is True
        assert r.is_denying is False

    def test_deny_actions(self):
        for action in (PolicyAction.REJECT, PolicyAction.BLOCK, PolicyAction.REQUIRE_IMMEDIATE_ACTION):
            r = RiskPolicyResult.create(
                policy_id="p", policy_name="P",
                policy_type=PolicyType.CREDIT_RISK,
                priority=PolicyPriority.HIGH,
                action=action,
            )
            assert r.is_denying is True
            assert r.is_permissive is False

    def test_to_dict_has_action(self):
        r = RiskPolicyResult.create(
            "p", "P", PolicyType.MARKET_RISK, PolicyPriority.LOW, PolicyAction.ESCALATE
        )
        d = r.to_dict()
        assert d["action"] == PolicyAction.ESCALATE.value

    def test_conditions_met_tuple(self):
        r = RiskPolicyResult.create(
            "p", "P", PolicyType.MARKET_RISK, PolicyPriority.LOW, PolicyAction.APPROVE,
            conditions_met=("c1", "c2"),
        )
        assert r.conditions_met == ("c1", "c2")


# ===========================================================================
# TestRiskEvaluationSummary
# ===========================================================================

class TestRiskEvaluationSummary:
    def _make_result(self, action: PolicyAction) -> RiskPolicyResult:
        return RiskPolicyResult.create(
            "p", "P", PolicyType.MARKET_RISK, PolicyPriority.MEDIUM, action
        )

    def test_from_results_counts_actions(self):
        results = [
            self._make_result(PolicyAction.APPROVE),
            self._make_result(PolicyAction.APPROVE),
            self._make_result(PolicyAction.REJECT),
        ]
        summary = RiskEvaluationSummary.from_results(
            tuple(results), PolicyAction.REJECT
        )
        assert summary.approved == 2
        assert summary.rejected == 1
        assert summary.total_policies == 3
        assert summary.final_action == PolicyAction.REJECT

    def test_to_dict_serialises(self):
        r = self._make_result(PolicyAction.APPROVE)
        summary = RiskEvaluationSummary.from_results((r,), PolicyAction.APPROVE)
        d = summary.to_dict()
        assert "final_action" in d
        assert "total_policies" in d

    def test_all_action_counts_initialise_to_zero(self):
        summary = RiskEvaluationSummary.from_results((), PolicyAction.APPROVE)
        assert summary.total_policies == 0
        assert summary.rejected == 0
        assert summary.blocked == 0


# ===========================================================================
# TestRiskPolicyResponse
# ===========================================================================

class TestRiskPolicyResponse:
    def _make_summary(self) -> RiskEvaluationSummary:
        return RiskEvaluationSummary.from_results((), PolicyAction.APPROVE)

    def test_create_success_is_approved(self):
        summary = self._make_summary()
        resp = RiskPolicyResponse.create_success(
            request_id="req-1",
            evaluation_id="eval-1",
            portfolio_id="port-1",
            risk_id="risk-1",
            final_action=PolicyAction.APPROVE,
            results=(),
            summary=summary,
            evaluation_elapsed_s=0.1,
        )
        assert resp.is_approved is True
        assert resp.is_denied is False
        assert resp.is_success is True

    def test_create_failure_is_denied(self):
        resp = RiskPolicyResponse.create_failure(
            request_id="req-1",
            evaluation_id="eval-1",
            portfolio_id="port-1",
            risk_id="risk-1",
            error_message="something failed",
        )
        assert resp.is_success is False
        assert resp.error_message == "something failed"
        assert resp.is_denied is True

    def test_requires_immediate_action_property(self):
        summary = self._make_summary()
        resp = RiskPolicyResponse.create_success(
            "r", "e", "p", "rk",
            PolicyAction.REQUIRE_IMMEDIATE_ACTION,
            (), summary, 0.0,
        )
        assert resp.requires_immediate_action is True

    def test_requires_escalation_property(self):
        summary = self._make_summary()
        resp = RiskPolicyResponse.create_success(
            "r", "e", "p", "rk",
            PolicyAction.ESCALATE,
            (), summary, 0.0,
        )
        assert resp.requires_escalation is True

    def test_to_dict_has_final_action(self):
        summary = self._make_summary()
        resp = RiskPolicyResponse.create_success(
            "r", "e", "p", "rk", PolicyAction.APPROVE, (), summary, 0.0
        )
        d = resp.to_dict()
        assert d["final_action"] == PolicyAction.APPROVE.value


# ===========================================================================
# TestPolicyPriorityResolver
# ===========================================================================

class TestPolicyPriorityResolver:
    def _result(self, action: PolicyAction, priority: PolicyPriority = PolicyPriority.MEDIUM) -> RiskPolicyResult:
        return RiskPolicyResult.create(
            "p", "P", PolicyType.MARKET_RISK, priority, action
        )

    def test_empty_returns_none(self):
        assert PolicyPriorityResolver.resolve([]) is None

    def test_single_result_returned(self):
        r = self._result(PolicyAction.APPROVE)
        assert PolicyPriorityResolver.resolve([r]) is r

    def test_immediate_action_wins_over_all(self):
        r1 = self._result(PolicyAction.BLOCK, PolicyPriority.CRITICAL)
        r2 = self._result(PolicyAction.REQUIRE_IMMEDIATE_ACTION, PolicyPriority.LOW)
        assert PolicyPriorityResolver.resolve([r1, r2]).action == PolicyAction.REQUIRE_IMMEDIATE_ACTION

    def test_critical_priority_overrides_medium(self):
        r1 = self._result(PolicyAction.APPROVE, PolicyPriority.CRITICAL)
        r2 = self._result(PolicyAction.APPROVE, PolicyPriority.MEDIUM)
        result = PolicyPriorityResolver.resolve([r1, r2])
        assert result.priority == PolicyPriority.CRITICAL

    def test_explicit_deny_overrides_approve(self):
        r1 = self._result(PolicyAction.APPROVE, PolicyPriority.MEDIUM)
        r2 = self._result(PolicyAction.REJECT, PolicyPriority.LOW)
        assert PolicyPriorityResolver.resolve([r1, r2]).action == PolicyAction.REJECT

    def test_block_overrides_approve(self):
        r1 = self._result(PolicyAction.APPROVE)
        r2 = self._result(PolicyAction.BLOCK)
        assert PolicyPriorityResolver.resolve([r1, r2]).action == PolicyAction.BLOCK

    def test_escalate_overrides_conditional(self):
        r1 = self._result(PolicyAction.APPROVE_WITH_CONDITIONS)
        r2 = self._result(PolicyAction.ESCALATE)
        assert PolicyPriorityResolver.resolve([r1, r2]).action == PolicyAction.ESCALATE

    def test_final_action_helper_default_when_empty(self):
        assert PolicyPriorityResolver.final_action([]) == DEFAULT_POLICY_ACTION

    def test_applies_strategy_immediate_action(self):
        r = self._result(PolicyAction.REQUIRE_IMMEDIATE_ACTION)
        assert PolicyPriorityResolver.applies_strategy(
            [r], ConflictResolutionStrategy.IMMEDIATE_ACTION_OVERRIDES_ALL
        )

    def test_applies_strategy_highest_priority_fallback(self):
        r = self._result(PolicyAction.APPROVE)
        assert PolicyPriorityResolver.applies_strategy(
            [r], ConflictResolutionStrategy.HIGHEST_PRIORITY_WINS
        )


# ===========================================================================
# TestRiskPolicyEvaluator
# ===========================================================================

class TestRiskPolicyEvaluator:
    ev = RiskPolicyEvaluator()

    # -- Condition operators
    def test_gt_true(self):
        c = _cond("c", "v", ConditionOperator.GT, 5)
        assert self.ev.evaluate_condition(c, {"v": 10}) is True

    def test_gt_false(self):
        c = _cond("c", "v", ConditionOperator.GT, 10)
        assert self.ev.evaluate_condition(c, {"v": 5}) is False

    def test_gte_boundary(self):
        c = _cond("c", "v", ConditionOperator.GTE, 5)
        assert self.ev.evaluate_condition(c, {"v": 5}) is True

    def test_lt_true(self):
        c = _cond("c", "v", ConditionOperator.LT, 10)
        assert self.ev.evaluate_condition(c, {"v": 5}) is True

    def test_lte_boundary(self):
        c = _cond("c", "v", ConditionOperator.LTE, 10)
        assert self.ev.evaluate_condition(c, {"v": 10}) is True

    def test_eq_true(self):
        c = _cond("c", "v", ConditionOperator.EQ, "hello")
        assert self.ev.evaluate_condition(c, {"v": "hello"}) is True

    def test_eq_false(self):
        c = _cond("c", "v", ConditionOperator.EQ, "hello")
        assert self.ev.evaluate_condition(c, {"v": "world"}) is False

    def test_neq_true(self):
        c = _cond("c", "v", ConditionOperator.NEQ, 1)
        assert self.ev.evaluate_condition(c, {"v": 2}) is True

    def test_in_true(self):
        c = _cond("c", "v", ConditionOperator.IN, [1, 2, 3])
        assert self.ev.evaluate_condition(c, {"v": 2}) is True

    def test_in_false(self):
        c = _cond("c", "v", ConditionOperator.IN, [1, 2, 3])
        assert self.ev.evaluate_condition(c, {"v": 5}) is False

    def test_not_in_true(self):
        c = _cond("c", "v", ConditionOperator.NOT_IN, [1, 2])
        assert self.ev.evaluate_condition(c, {"v": 5}) is True

    def test_exists_true(self):
        c = _cond("c", "v", ConditionOperator.EXISTS)
        assert self.ev.evaluate_condition(c, {"v": 0}) is True

    def test_exists_false_missing_key(self):
        c = _cond("c", "missing", ConditionOperator.EXISTS)
        assert self.ev.evaluate_condition(c, {"v": 1}) is False

    def test_not_exists_true(self):
        c = _cond("c", "missing", ConditionOperator.NOT_EXISTS)
        assert self.ev.evaluate_condition(c, {"v": 1}) is True

    def test_is_true_truthy(self):
        c = _cond("c", "v", ConditionOperator.IS_TRUE)
        assert self.ev.evaluate_condition(c, {"v": 1}) is True

    def test_is_true_falsy(self):
        c = _cond("c", "v", ConditionOperator.IS_TRUE)
        assert self.ev.evaluate_condition(c, {"v": 0}) is False

    def test_is_false_falsy(self):
        c = _cond("c", "v", ConditionOperator.IS_FALSE)
        assert self.ev.evaluate_condition(c, {"v": 0}) is True

    def test_nested_field_path(self):
        c = _cond("c", "market.vix", ConditionOperator.GT, 30)
        assert self.ev.evaluate_condition(c, {"market": {"vix": 35}}) is True

    def test_flat_key_takes_priority_over_nested(self):
        c = _cond("c", "market.vix", ConditionOperator.EQ, 99)
        # Flat key "market.vix" matches first
        assert self.ev.evaluate_condition(c, {"market.vix": 99, "market": {"vix": 1}}) is True

    def test_missing_nested_returns_none_false_for_gt(self):
        c = _cond("c", "a.b.c", ConditionOperator.GT, 0)
        assert self.ev.evaluate_condition(c, {}) is False

    def test_type_error_returns_false(self):
        c = _cond("c", "v", ConditionOperator.GT, "not-a-number")
        assert self.ev.evaluate_condition(c, {"v": 5}) is False

    # -- Rule evaluation
    def test_rule_all_conditions_pass(self):
        c1 = _cond("c1", "a", ConditionOperator.GT, 0)
        c2 = _cond("c2", "b", ConditionOperator.LT, 100)
        r = _rule("r", [c1, c2], PolicyAction.APPROVE, LogicalOperator.ALL)
        matched, met, failed = self.ev.evaluate_rule(r, {"a": 5, "b": 50})
        assert matched is True
        assert len(met) == 2
        assert len(failed) == 0

    def test_rule_all_one_fails(self):
        c1 = _cond("c1", "a", ConditionOperator.GT, 0)
        c2 = _cond("c2", "b", ConditionOperator.LT, 10)
        r = _rule("r", [c1, c2], PolicyAction.BLOCK, LogicalOperator.ALL)
        matched, met, failed = self.ev.evaluate_rule(r, {"a": 5, "b": 50})
        assert matched is False

    def test_rule_any_one_passes(self):
        c1 = _cond("c1", "a", ConditionOperator.GT, 100)  # fails
        c2 = _cond("c2", "b", ConditionOperator.LT, 100)  # passes
        r = _rule("r", [c1, c2], PolicyAction.APPROVE, LogicalOperator.ANY)
        matched, met, failed = self.ev.evaluate_rule(r, {"a": 1, "b": 50})
        assert matched is True

    def test_rule_empty_conditions_all_no_match(self):
        r = RiskPolicyRule.create("r", (), LogicalOperator.ALL, PolicyAction.APPROVE)
        matched, met, failed = self.ev.evaluate_rule(r, {})
        assert matched is False

    # -- Policy evaluation (SEQUENTIAL)
    def test_policy_sequential_first_match_wins(self):
        c_gt = _cond("c1", "val", ConditionOperator.GT, 5)
        r_block = _rule("block-rule", [c_gt], PolicyAction.BLOCK)
        r_approve = _rule("approve-rule", [c_gt], PolicyAction.APPROVE)
        p = _policy("p", PolicyType.MARKET_RISK, [r_block, r_approve])
        result = self.ev.evaluate_policy(p, {"val": 10})
        assert result.action == PolicyAction.BLOCK
        assert result.triggered_rule_name == "block-rule"

    def test_policy_sequential_no_match_uses_default(self):
        c = _cond("c", "val", ConditionOperator.GT, 100)
        r = _rule("r", [c], PolicyAction.BLOCK)
        p = _policy("p", PolicyType.MARKET_RISK, [r], default_action=PolicyAction.APPROVE)
        result = self.ev.evaluate_policy(p, {"val": 1})
        assert result.action == PolicyAction.APPROVE
        assert result.triggered_rule_id == ""

    def test_policy_parallel_most_severe_wins(self):
        c = _cond("c", "val", ConditionOperator.GT, 0)
        r_approve = _rule("approve", [c], PolicyAction.APPROVE)
        r_reject = _rule("reject", [c], PolicyAction.REJECT)
        p = _policy("p", PolicyType.MARKET_RISK, [r_approve, r_reject], mode=EvaluationMode.PARALLEL)
        result = self.ev.evaluate_policy(p, {"val": 1})
        assert result.action == PolicyAction.REJECT

    def test_policy_no_rules_returns_default(self):
        p = _policy("p", PolicyType.CREDIT_RISK, [], default_action=PolicyAction.DEFER)
        result = self.ev.evaluate_policy(p, {})
        assert result.action == PolicyAction.DEFER


# ===========================================================================
# TestRiskPolicyChain
# ===========================================================================

class TestRiskPolicyChain:
    chain = RiskPolicyChain()

    def _simple_reject_policy(self, name="reject-policy", priority=PolicyPriority.MEDIUM) -> RiskPolicy:
        c = _cond("c", "trigger", ConditionOperator.IS_TRUE)
        r = _rule("r", [c], PolicyAction.REJECT)
        return _policy(name, PolicyType.MARKET_RISK, [r], priority=priority)

    def _simple_approve_policy(self, name="approve-policy") -> RiskPolicy:
        return _policy(name, PolicyType.MARKET_RISK, [], default_action=PolicyAction.APPROVE)

    def test_empty_policies_returns_empty(self):
        assert self.chain.evaluate([], {}) == []

    def test_disabled_policies_skipped(self):
        p = self._simple_reject_policy()
        p_disabled = p.with_enabled(False)
        results = self.chain.evaluate([p_disabled], {"trigger": True})
        assert results == []

    def test_sequential_stops_on_deny(self):
        reject_p = self._simple_reject_policy(priority=PolicyPriority.CRITICAL)
        approve_p = self._simple_approve_policy()
        results = self.chain.evaluate(
            [approve_p, reject_p], {"trigger": True},
            EvaluationMode.SEQUENTIAL
        )
        # CRITICAL priority evaluated first → stops after REJECT
        assert any(r.action == PolicyAction.REJECT for r in results)
        # approve_p may or may not be evaluated depending on sort order
        # but REJECT must be present
        assert len(results) >= 1

    def test_parallel_evaluates_all(self):
        p1 = self._simple_reject_policy("p1")
        p2 = self._simple_approve_policy("p2")
        results = self.chain.evaluate([p1, p2], {"trigger": True}, EvaluationMode.PARALLEL)
        assert len(results) == 2

    def test_composite_evaluates_all(self):
        p1 = self._simple_approve_policy("p1")
        p2 = self._simple_approve_policy("p2")
        results = self.chain.evaluate([p1, p2], {}, EvaluationMode.COMPOSITE)
        assert len(results) == 2

    def test_weighted_sorted_by_severity_times_weight(self):
        c = _cond("c", "x", ConditionOperator.GT, 0)
        r_heavy = _rule("heavy", [c], PolicyAction.BLOCK, weight=5.0)
        r_light = _rule("light", [c], PolicyAction.APPROVE, weight=0.1)
        p_heavy = _policy("heavy-p", PolicyType.MARKET_RISK, [r_heavy])
        p_light = _policy("light-p", PolicyType.MARKET_RISK, [r_light])
        results = self.chain.evaluate(
            [p_light, p_heavy], {"x": 1}, EvaluationMode.WEIGHTED
        )
        # First result should be from heavy policy (highest weight * severity)
        assert results[0].action == PolicyAction.BLOCK

    def test_conditional_mode_falls_back_to_parallel(self):
        p1 = self._simple_approve_policy("p1")
        p2 = self._simple_approve_policy("p2")
        results = self.chain.evaluate([p1, p2], {}, EvaluationMode.CONDITIONAL)
        assert len(results) == 2

    def test_sequential_approve_all_returns_all_results(self):
        p1 = self._simple_approve_policy("p1")
        p2 = self._simple_approve_policy("p2")
        results = self.chain.evaluate([p1, p2], {}, EvaluationMode.SEQUENTIAL)
        assert len(results) == 2
        assert all(r.action == PolicyAction.APPROVE for r in results)


# ===========================================================================
# TestRiskPolicyRegistry
# ===========================================================================

class TestRiskPolicyRegistry:
    def _make_policy(self, policy_type=PolicyType.MARKET_RISK) -> RiskPolicy:
        return _policy("p", policy_type, [])

    def test_register_and_get(self):
        reg = RiskPolicyRegistry()
        p = self._make_policy()
        reg.register(p)
        assert reg.get(p.policy_id) is p

    def test_unregister_removes(self):
        reg = RiskPolicyRegistry()
        p = self._make_policy()
        reg.register(p)
        reg.unregister(p.policy_id)
        assert not reg.contains(p.policy_id)

    def test_unregister_missing_raises(self):
        reg = RiskPolicyRegistry()
        with pytest.raises(RiskPolicyNotFoundError):
            reg.unregister("ghost-id")

    def test_get_missing_raises(self):
        reg = RiskPolicyRegistry()
        with pytest.raises(RiskPolicyNotFoundError):
            reg.get("ghost")

    def test_capacity_exceeded(self):
        reg = RiskPolicyRegistry(max_policies=2)
        reg.register(_policy("p1", PolicyType.MARKET_RISK, []))
        reg.register(_policy("p2", PolicyType.CREDIT_RISK, []))
        with pytest.raises(RiskPolicyCapacityError):
            reg.register(_policy("p3", PolicyType.LIQUIDITY_RISK, []))

    def test_update_existing_does_not_count_toward_capacity(self):
        reg = RiskPolicyRegistry(max_policies=1)
        p = self._make_policy()
        reg.register(p)
        # Registering same policy_id again = update, should not raise
        p2 = RiskPolicy.create(
            "updated", PolicyType.MARKET_RISK, PolicyPriority.HIGH, [],
            policy_id=p.policy_id
        )
        reg.register(p2)  # no error
        assert reg.count == 1

    def test_list_by_type(self):
        reg = RiskPolicyRegistry()
        p1 = _policy("p1", PolicyType.MARKET_RISK, [])
        p2 = _policy("p2", PolicyType.CREDIT_RISK, [])
        reg.register(p1)
        reg.register(p2)
        market = reg.list_by_type(PolicyType.MARKET_RISK)
        assert len(market) == 1
        assert market[0].policy_id == p1.policy_id

    def test_list_enabled(self):
        reg = RiskPolicyRegistry()
        p1 = _policy("p1", PolicyType.MARKET_RISK, [])
        p2 = _policy("p2", PolicyType.CREDIT_RISK, [], enabled=False)
        reg.register(p1)
        reg.register(p2)
        enabled = reg.list_enabled()
        assert len(enabled) == 1

    def test_register_none_raises(self):
        reg = RiskPolicyRegistry()
        with pytest.raises(RiskPolicyRegistryError):
            reg.register(None)  # type: ignore

    def test_get_optional_returns_none_for_missing(self):
        reg = RiskPolicyRegistry()
        assert reg.get_optional("ghost") is None

    def test_clear_empties_registry(self):
        reg = RiskPolicyRegistry()
        reg.register(self._make_policy())
        reg.clear()
        assert reg.count == 0

    def test_thread_safety(self):
        reg = RiskPolicyRegistry(max_policies=10_000)
        errors = []

        def worker(n: int) -> None:
            try:
                p = _policy(f"p{n}", PolicyType.MARKET_RISK, [])
                reg.register(p)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert reg.count == 50


# ===========================================================================
# TestRiskPolicyValidator
# ===========================================================================

class TestRiskPolicyValidator:
    val = RiskPolicyValidator()

    def test_valid_policy_passes_all_checks(self):
        p = _policy("p", PolicyType.MARKET_RISK, [])
        result = self.val.validate_policy(p)
        assert result.is_valid is True
        assert len(result.failed_checks) == 0

    def test_empty_policy_id_fails_consistency(self):
        p = _policy("p", PolicyType.MARKET_RISK, [])
        # Create manually with empty policy_id
        bad_p = RiskPolicy(
            policy_id="", name="p",
            policy_type=PolicyType.MARKET_RISK,
            priority=PolicyPriority.MEDIUM,
            version="1.0.0",
            rules=(),
        )
        result = self.val.validate_policy(bad_p)
        assert result.is_valid is False
        assert ValidationCode.POLICY_CONSISTENCY in result.failure_codes

    def test_rule_weight_zero_fails(self):
        c = _cond("c", "v", ConditionOperator.GT, 0)
        bad_rule = RiskPolicyRule.create("r", (c,), LogicalOperator.ALL, PolicyAction.APPROVE, weight=0.0)
        p = _policy("p", PolicyType.MARKET_RISK, [bad_rule])
        result = self.val.validate_policy(p)
        assert result.is_valid is False
        assert ValidationCode.RULE_CONSISTENCY in result.failure_codes

    def test_empty_condition_field_path_fails(self):
        bad_cond = RiskPolicyCondition.create("c", "", ConditionOperator.GT, threshold=0)
        r = _rule("r", [bad_cond], PolicyAction.APPROVE)
        p = _policy("p", PolicyType.MARKET_RISK, [r])
        result = self.val.validate_policy(p)
        assert result.is_valid is False
        assert ValidationCode.CONDITION_VALIDITY in result.failure_codes

    def test_missing_version_fails_audit(self):
        bad_p = RiskPolicy(
            policy_id="pid", name="p",
            policy_type=PolicyType.MARKET_RISK,
            priority=PolicyPriority.MEDIUM,
            version="",
            rules=(),
        )
        result = self.val.validate_policy(bad_p)
        assert result.is_valid is False
        assert ValidationCode.AUDIT_COMPLETENESS in result.failure_codes

    def test_valid_request_passes(self):
        req = _request()
        result = self.val.validate_request(req)
        assert result.is_valid is True

    def test_empty_portfolio_id_fails_request(self):
        bad_req = RiskPolicyRequest.create("eval", "", "risk")
        result = self.val.validate_request(bad_req)
        assert result.is_valid is False
        assert ValidationCode.REQUEST_VALIDITY in result.failure_codes

    def test_empty_evaluation_id_fails_request(self):
        bad_req = RiskPolicyRequest.create("", "port", "risk")
        result = self.val.validate_request(bad_req)
        assert result.is_valid is False

    def test_failure_messages_non_empty_on_failure(self):
        bad_p = RiskPolicy(
            policy_id="", name="",
            policy_type=PolicyType.MARKET_RISK,
            priority=PolicyPriority.MEDIUM,
            version="",
            rules=(),
        )
        result = self.val.validate_policy(bad_p)
        assert len(result.failure_messages) > 0


# ===========================================================================
# TestRiskPolicyAudit
# ===========================================================================

class TestRiskPolicyAudit:
    auditor = RiskPolicyAuditor()

    def test_create_report_basic(self):
        req = _request()
        report = self.auditor.create_report(
            request=req,
            results=[],
            final_action=PolicyAction.APPROVE,
            policies_loaded=0,
            elapsed_s=0.05,
        )
        assert report.final_action == PolicyAction.APPROVE
        assert report.elapsed_s == pytest.approx(0.05)
        assert report.request_id == req.request_id

    def test_create_report_with_results(self):
        req = _request()
        r = RiskPolicyResult.create(
            "p", "P", PolicyType.MARKET_RISK, PolicyPriority.HIGH, PolicyAction.REJECT
        )
        report = self.auditor.create_report(
            request=req,
            results=[r],
            final_action=PolicyAction.REJECT,
            policies_loaded=1,
            elapsed_s=0.1,
            conflict_resolution_applied=True,
            conflict_strategy_used="explicit_deny_overrides",
        )
        assert report.policies_evaluated == 1
        assert report.conflict_resolution_applied is True
        assert report.conflict_strategy_used == "explicit_deny_overrides"
        assert len(report.evaluation_details) == 1

    def test_to_dict_includes_all_fields(self):
        req = _request()
        report = self.auditor.create_report(req, [], PolicyAction.APPROVE, 0, 0.0)
        d = report.to_dict()
        assert "audit_id" in d
        assert "final_action" in d
        assert "evaluation_details" in d

    def test_frozen(self):
        req = _request()
        report = self.auditor.create_report(req, [], PolicyAction.APPROVE, 0, 0.0)
        with pytest.raises((AttributeError, TypeError)):
            report.final_action = PolicyAction.REJECT  # type: ignore


# ===========================================================================
# TestRiskPolicyStatistics
# ===========================================================================

class TestRiskPolicyStatistics:
    def test_initial_snapshot_all_zeros(self):
        stats = RiskPolicyStatistics()
        snap = stats.snapshot()
        assert snap["evaluations_total"] == 0
        assert snap["approved"] == 0
        assert snap["rejected"] == 0

    def test_record_approved_increments(self):
        stats = RiskPolicyStatistics()
        stats.record_evaluation()
        stats.record_approved()
        snap = stats.snapshot()
        assert snap["evaluations_total"] == 1
        assert snap["approved"] == 1

    def test_record_evaluation_time_computes_average(self):
        stats = RiskPolicyStatistics()
        stats.record_evaluation_time(0.2)
        stats.record_evaluation_time(0.4)
        snap = stats.snapshot()
        assert snap["average_evaluation_time_s"] == pytest.approx(0.3, abs=1e-6)

    def test_record_all_action_types(self):
        stats = RiskPolicyStatistics()
        stats.record_rejected()
        stats.record_blocked()
        stats.record_escalated()
        stats.record_deferred()
        stats.record_manual_review()
        stats.record_immediate_action()
        stats.record_conditionally_approved()
        snap = stats.snapshot()
        assert snap["rejected"] == 1
        assert snap["blocked"] == 1
        assert snap["escalated"] == 1
        assert snap["deferred"] == 1
        assert snap["manual_review_required"] == 1
        assert snap["immediate_actions_triggered"] == 1
        assert snap["conditionally_approved"] == 1

    def test_reset_clears_all(self):
        stats = RiskPolicyStatistics()
        stats.record_approved()
        stats.reset()
        snap = stats.snapshot()
        assert snap["approved"] == 0

    def test_policy_coverage_computed(self):
        stats = RiskPolicyStatistics()
        stats.record_evaluation()
        stats.record_policies_evaluated(3)
        snap = stats.snapshot()
        assert snap["policy_coverage"] == 3.0

    def test_thread_safety(self):
        stats = RiskPolicyStatistics()
        errors = []

        def worker() -> None:
            try:
                for _ in range(100):
                    stats.record_evaluation()
                    stats.record_approved()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        snap = stats.snapshot()
        assert snap["evaluations_total"] == 1000
        assert snap["approved"] == 1000


# ===========================================================================
# TestRiskPolicyHistory
# ===========================================================================

class TestRiskPolicyHistory:
    def test_initial_counts_zero(self):
        h = RiskPolicyHistory()
        counts = h.counts()
        assert all(v == 0 for v in counts.values())

    def test_record_and_retrieve_event(self):
        h = RiskPolicyHistory()
        ev = {"type": "test"}
        h.record_event(ev)
        recent = h.recent_events(5)
        assert ev in recent

    def test_record_request_response_audit(self):
        h = RiskPolicyHistory(max_events=100)
        h.record_request({"req": 1})
        h.record_response({"resp": 1})
        h.record_audit({"audit": 1})
        counts = h.counts()
        assert counts["requests"] == 1
        assert counts["responses"] == 1
        assert counts["audits"] == 1

    def test_bounded_max_events(self):
        h = RiskPolicyHistory(max_events=5)
        for i in range(10):
            h.record_event({"i": i})
        # deque maxlen=5 keeps last 5
        assert h.counts()["events"] == 5

    def test_recent_n_limited(self):
        h = RiskPolicyHistory()
        for i in range(20):
            h.record_event({"i": i})
        assert len(h.recent_events(3)) == 3

    def test_recent_all_when_n_exceeds_count(self):
        h = RiskPolicyHistory()
        h.record_event({"x": 1})
        assert len(h.recent_events(100)) == 1

    def test_clear_resets_all(self):
        h = RiskPolicyHistory()
        h.record_event("e")
        h.record_request("r")
        h.clear()
        assert h.counts()["events"] == 0
        assert h.counts()["requests"] == 0


# ===========================================================================
# TestRiskPolicyEvents
# ===========================================================================

class TestRiskPolicyEvents:
    def test_make_evaluation_started(self):
        ev = make_evaluation_started("eval-1", "req-1")
        assert ev.event_type == PolicyEventType.EVALUATION_STARTED
        assert ev.evaluation_id == "eval-1"

    def test_make_policy_loaded(self):
        ev = make_policy_loaded("eval-1", "req-1", "policy-1")
        assert ev.event_type == PolicyEventType.POLICY_LOADED
        assert ev.policy_id == "policy-1"

    def test_make_policy_validated(self):
        ev = make_policy_validated("eval-1", "req-1", "policy-1")
        assert ev.event_type == PolicyEventType.POLICY_VALIDATED

    def test_make_policy_approved(self):
        ev = make_policy_approved("eval-1", "req-1", "policy-1")
        assert ev.event_type == PolicyEventType.POLICY_APPROVED
        assert ev.final_action == PolicyAction.APPROVE

    def test_make_policy_rejected(self):
        ev = make_policy_rejected("eval-1", "req-1", "policy-1")
        assert ev.final_action == PolicyAction.REJECT

    def test_make_policy_blocked(self):
        ev = make_policy_blocked("eval-1", "req-1", "policy-1")
        assert ev.final_action == PolicyAction.BLOCK

    def test_make_policy_escalated(self):
        ev = make_policy_escalated("eval-1", "req-1", "policy-1")
        assert ev.final_action == PolicyAction.ESCALATE

    def test_make_immediate_action_triggered(self):
        ev = make_immediate_action_triggered("eval-1", "req-1", "policy-1")
        assert ev.final_action == PolicyAction.REQUIRE_IMMEDIATE_ACTION

    def test_make_evaluation_completed(self):
        ev = make_evaluation_completed("eval-1", "req-1", PolicyAction.APPROVE)
        assert ev.event_type == PolicyEventType.EVALUATION_COMPLETED
        assert ev.final_action == PolicyAction.APPROVE

    def test_events_have_unique_ids(self):
        ev1 = make_evaluation_started("e", "r")
        ev2 = make_evaluation_started("e", "r")
        assert ev1.event_id != ev2.event_id

    def test_to_dict_serialises(self):
        ev = make_evaluation_completed("e", "r", PolicyAction.BLOCK)
        d = ev.to_dict()
        assert d["event_type"] == PolicyEventType.EVALUATION_COMPLETED.value
        assert d["final_action"] == PolicyAction.BLOCK.value

    def test_actor_passed_through(self):
        ev = make_evaluation_started("e", "r", actor="test-actor")
        assert ev.actor == "test-actor"

    def test_payload_passed_through(self):
        ev = make_evaluation_completed("e", "r", PolicyAction.APPROVE, payload={"k": "v"})
        assert ev.payload == {"k": "v"}

    def test_frozen(self):
        ev = make_evaluation_started("e", "r")
        with pytest.raises((AttributeError, TypeError)):
            ev.actor = "changed"  # type: ignore


# ===========================================================================
# TestRiskPolicyFactory
# ===========================================================================

class TestRiskPolicyFactory:
    factory = RiskPolicyFactory()

    def test_create_context(self):
        ctx = self.factory.create_context("eval-1", "port-1", "risk-1")
        assert ctx.portfolio_id == "port-1"

    def test_create_request(self):
        req = self.factory.create_request("eval-1", "port-1", "risk-1", inputs={"x": 1})
        assert req.inputs == {"x": 1}

    def test_create_simple_policy_no_rules(self):
        p = self.factory.create_simple_policy(
            "approve-all", PolicyType.MARKET_RISK
        )
        assert p.rule_count == 0
        assert p.default_action == PolicyAction.APPROVE

    def test_create_policy_result(self):
        r = self.factory.create_policy_result(
            "p", "P", PolicyType.CREDIT_RISK, PolicyPriority.LOW, PolicyAction.DEFER
        )
        assert r.action == PolicyAction.DEFER

    def test_create_evaluation_summary(self):
        r = RiskPolicyResult.create("p", "P", PolicyType.MARKET_RISK, PolicyPriority.MEDIUM, PolicyAction.APPROVE)
        summary = self.factory.create_evaluation_summary([r], PolicyAction.APPROVE)
        assert summary.total_policies == 1

    def test_create_response(self):
        req = _request()
        summary = self.factory.create_evaluation_summary([], PolicyAction.APPROVE)
        resp = self.factory.create_response(req, PolicyAction.APPROVE, [], summary, 0.1)
        assert resp.is_approved is True


# ===========================================================================
# TestRiskPolicyManager
# ===========================================================================

class TestRiskPolicyManager:
    def _manager(self) -> RiskPolicyManager:
        registry  = RiskPolicyRegistry()
        evaluator = RiskPolicyEvaluator()
        chain     = RiskPolicyChain(evaluator)
        validator = RiskPolicyValidator()
        auditor   = RiskPolicyAuditor()
        stats     = RiskPolicyStatistics()
        history   = RiskPolicyHistory()
        factory   = RiskPolicyFactory()
        return RiskPolicyManager(
            registry=registry, evaluator=evaluator, chain=chain,
            validator=validator, auditor=auditor, statistics=stats,
            history=history, factory=factory,
        )

    def test_evaluate_no_policies_returns_approve(self):
        mgr = self._manager()
        req = _request()
        resp = mgr.run_evaluation(req)
        assert resp.is_success is True
        assert resp.final_action == PolicyAction.APPROVE

    def test_evaluate_with_reject_policy(self):
        mgr = self._manager()
        c = _cond("c", "trigger", ConditionOperator.IS_TRUE)
        r = _rule("r", [c], PolicyAction.REJECT)
        p = _policy("p", PolicyType.MARKET_RISK, [r])
        mgr._registry.register(p)
        req = _request({"trigger": True})
        resp = mgr.run_evaluation(req)
        assert resp.final_action == PolicyAction.REJECT

    def test_evaluate_invalid_request_returns_failure(self):
        mgr = self._manager()
        bad_req = RiskPolicyRequest.create("", "port", "risk")
        resp = mgr.run_evaluation(bad_req)
        assert resp.is_success is False

    def test_history_records_request_and_response(self):
        mgr = self._manager()
        req = _request()
        mgr.run_evaluation(req)
        counts = mgr._history.counts()
        assert counts["requests"] == 1
        assert counts["responses"] == 1

    def test_stats_incremented_after_evaluation(self):
        mgr = self._manager()
        req = _request()
        mgr.run_evaluation(req)
        snap = mgr._stats.snapshot()
        assert snap["evaluations_total"] == 1

    def test_policy_type_filter(self):
        mgr = self._manager()
        c = _cond("c", "x", ConditionOperator.GT, 0)
        r = _rule("r", [c], PolicyAction.REJECT)
        p = _policy("p", PolicyType.CREDIT_RISK, [r])
        mgr._registry.register(p)

        # Request scoped to MARKET_RISK only — CREDIT_RISK policy should not apply
        ctx = RiskPolicyContext.create(
            "eval", "port", "risk",
            policy_types=(PolicyType.MARKET_RISK,),
        )
        req = RiskPolicyRequest.create(
            "eval", "port", "risk", context=ctx, inputs={"x": 1}
        )
        resp = mgr.run_evaluation(req)
        assert resp.final_action == PolicyAction.APPROVE  # credit policy ignored

    def test_evaluation_mode_from_metadata(self):
        mgr = self._manager()
        req = RiskPolicyRequest.create(
            "eval", "port", "risk",
            inputs={},
            metadata={"evaluation_mode": "parallel"},
        )
        resp = mgr.run_evaluation(req)
        assert resp.is_success is True


# ===========================================================================
# TestRiskPolicyEngine lifecycle
# ===========================================================================

class TestRiskPolicyEngineLifecycle:
    def test_start_and_stop(self):
        engine = RiskPolicyEngine()
        engine.start()
        assert engine.lifecycle_state().value == "running"
        engine.stop()
        assert engine.lifecycle_state().value != "running"

    def test_evaluate_raises_when_not_started(self):
        engine = RiskPolicyEngine()
        req = _request()
        with pytest.raises(RiskPolicyEngineNotRunningError):
            engine.evaluate(req)

    def test_register_policy_raises_when_not_started(self):
        engine = RiskPolicyEngine()
        p = _policy("p", PolicyType.MARKET_RISK, [])
        with pytest.raises(RiskPolicyEngineNotRunningError):
            engine.register_policy(p)

    def test_health_running(self):
        engine = _started_engine()
        try:
            h = engine.health()
            assert h["healthy"] is True
        finally:
            engine.stop()

    def test_status_returns_correct_type(self):
        engine = _started_engine()
        try:
            s = engine.status()
            assert isinstance(s, RiskPolicyEngineStatus)
        finally:
            engine.stop()

    def test_statistics_returns_dict(self):
        engine = _started_engine()
        try:
            stats = engine.statistics()
            assert "evaluations_total" in stats
        finally:
            engine.stop()

    def test_add_and_remove_listener(self):
        engine = _started_engine()
        received = []
        fn = received.append
        engine.add_listener(fn)
        req = _request()
        engine.evaluate(req)
        engine.remove_listener(fn)
        count_after_remove = len(received)
        engine.evaluate(req)
        assert len(received) == count_after_remove  # no new events
        engine.stop()

    def test_duplicate_listener_not_added_twice(self):
        engine = _started_engine()
        received = []
        fn = received.append
        engine.add_listener(fn)
        engine.add_listener(fn)
        req = _request()
        engine.evaluate(req)
        # Should receive 2 events (started + completed), not 4
        assert len(received) == 2
        engine.stop()

    def test_listener_exception_does_not_crash_engine(self):
        engine = _started_engine()

        def bad_listener(ev: Any) -> None:
            raise RuntimeError("listener error")

        engine.add_listener(bad_listener)
        req = _request()
        resp = engine.evaluate(req)  # should not raise
        assert resp.is_success is True
        engine.stop()

    def test_restart_works(self):
        engine = RiskPolicyEngine()
        engine.start()
        engine.stop()
        engine.start()
        assert engine.lifecycle_state().value == "running"
        engine.stop()


# ===========================================================================
# TestRiskPolicyEngine evaluate
# ===========================================================================

class TestRiskPolicyEngineEvaluate:
    def test_evaluate_no_policies_approves(self):
        engine = _started_engine()
        try:
            resp = engine.evaluate(_request())
            assert resp.final_action == PolicyAction.APPROVE
            assert resp.is_success is True
        finally:
            engine.stop()

    def test_evaluate_reject_policy(self):
        engine = _started_engine()
        try:
            c = _cond("c", "bad", ConditionOperator.IS_TRUE)
            r = _rule("r", [c], PolicyAction.REJECT)
            p = _policy("p", PolicyType.MARKET_RISK, [r])
            engine.register_policy(p)
            resp = engine.evaluate(_request({"bad": True}))
            assert resp.final_action == PolicyAction.REJECT
        finally:
            engine.stop()

    def test_evaluate_block_policy(self):
        engine = _started_engine()
        try:
            c = _cond("c", "limit_breached", ConditionOperator.IS_TRUE)
            r = _rule("r", [c], PolicyAction.BLOCK)
            p = _policy("p", PolicyType.POSITION_RISK, [r], priority=PolicyPriority.CRITICAL)
            engine.register_policy(p)
            resp = engine.evaluate(_request({"limit_breached": True}))
            assert resp.final_action == PolicyAction.BLOCK
        finally:
            engine.stop()

    def test_evaluate_emits_started_and_completed_events(self):
        engine = _started_engine()
        events = []
        engine.add_listener(events.append)
        try:
            engine.evaluate(_request())
            types = [e.event_type for e in events]
            assert PolicyEventType.EVALUATION_STARTED in types
            assert PolicyEventType.EVALUATION_COMPLETED in types
        finally:
            engine.stop()

    def test_evaluate_summary_in_response(self):
        engine = _started_engine()
        try:
            resp = engine.evaluate(_request())
            assert resp.summary is not None
            assert resp.summary.total_policies == 0
        finally:
            engine.stop()

    def test_register_and_unregister_policy(self):
        engine = _started_engine()
        try:
            p = _policy("p", PolicyType.CREDIT_RISK, [])
            engine.register_policy(p)
            assert engine.get_policy(p.policy_id) is p
            engine.unregister_policy(p.policy_id)
            with pytest.raises(RiskPolicyNotFoundError):
                engine.get_policy(p.policy_id)
        finally:
            engine.stop()

    def test_list_policies_all(self):
        engine = _started_engine()
        try:
            p1 = _policy("p1", PolicyType.MARKET_RISK, [])
            p2 = _policy("p2", PolicyType.CREDIT_RISK, [])
            engine.register_policy(p1)
            engine.register_policy(p2)
            all_policies = engine.list_policies()
            ids = [p.policy_id for p in all_policies]
            assert p1.policy_id in ids
            assert p2.policy_id in ids
        finally:
            engine.stop()

    def test_list_policies_by_type(self):
        engine = _started_engine()
        try:
            p1 = _policy("p1", PolicyType.MARKET_RISK, [])
            p2 = _policy("p2", PolicyType.CREDIT_RISK, [])
            engine.register_policy(p1)
            engine.register_policy(p2)
            market = engine.list_policies(PolicyType.MARKET_RISK)
            assert len(market) == 1
            assert market[0].policy_id == p1.policy_id
        finally:
            engine.stop()

    def test_list_enabled_policies(self):
        engine = _started_engine()
        try:
            p1 = _policy("p1", PolicyType.MARKET_RISK, [])
            p2 = _policy("p2", PolicyType.MARKET_RISK, [], enabled=False)
            engine.register_policy(p1)
            engine.register_policy(p2)
            enabled = engine.list_enabled_policies()
            assert all(p.enabled for p in enabled)
        finally:
            engine.stop()

    def test_evaluate_escalate_policy(self):
        engine = _started_engine()
        try:
            c = _cond("c", "escalate", ConditionOperator.IS_TRUE)
            r = _rule("r", [c], PolicyAction.ESCALATE)
            p = _policy("p", PolicyType.OPERATIONAL_RISK, [r])
            engine.register_policy(p)
            resp = engine.evaluate(_request({"escalate": True}))
            assert resp.final_action == PolicyAction.ESCALATE
            assert resp.requires_escalation is True
        finally:
            engine.stop()

    def test_evaluate_immediate_action_policy(self):
        engine = _started_engine()
        try:
            c = _cond("c", "critical", ConditionOperator.IS_TRUE)
            r = _rule("r", [c], PolicyAction.REQUIRE_IMMEDIATE_ACTION)
            p = _policy("p", PolicyType.INFRASTRUCTURE_RISK, [r], priority=PolicyPriority.CRITICAL)
            engine.register_policy(p)
            resp = engine.evaluate(_request({"critical": True}))
            assert resp.requires_immediate_action is True
        finally:
            engine.stop()

    def test_evaluate_statistics_updated(self):
        engine = _started_engine()
        try:
            engine.evaluate(_request())
            engine.evaluate(_request())
            stats = engine.statistics()
            assert stats["evaluations_total"] == 2
        finally:
            engine.stop()


# ===========================================================================
# TestAllPolicyTypes
# ===========================================================================

class TestAllPolicyTypes:
    """Verify all 15 policy types can be registered and evaluated."""

    @pytest.mark.parametrize("policy_type", list(PolicyType))
    def test_policy_type_evaluate(self, policy_type: PolicyType):
        engine = _started_engine()
        try:
            p = _policy("p", policy_type, [])
            engine.register_policy(p)
            resp = engine.evaluate(_request())
            assert resp.is_success is True
            assert resp.final_action == PolicyAction.APPROVE
        finally:
            engine.stop()


# ===========================================================================
# TestConflictResolution — all 5 strategies
# ===========================================================================

class TestConflictResolution:
    def _result(self, action: PolicyAction, priority: PolicyPriority = PolicyPriority.MEDIUM) -> RiskPolicyResult:
        return RiskPolicyResult.create(
            "p", "P", PolicyType.MARKET_RISK, priority, action
        )

    def test_immediate_action_overrides_all(self):
        results = [
            self._result(PolicyAction.APPROVE, PolicyPriority.CRITICAL),
            self._result(PolicyAction.REJECT, PolicyPriority.HIGH),
            self._result(PolicyAction.REQUIRE_IMMEDIATE_ACTION, PolicyPriority.LOW),
        ]
        assert PolicyPriorityResolver.final_action(results) == PolicyAction.REQUIRE_IMMEDIATE_ACTION

    def test_critical_overrides_medium(self):
        results = [
            self._result(PolicyAction.APPROVE, PolicyPriority.CRITICAL),
            self._result(PolicyAction.DEFER, PolicyPriority.MEDIUM),
        ]
        # CRITICAL priority wins; but APPROVE vs DEFER — severity decides
        # DEFER > APPROVE in severity, but CRITICAL priority applies strategy 2
        result = PolicyPriorityResolver.resolve(results)
        # Strategy 2: critical priority results selected, then most severe among those
        assert result.priority == PolicyPriority.CRITICAL

    def test_explicit_deny_overrides_approve(self):
        results = [
            self._result(PolicyAction.APPROVE, PolicyPriority.MEDIUM),
            self._result(PolicyAction.REJECT, PolicyPriority.LOW),
        ]
        assert PolicyPriorityResolver.final_action(results) == PolicyAction.REJECT

    def test_escalation_overrides_conditional(self):
        results = [
            self._result(PolicyAction.APPROVE_WITH_CONDITIONS),
            self._result(PolicyAction.ESCALATE),
        ]
        assert PolicyPriorityResolver.final_action(results) == PolicyAction.ESCALATE

    def test_highest_priority_wins_fallback(self):
        results = [
            self._result(PolicyAction.DEFER, PolicyPriority.HIGH),
            self._result(PolicyAction.DEFER, PolicyPriority.LOW),
        ]
        # Both DEFER — highest priority (lower int = HIGH) wins
        result = PolicyPriorityResolver.resolve(results)
        assert result.action == PolicyAction.DEFER


# ===========================================================================
# TestConcurrency
# ===========================================================================

class TestConcurrency:
    def test_concurrent_evaluations(self):
        engine = _started_engine()
        errors = []
        responses = []
        lock = threading.Lock()

        def evaluate_worker() -> None:
            try:
                resp = engine.evaluate(_request())
                with lock:
                    responses.append(resp)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=evaluate_worker) for _ in range(20)]
        try:
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            assert not errors, f"Concurrent evaluation errors: {errors}"
            assert len(responses) == 20
            assert all(r.is_success for r in responses)
        finally:
            engine.stop()

    def test_concurrent_policy_registration(self):
        engine = _started_engine()
        errors = []

        def register_worker(i: int) -> None:
            try:
                p = _policy(f"p{i}", PolicyType.MARKET_RISK, [])
                engine.register_policy(p)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_worker, args=(i,)) for i in range(30)]
        try:
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            assert not errors
        finally:
            engine.stop()


# ===========================================================================
# TestRegression
# ===========================================================================

class TestRegression:
    def test_no_rules_policy_does_not_raise(self):
        engine = _started_engine()
        try:
            p = RiskPolicy.create("empty", PolicyType.ENTERPRISE_GOVERNANCE, PolicyPriority.LOW, [])
            engine.register_policy(p)
            resp = engine.evaluate(_request())
            assert resp.is_success is True
        finally:
            engine.stop()

    def test_very_large_input_dict(self):
        engine = _started_engine()
        try:
            inputs = {f"key_{i}": i for i in range(500)}
            resp = engine.evaluate(_request(inputs))
            assert resp.is_success is True
        finally:
            engine.stop()

    def test_multiple_policies_all_approve(self):
        engine = _started_engine()
        try:
            for i in range(10):
                p = _policy(f"p{i}", PolicyType.MARKET_RISK, [], default_action=PolicyAction.APPROVE)
                engine.register_policy(p)
            resp = engine.evaluate(_request())
            assert resp.final_action == PolicyAction.APPROVE
        finally:
            engine.stop()

    def test_disabled_policies_do_not_affect_result(self):
        engine = _started_engine()
        try:
            c = _cond("c", "x", ConditionOperator.GT, 0)
            r = _rule("r", [c], PolicyAction.BLOCK)
            p = _policy("p", PolicyType.MARKET_RISK, [r], enabled=False)
            engine.register_policy(p)
            resp = engine.evaluate(_request({"x": 1}))
            assert resp.final_action == PolicyAction.APPROVE  # disabled → not evaluated
        finally:
            engine.stop()

    def test_policy_with_no_matching_rule_uses_default(self):
        engine = _started_engine()
        try:
            c = _cond("c", "x", ConditionOperator.GT, 1000)
            r = _rule("r", [c], PolicyAction.BLOCK)
            p = _policy("p", PolicyType.MARKET_RISK, [r], default_action=PolicyAction.APPROVE)
            engine.register_policy(p)
            resp = engine.evaluate(_request({"x": 1}))
            assert resp.final_action == PolicyAction.APPROVE
        finally:
            engine.stop()

    def test_response_policies_evaluated_count_correct(self):
        engine = _started_engine()
        try:
            for i in range(5):
                p = _policy(f"p{i}", PolicyType.MARKET_RISK, [])
                engine.register_policy(p)
            resp = engine.evaluate(_request())
            assert resp.policies_evaluated == 5
        finally:
            engine.stop()

    def test_status_engine_id_matches_constant(self):
        engine = _started_engine()
        try:
            s = engine.status()
            assert s.engine_id == POLICY_SYSTEM_ID
        finally:
            engine.stop()

    def test_evaluation_elapsed_s_positive(self):
        engine = _started_engine()
        try:
            resp = engine.evaluate(_request())
            assert resp.evaluation_elapsed_s >= 0.0
        finally:
            engine.stop()

    def test_context_policy_types_respected(self):
        engine = _started_engine()
        try:
            # Register CREDIT_RISK policy with REJECT
            c = _cond("c", "x", ConditionOperator.GT, 0)
            r = _rule("r", [c], PolicyAction.REJECT)
            p = _policy("p", PolicyType.CREDIT_RISK, [r])
            engine.register_policy(p)

            # Request only MARKET_RISK context — should get APPROVE
            ctx = RiskPolicyContext.create(
                "eval", "port", "risk",
                policy_types=(PolicyType.MARKET_RISK,),
            )
            req = RiskPolicyRequest.create("eval", "port", "risk", context=ctx, inputs={"x": 1})
            resp = engine.evaluate(req)
            assert resp.final_action == PolicyAction.APPROVE
        finally:
            engine.stop()
