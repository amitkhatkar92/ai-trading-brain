"""
tests/unit/decision/policies/test_policies.py
=============================================
Comprehensive test suite for the Decision Policy Framework.

C9 Decision Intelligence — Phase 1, Module 3
~180 tests covering all components.
"""
from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from iios.decision.policies import (
    ConflictResolutionStrategy,
    DecisionPolicy,
    DecisionPolicyChain,
    DecisionPolicyEngine,
    DecisionPolicyEvaluator,
    DecisionPolicyFactory,
    DecisionPolicyHistory,
    DecisionPolicyManager,
    DecisionPolicyRegistry,
    DecisionPolicyStatistics,
    DecisionPolicyValidator,
    PolicyAction,
    PolicyAuditReport,
    PolicyChainMode,
    PolicyCondition,
    PolicyConditionOperator,
    PolicyEngineNotRunningError,
    PolicyEvaluationContext,
    PolicyEvaluationRequest,
    PolicyEvaluationStatus,
    PolicyEvaluationSummary,
    PolicyEventType,
    PolicyFrameworkAdapter,
    PolicyNotFoundError,
    PolicyPriority,
    PolicyPriorityResolver,
    PolicyRegistryError,
    PolicyRuleLogic,
    PolicyRuleResult,
    PolicyStatus,
    PolicyType,
    PolicyValidationCode,
    SinglePolicyResult,
    build_audit_report,
    make_policy_approved,
    make_policy_blocked,
    make_policy_escalated,
    make_policy_evaluation_completed,
    make_policy_evaluation_started,
    make_policy_loaded,
    make_policy_rejected,
    make_policy_validated,
)
from iios.decision.policies.decision_policy_rule import PolicyRule


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def make_condition(
    name:      str               = "cond",
    field:     str               = "inputs.value",
    op:        PolicyConditionOperator = PolicyConditionOperator.GT,
    threshold: Any               = 0,
    **kw: Any,
) -> PolicyCondition:
    return PolicyCondition.create(name=name, field_path=field, operator=op, threshold=threshold, **kw)


def make_rule(
    name:      str              = "rule",
    conditions = None,
    action:    PolicyAction     = PolicyAction.APPROVE,
    logic:     PolicyRuleLogic  = PolicyRuleLogic.AND,
) -> PolicyRule:
    if conditions is None:
        conditions = [make_condition()]
    return PolicyRule.create(name=name, conditions=conditions, action=action, logic=logic)


def make_policy(
    name:           str           = "TestPolicy",
    policy_type:    PolicyType    = PolicyType.RISK,
    priority:       PolicyPriority = PolicyPriority.MEDIUM,
    default_action: PolicyAction  = PolicyAction.APPROVE,
    rules           = None,
    **kw: Any,
) -> DecisionPolicy:
    return DecisionPolicy.create(
        name=name, policy_type=policy_type, priority=priority,
        default_action=default_action, rules=rules or [], **kw
    )


def make_context(
    inputs:  dict = None,
    **kw: Any,
) -> PolicyEvaluationContext:
    return PolicyEvaluationContext.create(
        request_id  = kw.get("request_id",  str(uuid.uuid4())),
        decision_id = kw.get("decision_id", str(uuid.uuid4())),
        inputs      = inputs or {},
    )


@pytest.fixture
def factory() -> DecisionPolicyFactory:
    return DecisionPolicyFactory()


@pytest.fixture
def engine() -> DecisionPolicyEngine:
    e = DecisionPolicyEngine()
    e.start()
    yield e
    if e.lifecycle_state() not in ("stopped", "shutdown"):
        e.stop()


@pytest.fixture
def registry() -> DecisionPolicyRegistry:
    return DecisionPolicyRegistry()


@pytest.fixture
def stats() -> DecisionPolicyStatistics:
    return DecisionPolicyStatistics()


# ===========================================================================
# 1 — PolicyCondition
# ===========================================================================

class TestPolicyConditionOperators:
    """All 10 operators."""

    def _ctx(self, value: Any, field: str = "inputs.x") -> dict:
        return {"inputs": {"x": value}}

    def test_gt_true(self):
        c = make_condition(op=PolicyConditionOperator.GT, threshold=5)
        assert c.evaluate({"inputs": {"value": 10}}) is True

    def test_gt_false(self):
        c = make_condition(op=PolicyConditionOperator.GT, threshold=5)
        assert c.evaluate({"inputs": {"value": 3}}) is False

    def test_gte_equal(self):
        c = make_condition(op=PolicyConditionOperator.GTE, threshold=5)
        assert c.evaluate({"inputs": {"value": 5}}) is True

    def test_lt_true(self):
        c = make_condition(op=PolicyConditionOperator.LT, threshold=5)
        assert c.evaluate({"inputs": {"value": 3}}) is True

    def test_lt_false(self):
        c = make_condition(op=PolicyConditionOperator.LT, threshold=5)
        assert c.evaluate({"inputs": {"value": 7}}) is False

    def test_lte_equal(self):
        c = make_condition(op=PolicyConditionOperator.LTE, threshold=5)
        assert c.evaluate({"inputs": {"value": 5}}) is True

    def test_eq_true(self):
        c = make_condition(op=PolicyConditionOperator.EQ, threshold="active")
        assert c.evaluate({"inputs": {"value": "active"}}) is True

    def test_eq_false(self):
        c = make_condition(op=PolicyConditionOperator.EQ, threshold="active")
        assert c.evaluate({"inputs": {"value": "inactive"}}) is False

    def test_ne_true(self):
        c = make_condition(op=PolicyConditionOperator.NE, threshold="active")
        assert c.evaluate({"inputs": {"value": "inactive"}}) is True

    def test_in_true(self):
        c = make_condition(op=PolicyConditionOperator.IN, threshold=["a", "b", "c"])
        assert c.evaluate({"inputs": {"value": "b"}}) is True

    def test_in_false(self):
        c = make_condition(op=PolicyConditionOperator.IN, threshold=["a", "b"])
        assert c.evaluate({"inputs": {"value": "z"}}) is False

    def test_not_in_true(self):
        c = make_condition(op=PolicyConditionOperator.NOT_IN, threshold=["a", "b"])
        assert c.evaluate({"inputs": {"value": "z"}}) is True

    def test_exists_true(self):
        c = make_condition(op=PolicyConditionOperator.EXISTS, threshold=None)
        assert c.evaluate({"inputs": {"value": 0}}) is True

    def test_exists_false_missing(self):
        c = make_condition(op=PolicyConditionOperator.EXISTS, threshold=None)
        assert c.evaluate({"inputs": {}}) is False

    def test_not_exists_true_missing(self):
        c = make_condition(op=PolicyConditionOperator.NOT_EXISTS, threshold=None)
        assert c.evaluate({"inputs": {}}) is True

    def test_not_exists_false_present(self):
        c = make_condition(op=PolicyConditionOperator.NOT_EXISTS, threshold=None)
        assert c.evaluate({"inputs": {"value": 42}}) is False

    def test_missing_field_returns_false_for_gt(self):
        c = make_condition(op=PolicyConditionOperator.GT, threshold=5)
        assert c.evaluate({}) is False

    def test_invalid_numeric_returns_false(self):
        c = make_condition(op=PolicyConditionOperator.GT, threshold=5)
        assert c.evaluate({"inputs": {"value": "not-a-number"}}) is False

    def test_nested_dotted_path(self):
        c = PolicyCondition.create(
            "deep", "snapshots.risk.score", PolicyConditionOperator.GT, 50
        )
        assert c.evaluate({"snapshots": {"risk": {"score": 80}}}) is True

    def test_custom_evaluator_used(self):
        called = []
        def fn(data):
            called.append(True)
            return True
        c = PolicyCondition.create(
            "custom", "inputs.x", PolicyConditionOperator.GT, 0,
            custom_evaluator=fn,
        )
        result = c.evaluate({"inputs": {"x": -1}})
        assert result is True
        assert called

    def test_custom_evaluator_exception_returns_false(self):
        c = PolicyCondition.create(
            "bad", "inputs.x", PolicyConditionOperator.GT, 0,
            custom_evaluator=lambda d: 1 / 0,
        )
        assert c.evaluate({}) is False


# ===========================================================================
# 2 — PolicyRule
# ===========================================================================

class TestPolicyRule:

    def test_and_logic_all_true(self):
        c1 = make_condition("c1", "inputs.a", PolicyConditionOperator.GT, 0)
        c2 = make_condition("c2", "inputs.b", PolicyConditionOperator.GT, 0)
        rule = PolicyRule.create("r", [c1, c2], PolicyAction.REJECT, logic=PolicyRuleLogic.AND)
        rr   = rule.evaluate({"inputs": {"a": 1, "b": 1}})
        assert rr.triggered is True
        assert rr.action == PolicyAction.REJECT

    def test_and_logic_one_false(self):
        c1 = make_condition("c1", "inputs.a", PolicyConditionOperator.GT, 0)
        c2 = make_condition("c2", "inputs.b", PolicyConditionOperator.GT, 0)
        rule = PolicyRule.create("r", [c1, c2], PolicyAction.REJECT, logic=PolicyRuleLogic.AND)
        rr   = rule.evaluate({"inputs": {"a": 1, "b": -1}})
        assert rr.triggered is False
        assert rr.action is None

    def test_or_logic_one_true(self):
        c1 = make_condition("c1", "inputs.a", PolicyConditionOperator.GT, 0)
        c2 = make_condition("c2", "inputs.b", PolicyConditionOperator.GT, 0)
        rule = PolicyRule.create("r", [c1, c2], PolicyAction.BLOCK, logic=PolicyRuleLogic.OR)
        rr   = rule.evaluate({"inputs": {"a": -1, "b": 1}})
        assert rr.triggered is True

    def test_or_logic_none_true(self):
        c1 = make_condition("c1", "inputs.a", PolicyConditionOperator.GT, 0)
        rule = PolicyRule.create("r", [c1], PolicyAction.BLOCK, logic=PolicyRuleLogic.OR)
        rr   = rule.evaluate({"inputs": {"a": -1}})
        assert rr.triggered is False

    def test_not_logic_negates_and(self):
        c1 = make_condition("c1", "inputs.a", PolicyConditionOperator.GT, 0)
        rule = PolicyRule.create("r", [c1], PolicyAction.ESCALATE, logic=PolicyRuleLogic.NOT)
        # GT(a > 0): a=5 → True → NOT → False
        rr = rule.evaluate({"inputs": {"a": 5}})
        assert rr.triggered is False
        # a=-1 → False → NOT → True
        rr2 = rule.evaluate({"inputs": {"a": -1}})
        assert rr2.triggered is True

    def test_empty_conditions_never_triggers(self):
        rule = PolicyRule.create("empty", [], PolicyAction.REJECT)
        rr   = rule.evaluate({})
        assert rr.triggered is False

    def test_conditions_met_count(self):
        c1 = make_condition("c1", "inputs.a", PolicyConditionOperator.GT, 0)
        c2 = make_condition("c2", "inputs.b", PolicyConditionOperator.GT, 0)
        rule = PolicyRule.create("r", [c1, c2], PolicyAction.APPROVE, logic=PolicyRuleLogic.AND)
        rr   = rule.evaluate({"inputs": {"a": 1, "b": -1}})
        assert rr.conditions_met == 1
        assert rr.conditions_evaluated == 2

    def test_rule_weight_propagated(self):
        rule = PolicyRule.create("r", [make_condition()], PolicyAction.APPROVE, weight=2.5)
        rr   = rule.evaluate({"inputs": {"value": 1}})
        assert rr.weight == 2.5


# ===========================================================================
# 3 — DecisionPolicy
# ===========================================================================

class TestDecisionPolicy:

    def test_first_triggered_rule_wins(self):
        c_reject = make_condition("cr", "inputs.risk", PolicyConditionOperator.GT, 50)
        c_esc    = make_condition("ce", "inputs.risk", PolicyConditionOperator.GT, 30)
        r1 = PolicyRule.create("reject-rule", [c_reject], PolicyAction.REJECT)
        r2 = PolicyRule.create("esc-rule",    [c_esc],    PolicyAction.ESCALATE)
        p  = make_policy(rules=[r1, r2])
        ctx = make_context({"risk": 60})
        result = p.evaluate(ctx)
        assert result.action == PolicyAction.REJECT

    def test_default_action_when_no_rules_trigger(self):
        c = make_condition("c", "inputs.risk", PolicyConditionOperator.GT, 100)
        r = PolicyRule.create("rule", [c], PolicyAction.REJECT)
        p = make_policy(default_action=PolicyAction.APPROVE, rules=[r])
        ctx = make_context({"risk": 10})
        result = p.evaluate(ctx)
        assert result.action == PolicyAction.APPROVE

    def test_no_rules_returns_default_action(self):
        p   = make_policy(default_action=PolicyAction.DEFER, rules=[])
        ctx = make_context()
        result = p.evaluate(ctx)
        assert result.action == PolicyAction.DEFER

    def test_is_active(self):
        p = make_policy()
        assert p.is_active() is True

    def test_inactive_policy(self):
        p = make_policy(status=PolicyStatus.INACTIVE)
        assert p.is_active() is False

    def test_result_has_correct_metadata(self):
        p   = make_policy(name="P1", policy_type=PolicyType.COMPLIANCE)
        ctx = make_context()
        r   = p.evaluate(ctx)
        assert r.policy_id   == p.policy_id
        assert r.policy_name == "P1"
        assert r.policy_type == PolicyType.COMPLIANCE
        assert r.evaluation_time_s >= 0.0
        assert isinstance(r.evaluated_at, datetime)

    def test_conditions_total_and_met(self):
        c1 = make_condition("c1", "inputs.a", PolicyConditionOperator.GT, 0)
        c2 = make_condition("c2", "inputs.b", PolicyConditionOperator.GT, 0)
        r  = PolicyRule.create("r", [c1, c2], PolicyAction.APPROVE)
        p  = make_policy(rules=[r])
        ctx = make_context({"a": 1, "b": -1})
        res = p.evaluate(ctx)
        assert res.conditions_total == 2
        assert res.conditions_met   == 1


# ===========================================================================
# 4 — PolicyEvaluationContext
# ===========================================================================

class TestPolicyEvaluationContext:

    def test_get_nested_path(self):
        ctx = PolicyEvaluationContext.create(
            decision_id="d1",
            inputs={"price": 100},
            snapshots={"risk": {"var": 0.05}},
        )
        assert ctx.get("inputs.price")      == 100
        assert ctx.get("snapshots.risk.var") == 0.05

    def test_get_missing_returns_default(self):
        ctx = PolicyEvaluationContext.create()
        assert ctx.get("inputs.missing", 99) == 99

    def test_to_dict_contains_inputs_and_snapshots(self):
        ctx = PolicyEvaluationContext.create(
            inputs={"k": "v"}, snapshots={"s": {"a": 1}}
        )
        d = ctx.to_dict()
        assert d["inputs"]["k"] == "v"
        assert d["snapshots"]["s"]["a"] == 1

    def test_from_engine_context(self):
        mock_ctx = MagicMock()
        mock_ctx.request_id  = "req-1"
        mock_ctx.decision_id = "dec-1"
        mock_ctx.session_id  = "sess-1"
        mock_ctx.pipeline_id = "pipe-1"
        mock_ctx.inputs      = {"x": 1}
        mock_ctx.metadata    = {}
        ctx = PolicyEvaluationContext.from_engine_context(mock_ctx)
        assert ctx.request_id  == "req-1"
        assert ctx.decision_id == "dec-1"

    def test_create_generates_context_id(self):
        ctx1 = PolicyEvaluationContext.create()
        ctx2 = PolicyEvaluationContext.create()
        assert ctx1.context_id != ctx2.context_id

    def test_snapshot_with_to_dict_method(self):
        class Snap:
            def to_dict(self):
                return {"val": 42}
        ctx = PolicyEvaluationContext.create(snapshots={"s": Snap()})
        d   = ctx.to_dict()
        assert d["snapshots"]["s"]["val"] == 42

    def test_snapshot_with_dict_attr(self):
        class Snap:
            def __init__(self):
                self.score = 99
        ctx = PolicyEvaluationContext.create(snapshots={"s": Snap()})
        d   = ctx.to_dict()
        assert d["snapshots"]["s"]["score"] == 99


# ===========================================================================
# 5 — PolicyPriorityResolver
# ===========================================================================

class TestPolicyPriorityResolver:

    def _make_result(
        self,
        action:   PolicyAction,
        priority: PolicyPriority = PolicyPriority.MEDIUM,
    ) -> SinglePolicyResult:
        return SinglePolicyResult(
            result_id         = str(uuid.uuid4()),
            policy_id         = str(uuid.uuid4()),
            policy_name       = "Test",
            policy_type       = PolicyType.RISK,
            priority          = priority,
            action            = action,
            conditions_met    = 0,
            conditions_total  = 0,
            rule_results      = (),
            reason            = "",
            evaluation_time_s = 0.0,
            evaluated_at      = datetime.now(timezone.utc),
        )

    def test_empty_results_returns_approve(self):
        r = PolicyPriorityResolver()
        action, conflict = r.resolve([], ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES)
        assert action == PolicyAction.APPROVE
        assert conflict is False

    def test_explicit_deny_block_wins_over_approve(self):
        r = PolicyPriorityResolver()
        results = [
            self._make_result(PolicyAction.APPROVE),
            self._make_result(PolicyAction.BLOCK),
        ]
        action, _ = r.resolve(results, ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES)
        assert action == PolicyAction.BLOCK

    def test_explicit_deny_block_beats_reject(self):
        r = PolicyPriorityResolver()
        results = [
            self._make_result(PolicyAction.REJECT),
            self._make_result(PolicyAction.BLOCK),
        ]
        action, _ = r.resolve(results, ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES)
        assert action == PolicyAction.BLOCK

    def test_highest_priority_wins_critical_beats_medium(self):
        r = PolicyPriorityResolver()
        results = [
            self._make_result(PolicyAction.DEFER,    PolicyPriority.MEDIUM),
            self._make_result(PolicyAction.ESCALATE, PolicyPriority.CRITICAL),
        ]
        action, _ = r.resolve(results, ConflictResolutionStrategy.HIGHEST_PRIORITY_WINS)
        assert action == PolicyAction.ESCALATE

    def test_highest_priority_single_result(self):
        r = PolicyPriorityResolver()
        results = [self._make_result(PolicyAction.REJECT)]
        action, conflict = r.resolve(results, ConflictResolutionStrategy.HIGHEST_PRIORITY_WINS)
        assert action  == PolicyAction.REJECT
        assert conflict is False

    def test_escalation_overrides_approve(self):
        r = PolicyPriorityResolver()
        results = [
            self._make_result(PolicyAction.APPROVE),
            self._make_result(PolicyAction.APPROVE),
            self._make_result(PolicyAction.ESCALATE),
        ]
        action, _ = r.resolve(results, ConflictResolutionStrategy.ESCALATION_OVERRIDES)
        assert action == PolicyAction.ESCALATE

    def test_escalation_overrides_falls_back_to_deny(self):
        r = PolicyPriorityResolver()
        results = [
            self._make_result(PolicyAction.APPROVE),
            self._make_result(PolicyAction.BLOCK),
        ]
        action, _ = r.resolve(results, ConflictResolutionStrategy.ESCALATION_OVERRIDES)
        assert action == PolicyAction.BLOCK

    def test_conflict_applied_false_when_single_action(self):
        r = PolicyPriorityResolver()
        results = [
            self._make_result(PolicyAction.APPROVE),
            self._make_result(PolicyAction.APPROVE),
        ]
        _, conflict = r.resolve(results, ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES)
        assert conflict is False

    def test_conflict_applied_true_when_mixed_actions(self):
        r = PolicyPriorityResolver()
        results = [
            self._make_result(PolicyAction.APPROVE),
            self._make_result(PolicyAction.REJECT),
        ]
        _, conflict = r.resolve(results, ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES)
        assert conflict is True


# ===========================================================================
# 6 — DecisionPolicyRegistry
# ===========================================================================

class TestDecisionPolicyRegistry:

    def test_register_and_get(self, registry):
        p = make_policy()
        registry.register(p)
        retrieved = registry.get(p.policy_id)
        assert retrieved is p

    def test_find_returns_none_when_not_found(self, registry):
        assert registry.find("nonexistent") is None

    def test_get_raises_when_not_found(self, registry):
        with pytest.raises(PolicyNotFoundError):
            registry.get("nonexistent")

    def test_deregister_returns_policy(self, registry):
        p = make_policy()
        registry.register(p)
        removed = registry.deregister(p.policy_id)
        assert removed is p

    def test_deregister_returns_none_when_absent(self, registry):
        assert registry.deregister("ghost") is None

    def test_active_policies_excludes_inactive(self, registry):
        p1 = make_policy(status=PolicyStatus.ACTIVE)
        p2 = make_policy(status=PolicyStatus.INACTIVE)
        registry.register(p1)
        registry.register(p2)
        active = registry.active_policies()
        assert p1 in active
        assert p2 not in active

    def test_policies_by_type(self, registry):
        p_risk = make_policy(policy_type=PolicyType.RISK)
        p_comp = make_policy(policy_type=PolicyType.COMPLIANCE)
        registry.register(p_risk)
        registry.register(p_comp)
        assert registry.policies_by_type(PolicyType.RISK)       == [p_risk]
        assert registry.policies_by_type(PolicyType.COMPLIANCE) == [p_comp]

    def test_policy_count(self, registry):
        registry.register(make_policy())
        registry.register(make_policy())
        assert registry.policy_count() == 2

    def test_clear_empties_registry(self, registry):
        registry.register(make_policy())
        registry.clear()
        assert registry.policy_count() == 0

    def test_max_policies_enforced(self):
        r = DecisionPolicyRegistry(max_policies=2)
        r.register(make_policy())
        r.register(make_policy())
        with pytest.raises(PolicyRegistryError):
            r.register(make_policy())

    def test_update_existing_policy(self, registry):
        p = make_policy()
        registry.register(p)
        p2 = make_policy()
        p2.__class__ = type(p2)
        # Registering same ID again should update (no error)
        p_copy = DecisionPolicy.create(
            "Updated", PolicyType.RISK, PolicyPriority.HIGH, PolicyAction.APPROVE,
            policy_id=p.policy_id,
        )
        registry.register(p_copy)
        assert registry.get(p.policy_id).name == "Updated"

    def test_thread_safe_concurrent_register(self, registry):
        errors = []
        def add(i):
            try:
                registry.register(make_policy(name=f"p{i}"))
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=add, args=(i,)) for i in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors


# ===========================================================================
# 7 — DecisionPolicyValidator
# ===========================================================================

class TestDecisionPolicyValidator:

    def test_valid_policy_passes_all_checks(self):
        v   = DecisionPolicyValidator()
        c   = make_condition()
        r   = make_rule(conditions=[c])
        p   = make_policy(rules=[r])
        res = v.validate_policy(p)
        assert res.is_valid is True
        assert res.failed_count == 0

    def test_empty_policy_id_fails(self):
        v = DecisionPolicyValidator()
        p = make_policy()
        p.policy_id = ""
        res = v.validate_policy(p)
        assert res.is_valid is False
        assert PolicyValidationCode.POLICY_IDENTITY in res.failed_checks

    def test_empty_name_fails(self):
        v = DecisionPolicyValidator()
        p = make_policy()
        p.name = ""
        res = v.validate_policy(p)
        assert res.is_valid is False

    def test_rule_with_no_conditions_fails(self):
        v = DecisionPolicyValidator()
        r = PolicyRule.create("empty", [], PolicyAction.REJECT)
        p = make_policy(rules=[r])
        res = v.validate_policy(p)
        assert PolicyValidationCode.RULE_CONSISTENCY in res.failed_checks

    def test_condition_with_empty_field_path_fails(self):
        v = DecisionPolicyValidator()
        c = PolicyCondition.create("c", "", PolicyConditionOperator.GT, 0)
        r = make_rule(conditions=[c])
        p = make_policy(rules=[r])
        res = v.validate_policy(p)
        assert PolicyValidationCode.CONDITION_VALIDITY in res.failed_checks

    def test_valid_request_passes(self):
        v   = DecisionPolicyValidator()
        ctx = make_context()
        req = PolicyEvaluationRequest.create(ctx)
        res = v.validate_request(req)
        assert res.is_valid is True

    def test_empty_request_id_fails(self):
        v   = DecisionPolicyValidator()
        ctx = make_context()
        # Construct directly to bypass factory's auto-ID generation
        req = PolicyEvaluationRequest(request_id="", context=ctx)
        res = v.validate_request(req)
        assert res.is_valid is False

    def test_error_messages_populated_on_failure(self):
        v = DecisionPolicyValidator()
        p = make_policy()
        p.policy_id = ""
        res = v.validate_policy(p)
        assert len(res.error_messages) > 0


# ===========================================================================
# 8 — DecisionPolicyEvaluator
# ===========================================================================

class TestDecisionPolicyEvaluator:

    def test_successful_evaluation(self):
        ev  = DecisionPolicyEvaluator()
        c   = make_condition("c", "inputs.x", PolicyConditionOperator.GT, 0)
        r   = make_rule(conditions=[c], action=PolicyAction.REJECT)
        p   = make_policy(rules=[r])
        ctx = make_context({"x": 10})
        res = ev.evaluate(p, ctx)
        assert res.action == PolicyAction.REJECT

    def test_exception_returns_block_result(self):
        ev = DecisionPolicyEvaluator()

        class BadPolicy:
            policy_id   = "bad-1"
            name        = "Bad"
            policy_type = PolicyType.RISK
            priority    = PolicyPriority.MEDIUM
            def evaluate(self, ctx):
                raise RuntimeError("boom")

        ctx = make_context()
        res = ev.evaluate(BadPolicy(), ctx)  # type: ignore
        assert res.action == PolicyAction.BLOCK
        assert "boom" in res.reason


# ===========================================================================
# 9 — DecisionPolicyChain
# ===========================================================================

class TestDecisionPolicyChain:

    def _policy_with_action(self, action: PolicyAction, priority: PolicyPriority = PolicyPriority.MEDIUM) -> DecisionPolicy:
        """Policy that always returns *action* (condition always True)."""
        c = make_condition("c", "inputs.x", PolicyConditionOperator.GTE, -999)
        r = PolicyRule.create("r", [c], action)
        return make_policy(rules=[r], priority=priority)

    def test_sequential_stops_on_block(self):
        p_block  = self._policy_with_action(PolicyAction.BLOCK,   PolicyPriority.CRITICAL)
        p_reject = self._policy_with_action(PolicyAction.REJECT,  PolicyPriority.HIGH)
        chain = DecisionPolicyChain.create("c", PolicyChainMode.SEQUENTIAL, [p_block, p_reject])
        ctx   = make_context({"x": 1})
        results = chain.evaluate(ctx)
        # Stops after BLOCK — only 1 result
        assert len(results) == 1
        assert results[0].action == PolicyAction.BLOCK

    def test_sequential_evaluates_all_if_no_block(self):
        p1 = self._policy_with_action(PolicyAction.APPROVE, PolicyPriority.CRITICAL)
        p2 = self._policy_with_action(PolicyAction.APPROVE, PolicyPriority.HIGH)
        chain = DecisionPolicyChain.create("c", PolicyChainMode.SEQUENTIAL, [p1, p2])
        ctx   = make_context({"x": 1})
        results = chain.evaluate(ctx)
        assert len(results) == 2

    def test_parallel_evaluates_all(self):
        p1 = self._policy_with_action(PolicyAction.BLOCK)
        p2 = self._policy_with_action(PolicyAction.APPROVE)
        chain = DecisionPolicyChain.create("c", PolicyChainMode.PARALLEL, [p1, p2])
        ctx   = make_context({"x": 1})
        results = chain.evaluate(ctx)
        assert len(results) == 2

    def test_weighted_evaluates_all(self):
        p1 = self._policy_with_action(PolicyAction.APPROVE)
        p2 = self._policy_with_action(PolicyAction.REJECT)
        chain = DecisionPolicyChain.create("c", PolicyChainMode.WEIGHTED, [p1, p2])
        ctx   = make_context({"x": 1})
        results = chain.evaluate(ctx)
        assert len(results) == 2

    def test_empty_policies_returns_empty(self):
        chain = DecisionPolicyChain.create("c", PolicyChainMode.SEQUENTIAL, [])
        results = chain.evaluate(make_context())
        assert results == []

    def test_sequential_ordered_by_priority(self):
        p_high   = self._policy_with_action(PolicyAction.APPROVE,  PolicyPriority.HIGH)
        p_medium = self._policy_with_action(PolicyAction.ESCALATE, PolicyPriority.MEDIUM)
        p_crit   = self._policy_with_action(PolicyAction.BLOCK,    PolicyPriority.CRITICAL)
        chain = DecisionPolicyChain.create("c", PolicyChainMode.SEQUENTIAL, [p_medium, p_high, p_crit])
        ctx   = make_context({"x": 1})
        results = chain.evaluate(ctx)
        # CRITICAL is first; BLOCK stops chain
        assert results[0].action == PolicyAction.BLOCK
        assert len(results) == 1


# ===========================================================================
# 10 — DecisionPolicyAudit
# ===========================================================================

class TestDecisionPolicyAudit:

    def _make_single_result(self, action: PolicyAction) -> SinglePolicyResult:
        return SinglePolicyResult(
            result_id         = str(uuid.uuid4()),
            policy_id         = str(uuid.uuid4()),
            policy_name       = "P",
            policy_type       = PolicyType.RISK,
            priority          = PolicyPriority.MEDIUM,
            action            = action,
            conditions_met    = 1,
            conditions_total  = 1,
            rule_results      = (PolicyRuleResult("r", "rule", True, action, "reason", 1, 1, 1.0),),
            reason            = "reason",
            evaluation_time_s = 0.01,
            evaluated_at      = datetime.now(timezone.utc),
        )

    def test_build_audit_report_basic(self):
        results = [self._make_single_result(PolicyAction.REJECT)]
        report  = build_audit_report("req-1", "dec-1", results, PolicyAction.REJECT)
        assert report.final_action == PolicyAction.REJECT
        assert len(report.entries) == 1
        assert report.total_policies == 1

    def test_audit_entry_fields(self):
        results = [self._make_single_result(PolicyAction.BLOCK)]
        report  = build_audit_report("req-1", "dec-1", results, PolicyAction.BLOCK)
        e = report.entries[0]
        assert e.action           == PolicyAction.BLOCK
        assert e.rules_evaluated  == 1
        assert e.rules_triggered  == 1

    def test_conflict_applied_propagated(self):
        results = [self._make_single_result(PolicyAction.APPROVE)]
        report  = build_audit_report("r", "d", results, PolicyAction.APPROVE, conflict_applied=True)
        assert report.conflict_resolution_applied is True

    def test_empty_results(self):
        report = build_audit_report("r", "d", [], PolicyAction.APPROVE)
        assert len(report.entries)  == 0
        assert report.total_policies == 0

    def test_to_dict(self):
        results = [self._make_single_result(PolicyAction.REJECT)]
        report  = build_audit_report("r", "d", results, PolicyAction.REJECT)
        d = report.to_dict()
        assert d["final_action"]  == "reject"
        assert isinstance(d["entries"], list)


# ===========================================================================
# 11 — DecisionPolicyStatistics
# ===========================================================================

class TestDecisionPolicyStatistics:

    def test_initial_state(self, stats):
        s = stats.snapshot()
        assert s["policies_evaluated"]   == 0
        assert s["policies_approved"]    == 0
        assert s["policies_rejected"]    == 0
        assert s["policies_blocked"]     == 0
        assert s["policies_escalated"]   == 0
        assert s["average_evaluation_time_s"] == 0.0
        assert s["policy_coverage"]      == 0.0
        assert s["evaluation_throughput"] == 0

    def test_record_started(self, stats):
        stats.record_evaluation_started()
        stats.record_evaluation_started()
        assert stats.snapshot()["policies_evaluated"] == 2

    def test_record_approve(self, stats):
        stats.record_evaluation_completed(PolicyAction.APPROVE, 0.1)
        assert stats.snapshot()["policies_approved"] == 1

    def test_record_approve_with_conditions(self, stats):
        stats.record_evaluation_completed(PolicyAction.APPROVE_WITH_CONDITIONS, 0.1)
        assert stats.snapshot()["policies_approved"] == 1

    def test_record_reject(self, stats):
        stats.record_evaluation_completed(PolicyAction.REJECT, 0.1)
        assert stats.snapshot()["policies_rejected"] == 1

    def test_record_block(self, stats):
        stats.record_evaluation_completed(PolicyAction.BLOCK, 0.1)
        assert stats.snapshot()["policies_blocked"] == 1

    def test_record_escalate(self, stats):
        stats.record_evaluation_completed(PolicyAction.ESCALATE, 0.1)
        assert stats.snapshot()["policies_escalated"] == 1

    def test_record_defer_goes_to_escalated(self, stats):
        stats.record_evaluation_completed(PolicyAction.DEFER, 0.1)
        assert stats.snapshot()["policies_escalated"] == 1

    def test_ema_updates(self, stats):
        stats.record_evaluation_completed(PolicyAction.APPROVE, 1.0)
        stats.record_evaluation_completed(PolicyAction.APPROVE, 1.0)
        s = stats.snapshot()
        assert s["average_evaluation_time_s"] > 0.0

    def test_coverage_clamps_to_unit(self, stats):
        stats.record_coverage(1.5)
        assert stats.snapshot()["policy_coverage"] == 1.0
        stats.record_coverage(-0.5)
        assert stats.snapshot()["policy_coverage"] == 0.0

    def test_reset(self, stats):
        stats.record_evaluation_started()
        stats.record_evaluation_completed(PolicyAction.APPROVE, 0.1)
        stats.reset()
        s = stats.snapshot()
        assert s["policies_evaluated"] == 0
        assert s["policies_approved"]  == 0

    def test_throughput_window(self, stats):
        for _ in range(5):
            stats.record_evaluation_completed(PolicyAction.APPROVE, 0.01)
        assert stats.snapshot()["evaluation_throughput"] == 5

    def test_thread_safe_concurrent_updates(self, stats):
        def work():
            for _ in range(100):
                stats.record_evaluation_started()
                stats.record_evaluation_completed(PolicyAction.APPROVE, 0.001)
        threads = [threading.Thread(target=work) for _ in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()
        s = stats.snapshot()
        assert s["policies_evaluated"] == 400
        assert s["policies_approved"]  == 400


# ===========================================================================
# 12 — DecisionPolicyHistory
# ===========================================================================

class TestDecisionPolicyHistory:

    def test_record_and_retrieve_event(self):
        h = DecisionPolicyHistory()
        e = make_policy_evaluation_started("r1", "d1", "test")
        h.record_event(e)
        assert h.event_count() == 1
        assert h.latest_event() is e

    def test_record_and_retrieve_response(self):
        from iios.decision.policies import DecisionPolicyResponse
        h = DecisionPolicyHistory()
        r = DecisionPolicyResponse.failure("r1", "d1", "err")
        h.record_response(r)
        assert h.response_count() == 1
        assert h.latest_response() is r

    def test_events_for_decision(self):
        h  = DecisionPolicyHistory()
        e1 = make_policy_evaluation_started("r1", "d1", "test")
        e2 = make_policy_evaluation_started("r2", "d2", "test")
        h.record_event(e1)
        h.record_event(e2)
        assert len(h.events_for_decision("d1")) == 1

    def test_events_by_type(self):
        h  = DecisionPolicyHistory()
        e1 = make_policy_evaluation_started("r1", "d1", "s")
        e2 = make_policy_blocked("r2", "d2", "s")
        h.record_event(e1)
        h.record_event(e2)
        started_events = h.events_by_type(PolicyEventType.POLICY_EVALUATION_STARTED)
        assert len(started_events) == 1

    def test_bounded_maxlen(self):
        h = DecisionPolicyHistory(max_events=3)
        for i in range(5):
            h.record_event(make_policy_evaluation_started(f"r{i}", f"d{i}", "s"))
        assert h.event_count() == 3

    def test_clear(self):
        h = DecisionPolicyHistory()
        h.record_event(make_policy_evaluation_started("r1", "d1", "s"))
        h.clear()
        assert h.event_count() == 0

    def test_latest_event_none_when_empty(self):
        h = DecisionPolicyHistory()
        assert h.latest_event() is None

    def test_latest_response_none_when_empty(self):
        h = DecisionPolicyHistory()
        assert h.latest_response() is None


# ===========================================================================
# 13 — Event factory functions
# ===========================================================================

class TestEventFactories:

    def test_evaluation_started(self):
        e = make_policy_evaluation_started("r1", "d1", "test", policy_count=5)
        assert e.event_type == PolicyEventType.POLICY_EVALUATION_STARTED
        assert e.payload["policy_count"] == 5

    def test_policy_loaded(self):
        e = make_policy_loaded("r1", "d1", "test", policy_id="pid", policy_name="P")
        assert e.event_type == PolicyEventType.POLICY_LOADED
        assert e.payload["policy_id"] == "pid"

    def test_policy_validated(self):
        e = make_policy_validated("r1", "d1", "test", policy_id="pid", is_valid=True)
        assert e.event_type == PolicyEventType.POLICY_VALIDATED
        assert e.payload["is_valid"] is True

    def test_policy_approved(self):
        e = make_policy_approved("r1", "d1", "test", action="approve")
        assert e.event_type == PolicyEventType.POLICY_APPROVED

    def test_policy_rejected(self):
        e = make_policy_rejected("r1", "d1", "test", reason="too risky")
        assert e.event_type == PolicyEventType.POLICY_REJECTED
        assert e.payload["reason"] == "too risky"

    def test_policy_blocked(self):
        e = make_policy_blocked("r1", "d1", "test")
        assert e.event_type == PolicyEventType.POLICY_BLOCKED

    def test_policy_escalated(self):
        e = make_policy_escalated("r1", "d1", "test")
        assert e.event_type == PolicyEventType.POLICY_ESCALATED

    def test_evaluation_completed(self):
        e = make_policy_evaluation_completed(
            "r1", "d1", "test",
            final_action="approve", evaluation_time_s=0.05, total_evaluated=3,
        )
        assert e.event_type == PolicyEventType.POLICY_EVALUATION_COMPLETED
        assert e.payload["total_evaluated"] == 3

    def test_event_has_unique_ids(self):
        e1 = make_policy_blocked("r1", "d1", "test")
        e2 = make_policy_blocked("r1", "d1", "test")
        assert e1.event_id != e2.event_id

    def test_event_to_dict(self):
        e = make_policy_evaluation_started("r1", "d1", "test")
        d = e.to_dict()
        assert "event_id"   in d
        assert "event_type" in d
        assert d["event_type"] == PolicyEventType.POLICY_EVALUATION_STARTED.value


# ===========================================================================
# 14 — DecisionPolicyFactory
# ===========================================================================

class TestDecisionPolicyFactory:

    def test_create_condition(self, factory):
        c = factory.create_condition("c", "inputs.x", PolicyConditionOperator.GT, 5)
        assert c.name      == "c"
        assert c.threshold == 5

    def test_create_rule(self, factory):
        c = factory.create_condition("c", "inputs.x", PolicyConditionOperator.GT, 0)
        r = factory.create_rule("r", [c], PolicyAction.REJECT)
        assert r.name   == "r"
        assert r.action == PolicyAction.REJECT

    def test_create_policy(self, factory):
        p = factory.create_policy("P", PolicyType.RISK, PolicyPriority.HIGH, PolicyAction.APPROVE)
        assert p.name           == "P"
        assert p.policy_type    == PolicyType.RISK
        assert p.default_action == PolicyAction.APPROVE

    def test_create_context(self, factory):
        ctx = factory.create_context(inputs={"k": "v"})
        assert ctx.inputs["k"] == "v"

    def test_create_request(self, factory):
        ctx = factory.create_context()
        req = factory.create_request(ctx)
        assert req.context is ctx

    def test_create_chain(self, factory):
        chain = factory.create_chain("c", PolicyChainMode.PARALLEL, [])
        assert chain.mode == PolicyChainMode.PARALLEL

    def test_factory_generates_unique_ids(self, factory):
        c1 = factory.create_condition("c", "inputs.x", PolicyConditionOperator.GT, 0)
        c2 = factory.create_condition("c", "inputs.x", PolicyConditionOperator.GT, 0)
        assert c1.condition_id != c2.condition_id


# ===========================================================================
# 15 — DecisionPolicyManager
# ===========================================================================

class TestDecisionPolicyManager:

    def _make_manager(self):
        r = DecisionPolicyRegistry()
        e = DecisionPolicyEvaluator()
        v = DecisionPolicyValidator()
        return DecisionPolicyManager(r, e, v), r

    def test_zero_policies_returns_approve(self):
        m, _ = self._make_manager()
        ctx  = make_context()
        req  = PolicyEvaluationRequest.create(ctx)
        summary, audit = m.evaluate(req)
        assert summary.final_action  == PolicyAction.APPROVE
        assert summary.total_evaluated == 0
        assert summary.coverage == 0.0

    def test_single_approve_policy(self):
        m, reg = self._make_manager()
        p = make_policy(default_action=PolicyAction.APPROVE)
        reg.register(p)
        ctx = make_context()
        req = PolicyEvaluationRequest.create(ctx)
        summary, audit = m.evaluate(req)
        assert summary.final_action  == PolicyAction.APPROVE
        assert summary.total_evaluated == 1

    def test_policy_ids_filter(self):
        m, reg = self._make_manager()
        p1 = make_policy(default_action=PolicyAction.APPROVE)
        p2 = make_policy(default_action=PolicyAction.REJECT)
        reg.register(p1)
        reg.register(p2)
        ctx = make_context()
        req = PolicyEvaluationRequest.create(ctx, policy_ids=[p1.policy_id])
        summary, _ = m.evaluate(req)
        assert summary.total_evaluated == 1
        assert summary.final_action    == PolicyAction.APPROVE

    def test_policy_types_filter(self):
        m, reg = self._make_manager()
        p_risk = make_policy(policy_type=PolicyType.RISK,       default_action=PolicyAction.REJECT)
        p_comp = make_policy(policy_type=PolicyType.COMPLIANCE, default_action=PolicyAction.APPROVE)
        reg.register(p_risk)
        reg.register(p_comp)
        ctx = make_context()
        req = PolicyEvaluationRequest.create(ctx, policy_types=[PolicyType.COMPLIANCE])
        summary, _ = m.evaluate(req)
        assert summary.total_evaluated == 1
        assert summary.final_action    == PolicyAction.APPROVE

    def test_explicit_deny_wins(self):
        m, reg = self._make_manager()
        p1 = make_policy(default_action=PolicyAction.APPROVE, priority=PolicyPriority.HIGH)
        p2 = make_policy(default_action=PolicyAction.BLOCK,   priority=PolicyPriority.MEDIUM)
        reg.register(p1)
        reg.register(p2)
        ctx     = make_context()
        req     = PolicyEvaluationRequest.create(ctx, conflict_strategy=ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES)
        summary, _ = m.evaluate(req)
        assert summary.final_action == PolicyAction.BLOCK

    def test_coverage_fraction(self):
        m, reg = self._make_manager()
        p1 = make_policy()
        p2 = make_policy()
        reg.register(p1)
        reg.register(p2)
        ctx = make_context()
        req = PolicyEvaluationRequest.create(ctx)
        summary, _ = m.evaluate(req)
        assert summary.coverage == 1.0   # all 2 evaluated / 2 registered


# ===========================================================================
# 16 — DecisionPolicyEngine (full lifecycle)
# ===========================================================================

class TestDecisionPolicyEngine:

    def test_evaluate_not_running_raises(self):
        e   = DecisionPolicyEngine()
        ctx = make_context()
        req = PolicyEvaluationRequest.create(ctx)
        with pytest.raises(PolicyEngineNotRunningError):
            e.evaluate(req)

    def test_start_stop_lifecycle(self, engine):
        assert engine.lifecycle_state() in ("running",)
        engine.stop()
        assert engine.lifecycle_state() not in ("running",)

    def test_register_and_list(self, engine):
        p = make_policy(policy_type=PolicyType.RISK)
        engine.register_policy(p)
        all_p = engine.list_policies()
        risk_p = engine.list_policies(PolicyType.RISK)
        assert p in all_p
        assert p in risk_p

    def test_deregister_policy(self, engine):
        p = make_policy()
        engine.register_policy(p)
        assert engine.deregister_policy(p.policy_id) is True
        assert engine.get_policy(p.policy_id) is None

    def test_deregister_missing_returns_false(self, engine):
        assert engine.deregister_policy("ghost") is False

    def test_evaluate_approve_by_default(self, engine):
        ctx  = make_context()
        req  = PolicyEvaluationRequest.create(ctx)
        resp = engine.evaluate(req)
        assert resp.is_success
        assert resp.action == PolicyAction.APPROVE

    def test_evaluate_with_reject_policy(self, engine):
        c = make_condition("c", "inputs.risk", PolicyConditionOperator.GT, 50)
        r = PolicyRule.create("r", [c], PolicyAction.REJECT)
        p = make_policy(rules=[r], default_action=PolicyAction.APPROVE)
        engine.register_policy(p)
        ctx  = make_context({"risk": 80})
        resp = engine.evaluate(PolicyEvaluationRequest.create(ctx))
        assert resp.action == PolicyAction.REJECT
        assert resp.is_rejected

    def test_evaluate_captures_error_in_response(self, engine):
        """Engine must not raise on policy-level errors."""
        ctx = make_context()
        req = PolicyEvaluationRequest.create(ctx)
        # Patch manager to raise
        original = engine._manager.evaluate
        def boom(req):
            raise RuntimeError("internal failure")
        engine._manager.evaluate = boom
        resp = engine.evaluate(req)
        assert resp.is_success is False
        assert "internal failure" in resp.error
        engine._manager.evaluate = original

    def test_statistics_updated_after_evaluation(self, engine):
        ctx  = make_context()
        req  = PolicyEvaluationRequest.create(ctx)
        engine.evaluate(req)
        s = engine.statistics().snapshot()
        assert s["policies_evaluated"] == 1

    def test_history_records_events_and_response(self, engine):
        ctx  = make_context()
        req  = PolicyEvaluationRequest.create(ctx)
        engine.evaluate(req)
        assert engine.history().event_count()    >= 1
        assert engine.history().response_count() == 1

    def test_add_and_call_listener(self, engine):
        received = []
        engine.add_listener(received.append)
        ctx = make_context()
        req = PolicyEvaluationRequest.create(ctx)
        engine.evaluate(req)
        assert len(received) >= 1

    def test_remove_listener(self, engine):
        received = []
        cb = received.append
        engine.add_listener(cb)
        engine.remove_listener(cb)
        engine.evaluate(PolicyEvaluationRequest.create(make_context()))
        assert len(received) == 0

    def test_listener_exception_does_not_crash_evaluation(self, engine):
        def bad_listener(ev):
            raise RuntimeError("bad")
        engine.add_listener(bad_listener)
        resp = engine.evaluate(PolicyEvaluationRequest.create(make_context()))
        assert resp.is_success

    def test_health_dict_structure(self, engine):
        h = engine.health()
        assert "engine_id"     in h
        assert "is_healthy"    in h
        assert "policy_count"  in h
        assert h["is_healthy"] is True

    def test_status_dict_structure(self, engine):
        s = engine.status()
        assert "state"   in s
        assert "version" in s

    def test_concurrent_evaluations(self, engine):
        p = make_policy(default_action=PolicyAction.APPROVE)
        engine.register_policy(p)
        results = []
        errors  = []
        def work():
            try:
                ctx  = make_context()
                req  = PolicyEvaluationRequest.create(ctx)
                resp = engine.evaluate(req)
                results.append(resp.action)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=work) for _ in range(30)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert len(results) == 30

    def test_multiple_policies_summary(self, engine):
        p1 = make_policy(name="P1", default_action=PolicyAction.APPROVE, priority=PolicyPriority.HIGH)
        p2 = make_policy(name="P2", default_action=PolicyAction.APPROVE, priority=PolicyPriority.LOW)
        engine.register_policy(p1)
        engine.register_policy(p2)
        resp = engine.evaluate(PolicyEvaluationRequest.create(make_context()))
        assert resp.summary is not None
        assert resp.summary.total_evaluated == 2

    def test_audit_report_in_response(self, engine):
        p = make_policy(default_action=PolicyAction.REJECT)
        engine.register_policy(p)
        resp = engine.evaluate(PolicyEvaluationRequest.create(make_context()))
        assert resp.audit_report is not None
        assert isinstance(resp.audit_report, PolicyAuditReport)


# ===========================================================================
# 17 — PolicyFrameworkAdapter (M2 bridge)
# ===========================================================================

class TestPolicyFrameworkAdapter:

    def test_adapter_evaluate_returns_dict(self, engine):
        adapter = PolicyFrameworkAdapter(engine)
        mock_ctx = MagicMock()
        mock_ctx.request_id  = "r1"
        mock_ctx.decision_id = "d1"
        mock_ctx.session_id  = "s1"
        mock_ctx.pipeline_id = "p1"
        mock_ctx.inputs      = {}
        mock_ctx.metadata    = {}
        result = adapter.evaluate(mock_ctx, {})
        assert "action"      in result
        assert "is_approved" in result
        assert "is_rejected" in result
        assert "is_blocked"  in result
        assert "response_id" in result

    def test_adapter_passes_inputs(self, engine):
        c = make_condition("c", "inputs.x", PolicyConditionOperator.GT, 5)
        r = PolicyRule.create("r", [c], PolicyAction.REJECT)
        p = make_policy(rules=[r])
        engine.register_policy(p)

        adapter  = PolicyFrameworkAdapter(engine)
        mock_ctx = MagicMock()
        mock_ctx.request_id  = "r2"
        mock_ctx.decision_id = "d2"
        mock_ctx.session_id  = ""
        mock_ctx.pipeline_id = ""
        mock_ctx.inputs      = {}
        mock_ctx.metadata    = {}
        result = adapter.evaluate(mock_ctx, {"x": 10})
        assert result["action"] == "reject"

    def test_adapter_is_success_when_engine_running(self, engine):
        adapter  = PolicyFrameworkAdapter(engine)
        mock_ctx = MagicMock()
        mock_ctx.request_id  = "r3"
        mock_ctx.decision_id = "d3"
        mock_ctx.session_id  = ""
        mock_ctx.pipeline_id = ""
        mock_ctx.inputs      = {}
        mock_ctx.metadata    = {}
        result = adapter.evaluate(mock_ctx, {})
        assert result["is_approved"] is True


# ===========================================================================
# 18 — Regression & interface contracts
# ===========================================================================

class TestRegressionContracts:

    def test_policy_types_count(self):
        assert len(PolicyType) == 15

    def test_policy_actions_count(self):
        assert len(PolicyAction) == 7

    def test_policy_priority_count(self):
        assert len(PolicyPriority) == 5

    def test_policy_chain_modes_count(self):
        assert len(PolicyChainMode) == 6

    def test_conflict_resolution_strategies_count(self):
        assert len(ConflictResolutionStrategy) == 3

    def test_policy_event_types_count(self):
        assert len(PolicyEventType) == 8

    def test_policy_validation_codes_count(self):
        assert len(PolicyValidationCode) == 6

    def test_action_precedence_complete(self):
        from iios.decision.policies import ACTION_PRECEDENCE
        assert len(ACTION_PRECEDENCE) == 7
        for action in PolicyAction:
            assert action in ACTION_PRECEDENCE

    def test_deny_actions_are_block_and_reject(self):
        from iios.decision.policies import DENY_ACTIONS
        assert PolicyAction.BLOCK  in DENY_ACTIONS
        assert PolicyAction.REJECT in DENY_ACTIONS

    def test_approval_actions_include_conditional(self):
        from iios.decision.policies import APPROVAL_ACTIONS
        assert PolicyAction.APPROVE                 in APPROVAL_ACTIONS
        assert PolicyAction.APPROVE_WITH_CONDITIONS in APPROVAL_ACTIONS

    def test_escalation_actions_include_manual_review(self):
        from iios.decision.policies import ESCALATION_ACTIONS
        assert PolicyAction.ESCALATE               in ESCALATION_ACTIONS
        assert PolicyAction.REQUIRE_MANUAL_REVIEW  in ESCALATION_ACTIONS

    def test_engine_system_id(self):
        assert DecisionPolicyEngine.SYSTEM_ID == "iios:decision:policies"

    def test_failure_response_is_blocked(self):
        from iios.decision.policies import DecisionPolicyResponse
        r = DecisionPolicyResponse.failure("r1", "d1", "oops")
        assert r.is_success is False
        assert r.action     == PolicyAction.BLOCK
        assert r.error      == "oops"

    def test_summary_properties(self):
        from iios.decision.policies import APPROVAL_ACTIONS
        s = PolicyEvaluationSummary(
            summary_id                   = "s1",
            request_id                   = "r1",
            decision_id                  = "d1",
            final_action                 = PolicyAction.APPROVE,
            policy_results               = (),
            total_evaluated              = 0,
            approved_count               = 0,
            rejected_count               = 0,
            blocked_count                = 0,
            escalated_count              = 0,
            deferred_count               = 0,
            manual_review_count          = 0,
            conditions                   = (),
            conflict_resolution_applied  = False,
            conflict_resolution_strategy = ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES,
            evaluation_time_s            = 0.0,
            coverage                     = 0.0,
            evaluated_at                 = datetime.now(timezone.utc),
        )
        assert s.is_approved          is True
        assert s.is_rejected          is False
        assert s.is_blocked           is False
        assert s.requires_escalation  is False

    def test_policy_evaluation_request_create(self):
        ctx = make_context()
        req = PolicyEvaluationRequest.create(ctx, chain_mode=PolicyChainMode.PARALLEL)
        assert req.chain_mode == PolicyChainMode.PARALLEL
        assert req.context    is ctx

    def test_engine_not_running_error_code(self):
        err = PolicyEngineNotRunningError()
        assert err.error_code == "DP-008"

    def test_policy_not_found_error_has_policy_id(self):
        err = PolicyNotFoundError("p123")
        assert err.policy_id == "p123"
        assert err.error_code == "DP-001"
