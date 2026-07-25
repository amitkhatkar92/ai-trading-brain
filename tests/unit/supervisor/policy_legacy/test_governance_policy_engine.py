"""
test_governance_policy_engine.py — tests.unit.supervisor.policy
-----------------------------------------------------------------
Comprehensive tests for the C13 M3 AI Governance Policy Framework.

Coverage targets:
  - constants.py           — enumerations, sets, dicts
  - exceptions.py          — hierarchy, attributes
  - governance_policy_condition.py
  - governance_policy_rule.py
  - governance_policy.py
  - governance_policy_context.py
  - governance_policy_request.py
  - governance_policy_result.py
  - governance_policy_response.py
  - governance_policy_evaluator.py
  - governance_policy_chain.py
  - governance_policy_registry.py
  - governance_policy_history.py
  - governance_policy_statistics.py
  - governance_policy_events.py
  - governance_policy_validation.py
  - governance_policy_factory.py
  - governance_policy_manager.py
  - governance_policy_engine.py  (lifecycle, evaluate, management, concurrency)
  - __init__.py             — public surface

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

import pytest

from iios.supervisor.policy_legacy import (
    # enumerations
    ConditionOperator,
    ConflictResolutionStrategy,
    EvaluationMode,
    GovernancePolicyEventType,
    GovernancePolicyType,
    GovernanceValidationCode,
    LogicalOperator,
    PolicyAction,
    PolicyPriority,
    # constants
    ACTION_SEVERITY,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    DEFAULT_POLICY_ACTION,
    POLICY_SYSTEM_ID,
    VERSION,
    # exceptions
    GovernancePolicyCapacityError,
    GovernancePolicyConditionError,
    GovernancePolicyEngineNotRunningError,
    GovernancePolicyError,
    GovernancePolicyEvaluationError,
    GovernancePolicyHistoryError,
    GovernancePolicyNotFoundError,
    GovernancePolicyRegistryError,
    GovernancePolicyRuleError,
    GovernancePolicyValidationError,
    # value objects
    GovernancePolicy,
    GovernancePolicyCondition,
    GovernancePolicyContext,
    GovernancePolicyRequest,
    GovernancePolicyResponse,
    GovernancePolicyResult,
    GovernancePolicyRule,
    GovernanceEvaluationSummary,
    # events
    GovernancePolicyEvent,
    make_conflict_resolved_event,
    make_engine_started_event,
    make_engine_stopped_event,
    make_evaluation_completed_event,
    make_evaluation_failed_event,
    make_evaluation_started_event,
    make_policy_registered_event,
    make_policy_unregistered_event,
    # validation
    GovernancePolicyValidator,
    GovernanceValidationCheckResult,
    GovernanceValidationResult,
    # subsystems
    GovernancePolicyChain,
    GovernancePolicyEvaluator,
    GovernancePolicyFactory,
    GovernancePolicyHistory,
    GovernancePolicyManager,
    GovernancePolicyRegistry,
    GovernancePolicyStatistics,
    # engine
    GovernancePolicyEngine,
)


# ===========================================================================
# Shared helpers / fixtures
# ===========================================================================

def _make_condition(
    field_path: str = "health.score",
    operator: ConditionOperator = ConditionOperator.LT,
    threshold: Any = 0.5,
    name: str = "health check",
) -> GovernancePolicyCondition:
    return GovernancePolicyCondition.create(
        name       = name,
        field_path = field_path,
        operator   = operator,
        threshold  = threshold,
    )


def _make_rule(
    conditions: List[GovernancePolicyCondition] | None = None,
    action: PolicyAction = PolicyAction.BLOCK,
    logical_operator: LogicalOperator = LogicalOperator.ALL,
    name: str = "test rule",
) -> GovernancePolicyRule:
    if conditions is None:
        conditions = [_make_condition()]
    return GovernancePolicyRule.create(
        name             = name,
        conditions       = conditions,
        logical_operator = logical_operator,
        action           = action,
    )


def _make_policy(
    rules: List[GovernancePolicyRule] | None = None,
    policy_type: GovernancePolicyType = GovernancePolicyType.HEALTH_GOVERNANCE,
    priority: PolicyPriority = PolicyPriority.HIGH,
    name: str = "test policy",
    enabled: bool = True,
    evaluation_mode: EvaluationMode = EvaluationMode.SEQUENTIAL,
) -> GovernancePolicy:
    if rules is None:
        rules = [_make_rule()]
    return GovernancePolicy.create(
        name            = name,
        policy_type     = policy_type,
        priority        = priority,
        rules           = rules,
        enabled         = enabled,
        evaluation_mode = evaluation_mode,
    )


def _make_request(
    supervision_id: str = "sup-001",
    subsystem_id: str = "subsys-001",
    inputs: Dict[str, Any] | None = None,
    policy_types: List[GovernancePolicyType] | None = None,
) -> GovernancePolicyRequest:
    return GovernancePolicyRequest.create(
        supervision_id = supervision_id,
        subsystem_id   = subsystem_id,
        workflow_type  = "test-workflow",
        inputs         = inputs or {},
        policy_types   = policy_types or [],
    )


def _started_engine() -> GovernancePolicyEngine:
    engine = GovernancePolicyEngine()
    engine.start()
    return engine


# ===========================================================================
# 1. Constants
# ===========================================================================

class TestConstants:
    def test_policy_system_id_nonempty(self):
        assert POLICY_SYSTEM_ID

    def test_version_nonempty(self):
        assert VERSION

    def test_action_severity_covers_all_actions(self):
        for a in PolicyAction:
            assert a in ACTION_SEVERITY

    def test_block_highest_severity(self):
        assert ACTION_SEVERITY[PolicyAction.BLOCK] > ACTION_SEVERITY[PolicyAction.APPROVE]

    def test_default_policy_action_is_approve(self):
        assert DEFAULT_POLICY_ACTION == PolicyAction.APPROVE

    def test_default_max_policies_positive(self):
        assert DEFAULT_MAX_POLICIES > 0

    def test_default_max_history_positive(self):
        assert DEFAULT_MAX_HISTORY > 0

    def test_policy_priority_int_enum(self):
        assert PolicyPriority.CRITICAL < PolicyPriority.INFORMATIONAL

    def test_governance_policy_type_count(self):
        assert len(GovernancePolicyType) == 12

    def test_policy_action_count(self):
        assert len(PolicyAction) == 7

    def test_condition_operator_count(self):
        assert len(ConditionOperator) == 12

    def test_evaluation_mode_count(self):
        assert len(EvaluationMode) == 6

    def test_conflict_resolution_strategy_count(self):
        assert len(ConflictResolutionStrategy) == 5

    def test_event_type_count(self):
        assert len(GovernancePolicyEventType) == 8

    def test_validation_code_count(self):
        assert len(GovernanceValidationCode) == 5


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(GovernancePolicyError, IIOSError)

    def test_engine_not_running_subclass(self):
        assert issubclass(GovernancePolicyEngineNotRunningError, GovernancePolicyError)

    def test_not_found_has_policy_id(self):
        exc = GovernancePolicyNotFoundError("pid-1")
        assert exc.policy_id == "pid-1"

    def test_capacity_has_limit(self):
        exc = GovernancePolicyCapacityError(100)
        assert exc.limit == 100

    def test_evaluation_has_request_id(self):
        exc = GovernancePolicyEvaluationError("something", request_id="req-1")
        assert exc.request_id == "req-1"

    def test_registry_error_subclass(self):
        assert issubclass(GovernancePolicyRegistryError, GovernancePolicyError)

    def test_validation_error_subclass(self):
        assert issubclass(GovernancePolicyValidationError, GovernancePolicyError)

    def test_condition_error_subclass(self):
        assert issubclass(GovernancePolicyConditionError, GovernancePolicyError)

    def test_rule_error_subclass(self):
        assert issubclass(GovernancePolicyRuleError, GovernancePolicyError)

    def test_history_error_subclass(self):
        assert issubclass(GovernancePolicyHistoryError, GovernancePolicyError)


# ===========================================================================
# 3. GovernancePolicyCondition
# ===========================================================================

class TestGovernancePolicyCondition:
    def test_create_returns_frozen_dataclass(self):
        cond = _make_condition()
        assert cond.field_path == "health.score"
        assert cond.operator == ConditionOperator.LT
        assert cond.threshold == 0.5

    def test_create_generates_id(self):
        cond = _make_condition()
        assert cond.condition_id

    def test_create_explicit_id(self):
        cond = GovernancePolicyCondition.create(
            name="x", field_path="a.b", operator=ConditionOperator.EQ,
            threshold=1, condition_id="my-cid",
        )
        assert cond.condition_id == "my-cid"

    def test_frozen_immutable(self):
        cond = _make_condition()
        with pytest.raises((TypeError, AttributeError)):
            cond.field_path = "other"  # type: ignore

    def test_to_dict_roundtrip(self):
        cond = _make_condition()
        d = cond.to_dict()
        assert d["field_path"] == "health.score"
        assert d["operator"] == ConditionOperator.LT.value


# ===========================================================================
# 4. GovernancePolicyRule
# ===========================================================================

class TestGovernancePolicyRule:
    def test_create(self):
        rule = _make_rule()
        assert rule.name == "test rule"
        assert len(rule.conditions) == 1

    def test_condition_count_property(self):
        rule = _make_rule(conditions=[_make_condition(), _make_condition()])
        assert rule.condition_count == 2

    def test_frozen(self):
        rule = _make_rule()
        with pytest.raises((TypeError, AttributeError)):
            rule.name = "x"  # type: ignore

    def test_to_dict_has_action(self):
        rule = _make_rule(action=PolicyAction.REJECT)
        d = rule.to_dict()
        assert d["action"] == PolicyAction.REJECT.value

    def test_conditions_stored_as_tuple(self):
        rule = _make_rule()
        assert isinstance(rule.conditions, tuple)


# ===========================================================================
# 5. GovernancePolicy
# ===========================================================================

class TestGovernancePolicy:
    def test_create(self):
        policy = _make_policy()
        assert policy.name == "test policy"
        assert policy.enabled

    def test_rule_count(self):
        policy = _make_policy(rules=[_make_rule(), _make_rule(name="r2")])
        assert policy.rule_count == 2

    def test_is_enabled(self):
        policy = _make_policy(enabled=True)
        assert policy.is_enabled

    def test_with_enabled_returns_new_instance(self):
        policy = _make_policy(enabled=True)
        disabled = policy.with_enabled(False)
        assert not disabled.is_enabled
        assert policy.is_enabled  # original unchanged

    def test_to_dict(self):
        policy = _make_policy()
        d = policy.to_dict()
        assert d["name"] == "test policy"

    def test_frozen(self):
        policy = _make_policy()
        with pytest.raises((TypeError, AttributeError)):
            policy.name = "x"  # type: ignore


# ===========================================================================
# 6. GovernancePolicyContext
# ===========================================================================

class TestGovernancePolicyContext:
    def test_create(self):
        ctx = GovernancePolicyContext.create(supervision_id="sup-1")
        assert ctx.supervision_id == "sup-1"

    def test_defaults(self):
        ctx = GovernancePolicyContext.create(supervision_id="s")
        assert isinstance(ctx.platform_health, dict)
        assert isinstance(ctx.inputs, dict)

    def test_to_dict(self):
        ctx = GovernancePolicyContext.create(supervision_id="s")
        assert ctx.to_dict()["supervision_id"] == "s"


# ===========================================================================
# 7. GovernancePolicyRequest
# ===========================================================================

class TestGovernancePolicyRequest:
    def test_create(self):
        req = _make_request()
        assert req.supervision_id == "sup-001"

    def test_auto_context_creation(self):
        req = _make_request()
        assert req.context is not None
        assert req.context.supervision_id == "sup-001"

    def test_with_inputs_merges(self):
        req = _make_request(inputs={"a": 1})
        req2 = req.with_inputs({"b": 2})
        assert req2.inputs["a"] == 1
        assert req2.inputs["b"] == 2

    def test_to_dict(self):
        req = _make_request()
        d = req.to_dict()
        assert "request_id" in d

    def test_frozen(self):
        req = _make_request()
        with pytest.raises((TypeError, AttributeError)):
            req.supervision_id = "x"  # type: ignore


# ===========================================================================
# 8. GovernancePolicyResult
# ===========================================================================

class TestGovernancePolicyResult:
    def test_create(self):
        result = GovernancePolicyResult.create(
            policy_id   = "p-1",
            policy_name = "test",
            policy_type = GovernancePolicyType.HEALTH_GOVERNANCE,
            priority    = PolicyPriority.HIGH,
            action      = PolicyAction.APPROVE,
        )
        assert result.action == PolicyAction.APPROVE

    def test_is_permissive(self):
        result = GovernancePolicyResult.create(
            policy_id="p",policy_name="n",
            policy_type=GovernancePolicyType.HEALTH_GOVERNANCE,
            priority=PolicyPriority.HIGH,action=PolicyAction.APPROVE,
        )
        assert result.is_permissive

    def test_is_denying_block(self):
        result = GovernancePolicyResult.create(
            policy_id="p",policy_name="n",
            policy_type=GovernancePolicyType.HEALTH_GOVERNANCE,
            priority=PolicyPriority.HIGH,action=PolicyAction.BLOCK,
        )
        assert result.is_denying

    def test_is_denying_reject(self):
        result = GovernancePolicyResult.create(
            policy_id="p",policy_name="n",
            policy_type=GovernancePolicyType.HEALTH_GOVERNANCE,
            priority=PolicyPriority.HIGH,action=PolicyAction.REJECT,
        )
        assert result.is_denying

    def test_to_dict(self):
        result = GovernancePolicyResult.create(
            policy_id="p",policy_name="n",
            policy_type=GovernancePolicyType.HEALTH_GOVERNANCE,
            priority=PolicyPriority.HIGH,action=PolicyAction.APPROVE,
        )
        d = result.to_dict()
        assert d["action"] == PolicyAction.APPROVE.value


# ===========================================================================
# 9. GovernancePolicyResponse
# ===========================================================================

class TestGovernancePolicyResponse:
    def _summary(self, action=PolicyAction.APPROVE):
        return GovernanceEvaluationSummary.from_results((), action)

    def test_create_success(self):
        resp = GovernancePolicyResponse.create_success(
            request_id     = "r1",
            supervision_id = "s1",
            subsystem_id   = "ss1",
            final_action   = PolicyAction.APPROVE,
            results        = (),
            summary        = self._summary(),
        )
        assert resp.is_success
        assert resp.is_approved

    def test_create_failure(self):
        resp = GovernancePolicyResponse.create_failure(
            request_id="r1", supervision_id="s1", subsystem_id="ss1",
            error_message="oops",
        )
        assert not resp.is_success
        assert resp.is_denied

    def test_to_dict_keys(self):
        resp = GovernancePolicyResponse.create_success(
            request_id="r",supervision_id="s",subsystem_id="ss",
            final_action=PolicyAction.APPROVE,results=(),summary=self._summary(),
        )
        d = resp.to_dict()
        assert "final_action" in d and "is_approved" in d

    def test_summary_from_results_counts(self):
        r1 = GovernancePolicyResult.create(
            policy_id="p1",policy_name="n",
            policy_type=GovernancePolicyType.HEALTH_GOVERNANCE,
            priority=PolicyPriority.HIGH,action=PolicyAction.APPROVE,
        )
        r2 = GovernancePolicyResult.create(
            policy_id="p2",policy_name="n",
            policy_type=GovernancePolicyType.HEALTH_GOVERNANCE,
            priority=PolicyPriority.HIGH,action=PolicyAction.BLOCK,
        )
        summary = GovernanceEvaluationSummary.from_results(
            (r1, r2), PolicyAction.BLOCK
        )
        assert summary.total_policies == 2
        assert summary.approved == 1
        assert summary.blocked == 1


# ===========================================================================
# 10. GovernancePolicyEvaluator
# ===========================================================================

class TestGovernancePolicyEvaluator:
    def test_evaluate_condition_lt_true(self):
        ev = GovernancePolicyEvaluator()
        cond = _make_condition(threshold=0.5, operator=ConditionOperator.LT)
        assert ev.evaluate_condition(cond, {"health.score": 0.3})

    def test_evaluate_condition_lt_false(self):
        ev = GovernancePolicyEvaluator()
        cond = _make_condition(threshold=0.5, operator=ConditionOperator.LT)
        assert not ev.evaluate_condition(cond, {"health.score": 0.8})

    def test_evaluate_condition_gt(self):
        ev = GovernancePolicyEvaluator()
        cond = _make_condition(threshold=0.5, operator=ConditionOperator.GT)
        assert ev.evaluate_condition(cond, {"health.score": 0.8})
        assert not ev.evaluate_condition(cond, {"health.score": 0.3})

    def test_evaluate_condition_eq(self):
        ev = GovernancePolicyEvaluator()
        cond = _make_condition(threshold="active", operator=ConditionOperator.EQ,
                               field_path="status")
        assert ev.evaluate_condition(cond, {"status": "active"})
        assert not ev.evaluate_condition(cond, {"status": "idle"})

    def test_evaluate_condition_in(self):
        ev = GovernancePolicyEvaluator()
        cond = _make_condition(threshold=["A", "B"], operator=ConditionOperator.IN,
                               field_path="tier")
        assert ev.evaluate_condition(cond, {"tier": "A"})
        assert not ev.evaluate_condition(cond, {"tier": "C"})

    def test_evaluate_condition_exists(self):
        ev = GovernancePolicyEvaluator()
        cond = _make_condition(threshold=None, operator=ConditionOperator.EXISTS,
                               field_path="x")
        assert ev.evaluate_condition(cond, {"x": 1})
        assert not ev.evaluate_condition(cond, {})

    def test_evaluate_condition_not_exists(self):
        ev = GovernancePolicyEvaluator()
        cond = _make_condition(threshold=None, operator=ConditionOperator.NOT_EXISTS,
                               field_path="x")
        assert ev.evaluate_condition(cond, {})

    def test_evaluate_condition_is_true(self):
        ev = GovernancePolicyEvaluator()
        cond = _make_condition(threshold=None, operator=ConditionOperator.IS_TRUE,
                               field_path="flag")
        assert ev.evaluate_condition(cond, {"flag": True})
        assert not ev.evaluate_condition(cond, {"flag": False})

    def test_evaluate_condition_is_false(self):
        ev = GovernancePolicyEvaluator()
        cond = _make_condition(threshold=None, operator=ConditionOperator.IS_FALSE,
                               field_path="flag")
        assert ev.evaluate_condition(cond, {"flag": False})

    def test_evaluate_condition_nested_path(self):
        ev = GovernancePolicyEvaluator()
        cond = _make_condition(field_path="a.b", threshold=5, operator=ConditionOperator.GT)
        assert ev.evaluate_condition(cond, {"a": {"b": 10}})
        assert not ev.evaluate_condition(cond, {"a": {"b": 3}})

    def test_evaluate_rule_all_match(self):
        ev = GovernancePolicyEvaluator()
        c1 = _make_condition(field_path="a", threshold=5, operator=ConditionOperator.GT)
        c2 = _make_condition(field_path="b", threshold=10, operator=ConditionOperator.LT)
        rule = _make_rule(conditions=[c1, c2], logical_operator=LogicalOperator.ALL)
        matched, met, failed = ev.evaluate_rule(rule, {"a": 10, "b": 5})
        assert matched
        assert len(met) == 2
        assert len(failed) == 0

    def test_evaluate_rule_all_partial_fail(self):
        ev = GovernancePolicyEvaluator()
        c1 = _make_condition(field_path="a", threshold=5, operator=ConditionOperator.GT)
        c2 = _make_condition(field_path="b", threshold=10, operator=ConditionOperator.LT)
        rule = _make_rule(conditions=[c1, c2], logical_operator=LogicalOperator.ALL)
        matched, met, failed = ev.evaluate_rule(rule, {"a": 3, "b": 5})
        assert not matched

    def test_evaluate_rule_any_partial(self):
        ev = GovernancePolicyEvaluator()
        c1 = _make_condition(field_path="a", threshold=5, operator=ConditionOperator.GT)
        c2 = _make_condition(field_path="b", threshold=10, operator=ConditionOperator.LT)
        rule = _make_rule(conditions=[c1, c2], logical_operator=LogicalOperator.ANY)
        matched, _, _ = ev.evaluate_rule(rule, {"a": 3, "b": 5})
        assert matched  # b<10 passes

    def test_evaluate_policy_default_when_no_match(self):
        ev = GovernancePolicyEvaluator()
        policy = _make_policy()  # rule requires health.score < 0.5
        result = ev.evaluate_policy(policy, {"health.score": 0.9})
        # no rule matched → default action
        assert result.action == policy.default_action

    def test_evaluate_policy_rule_match_sequential(self):
        ev = GovernancePolicyEvaluator()
        policy = _make_policy()  # BLOCK when health.score < 0.5
        result = ev.evaluate_policy(policy, {"health.score": 0.2})
        assert result.action == PolicyAction.BLOCK

    def test_evaluate_policy_parallel_mode(self):
        ev = GovernancePolicyEvaluator()
        policy = _make_policy(evaluation_mode=EvaluationMode.PARALLEL)
        result = ev.evaluate_policy(policy, {"health.score": 0.2})
        assert result.action == PolicyAction.BLOCK

    def test_evaluate_condition_type_error_returns_false(self):
        ev = GovernancePolicyEvaluator()
        cond = _make_condition(threshold=5, operator=ConditionOperator.GT, field_path="x")
        # value is a string — comparison raises TypeError → should return False
        assert not ev.evaluate_condition(cond, {"x": "not_a_number"})


# ===========================================================================
# 11. GovernancePolicyChain
# ===========================================================================

class TestGovernancePolicyChain:
    def test_sequential_stops_on_deny(self):
        chain = GovernancePolicyChain()
        block_policy = _make_policy(
            rules=[_make_rule(action=PolicyAction.BLOCK)],
            priority=PolicyPriority.CRITICAL,
        )
        approve_policy = _make_policy(
            rules=[_make_rule(action=PolicyAction.APPROVE,
                              conditions=[_make_condition(
                                  threshold=0.5, operator=ConditionOperator.GT)])],
            priority=PolicyPriority.LOW,
            name="approve policy",
        )
        results = chain.evaluate(
            [block_policy, approve_policy],
            {"health.score": 0.2},
            EvaluationMode.SEQUENTIAL,
        )
        # CRITICAL policy blocks first → chain should stop
        assert any(r.action == PolicyAction.BLOCK for r in results)
        # APPROVE policy should NOT be evaluated
        assert not any(r.policy_name == "approve policy" for r in results)

    def test_parallel_evaluates_all(self):
        chain = GovernancePolicyChain()
        p1 = _make_policy(name="p1")
        p2 = _make_policy(name="p2")
        results = chain.evaluate([p1, p2], {"health.score": 0.2}, EvaluationMode.PARALLEL)
        assert len(results) == 2

    def test_empty_policies_empty_results(self):
        chain = GovernancePolicyChain()
        assert chain.evaluate([], {}) == []

    def test_disabled_policies_skipped(self):
        chain = GovernancePolicyChain()
        disabled = _make_policy(enabled=False, name="disabled")
        results = chain.evaluate([disabled], {"health.score": 0.2})
        assert results == []

    def test_composite_evaluates_all(self):
        chain = GovernancePolicyChain()
        p1 = _make_policy(name="p1")
        p2 = _make_policy(name="p2")
        results = chain.evaluate([p1, p2], {"health.score": 0.2}, EvaluationMode.COMPOSITE)
        assert len(results) == 2


# ===========================================================================
# 12. GovernancePolicyRegistry
# ===========================================================================

class TestGovernancePolicyRegistry:
    def test_register_and_get(self):
        reg = GovernancePolicyRegistry()
        policy = _make_policy()
        reg.register(policy)
        assert reg.get(policy.policy_id) is policy

    def test_register_updates_existing(self):
        reg = GovernancePolicyRegistry()
        policy = _make_policy()
        reg.register(policy)
        updated = policy.with_enabled(False)
        reg.register(updated)
        assert reg.count == 1
        assert not reg.get(policy.policy_id).is_enabled

    def test_unregister(self):
        reg = GovernancePolicyRegistry()
        policy = _make_policy()
        reg.register(policy)
        reg.unregister(policy.policy_id)
        assert reg.count == 0

    def test_unregister_missing_raises(self):
        reg = GovernancePolicyRegistry()
        with pytest.raises(GovernancePolicyNotFoundError):
            reg.unregister("missing-id")

    def test_get_missing_raises(self):
        reg = GovernancePolicyRegistry()
        with pytest.raises(GovernancePolicyNotFoundError):
            reg.get("missing-id")

    def test_get_optional_returns_none(self):
        reg = GovernancePolicyRegistry()
        assert reg.get_optional("x") is None

    def test_capacity_enforced(self):
        reg = GovernancePolicyRegistry(max_policies=2)
        reg.register(_make_policy(name="p1"))
        reg.register(_make_policy(name="p2"))
        with pytest.raises(GovernancePolicyCapacityError):
            reg.register(_make_policy(name="p3"))

    def test_none_policy_raises(self):
        reg = GovernancePolicyRegistry()
        with pytest.raises(GovernancePolicyRegistryError):
            reg.register(None)  # type: ignore

    def test_enabled_policies_filtered(self):
        reg = GovernancePolicyRegistry()
        reg.register(_make_policy(name="enabled", enabled=True))
        reg.register(_make_policy(name="disabled", enabled=False))
        assert len(reg.enabled_policies()) == 1

    def test_policies_by_type(self):
        reg = GovernancePolicyRegistry()
        reg.register(_make_policy(policy_type=GovernancePolicyType.HEALTH_GOVERNANCE))
        reg.register(_make_policy(policy_type=GovernancePolicyType.RISK_GOVERNANCE,
                                  name="risk-p"))
        health_policies = reg.policies_by_type(GovernancePolicyType.HEALTH_GOVERNANCE)
        assert len(health_policies) == 1

    def test_clear(self):
        reg = GovernancePolicyRegistry()
        reg.register(_make_policy())
        reg.clear()
        assert reg.count == 0

    def test_enable_disable(self):
        reg = GovernancePolicyRegistry()
        policy = _make_policy(enabled=True)
        reg.register(policy)
        reg.disable(policy.policy_id)
        assert not reg.get(policy.policy_id).is_enabled
        reg.enable(policy.policy_id)
        assert reg.get(policy.policy_id).is_enabled

    def test_thread_safe_concurrent_register(self):
        reg = GovernancePolicyRegistry(max_policies=1000)
        errors: List[Exception] = []

        def worker(i):
            try:
                reg.register(_make_policy(name=f"p-{i}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert reg.count == 100


# ===========================================================================
# 13. GovernancePolicyHistory
# ===========================================================================

class TestGovernancePolicyHistory:
    def test_record_and_recent_requests(self):
        h = GovernancePolicyHistory()
        req = _make_request()
        h.record_request(req)
        assert req in h.recent_requests()

    def test_recent_requests_limited(self):
        h = GovernancePolicyHistory()
        for i in range(10):
            h.record_request(f"req-{i}")
        assert len(h.recent_requests(3)) == 3

    def test_bounded_maxlen(self):
        h = GovernancePolicyHistory(max_requests=5)
        for i in range(10):
            h.record_request(f"item-{i}")
        assert h.request_count() == 5

    def test_record_response_and_event(self):
        h = GovernancePolicyHistory()
        h.record_response("resp")
        h.record_event("evt")
        assert h.response_count() == 1
        assert h.event_count() == 1

    def test_counts(self):
        h = GovernancePolicyHistory()
        h.record_request("r")
        h.record_response("rsp")
        counts = h.counts()
        assert counts["requests"] == 1
        assert counts["responses"] == 1

    def test_clear(self):
        h = GovernancePolicyHistory()
        h.record_request("r")
        h.clear()
        assert h.request_count() == 0


# ===========================================================================
# 14. GovernancePolicyStatistics
# ===========================================================================

class TestGovernancePolicyStatistics:
    def test_initial_snapshot_zeros(self):
        s = GovernancePolicyStatistics()
        snap = s.snapshot()
        assert snap["evaluations"] == 0
        assert snap["approved"] == 0

    def test_record_evaluation(self):
        s = GovernancePolicyStatistics()
        s.record_evaluation()
        assert s.snapshot()["evaluations"] == 1

    def test_record_success_updates_avg(self):
        s = GovernancePolicyStatistics()
        s.record_success(0.1)
        snap = s.snapshot()
        assert snap["successes"] == 1
        assert snap["average_evaluation_s"] == pytest.approx(0.1)

    def test_record_failure(self):
        s = GovernancePolicyStatistics()
        s.record_failure()
        assert s.snapshot()["failures"] == 1

    def test_record_approved(self):
        s = GovernancePolicyStatistics()
        s.record_approved()
        assert s.snapshot()["approved"] == 1

    def test_record_denied(self):
        s = GovernancePolicyStatistics()
        s.record_denied()
        assert s.snapshot()["denied"] == 1

    def test_record_escalated(self):
        s = GovernancePolicyStatistics()
        s.record_escalated()
        assert s.snapshot()["escalated"] == 1

    def test_record_deferred(self):
        s = GovernancePolicyStatistics()
        s.record_deferred()
        assert s.snapshot()["deferred"] == 1

    def test_reset(self):
        s = GovernancePolicyStatistics()
        s.record_evaluation()
        s.reset()
        assert s.snapshot()["evaluations"] == 0

    def test_thread_safe_concurrent_record(self):
        s = GovernancePolicyStatistics()
        threads = [threading.Thread(target=s.record_evaluation) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert s.snapshot()["evaluations"] == 100


# ===========================================================================
# 15. GovernancePolicyEvents
# ===========================================================================

class TestGovernancePolicyEvents:
    def test_make_policy_registered(self):
        e = make_policy_registered_event("s1", policy_id="p1", policy_name="n")
        assert e.event_type == GovernancePolicyEventType.POLICY_REGISTERED
        assert e.payload["policy_id"] == "p1"

    def test_make_policy_unregistered(self):
        e = make_policy_unregistered_event("s1", policy_id="p1")
        assert e.event_type == GovernancePolicyEventType.POLICY_UNREGISTERED

    def test_make_evaluation_started(self):
        e = make_evaluation_started_event("s1", request_id="r1")
        assert e.event_type == GovernancePolicyEventType.EVALUATION_STARTED

    def test_make_evaluation_completed(self):
        e = make_evaluation_completed_event("s1", request_id="r1", final_action="APPROVE")
        assert e.event_type == GovernancePolicyEventType.EVALUATION_COMPLETED

    def test_make_evaluation_failed(self):
        e = make_evaluation_failed_event("s1", request_id="r1", reason="err")
        assert e.event_type == GovernancePolicyEventType.EVALUATION_FAILED

    def test_make_engine_started(self):
        e = make_engine_started_event()
        assert e.event_type == GovernancePolicyEventType.POLICY_ENGINE_STARTED

    def test_make_engine_stopped(self):
        e = make_engine_stopped_event()
        assert e.event_type == GovernancePolicyEventType.POLICY_ENGINE_STOPPED

    def test_make_conflict_resolved(self):
        e = make_conflict_resolved_event("s1", dominant_policy_id="p1")
        assert e.event_type == GovernancePolicyEventType.CONFLICT_RESOLVED

    def test_event_frozen(self):
        e = make_engine_started_event()
        with pytest.raises((TypeError, AttributeError)):
            e.source = "x"  # type: ignore

    def test_event_to_dict(self):
        e = make_engine_started_event()
        d = e.to_dict()
        assert "event_type" in d

    def test_event_has_unique_id(self):
        e1 = make_engine_started_event()
        e2 = make_engine_started_event()
        assert e1.event_id != e2.event_id


# ===========================================================================
# 16. GovernancePolicyValidation
# ===========================================================================

class TestGovernancePolicyValidation:
    def test_valid_request(self):
        validator = GovernancePolicyValidator()
        req = _make_request(supervision_id="sup-1")
        result = validator.validate_request(req)
        assert result.is_valid

    def test_valid_policy(self):
        validator = GovernancePolicyValidator()
        policy = _make_policy()
        result = validator.validate_policy(policy)
        assert result.is_valid

    def test_result_has_checks(self):
        validator = GovernancePolicyValidator()
        result = validator.validate_request(_make_request())
        assert len(result.checks) > 0

    def test_validation_result_frozen(self):
        v = GovernanceValidationResult(
            is_valid=True, checks=(), failed_checks=(),
            passed_count=0, failed_count=0,
        )
        with pytest.raises((TypeError, AttributeError)):
            v.is_valid = False  # type: ignore

    def test_failure_messages_property(self):
        check = GovernanceValidationCheckResult(
            code=GovernanceValidationCode.REQUEST_COMPLETENESS,
            passed=False,
            message="Missing field",
        )
        result = GovernanceValidationResult(
            is_valid=False, checks=(check,), failed_checks=(check,),
            passed_count=0, failed_count=1,
        )
        assert "Missing field" in result.failure_messages


# ===========================================================================
# 17. GovernancePolicyFactory
# ===========================================================================

class TestGovernancePolicyFactory:
    def test_create_condition(self):
        factory = GovernancePolicyFactory()
        cond = factory.create_condition("c", "x.y", ConditionOperator.GT, 5)
        assert cond.field_path == "x.y"

    def test_create_rule(self):
        factory = GovernancePolicyFactory()
        cond = factory.create_condition("c", "x", ConditionOperator.EQ, 1)
        rule = factory.create_rule("r", [cond], LogicalOperator.ALL, PolicyAction.APPROVE)
        assert rule.condition_count == 1

    def test_create_policy(self):
        factory = GovernancePolicyFactory()
        cond = factory.create_condition("c", "x", ConditionOperator.EQ, 1)
        rule = factory.create_rule("r", [cond], LogicalOperator.ALL, PolicyAction.APPROVE)
        policy = factory.create_policy("p", GovernancePolicyType.HEALTH_GOVERNANCE,
                                       PolicyPriority.HIGH, [rule])
        assert policy.enabled

    def test_create_request(self):
        factory = GovernancePolicyFactory()
        req = factory.create_request("sup-x")
        assert req.supervision_id == "sup-x"

    def test_create_health_threshold_policy(self):
        factory = GovernancePolicyFactory()
        policy = factory.create_health_threshold_policy("HP", "score", 0.7)
        assert policy.policy_type == GovernancePolicyType.HEALTH_GOVERNANCE
        assert policy.rule_count == 1

    def test_health_threshold_blocks_below(self):
        factory = GovernancePolicyFactory()
        evaluator = GovernancePolicyEvaluator()
        policy = factory.create_health_threshold_policy("HP", "score", 0.7)
        result = evaluator.evaluate_policy(policy, {"score": 0.5})
        assert result.action == PolicyAction.BLOCK

    def test_health_threshold_approves_above(self):
        factory = GovernancePolicyFactory()
        evaluator = GovernancePolicyEvaluator()
        policy = factory.create_health_threshold_policy("HP", "score", 0.7)
        result = evaluator.evaluate_policy(policy, {"score": 0.9})
        assert result.action == PolicyAction.APPROVE


# ===========================================================================
# 18. GovernancePolicyManager
# ===========================================================================

class TestGovernancePolicyManager:
    def _manager_with_policy(self, policy: GovernancePolicy):
        registry = GovernancePolicyRegistry()
        registry.register(policy)
        return GovernancePolicyManager(registry=registry)

    def test_run_evaluation_success(self):
        policy = _make_policy()
        manager = self._manager_with_policy(policy)
        req = _make_request(inputs={"health.score": 0.2})
        resp = manager.run_evaluation(req)
        assert resp.is_success
        assert resp.final_action == PolicyAction.BLOCK

    def test_run_evaluation_no_policies_default(self):
        manager = GovernancePolicyManager()
        req = _make_request()
        resp = manager.run_evaluation(req)
        assert resp.is_success
        assert resp.final_action == DEFAULT_POLICY_ACTION

    def test_run_evaluation_filter_by_type(self):
        health_policy = _make_policy(
            policy_type=GovernancePolicyType.HEALTH_GOVERNANCE
        )
        risk_policy = _make_policy(
            policy_type=GovernancePolicyType.RISK_GOVERNANCE,
            name="risk-p",
        )
        registry = GovernancePolicyRegistry()
        registry.register(health_policy)
        registry.register(risk_policy)
        manager = GovernancePolicyManager(registry=registry)
        req = _make_request(
            inputs={"health.score": 0.2},
            policy_types=[GovernancePolicyType.HEALTH_GOVERNANCE],
        )
        resp = manager.run_evaluation(req)
        assert resp.policies_skipped == 1

    def test_never_raises_on_exception(self):
        class BrokenRegistry(GovernancePolicyRegistry):
            def enabled_policies(self):
                raise RuntimeError("boom")
        manager = GovernancePolicyManager(registry=BrokenRegistry())
        req = _make_request()
        resp = manager.run_evaluation(req)
        assert not resp.is_success
        assert "boom" in resp.error_message

    def test_conflict_resolution_highest_severity_wins(self):
        # In SEQUENTIAL mode policies are evaluated in priority order (CRITICAL=1, HIGH=2 ... LOW=4).
        # HIGH-priority REJECT policy evaluates first and is a DENY_ACTION → chain stops.
        # So the final action is REJECT (the dominant deny from the highest-priority policy).
        block_policy = _make_policy(
            rules=[_make_rule(action=PolicyAction.BLOCK)],
            priority=PolicyPriority.LOW,
            name="block-p",
        )
        reject_policy = _make_policy(
            rules=[_make_rule(action=PolicyAction.REJECT)],
            priority=PolicyPriority.HIGH,
            name="reject-p",
        )
        registry = GovernancePolicyRegistry()
        registry.register(block_policy)
        registry.register(reject_policy)
        manager = GovernancePolicyManager(registry=registry)
        req = _make_request(inputs={"health.score": 0.1})
        resp = manager.run_evaluation(req)
        # SEQUENTIAL: HIGH priority REJECT runs first and stops the chain
        assert resp.final_action == PolicyAction.REJECT

    def test_history_records_request_and_response(self):
        history = GovernancePolicyHistory()
        manager = GovernancePolicyManager(history=history)
        req = _make_request()
        manager.run_evaluation(req)
        assert history.request_count() == 1
        assert history.response_count() == 1


# ===========================================================================
# 19. GovernancePolicyEngine — lifecycle
# ===========================================================================

class TestGovernancePolicyEngineLifecycle:
    def test_engine_starts_and_stops(self):
        engine = GovernancePolicyEngine()
        engine.start()
        assert engine.lifecycle_state().value == "running"
        engine.stop()
        assert engine.lifecycle_state().value == "stopped"

    def test_evaluate_raises_when_not_running(self):
        engine = GovernancePolicyEngine()
        req = _make_request()
        with pytest.raises(GovernancePolicyEngineNotRunningError):
            engine.evaluate(req)

    def test_evaluate_raises_after_stop(self):
        engine = _started_engine()
        engine.stop()
        req = _make_request()
        with pytest.raises(GovernancePolicyEngineNotRunningError):
            engine.evaluate(req)

    def test_health_returns_dict(self):
        engine = _started_engine()
        h = engine.health()
        assert "status" in h
        engine.stop()

    def test_statistics_returns_dict(self):
        engine = _started_engine()
        s = engine.statistics()
        assert "evaluations" in s
        engine.stop()

    def test_status_returns_dict(self):
        engine = _started_engine()
        s = engine.status()
        assert "engine_id" in s
        engine.stop()

    def test_lifecycle_events_dispatched(self):
        events = []
        engine = GovernancePolicyEngine()
        engine.add_listener(events.append)
        engine.start()
        engine.stop()
        event_types = [e.event_type for e in events]
        assert GovernancePolicyEventType.POLICY_ENGINE_STARTED in event_types
        assert GovernancePolicyEventType.POLICY_ENGINE_STOPPED in event_types


# ===========================================================================
# 20. GovernancePolicyEngine — evaluate
# ===========================================================================

class TestGovernancePolicyEngineEvaluate:
    def test_evaluate_no_policies_returns_default(self):
        engine = _started_engine()
        resp = engine.evaluate(_make_request())
        assert resp.is_success
        assert resp.final_action == DEFAULT_POLICY_ACTION
        engine.stop()

    def test_evaluate_blocking_policy(self):
        engine = _started_engine()
        engine.register_policy(_make_policy())
        resp = engine.evaluate(_make_request(inputs={"health.score": 0.2}))
        assert resp.final_action == PolicyAction.BLOCK
        engine.stop()

    def test_evaluate_approving_policy(self):
        engine = _started_engine()
        engine.register_policy(_make_policy())
        resp = engine.evaluate(_make_request(inputs={"health.score": 0.8}))
        assert resp.final_action == PolicyAction.APPROVE
        engine.stop()

    def test_evaluate_fires_started_and_completed_events(self):
        engine = _started_engine()
        events = []
        engine.add_listener(events.append)
        engine.evaluate(_make_request())
        event_types = [e.event_type for e in events]
        assert GovernancePolicyEventType.EVALUATION_STARTED in event_types
        assert GovernancePolicyEventType.EVALUATION_COMPLETED in event_types
        engine.stop()

    def test_evaluate_response_has_elapsed(self):
        engine = _started_engine()
        resp = engine.evaluate(_make_request())
        assert resp.evaluation_elapsed_s >= 0
        engine.stop()


# ===========================================================================
# 21. GovernancePolicyEngine — management
# ===========================================================================

class TestGovernancePolicyEngineManagement:
    def test_register_and_get_policy(self):
        engine = _started_engine()
        policy = _make_policy()
        engine.register_policy(policy)
        assert engine.get_policy(policy.policy_id) is policy
        engine.stop()

    def test_unregister_policy(self):
        engine = _started_engine()
        policy = _make_policy()
        engine.register_policy(policy)
        engine.unregister_policy(policy.policy_id)
        with pytest.raises(GovernancePolicyNotFoundError):
            engine.get_policy(policy.policy_id)
        engine.stop()

    def test_register_fires_event(self):
        engine = _started_engine()
        events = []
        engine.add_listener(events.append)
        policy = _make_policy()
        engine.register_policy(policy)
        types = [e.event_type for e in events]
        assert GovernancePolicyEventType.POLICY_REGISTERED in types
        engine.stop()

    def test_unregister_fires_event(self):
        engine = _started_engine()
        events = []
        policy = _make_policy()
        engine.register_policy(policy)
        engine.add_listener(events.append)
        engine.unregister_policy(policy.policy_id)
        types = [e.event_type for e in events]
        assert GovernancePolicyEventType.POLICY_UNREGISTERED in types
        engine.stop()

    def test_health_policy_count(self):
        engine = _started_engine()
        engine.register_policy(_make_policy())
        h = engine.health()
        assert h["policies_registered"] == 1
        engine.stop()


# ===========================================================================
# 22. GovernancePolicyEngine — listeners
# ===========================================================================

class TestGovernancePolicyEngineListeners:
    def test_add_remove_listener(self):
        engine = _started_engine()
        events = []
        engine.add_listener(events.append)
        engine.remove_listener(events.append)
        engine.evaluate(_make_request())
        # Only lifecycle events come from stop(); evaluation events were removed
        engine.stop()
        # events only captures post-remove events from stop
        assert all(
            e.event_type in (
                GovernancePolicyEventType.POLICY_ENGINE_STOPPED,
            )
            for e in events
        )

    def test_listener_not_added_twice(self):
        engine = _started_engine()
        events = []
        engine.add_listener(events.append)
        engine.add_listener(events.append)
        engine.evaluate(_make_request())
        started_events = [
            e for e in events
            if e.event_type == GovernancePolicyEventType.EVALUATION_STARTED
        ]
        assert len(started_events) == 1
        engine.stop()

    def test_listener_exception_does_not_crash(self):
        engine = _started_engine()

        def bad_listener(e):
            raise RuntimeError("listener fail")

        engine.add_listener(bad_listener)
        resp = engine.evaluate(_make_request())
        assert resp.is_success
        engine.stop()


# ===========================================================================
# 23. Concurrency
# ===========================================================================

class TestConcurrency:
    def test_concurrent_evaluations(self):
        engine = _started_engine()
        engine.register_policy(_make_policy())
        results = []

        def worker():
            req = _make_request(inputs={"health.score": 0.2})
            resp = engine.evaluate(req)
            results.append(resp)

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 30
        assert all(r.is_success for r in results)
        engine.stop()

    def test_concurrent_register_and_evaluate(self):
        engine = _started_engine()
        errors: List[Exception] = []

        def register_worker(i):
            try:
                engine.register_policy(_make_policy(name=f"p-{i}"))
            except Exception as e:
                errors.append(e)

        def eval_worker():
            try:
                engine.evaluate(_make_request(inputs={"health.score": 0.2}))
            except Exception as e:
                errors.append(e)

        threads = (
            [threading.Thread(target=register_worker, args=(i,)) for i in range(20)]
            + [threading.Thread(target=eval_worker) for _ in range(20)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        engine.stop()


# ===========================================================================
# 24. Public surface (__all__)
# ===========================================================================

class TestPublicSurface:
    def test_all_exports_importable(self):
        import iios.supervisor.policy_legacy as module
        for name in module.__all__:
            assert hasattr(module, name), f"Missing export: {name}"

    def test_engine_in_all(self):
        import iios.supervisor.policy_legacy as module
        assert "GovernancePolicyEngine" in module.__all__

    def test_factory_in_all(self):
        import iios.supervisor.policy_legacy as module
        assert "GovernancePolicyFactory" in module.__all__


# ===========================================================================
# 25. Integration smoke test
# ===========================================================================

class TestIntegrationSmoke:
    def test_full_evaluation_pipeline(self):
        """End-to-end: engine → register policy → evaluate → assert BLOCK."""
        factory = GovernancePolicyFactory()
        engine  = GovernancePolicyEngine()
        engine.start()

        # Build a health policy that blocks when score < 0.6
        policy = factory.create_health_threshold_policy(
            "System Health Gate", "platform_health.overall", 0.6
        )
        engine.register_policy(policy)

        # Unhealthy request
        req = factory.create_request(
            "sup-smoke",
            inputs={"platform_health.overall": 0.4},
        )
        resp = engine.evaluate(req)
        assert resp.final_action == PolicyAction.BLOCK
        assert resp.is_denied
        assert resp.policies_evaluated == 1

        # Healthy request
        req2 = factory.create_request(
            "sup-smoke-2",
            inputs={"platform_health.overall": 0.9},
        )
        resp2 = engine.evaluate(req2)
        assert resp2.final_action == PolicyAction.APPROVE
        assert resp2.is_approved

        engine.stop()

    def test_statistics_reflect_evaluations(self):
        engine = _started_engine()
        for _ in range(5):
            engine.evaluate(_make_request())
        snap = engine.statistics()
        assert snap["evaluations"] >= 5
        engine.stop()

    def test_response_summary_has_correct_counts(self):
        engine = _started_engine()
        policy = _make_policy(
            rules=[_make_rule(action=PolicyAction.APPROVE,
                              conditions=[_make_condition(
                                  threshold=0.5, operator=ConditionOperator.GT)])]
        )
        engine.register_policy(policy)
        resp = engine.evaluate(_make_request(inputs={"health.score": 0.8}))
        assert resp.summary.total_policies == 1
        engine.stop()
