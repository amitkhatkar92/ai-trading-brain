"""
tests/unit/portfolio/policies/test_policies.py
===============================================
Comprehensive unit tests for the Portfolio Policy Framework (C10 M3).

Coverage targets:
- constants, enums, severity ordering
- exceptions (all 10 subclasses)
- PolicyContext / PortfolioPolicyRequest
- PolicyCondition / PolicyConditionResult
- PolicyRule / PolicyRuleResult
- PortfolioPolicy / PolicyOutcome
- PolicyPriorityResolver (all 3 strategies)
- PolicyEvaluationSummary / PortfolioPolicyResult
- PortfolioPolicyResponse (all factories, all properties)
- PolicyAuditEntry / PortfolioPolicyAuditReport
- PolicyEngineEvent / all 8 factories
- PortfolioPolicyStatistics
- PortfolioPolicyHistory (bounded, queries)
- PolicyChain (sequential, parallel, composite, stop_on_block)
- PortfolioPolicyEvaluator (full evaluation, filtering, exceptions)
- PolicyValidationCheckResult / PolicyValidationResult / PortfolioPolicyValidator
- PortfolioPolicyRegistry (CRUD, capacity, deactivate, deprecate)
- PortfolioPolicyFactory (all builders)
- PortfolioPolicyManager (full workflow, validation failure, evaluator error)
- PortfolioPolicyEngine (guard, register, submit, evaluate, listeners, status,
                         statistics, health, history, concurrency, all types)
- All 15 PolicyType values
- All 7 PolicyAction values
- All 5 PolicyPriority values
- All 8 PolicyEventType values
"""
from __future__ import annotations

import threading
import time
from typing import List

import pytest

from iios.portfolio.policies import (
    # Engine / primary interface
    PortfolioPolicyEngine,
    PolicyEngineStatus,
    # Manager
    PortfolioPolicyManager,
    # Request / response
    PortfolioPolicyRequest,
    PortfolioPolicyResponse,
    # Result
    PortfolioPolicyResult,
    PolicyEvaluationSummary,
    # Context
    PolicyContext,
    # Domain objects
    PolicyCondition,
    PolicyConditionResult,
    PolicyRule,
    PolicyRuleResult,
    PortfolioPolicy,
    PolicyOutcome,
    # Priority resolver
    PolicyPriorityResolver,
    # Audit
    PolicyAuditEntry,
    PortfolioPolicyAuditReport,
    # Events
    PolicyEngineEvent,
    make_policy_evaluation_started,
    make_policy_loaded,
    make_policy_validated,
    make_policy_approved,
    make_policy_rejected,
    make_policy_blocked,
    make_policy_escalated,
    make_policy_evaluation_completed,
    # Statistics / history
    PortfolioPolicyStatistics,
    PortfolioPolicyHistory,
    # Chain
    PolicyChain,
    # Evaluator / validator
    PortfolioPolicyEvaluator,
    PortfolioPolicyValidator,
    PolicyValidationCheckResult,
    PolicyValidationResult,
    # Registry / factory
    PortfolioPolicyRegistry,
    PortfolioPolicyFactory,
    # Enums / constants
    PolicyAction,
    PolicyChainMode,
    PolicyConflictResolution,
    PolicyEventType,
    PolicyPriority,
    PolicyStatus,
    PolicyType,
    ACTION_SEVERITY,
    APPROVAL_ACTIONS,
    BLOCKING_ACTIONS,
    ESCALATION_ACTIONS,
    # Exceptions
    PortfolioPolicyError,
    PortfolioPolicyNotFoundError,
    PortfolioPolicyNotRunningError,
    PortfolioPolicyConfigurationError,
    PortfolioPolicyEvaluationError,
    PortfolioPolicyConflictError,
    PortfolioPolicyValidationError,
    PortfolioPolicyAuditError,
    PortfolioPolicyCapacityError,
    PortfolioPolicyChainError,
)


# ===========================================================================
# Test helpers
# ===========================================================================

def _pass_condition(name: str = "pass") -> PolicyCondition:
    return PolicyCondition(name, lambda _: True)


def _fail_condition(name: str = "fail") -> PolicyCondition:
    return PolicyCondition(name, lambda _: False)


def _raise_condition(name: str = "raise") -> PolicyCondition:
    def _fn(inputs):
        raise RuntimeError("condition explosion")
    return PolicyCondition(name, _fn)


def _approve_rule(rule_id: str = "r-pass") -> PolicyRule:
    return PolicyRule(rule_id, "approve_rule", [_pass_condition()],
                      PolicyAction.APPROVE, PolicyAction.REJECT)


def _reject_rule(rule_id: str = "r-fail") -> PolicyRule:
    return PolicyRule(rule_id, "reject_rule", [_fail_condition()],
                      PolicyAction.APPROVE, PolicyAction.REJECT)


def _block_rule(rule_id: str = "r-block") -> PolicyRule:
    return PolicyRule(rule_id, "block_rule", [_fail_condition()],
                      PolicyAction.APPROVE, PolicyAction.BLOCK)


def _approve_policy(
    policy_id: str = "pol-approve",
    policy_type: PolicyType = PolicyType.RISK,
    priority: PolicyPriority = PolicyPriority.MEDIUM,
) -> PortfolioPolicy:
    return PortfolioPolicy(policy_id, f"Policy {policy_id}", policy_type,
                           priority, [_approve_rule()])


def _reject_policy(
    policy_id: str = "pol-reject",
    policy_type: PolicyType = PolicyType.RISK,
    priority: PolicyPriority = PolicyPriority.MEDIUM,
) -> PortfolioPolicy:
    return PortfolioPolicy(policy_id, f"Policy {policy_id}", policy_type,
                           priority, [_reject_rule()])


def _block_policy(
    policy_id: str = "pol-block",
    policy_type: PolicyType = PolicyType.RISK,
    priority: PolicyPriority = PolicyPriority.HIGH,
) -> PortfolioPolicy:
    return PortfolioPolicy(policy_id, f"Policy {policy_id}", policy_type,
                           priority, [_block_rule()])


def _request(
    portfolio_id: str = "pf-001",
    policy_types: list = None,
    **kw,
) -> PortfolioPolicyRequest:
    return PortfolioPolicyRequest.create(portfolio_id, policy_types, **kw)


def _started_engine(**kw) -> PortfolioPolicyEngine:
    e = PortfolioPolicyEngine(**kw)
    e.start()
    return e


# ===========================================================================
# Constants
# ===========================================================================

class TestConstants:
    def test_action_severity_lower_is_more_restrictive(self):
        assert ACTION_SEVERITY[PolicyAction.BLOCK]   < ACTION_SEVERITY[PolicyAction.REJECT]
        assert ACTION_SEVERITY[PolicyAction.REJECT]  < ACTION_SEVERITY[PolicyAction.ESCALATE]
        assert ACTION_SEVERITY[PolicyAction.APPROVE] > ACTION_SEVERITY[PolicyAction.BLOCK]

    def test_blocking_actions(self):
        assert PolicyAction.BLOCK  in BLOCKING_ACTIONS
        assert PolicyAction.REJECT in BLOCKING_ACTIONS
        assert PolicyAction.APPROVE not in BLOCKING_ACTIONS

    def test_approval_actions(self):
        assert PolicyAction.APPROVE                 in APPROVAL_ACTIONS
        assert PolicyAction.APPROVE_WITH_CONDITIONS in APPROVAL_ACTIONS
        assert PolicyAction.REJECT                  not in APPROVAL_ACTIONS

    def test_escalation_actions(self):
        assert PolicyAction.ESCALATE            in ESCALATION_ACTIONS
        assert PolicyAction.REQUIRE_MANUAL_REVIEW in ESCALATION_ACTIONS

    def test_all_policy_types(self):
        assert len(list(PolicyType)) == 15

    def test_all_policy_actions(self):
        assert len(list(PolicyAction)) == 7

    def test_all_priorities(self):
        assert len(list(PolicyPriority)) == 5

    def test_priority_ordering_critical_lowest(self):
        assert int(PolicyPriority.CRITICAL) < int(PolicyPriority.HIGH)
        assert int(PolicyPriority.HIGH)     < int(PolicyPriority.MEDIUM)

    def test_all_event_types(self):
        assert len(list(PolicyEventType)) == 8


# ===========================================================================
# Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert isinstance(PortfolioPolicyError("x"), IIOSError)
        assert PortfolioPolicyError("x").error_code == "PP-000"

    def test_not_found(self):
        e = PortfolioPolicyNotFoundError("p1")
        assert e.error_code == "PP-001"
        assert e.policy_id  == "p1"

    def test_not_running(self):
        e = PortfolioPolicyNotRunningError()
        assert e.error_code == "PP-002"

    def test_configuration_error(self):
        e = PortfolioPolicyConfigurationError("bad", field="priority")
        assert e.error_code == "PP-003"
        assert e.field       == "priority"

    def test_evaluation_error(self):
        e = PortfolioPolicyEvaluationError("failed", evaluation_id="ev1")
        assert e.error_code     == "PP-004"
        assert e.evaluation_id  == "ev1"

    def test_conflict_error(self):
        e = PortfolioPolicyConflictError("conflict", conflicting_policies=("a", "b"))
        assert e.error_code            == "PP-005"
        assert e.conflicting_policies  == ("a", "b")

    def test_validation_error(self):
        e = PortfolioPolicyValidationError("invalid", failed_checks=("c1",))
        assert e.error_code    == "PP-006"
        assert e.failed_checks == ("c1",)

    def test_audit_error(self):
        e = PortfolioPolicyAuditError("audit fail")
        assert e.error_code == "PP-007"

    def test_capacity_error(self):
        e = PortfolioPolicyCapacityError(100)
        assert e.error_code == "PP-008"
        assert e.limit       == 100

    def test_chain_error(self):
        e = PortfolioPolicyChainError("chain fail", chain_id="c1")
        assert e.error_code == "PP-009"
        assert e.chain_id   == "c1"


# ===========================================================================
# PolicyContext
# ===========================================================================

class TestPolicyContext:
    def test_create_defaults(self):
        ctx = PolicyContext.create("pf-001")
        assert ctx.portfolio_id == "pf-001"
        assert ctx.priority     == PolicyPriority.MEDIUM
        assert ctx.context_id         # UUID

    def test_create_custom(self):
        ctx = PolicyContext.create(
            "pf-002",
            policy_types = [PolicyType.RISK, PolicyType.COMPLIANCE],
            priority     = PolicyPriority.HIGH,
            source       = "test-src",
        )
        assert PolicyType.RISK       in ctx.policy_types
        assert PolicyType.COMPLIANCE in ctx.policy_types
        assert ctx.priority          == PolicyPriority.HIGH

    def test_to_dict(self):
        ctx = PolicyContext.create("pf-003", policy_types=[PolicyType.LIQUIDITY])
        d   = ctx.to_dict()
        assert d["portfolio_id"]  == "pf-003"
        assert "liquidity"        in d["policy_types"]
        assert "priority"         in d

    def test_frozen(self):
        ctx = PolicyContext.create("pf-004")
        with pytest.raises((AttributeError, TypeError)):
            ctx.portfolio_id = "mutated"  # type: ignore[misc]


# ===========================================================================
# PortfolioPolicyRequest
# ===========================================================================

class TestPortfolioPolicyRequest:
    def test_create_defaults(self):
        req = PortfolioPolicyRequest.create("pf-001")
        assert req.portfolio_id   == "pf-001"
        assert req.priority       == PolicyPriority.MEDIUM
        assert req.request_id          # UUID
        assert isinstance(req.inputs, dict)
        assert len(req.policy_types)   == 0   # empty = all policies

    def test_create_with_policy_types(self):
        req = PortfolioPolicyRequest.create(
            "pf-002",
            [PolicyType.RISK, PolicyType.COMPLIANCE],
        )
        assert PolicyType.RISK in req.policy_types

    def test_with_inputs(self):
        req  = PortfolioPolicyRequest.create("pf-003")
        req2 = req.with_inputs({"decision_snapshot": {"score": 9.0}})
        assert "decision_snapshot" in req2.inputs
        assert req2.request_id == req.request_id

    def test_to_dict(self):
        req = PortfolioPolicyRequest.create("pf-004", inputs={"k": 1})
        d   = req.to_dict()
        assert d["portfolio_id"] == "pf-004"
        assert "k" in d["input_keys"]

    def test_frozen(self):
        req = PortfolioPolicyRequest.create("pf-005")
        with pytest.raises((AttributeError, TypeError)):
            req.portfolio_id = "mutated"  # type: ignore[misc]


# ===========================================================================
# PolicyCondition
# ===========================================================================

class TestPolicyCondition:
    def test_pass(self):
        c   = _pass_condition("c1")
        res = c.evaluate({})
        assert res.passed
        assert res.condition_name == "c1"

    def test_fail(self):
        c   = _fail_condition("c2")
        res = c.evaluate({})
        assert not res.passed
        assert res.condition_name == "c2"

    def test_exception_is_treated_as_fail(self):
        c   = _raise_condition("c3")
        res = c.evaluate({})
        assert not res.passed
        assert "exception" in res.message

    def test_threshold_stored(self):
        c   = PolicyCondition("t", lambda _: True, threshold=7.0)
        res = c.evaluate({})
        assert res.threshold == 7.0

    def test_inputs_passed_to_fn(self):
        captured = {}
        def fn(inputs):
            captured.update(inputs)
            return True
        c = PolicyCondition("capture", fn)
        c.evaluate({"score": 8.0})
        assert captured.get("score") == 8.0

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            PolicyCondition("", lambda _: True)

    def test_non_callable_raises(self):
        with pytest.raises(TypeError):
            PolicyCondition("x", "not_callable")  # type: ignore

    def test_condition_result_to_dict(self):
        r = PolicyConditionResult("cond", True, value=5.0, threshold=4.0, message="ok")
        d = r.to_dict()
        assert d["condition_name"] == "cond"
        assert d["passed"]         is True


# ===========================================================================
# PolicyRule
# ===========================================================================

class TestPolicyRule:
    def test_all_conditions_pass(self):
        rule   = _approve_rule()
        result = rule.evaluate({})
        assert result.action == PolicyAction.APPROVE
        assert len(result.conditions_passed) == 1
        assert len(result.conditions_failed) == 0

    def test_condition_fails(self):
        rule   = _reject_rule()
        result = rule.evaluate({})
        assert result.action == PolicyAction.REJECT
        assert len(result.conditions_failed) == 1

    def test_block_on_fail(self):
        rule   = _block_rule()
        result = rule.evaluate({})
        assert result.action == PolicyAction.BLOCK

    def test_no_conditions_trivially_passes(self):
        rule   = PolicyRule("r0", "empty", [], PolicyAction.APPROVE, PolicyAction.REJECT)
        result = rule.evaluate({})
        assert result.action == PolicyAction.APPROVE
        assert "trivially" in result.reason

    def test_mixed_conditions(self):
        rule = PolicyRule(
            "r1", "mixed",
            [_pass_condition("p"), _fail_condition("f")],
            PolicyAction.APPROVE,
            PolicyAction.REJECT,
        )
        result = rule.evaluate({})
        assert result.action == PolicyAction.REJECT
        assert len(result.conditions_passed) == 1
        assert len(result.conditions_failed) == 1

    def test_rule_result_to_dict(self):
        rule   = _approve_rule()
        result = rule.evaluate({})
        d      = result.to_dict()
        assert d["action"]   == "approve"
        assert d["rule_name"] == "approve_rule"

    def test_elapsed_s_positive(self):
        rule   = _approve_rule()
        result = rule.evaluate({})
        assert result.elapsed_s >= 0.0


# ===========================================================================
# PortfolioPolicy
# ===========================================================================

class TestPortfolioPolicy:
    def test_approve_with_passing_rule(self):
        p   = _approve_policy()
        out = p.evaluate({})
        assert out.action == PolicyAction.APPROVE

    def test_reject_with_failing_rule(self):
        p   = _reject_policy()
        out = p.evaluate({})
        assert out.action == PolicyAction.REJECT

    def test_block_action(self):
        p   = _block_policy()
        out = p.evaluate({})
        assert out.action == PolicyAction.BLOCK

    def test_no_rules_approves(self):
        p   = PortfolioPolicy("p0", "empty", PolicyType.RISK)
        out = p.evaluate({})
        assert out.action == PolicyAction.APPROVE
        assert out.rules_evaluated == 0

    def test_most_restrictive_action_wins(self):
        p = PortfolioPolicy(
            "p-multi", "multi", PolicyType.RISK,
            rules=[_approve_rule(), _block_rule()],
        )
        out = p.evaluate({})
        assert out.action == PolicyAction.BLOCK

    def test_deactivate(self):
        p = _approve_policy()
        assert p.is_active
        p.deactivate()
        assert not p.is_active
        assert p.status == PolicyStatus.INACTIVE

    def test_activate_after_deactivate(self):
        p = _approve_policy()
        p.deactivate()
        p.activate()
        assert p.is_active

    def test_deprecate(self):
        p = _approve_policy()
        p.deprecate()
        assert p.status == PolicyStatus.DEPRECATED
        assert not p.is_active

    def test_outcome_to_dict(self):
        out = _approve_policy().evaluate({})
        d   = out.to_dict()
        assert d["action"]     == "approve"
        assert "policy_type"   in d
        assert "priority"      in d

    def test_outcome_fields(self):
        out = _approve_policy("p1", PolicyType.COMPLIANCE, PolicyPriority.HIGH)
        assert out.policy_id   == "p1"
        assert out.policy_type == PolicyType.COMPLIANCE
        assert out.priority    == PolicyPriority.HIGH

    def test_conditions_counted(self):
        rule = PolicyRule("r", "r", [_pass_condition("a"), _pass_condition("b")],
                          PolicyAction.APPROVE, PolicyAction.REJECT)
        p   = PortfolioPolicy("p", "p", PolicyType.RISK, rules=[rule])
        out = p.evaluate({})
        assert out.conditions_passed == 2
        assert out.conditions_failed == 0


# ===========================================================================
# PolicyPriorityResolver
# ===========================================================================

class TestPolicyPriorityResolver:
    def _outcome(
        self,
        action:   PolicyAction,
        priority: PolicyPriority = PolicyPriority.MEDIUM,
        policy_id: str = "p",
    ):
        return _approve_policy(policy_id).evaluate({}) if action == PolicyAction.APPROVE else \
               _reject_policy(policy_id).evaluate({}) if action == PolicyAction.REJECT else \
               _block_policy(policy_id).evaluate({})

    def _make_outcome(self, action: PolicyAction, priority: PolicyPriority, policy_id="p"):
        """Helper that builds a real PolicyOutcome without going through evaluate()."""
        p = PortfolioPolicy(policy_id, "p", PolicyType.RISK, priority, [])
        # Patch: return a synthesized outcome with the desired action
        from iios.portfolio.policies.portfolio_policy import PolicyOutcome
        import time
        return PolicyOutcome(
            policy_id=policy_id, policy_name="p",
            policy_type=PolicyType.RISK, action=action,
            priority=priority, rules_evaluated=0,
            conditions_passed=0, conditions_failed=0,
            reason="test", rule_results=(),
            elapsed_s=0.0, evaluated_at=time.time(),
        )

    def test_empty_resolves_to_approve(self):
        r = PolicyPriorityResolver()
        assert r.resolve([]) == PolicyAction.APPROVE

    def test_deny_overrides_block_wins(self):
        r  = PolicyPriorityResolver(PolicyConflictResolution.DENY_OVERRIDES)
        o1 = self._make_outcome(PolicyAction.APPROVE, PolicyPriority.HIGH)
        o2 = self._make_outcome(PolicyAction.BLOCK,   PolicyPriority.LOW)
        assert r.resolve([o1, o2]) == PolicyAction.BLOCK

    def test_deny_overrides_reject_wins_over_approve(self):
        r  = PolicyPriorityResolver(PolicyConflictResolution.DENY_OVERRIDES)
        o1 = self._make_outcome(PolicyAction.APPROVE, PolicyPriority.HIGH)
        o2 = self._make_outcome(PolicyAction.REJECT,  PolicyPriority.MEDIUM)
        assert r.resolve([o1, o2]) == PolicyAction.REJECT

    def test_deny_overrides_critical_policy_wins(self):
        r  = PolicyPriorityResolver(PolicyConflictResolution.DENY_OVERRIDES)
        o1 = self._make_outcome(PolicyAction.APPROVE, PolicyPriority.LOW)
        o2 = self._make_outcome(PolicyAction.REJECT,  PolicyPriority.CRITICAL)
        assert r.resolve([o1, o2]) == PolicyAction.REJECT

    def test_priority_wins_uses_highest_priority(self):
        r  = PolicyPriorityResolver(PolicyConflictResolution.PRIORITY_WINS)
        o1 = self._make_outcome(PolicyAction.APPROVE, PolicyPriority.HIGH)
        o2 = self._make_outcome(PolicyAction.REJECT,  PolicyPriority.LOW)
        # HIGH has lower int value → wins
        assert r.resolve([o1, o2]) == PolicyAction.APPROVE

    def test_priority_wins_critical_overrides(self):
        r  = PolicyPriorityResolver(PolicyConflictResolution.PRIORITY_WINS)
        o1 = self._make_outcome(PolicyAction.APPROVE, PolicyPriority.LOW)
        o2 = self._make_outcome(PolicyAction.BLOCK,   PolicyPriority.CRITICAL)
        assert r.resolve([o1, o2]) == PolicyAction.BLOCK

    def test_escalation_overrides_strategy(self):
        r  = PolicyPriorityResolver(PolicyConflictResolution.ESCALATION_OVERRIDES)
        o1 = self._make_outcome(PolicyAction.APPROVE,   PolicyPriority.HIGH)
        o2 = self._make_outcome(PolicyAction.ESCALATE,  PolicyPriority.MEDIUM)
        assert r.resolve([o1, o2]) == PolicyAction.ESCALATE

    def test_escalation_overrides_block_still_wins(self):
        r  = PolicyPriorityResolver(PolicyConflictResolution.ESCALATION_OVERRIDES)
        o1 = self._make_outcome(PolicyAction.ESCALATE, PolicyPriority.HIGH)
        o2 = self._make_outcome(PolicyAction.BLOCK,    PolicyPriority.LOW)
        assert r.resolve([o1, o2]) == PolicyAction.BLOCK

    def test_sort_by_priority(self):
        r  = PolicyPriorityResolver()
        o1 = self._make_outcome(PolicyAction.APPROVE, PolicyPriority.LOW)
        o2 = self._make_outcome(PolicyAction.REJECT,  PolicyPriority.CRITICAL)
        sorted_ = r.sort_by_priority([o1, o2])
        assert sorted_[0].priority == PolicyPriority.CRITICAL


# ===========================================================================
# PolicyEvaluationSummary / PortfolioPolicyResult
# ===========================================================================

class TestPolicyResult:
    def _make_summary(self, final_action: PolicyAction) -> PolicyEvaluationSummary:
        return PolicyEvaluationSummary(
            evaluation_id       = "ev-1",
            portfolio_id        = "pf-001",
            final_action        = final_action,
            total_policies      = 2,
            approved_count      = 1,
            conditional_count   = 0,
            rejected_count      = 0,
            blocked_count       = 1 if final_action == PolicyAction.BLOCK else 0,
            escalated_count     = 0,
            deferred_count      = 0,
            manual_review_count = 0,
            elapsed_s           = 0.1,
            evaluated_at        = time.time(),
        )

    def test_summary_is_approved(self):
        s = self._make_summary(PolicyAction.APPROVE)
        assert s.is_approved

    def test_summary_is_blocked(self):
        s = self._make_summary(PolicyAction.BLOCK)
        assert s.is_blocked
        assert not s.is_approved

    def test_summary_is_rejected(self):
        s = self._make_summary(PolicyAction.REJECT)
        assert s.is_rejected

    def test_summary_to_dict(self):
        s = self._make_summary(PolicyAction.APPROVE)
        d = s.to_dict()
        assert d["final_action"] == "approve"
        assert "total_policies"  in d

    def test_evaluator_produces_result(self):
        ev   = PortfolioPolicyEvaluator()
        req  = _request()
        pol  = _approve_policy()
        res  = ev.evaluate(req, [pol])
        assert isinstance(res, PortfolioPolicyResult)
        assert res.final_action == PolicyAction.APPROVE
        assert res.outcome_count == 1

    def test_result_to_dict(self):
        ev  = PortfolioPolicyEvaluator()
        req = _request()
        res = ev.evaluate(req, [_approve_policy()])
        d   = res.to_dict()
        assert d["final_action"]  == "approve"
        assert "outcomes"         in d
        assert len(d["outcomes"]) == 1


# ===========================================================================
# PortfolioPolicyResponse
# ===========================================================================

class TestPortfolioPolicyResponse:
    def _make_result(self, action: PolicyAction) -> PortfolioPolicyResult:
        ev  = PortfolioPolicyEvaluator()
        pol = _approve_policy() if action == PolicyAction.APPROVE else _block_policy()
        return ev.evaluate(_request(), [pol])

    def test_create_success_approve(self):
        result = self._make_result(PolicyAction.APPROVE)
        r = PortfolioPolicyResponse.create_success("req-1", "pf-001", result)
        assert r.is_approved
        assert not r.is_failure
        assert r.has_result
        assert r.final_action == PolicyAction.APPROVE

    def test_create_success_block(self):
        result = self._make_result(PolicyAction.BLOCK)
        r = PortfolioPolicyResponse.create_success("req-2", "pf-001", result)
        assert r.is_blocked
        assert not r.is_approved
        assert not r.is_failure

    def test_create_failure(self):
        r = PortfolioPolicyResponse.create_failure(
            "req-3", "pf-001", "engine exploded"
        )
        assert r.is_failure
        assert r.is_error
        assert r.error_message == "engine exploded"
        assert not r.has_result

    def test_requires_escalation(self):
        from iios.portfolio.policies.portfolio_policy_result import _build_summary
        import uuid, time as _time
        outcomes = []
        summary = _build_summary("ev", "pf", PolicyAction.ESCALATE, outcomes, 0.1)
        result  = PortfolioPolicyResult(
            result_id="r", evaluation_id="ev", portfolio_id="pf",
            final_action=PolicyAction.ESCALATE, outcomes=(), summary=summary,
            elapsed_s=0.1, evaluated_at=_time.time(),
        )
        r = PortfolioPolicyResponse.create_success("req", "pf", result)
        assert r.requires_escalation

    def test_requires_manual_review(self):
        from iios.portfolio.policies.portfolio_policy_result import _build_summary
        import time as _time
        summary = _build_summary("ev", "pf", PolicyAction.REQUIRE_MANUAL_REVIEW, [], 0.0)
        result  = PortfolioPolicyResult(
            result_id="r", evaluation_id="ev", portfolio_id="pf",
            final_action=PolicyAction.REQUIRE_MANUAL_REVIEW, outcomes=(), summary=summary,
            elapsed_s=0.0, evaluated_at=_time.time(),
        )
        r = PortfolioPolicyResponse.create_success("req", "pf", result)
        assert r.requires_manual_review

    def test_to_dict(self):
        result = self._make_result(PolicyAction.APPROVE)
        r = PortfolioPolicyResponse.create_success("req", "pf", result)
        d = r.to_dict()
        assert d["final_action"]  == "approve"
        assert "response_id"      in d

    def test_frozen(self):
        r = PortfolioPolicyResponse.create_failure("req", "pf", "err")
        with pytest.raises((AttributeError, TypeError)):
            r.portfolio_id = "mutated"  # type: ignore[misc]


# ===========================================================================
# PolicyAuditReport
# ===========================================================================

class TestPolicyAuditReport:
    def _entry(self, evaluation_id: str, policy_id: str = "p1") -> PolicyAuditEntry:
        return PolicyAuditEntry(
            entry_id          = "e1",
            evaluation_id     = evaluation_id,
            portfolio_id      = "pf-001",
            policy_id         = policy_id,
            policy_name       = "Test Policy",
            policy_type       = PolicyType.RISK,
            action            = PolicyAction.APPROVE,
            reason            = "passed",
            inputs_summary    = {},
            conditions_passed = 1,
            conditions_failed = 0,
            actor             = "test",
            recorded_at       = time.time(),
        )

    def test_add_entry(self):
        report = PortfolioPolicyAuditReport("ev-1", "pf-001")
        report.add_entry(self._entry("ev-1"))
        assert report.entry_count == 1

    def test_finalize(self):
        report = PortfolioPolicyAuditReport("ev-1", "pf-001")
        report.add_entry(self._entry("ev-1"))
        report.finalize(PolicyAction.APPROVE)
        assert report.is_finalized
        assert report.final_action == PolicyAction.APPROVE

    def test_cannot_add_after_finalize(self):
        report = PortfolioPolicyAuditReport("ev-1", "pf-001")
        report.finalize(PolicyAction.APPROVE)
        with pytest.raises(PortfolioPolicyAuditError):
            report.add_entry(self._entry("ev-1"))

    def test_to_dict(self):
        report = PortfolioPolicyAuditReport("ev-1", "pf-001")
        report.add_entry(self._entry("ev-1"))
        report.finalize(PolicyAction.APPROVE)
        d = report.to_dict()
        assert d["portfolio_id"] == "pf-001"
        assert d["entry_count"]  == 1
        assert d["final_action"] == "approve"
        assert d["is_finalized"] is True

    def test_audit_id_is_uuid(self):
        report = PortfolioPolicyAuditReport("ev-1", "pf-001")
        assert len(report.audit_id) == 36  # UUID format

    def test_entry_to_dict(self):
        e = self._entry("ev-1")
        d = e.to_dict()
        assert d["policy_type"] == "risk"
        assert d["action"]      == "approve"


# ===========================================================================
# PolicyEngineEvents / factories
# ===========================================================================

class TestPolicyEngineEvents:
    def _check(self, event: PolicyEngineEvent, expected_type: PolicyEventType):
        assert event.event_type    == expected_type
        assert event.event_id            # UUID
        assert event.evaluation_id       # non-empty
        assert event.portfolio_id == "pf-001"
        assert event.occurred_at   > 0

    def test_make_evaluation_started(self):
        e = make_policy_evaluation_started("ev-1", "pf-001", policy_count=3)
        self._check(e, PolicyEventType.POLICY_EVALUATION_STARTED)
        assert e.payload["policy_count"] == 3

    def test_make_policy_loaded(self):
        e = make_policy_loaded("ev-1", "pf-001", "pol-1", "Risk Policy")
        self._check(e, PolicyEventType.POLICY_LOADED)
        assert e.policy_id == "pol-1"
        assert e.payload["policy_name"] == "Risk Policy"

    def test_make_policy_validated(self):
        e = make_policy_validated("ev-1", "pf-001", "pol-1", passed=True)
        self._check(e, PolicyEventType.POLICY_VALIDATED)
        assert e.payload["passed"] is True

    def test_make_policy_approved(self):
        e = make_policy_approved("ev-1", "pf-001")
        self._check(e, PolicyEventType.POLICY_APPROVED)

    def test_make_policy_rejected(self):
        e = make_policy_rejected("ev-1", "pf-001", reason="risk limit")
        self._check(e, PolicyEventType.POLICY_REJECTED)
        assert e.payload["reason"] == "risk limit"

    def test_make_policy_blocked(self):
        e = make_policy_blocked("ev-1", "pf-001", reason="compliance")
        self._check(e, PolicyEventType.POLICY_BLOCKED)

    def test_make_policy_escalated(self):
        e = make_policy_escalated("ev-1", "pf-001", reason="needs review")
        self._check(e, PolicyEventType.POLICY_ESCALATED)

    def test_make_evaluation_completed(self):
        e = make_policy_evaluation_completed(
            "ev-1", "pf-001", PolicyAction.APPROVE,
            elapsed_s=0.5, total_policies=3,
        )
        self._check(e, PolicyEventType.POLICY_EVALUATION_COMPLETED)
        assert e.payload["final_action"]  == "approve"
        assert e.payload["elapsed_s"]     == 0.5
        assert e.payload["total_policies"] == 3

    def test_event_to_dict(self):
        e = make_policy_evaluation_started("ev-1", "pf-001")
        d = e.to_dict()
        assert d["event_type"]    == "portfolio_policy_evaluation_started"
        assert d["portfolio_id"]  == "pf-001"

    def test_frozen(self):
        e = make_policy_evaluation_started("ev-1", "pf-001")
        with pytest.raises((AttributeError, TypeError)):
            e.portfolio_id = "mutated"  # type: ignore[misc]


# ===========================================================================
# PortfolioPolicyStatistics
# ===========================================================================

class TestPolicyStatistics:
    def test_initial_zeros(self):
        s    = PortfolioPolicyStatistics()
        snap = s.snapshot()
        assert snap["evaluations_total"]   == 0
        assert snap["evaluations_approved"] == 0
        assert snap["evaluations_blocked"]  == 0

    def test_record_approved(self):
        s = PortfolioPolicyStatistics()
        s.record_evaluation_completed(PolicyAction.APPROVE, 0.1)
        snap = s.snapshot()
        assert snap["evaluations_total"]   == 1
        assert snap["evaluations_approved"] == 1

    def test_record_all_actions(self):
        s = PortfolioPolicyStatistics()
        for action in PolicyAction:
            s.record_evaluation_completed(action, 0.1)
        snap = s.snapshot()
        assert snap["evaluations_total"] == len(list(PolicyAction))

    def test_average_time(self):
        s = PortfolioPolicyStatistics()
        s.record_evaluation_completed(PolicyAction.APPROVE, 2.0)
        s.record_evaluation_completed(PolicyAction.APPROVE, 4.0)
        snap = s.snapshot()
        assert snap["average_evaluation_time_s"] == 3.0

    def test_record_error(self):
        s = PortfolioPolicyStatistics()
        s.record_evaluation_error()
        assert s.snapshot()["evaluations_error"] == 1

    def test_record_policy_registered(self):
        s = PortfolioPolicyStatistics()
        s.record_policy_registered()
        s.record_policy_registered()
        snap = s.snapshot()
        assert snap["policies_registered"] == 2
        assert snap["policies_active"]     == 2

    def test_record_policy_deactivated(self):
        s = PortfolioPolicyStatistics()
        s.record_policy_registered()
        s.record_policy_deactivated()
        assert s.snapshot()["policies_active"] == 0

    def test_by_type(self):
        s = PortfolioPolicyStatistics()
        s.record_evaluation_completed(PolicyAction.APPROVE, 0.1,
                                       policy_types=[PolicyType.RISK])
        snap = s.snapshot()
        assert snap["evaluations_by_type"]["risk"] == 1

    def test_reset(self):
        s = PortfolioPolicyStatistics()
        s.record_evaluation_completed(PolicyAction.APPROVE, 1.0)
        s.record_policy_registered()
        s.reset()
        snap = s.snapshot()
        assert snap["evaluations_total"]   == 0
        assert snap["policies_registered"] == 0

    def test_uptime_positive(self):
        s = PortfolioPolicyStatistics()
        time.sleep(0.01)
        assert s.snapshot()["uptime_s"] > 0


# ===========================================================================
# PortfolioPolicyHistory
# ===========================================================================

class TestPolicyHistory:
    def test_record_and_retrieve_event(self):
        h = PortfolioPolicyHistory()
        e = make_policy_evaluation_started("ev-1", "pf-001")
        h.record_event(e)
        assert h.latest_event() is e
        assert h.event_count()  == 1

    def test_events_by_type(self):
        h  = PortfolioPolicyHistory()
        e1 = make_policy_evaluation_started("ev-1", "pf-001")
        e2 = make_policy_evaluation_completed("ev-1", "pf-001", PolicyAction.APPROVE)
        h.record_event(e1)
        h.record_event(e2)
        result = h.events_by_type(PolicyEventType.POLICY_EVALUATION_STARTED)
        assert len(result) == 1

    def test_events_for_portfolio(self):
        h  = PortfolioPolicyHistory()
        e1 = make_policy_evaluation_started("ev-1", "pf-A")
        e2 = make_policy_evaluation_started("ev-2", "pf-B")
        h.record_event(e1)
        h.record_event(e2)
        assert len(h.events_for_portfolio("pf-A")) == 1

    def test_events_for_evaluation(self):
        h  = PortfolioPolicyHistory()
        e1 = make_policy_evaluation_started("ev-AAA", "pf-001")
        e2 = make_policy_evaluation_started("ev-BBB", "pf-001")
        h.record_event(e1)
        h.record_event(e2)
        assert len(h.events_for_evaluation("ev-AAA")) == 1

    def test_bounded_maxlen(self):
        h = PortfolioPolicyHistory(max_entries=3)
        for i in range(5):
            h.record_event(make_policy_evaluation_started(f"ev-{i}", "pf-001"))
        assert h.event_count() == 3

    def test_record_request(self):
        h   = PortfolioPolicyHistory()
        req = _request()
        h.record_request(req)
        assert h.request_count()  == 1
        assert h.latest_request() is req

    def test_record_response(self):
        h = PortfolioPolicyHistory()
        r = PortfolioPolicyResponse.create_failure("req", "pf", "err")
        h.record_response(r)
        assert h.response_count()  == 1
        assert h.latest_response() is r

    def test_record_audit(self):
        h      = PortfolioPolicyHistory()
        report = PortfolioPolicyAuditReport("ev", "pf")
        report.finalize(PolicyAction.APPROVE)
        h.record_audit(report)
        assert h.audit_count()  == 1
        assert h.latest_audit() is report

    def test_clear(self):
        h = PortfolioPolicyHistory()
        h.record_event(make_policy_evaluation_started("ev-1", "pf-001"))
        h.record_request(_request())
        h.clear()
        assert h.event_count()   == 0
        assert h.request_count() == 0

    def test_summary(self):
        h = PortfolioPolicyHistory()
        h.record_event(make_policy_evaluation_started("ev-1", "pf-001"))
        s = h.summary()
        assert s["events"] == 1


# ===========================================================================
# PolicyChain
# ===========================================================================

class TestPolicyChain:
    def test_add_and_evaluate_sequential(self):
        chain = PolicyChain(mode=PolicyChainMode.SEQUENTIAL)
        chain.add_policy(_approve_policy("p1"))
        chain.add_policy(_approve_policy("p2"))
        outcomes = chain.evaluate({})
        assert len(outcomes) == 2
        assert all(o.action == PolicyAction.APPROVE for o in outcomes)

    def test_sequential_stops_on_block(self):
        chain = PolicyChain(mode=PolicyChainMode.SEQUENTIAL, stop_on_block=True)
        chain.add_policy(_block_policy("p-block"))
        chain.add_policy(_approve_policy("p-after"))
        outcomes = chain.evaluate({})
        # Must stop after the BLOCK
        assert len(outcomes) == 1
        assert outcomes[0].action == PolicyAction.BLOCK

    def test_sequential_no_stop_on_block(self):
        chain = PolicyChain(mode=PolicyChainMode.SEQUENTIAL, stop_on_block=False)
        chain.add_policy(_block_policy("p-block"))
        chain.add_policy(_approve_policy("p-after"))
        outcomes = chain.evaluate({})
        assert len(outcomes) == 2

    def test_parallel_evaluates_all(self):
        chain = PolicyChain(mode=PolicyChainMode.PARALLEL, stop_on_block=True)
        chain.add_policy(_block_policy("p-block"))
        chain.add_policy(_approve_policy("p-after"))
        outcomes = chain.evaluate({})
        assert len(outcomes) == 2  # all evaluated

    def test_composite_mode_as_sequential(self):
        chain = PolicyChain(mode=PolicyChainMode.COMPOSITE, stop_on_block=True)
        chain.add_policy(_block_policy("p-block"))
        chain.add_policy(_approve_policy("p-after"))
        outcomes = chain.evaluate({})
        assert len(outcomes) == 1  # stops on BLOCK

    def test_empty_chain(self):
        chain    = PolicyChain()
        outcomes = chain.evaluate({})
        assert outcomes == []

    def test_remove_policy(self):
        chain = PolicyChain()
        p     = _approve_policy("p1")
        chain.add_policy(p)
        assert chain.remove_policy("p1")
        assert chain.policy_count == 0

    def test_capacity_exceeded(self):
        chain = PolicyChain(max_size=1)
        chain.add_policy(_approve_policy("p1"))
        with pytest.raises(PortfolioPolicyChainError):
            chain.add_policy(_approve_policy("p2"))

    def test_merge(self):
        c1 = PolicyChain()
        c2 = PolicyChain()
        c1.add_policy(_approve_policy("p1"))
        c2.add_policy(_approve_policy("p2"))
        c1.merge(c2)
        assert c1.policy_count == 2

    def test_to_dict(self):
        chain = PolicyChain(chain_id="c1", name="test-chain")
        d     = chain.to_dict()
        assert d["name"] == "test-chain"
        assert "mode"    in d

    def test_sorted_by_priority(self):
        chain = PolicyChain()
        chain.add_policy(_approve_policy("p-low",  priority=PolicyPriority.LOW))
        chain.add_policy(_approve_policy("p-crit", priority=PolicyPriority.CRITICAL))
        outcomes = chain.evaluate({})
        assert outcomes[0].policy_id == "p-crit"


# ===========================================================================
# PortfolioPolicyEvaluator
# ===========================================================================

class TestPortfolioPolicyEvaluator:
    def test_approve_with_single_policy(self):
        ev  = PortfolioPolicyEvaluator()
        req = _request()
        res = ev.evaluate(req, [_approve_policy()])
        assert res.final_action == PolicyAction.APPROVE
        assert res.outcome_count == 1

    def test_block_wins(self):
        ev  = PortfolioPolicyEvaluator()
        req = _request()
        res = ev.evaluate(req, [_approve_policy("p1"), _block_policy("p2")])
        assert res.final_action == PolicyAction.BLOCK

    def test_no_policies_approves(self):
        ev  = PortfolioPolicyEvaluator()
        req = _request()
        res = ev.evaluate(req, [])
        assert res.final_action == PolicyAction.APPROVE
        assert res.outcome_count == 0

    def test_filters_inactive_policies(self):
        ev  = PortfolioPolicyEvaluator()
        req = _request()
        p   = _block_policy()
        p.deactivate()
        res = ev.evaluate(req, [p, _approve_policy("p2")])
        assert res.final_action  == PolicyAction.APPROVE
        assert res.outcome_count == 1

    def test_filters_by_policy_type(self):
        ev  = PortfolioPolicyEvaluator()
        req = _request(policy_types=[PolicyType.COMPLIANCE])
        p1  = _block_policy("p1", PolicyType.RISK)         # should NOT be evaluated
        p2  = _approve_policy("p2", PolicyType.COMPLIANCE) # should be evaluated
        res = ev.evaluate(req, [p1, p2])
        assert res.outcome_count == 1
        assert res.outcomes[0].policy_id == "p2"

    def test_all_15_policy_types(self):
        ev = PortfolioPolicyEvaluator()
        for pt in PolicyType:
            req = _request(policy_types=[pt])
            pol = _approve_policy(f"pol-{pt.value}", pt)
            res = ev.evaluate(req, [pol])
            assert res.final_action == PolicyAction.APPROVE, f"failed for {pt}"

    def test_evaluation_summary_counts(self):
        ev  = PortfolioPolicyEvaluator()
        req = _request()
        res = ev.evaluate(req, [_approve_policy("p1"), _reject_policy("p2")])
        s   = res.summary
        assert s.approved_count == 1
        assert s.rejected_count == 1

    def test_custom_resolver(self):
        resolver = PolicyPriorityResolver(PolicyConflictResolution.PRIORITY_WINS)
        ev       = PortfolioPolicyEvaluator(resolver=resolver)
        req      = _request()
        p_high   = _approve_policy("p-high", priority=PolicyPriority.HIGH)
        p_low    = _block_policy("p-low",   priority=PolicyPriority.LOW)
        res      = ev.evaluate(req, [p_high, p_low])
        # HIGH priority approve wins over LOW priority block
        assert res.final_action == PolicyAction.APPROVE


# ===========================================================================
# PortfolioPolicyValidator
# ===========================================================================

class TestPolicyValidator:
    def test_valid_policy_all_pass(self):
        v   = PortfolioPolicyValidator()
        p   = _approve_policy()
        res = v.validate_policy(p)
        assert res.is_valid
        assert res.passed_count == 6
        assert res.failed_count == 0

    def test_empty_policy_id_fails(self):
        v = PortfolioPolicyValidator()

        # PortfolioPolicy auto-generates a UUID for empty ids, so test the
        # validator directly with a namespace object that has an empty policy_id.
        class _FakePolicy:
            policy_id   = ""
            name        = "name"
            policy_type = PolicyType.RISK
            priority    = PolicyPriority.MEDIUM
            status      = PolicyStatus.ACTIVE
            rule_count  = 0
            version     = "1.0.0"

        r = v.validate_policy(_FakePolicy())
        assert not r.is_valid
        assert r.failed_count > 0

    def test_valid_request_all_pass(self):
        v   = PortfolioPolicyValidator()
        req = _request()
        res = v.validate_request(req)
        assert res.is_valid
        assert res.passed_count == 6

    def test_empty_portfolio_id_fails(self):
        v   = PortfolioPolicyValidator()
        req = PortfolioPolicyRequest.create("")
        res = v.validate_request(req)
        assert not res.is_valid
        assert len(res.error_messages) > 0

    def test_error_messages_populated(self):
        v   = PortfolioPolicyValidator()
        req = PortfolioPolicyRequest.create("")
        res = v.validate_request(req)
        assert any(res.error_messages)

    def test_failed_checks_subset_of_checks(self):
        v   = PortfolioPolicyValidator()
        req = _request()
        res = v.validate_request(req)
        for fc in res.failed_checks:
            assert fc in res.checks

    def test_validation_check_result_to_dict(self):
        c = PolicyValidationCheckResult("CODE", True, "ok")
        d = c.to_dict()
        assert d["code"]   == "CODE"
        assert d["passed"] is True

    def test_validation_result_to_dict(self):
        v   = PortfolioPolicyValidator()
        req = _request()
        res = v.validate_request(req)
        d   = res.to_dict()
        assert d["is_valid"]     is True
        assert "passed_count"    in d


# ===========================================================================
# PortfolioPolicyRegistry
# ===========================================================================

class TestPolicyRegistry:
    def test_register_and_get(self):
        reg = PortfolioPolicyRegistry()
        p   = _approve_policy()
        reg.register(p)
        assert reg.get(p.policy_id) is p

    def test_capacity_exceeded(self):
        reg = PortfolioPolicyRegistry(max_policies=1)
        reg.register(_approve_policy("p1"))
        with pytest.raises(PortfolioPolicyCapacityError):
            reg.register(_approve_policy("p2"))

    def test_get_or_raise(self):
        reg = PortfolioPolicyRegistry()
        with pytest.raises(PortfolioPolicyNotFoundError):
            reg.get_or_raise("nonexistent")

    def test_find_by_type(self):
        reg = PortfolioPolicyRegistry()
        reg.register(_approve_policy("p1", PolicyType.RISK))
        reg.register(_approve_policy("p2", PolicyType.COMPLIANCE))
        reg.register(_approve_policy("p3", PolicyType.RISK))
        risk_policies = reg.find_by_type(PolicyType.RISK)
        assert len(risk_policies) == 2

    def test_all_active(self):
        reg = PortfolioPolicyRegistry()
        reg.register(_approve_policy("p1"))
        reg.register(_approve_policy("p2"))
        reg.deactivate("p1")
        active = reg.all_active()
        assert len(active) == 1
        assert active[0].policy_id == "p2"

    def test_deactivate_returns_true(self):
        reg = PortfolioPolicyRegistry()
        p   = _approve_policy()
        reg.register(p)
        assert reg.deactivate(p.policy_id)
        assert not p.is_active

    def test_deactivate_nonexistent_returns_false(self):
        reg = PortfolioPolicyRegistry()
        assert not reg.deactivate("ghost")

    def test_activate_after_deactivate(self):
        reg = PortfolioPolicyRegistry()
        p   = _approve_policy()
        reg.register(p)
        reg.deactivate(p.policy_id)
        reg.activate(p.policy_id)
        assert p.is_active

    def test_deprecate(self):
        reg = PortfolioPolicyRegistry()
        p   = _approve_policy()
        reg.register(p)
        assert reg.deprecate(p.policy_id)
        assert p.status == PolicyStatus.DEPRECATED

    def test_unregister(self):
        reg = PortfolioPolicyRegistry()
        p   = _approve_policy()
        reg.register(p)
        assert reg.unregister(p.policy_id)
        assert reg.get(p.policy_id) is None

    def test_counts(self):
        reg = PortfolioPolicyRegistry()
        reg.register(_approve_policy("p1"))
        reg.register(_approve_policy("p2"))
        reg.deactivate("p1")
        assert reg.policy_count() == 2
        assert reg.active_count() == 1

    def test_clear(self):
        reg = PortfolioPolicyRegistry()
        reg.register(_approve_policy("p1"))
        reg.clear()
        assert reg.policy_count() == 0

    def test_all_active_sorted_by_priority(self):
        reg = PortfolioPolicyRegistry()
        reg.register(_approve_policy("p-low",  priority=PolicyPriority.LOW))
        reg.register(_approve_policy("p-crit", priority=PolicyPriority.CRITICAL))
        active = reg.all_active()
        assert active[0].policy_id == "p-crit"


# ===========================================================================
# PortfolioPolicyFactory
# ===========================================================================

class TestPolicyFactory:
    def test_create_request(self):
        f   = PortfolioPolicyFactory()
        req = f.create_request("pf-001")
        assert isinstance(req, PortfolioPolicyRequest)
        assert req.portfolio_id == "pf-001"

    def test_create_condition(self):
        f   = PortfolioPolicyFactory()
        c   = f.create_condition("score_check", lambda i: i.get("score", 0) >= 7.0, threshold=7.0)
        res = c.evaluate({"score": 8.0})
        assert res.passed
        assert res.threshold == 7.0

    def test_create_rule(self):
        f   = PortfolioPolicyFactory()
        c   = f.create_condition("pass", lambda _: True)
        r   = f.create_rule("my_rule", [c], PolicyAction.APPROVE, PolicyAction.REJECT)
        res = r.evaluate({})
        assert res.action == PolicyAction.APPROVE

    def test_create_policy(self):
        f = PortfolioPolicyFactory()
        c = f.create_condition("pass", lambda _: True)
        r = f.create_rule("rule", [c])
        p = f.create_policy("My Policy", PolicyType.RISK, [r])
        assert isinstance(p, PortfolioPolicy)
        assert p.policy_type == PolicyType.RISK

    def test_create_permissive_policy(self):
        f   = PortfolioPolicyFactory()
        p   = f.create_permissive_policy("Permissive", PolicyType.COMPLIANCE)
        out = p.evaluate({})
        assert out.action == PolicyAction.APPROVE

    def test_create_restrictive_policy_block(self):
        f   = PortfolioPolicyFactory()
        p   = f.create_restrictive_policy("Restrictive", PolicyType.RISK)
        out = p.evaluate({})
        assert out.action == PolicyAction.BLOCK

    def test_create_restrictive_policy_reject(self):
        f   = PortfolioPolicyFactory()
        p   = f.create_restrictive_policy("Reject Policy", PolicyType.RISK,
                                           action=PolicyAction.REJECT)
        out = p.evaluate({})
        assert out.action == PolicyAction.REJECT

    def test_create_chain(self):
        f     = PortfolioPolicyFactory()
        chain = f.create_chain("my-chain", mode=PolicyChainMode.PARALLEL)
        assert isinstance(chain, PolicyChain)
        assert chain.mode == PolicyChainMode.PARALLEL


# ===========================================================================
# PortfolioPolicyEngine — guard
# ===========================================================================

class TestPolicyEngineGuard:
    def test_submit_blocked_when_not_started(self):
        e = PortfolioPolicyEngine()
        with pytest.raises(PortfolioPolicyNotRunningError):
            e.submit(_request())

    def test_register_blocked_when_not_started(self):
        e = PortfolioPolicyEngine()
        with pytest.raises(PortfolioPolicyNotRunningError):
            e.register_policy(_approve_policy())

    def test_evaluate_blocked_when_not_started(self):
        e = PortfolioPolicyEngine()
        with pytest.raises(PortfolioPolicyNotRunningError):
            e.evaluate("pf-001")

    def test_stop_then_submit_blocked(self):
        e = _started_engine()
        e.stop()
        with pytest.raises(PortfolioPolicyNotRunningError):
            e.submit(_request())


# ===========================================================================
# PortfolioPolicyEngine — happy path
# ===========================================================================

class TestPolicyEngineSubmit:
    def test_submit_no_policies_returns_approve(self):
        e = _started_engine()
        r = e.submit(_request())
        assert r.is_approved
        assert not r.is_failure
        e.stop()

    def test_submit_with_approve_policy(self):
        e = _started_engine()
        e.register_policy(_approve_policy())
        r = e.submit(_request())
        assert r.is_approved
        e.stop()

    def test_submit_with_block_policy(self):
        e = _started_engine()
        e.register_policy(_block_policy())
        r = e.submit(_request())
        assert r.is_blocked
        assert not r.is_approved
        e.stop()

    def test_submit_with_reject_policy(self):
        e = _started_engine()
        e.register_policy(_reject_policy())
        r = e.submit(_request())
        assert r.is_rejected
        e.stop()

    def test_submit_invalid_request_returns_failure(self):
        e = _started_engine()
        r = e.submit(PortfolioPolicyRequest.create(""))
        assert r.is_failure
        e.stop()

    def test_submit_has_result_on_success(self):
        e = _started_engine()
        r = e.submit(_request())
        assert r.has_result
        assert isinstance(r.result, PortfolioPolicyResult)
        e.stop()

    def test_submit_has_audit_id(self):
        e = _started_engine()
        r = e.submit(_request())
        assert r.audit_id  # non-empty
        e.stop()


# ===========================================================================
# PortfolioPolicyEngine — evaluate convenience method
# ===========================================================================

class TestPolicyEngineEvaluate:
    def test_evaluate_no_policies(self):
        e = _started_engine()
        r = e.evaluate("pf-001")
        assert r.is_approved
        e.stop()

    def test_evaluate_with_inputs(self):
        e = _started_engine()
        f = PortfolioPolicyFactory()
        c = f.create_condition("score", lambda i: i.get("score", 0) >= 7.0, threshold=7.0)
        rule = f.create_rule("r", [c], PolicyAction.APPROVE, PolicyAction.REJECT)
        pol  = f.create_policy("Score Policy", PolicyType.RISK, [rule])
        e.register_policy(pol)
        r = e.evaluate("pf-001", inputs={"score": 8.0})
        assert r.is_approved
        r2 = e.evaluate("pf-001", inputs={"score": 5.0})
        assert r2.is_rejected
        e.stop()

    def test_evaluate_filtered_by_type(self):
        e = _started_engine()
        e.register_policy(_block_policy("p-risk", PolicyType.RISK))
        e.register_policy(_approve_policy("p-comp", PolicyType.COMPLIANCE))
        # Only evaluate COMPLIANCE → should approve
        r = e.evaluate("pf-001", [PolicyType.COMPLIANCE])
        assert r.is_approved
        e.stop()


# ===========================================================================
# PortfolioPolicyEngine — policy management
# ===========================================================================

class TestPolicyEngineManagement:
    def test_register_and_get_policy(self):
        e = _started_engine()
        p = _approve_policy("pol-x")
        e.register_policy(p)
        got = e.get_policy("pol-x")
        assert got is p
        e.stop()

    def test_deactivate_policy(self):
        e = _started_engine()
        p = _block_policy("pol-block")
        e.register_policy(p)
        e.deactivate_policy("pol-block")
        r = e.submit(_request())
        assert r.is_approved  # deactivated policy not evaluated
        e.stop()

    def test_activate_policy(self):
        e = _started_engine()
        p = _block_policy("pol-block")
        e.register_policy(p)
        e.deactivate_policy("pol-block")
        e.activate_policy("pol-block")
        r = e.submit(_request())
        assert r.is_blocked
        e.stop()

    def test_list_policies_all_active(self):
        e = _started_engine()
        e.register_policy(_approve_policy("p1", PolicyType.RISK))
        e.register_policy(_approve_policy("p2", PolicyType.COMPLIANCE))
        e.register_policy(_approve_policy("p3", PolicyType.RISK))
        listed = e.list_policies()
        assert len(listed) == 3
        e.stop()

    def test_list_policies_by_type(self):
        e = _started_engine()
        e.register_policy(_approve_policy("p1", PolicyType.RISK))
        e.register_policy(_approve_policy("p2", PolicyType.COMPLIANCE))
        risk = e.list_policies(PolicyType.RISK)
        assert len(risk) == 1
        e.stop()

    def test_capacity_error_propagates(self):
        e = PortfolioPolicyEngine(max_policies=1)
        e.start()
        e.register_policy(_approve_policy("p1"))
        with pytest.raises(PortfolioPolicyCapacityError):
            e.register_policy(_approve_policy("p2"))
        e.stop()


# ===========================================================================
# PortfolioPolicyEngine — validation
# ===========================================================================

class TestPolicyEngineValidation:
    def test_validate_valid_request(self):
        e   = _started_engine()
        req = _request("pf-001")
        r   = e.validate(req)
        assert r.is_valid
        e.stop()

    def test_validate_invalid_request(self):
        e   = _started_engine()
        req = PortfolioPolicyRequest.create("")
        r   = e.validate(req)
        assert not r.is_valid
        e.stop()

    def test_validate_policy_config(self):
        e   = _started_engine()
        p   = _approve_policy()
        r   = e.validate_policy(p)
        assert r.is_valid
        e.stop()


# ===========================================================================
# PortfolioPolicyEngine — introspection
# ===========================================================================

class TestPolicyEngineIntrospection:
    def test_status_structure(self):
        e = _started_engine()
        e.register_policy(_approve_policy())
        e.submit(_request())
        s = e.status()
        assert isinstance(s, PolicyEngineStatus)
        assert s.lifecycle_state   == "running"
        assert s.total_policies    == 1
        assert s.evaluations_total == 1
        assert s.is_healthy        is True
        d = s.to_dict()
        assert "lifecycle_state" in d
        assert "total_policies"  in d
        e.stop()

    def test_statistics_keys(self):
        e = _started_engine()
        e.submit(_request())
        snap = e.statistics()
        assert "evaluations_total"        in snap
        assert "evaluations_approved"     in snap
        assert "average_evaluation_time_s" in snap
        assert "policies_registered"      in snap
        e.stop()

    def test_health_structure(self):
        e = _started_engine()
        h = e.health()
        assert h["is_healthy"]  is True
        assert "registry"       in h
        assert "evaluator"      in h
        assert "statistics"     in h
        e.stop()

    def test_history_structure(self):
        e = _started_engine()
        e.register_policy(_approve_policy())
        e.submit(_request())
        h = e.history()
        assert "events"    in h
        assert "requests"  in h
        assert "responses" in h
        assert "audits"    in h
        assert len(h["events"]) > 0
        e.stop()

    def test_statistics_approved_increments(self):
        e = _started_engine()
        e.register_policy(_approve_policy())
        e.submit(_request("pf-A"))
        e.submit(_request("pf-B"))
        snap = e.statistics()
        assert snap["evaluations_total"]   >= 2
        assert snap["evaluations_approved"] >= 2
        e.stop()


# ===========================================================================
# PortfolioPolicyEngine — event listeners
# ===========================================================================

class TestPolicyEngineListeners:
    def test_listener_receives_events(self):
        e        = _started_engine()
        received = []
        e.add_listener(received.append)
        e.submit(_request())
        assert len(received) > 0
        e.stop()

    def test_listener_receives_started_event(self):
        e        = _started_engine()
        received = []
        e.add_listener(received.append)
        e.submit(_request())
        types = {ev.event_type for ev in received}
        assert PolicyEventType.POLICY_EVALUATION_STARTED in types
        e.stop()

    def test_listener_receives_completed_event(self):
        e        = _started_engine()
        received = []
        e.add_listener(received.append)
        e.submit(_request())
        types = {ev.event_type for ev in received}
        assert PolicyEventType.POLICY_EVALUATION_COMPLETED in types
        e.stop()

    def test_listener_removed(self):
        e        = _started_engine()
        received = []
        e.add_listener(received.append)
        e.remove_listener(received.append)
        e.submit(_request())
        assert len(received) == 0
        e.stop()

    def test_listener_error_does_not_propagate(self):
        e = _started_engine()
        e.add_listener(lambda ev: (_ for _ in ()).throw(RuntimeError("bad listener")))
        e.submit(_request())  # must not raise
        e.stop()

    def test_multiple_listeners(self):
        e    = _started_engine()
        acc1 = []
        acc2 = []
        e.add_listener(acc1.append)
        e.add_listener(acc2.append)
        e.submit(_request())
        assert len(acc1) > 0
        assert len(acc2) > 0
        e.stop()

    def test_duplicate_listener_not_added_twice(self):
        e   = _started_engine()
        acc = []
        e.add_listener(acc.append)
        e.add_listener(acc.append)  # duplicate
        e.submit(_request())
        started_count = sum(
            1 for ev in acc if ev.event_type == PolicyEventType.POLICY_EVALUATION_STARTED
        )
        assert started_count == 1
        e.stop()


# ===========================================================================
# PortfolioPolicyEngine — all 15 policy types
# ===========================================================================

class TestAllPolicyTypes:
    def test_all_types_evaluate(self):
        e = _started_engine()
        for pt in PolicyType:
            e.register_policy(_approve_policy(f"pol-{pt.value}", pt))
        r = e.submit(_request())
        assert r.is_approved
        snap = e.statistics()
        assert snap["evaluations_total"] >= 1
        e.stop()

    def test_each_type_independently(self):
        for pt in PolicyType:
            e   = _started_engine()
            e.register_policy(_approve_policy(f"pol-{pt.value}", pt))
            req = _request(policy_types=[pt])
            r   = e.submit(req)
            assert r.is_approved, f"failed for {pt}"
            e.stop()


# ===========================================================================
# PortfolioPolicyEngine — all 7 policy actions
# ===========================================================================

class TestAllPolicyActions:
    def _policy_with_action(self, action: PolicyAction, policy_id: str) -> PortfolioPolicy:
        cond = _pass_condition() if action == PolicyAction.APPROVE else _fail_condition()
        rule = PolicyRule("r", "r", [cond],
                          PolicyAction.APPROVE if action == PolicyAction.APPROVE else PolicyAction.APPROVE,
                          action)
        return PortfolioPolicy(policy_id, "p", PolicyType.RISK, rules=[rule])

    def test_approve(self):
        e = _started_engine()
        e.register_policy(_approve_policy())
        r = e.submit(_request())
        assert r.final_action == PolicyAction.APPROVE
        e.stop()

    def test_block(self):
        e = _started_engine()
        e.register_policy(_block_policy())
        r = e.submit(_request())
        assert r.is_blocked
        e.stop()

    def test_reject(self):
        e = _started_engine()
        e.register_policy(_reject_policy())
        r = e.submit(_request())
        assert r.is_rejected
        e.stop()

    def test_escalate(self):
        e = _started_engine()
        e.register_policy(self._policy_with_action(PolicyAction.ESCALATE, "esc"))
        r = e.submit(_request())
        assert r.requires_escalation
        e.stop()

    def test_require_manual_review(self):
        e = _started_engine()
        e.register_policy(
            self._policy_with_action(PolicyAction.REQUIRE_MANUAL_REVIEW, "mrv")
        )
        r = e.submit(_request())
        assert r.requires_manual_review
        e.stop()

    def test_approve_with_conditions(self):
        e = _started_engine()
        e.register_policy(
            self._policy_with_action(PolicyAction.APPROVE_WITH_CONDITIONS, "cond")
        )
        r = e.submit(_request())
        assert r.final_action == PolicyAction.APPROVE_WITH_CONDITIONS
        e.stop()


# ===========================================================================
# PortfolioPolicyEngine — concurrency
# ===========================================================================

class TestPolicyEngineConcurrency:
    def test_concurrent_submits(self):
        e       = _started_engine()
        e.register_policy(_approve_policy())
        errors  = []
        results = []
        lock    = threading.Lock()

        def worker(i: int):
            try:
                r = e.submit(_request(f"pf-{i}"))
                with lock:
                    results.append(r)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(errors)  == 0, f"Errors: {errors}"
        assert len(results) == 30
        assert all(r.is_approved for r in results)
        e.stop()

    def test_concurrent_policy_registration(self):
        e      = _started_engine(max_policies=200)
        errors = []

        def registrar(i):
            try:
                e.register_policy(_approve_policy(f"pol-{i}"))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=registrar, args=(i,)) for i in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(errors) == 0
        e.stop()

    def test_concurrent_statistics_reads(self):
        e      = _started_engine()
        e.submit(_request())
        errors = []

        def reader():
            try:
                e.statistics()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert len(errors) == 0
        e.stop()


# ===========================================================================
# PortfolioPolicyEngine — stress test
# ===========================================================================

class TestPolicyEngineStress:
    def test_fifty_sequential_submits(self):
        e = _started_engine()
        e.register_policy(_approve_policy())
        results = [e.submit(_request(f"pf-stress-{i}")) for i in range(50)]
        assert all(r.is_approved for r in results)
        snap = e.statistics()
        assert snap["evaluations_total"] >= 50
        e.stop()

    def test_mixed_policies_many_portfolios(self):
        e = _started_engine()
        e.register_policy(_approve_policy("p-approve", PolicyType.COMPLIANCE))
        e.register_policy(_block_policy("p-block",   PolicyType.RISK))
        # Only evaluate COMPLIANCE → all approve
        results = [
            e.submit(_request(f"pf-{i}", [PolicyType.COMPLIANCE]))
            for i in range(20)
        ]
        assert all(r.is_approved for r in results)
        e.stop()


# ===========================================================================
# Integration
# ===========================================================================

class TestPolicyEngineIntegration:
    def test_full_evaluation_workflow(self):
        """
        Full workflow: start engine, register 3 policies, submit request,
        verify response, history, statistics, and audit trail.
        """
        e = _started_engine()

        f = PortfolioPolicyFactory()

        # Capital allocation policy — passes if decision score >= 7
        score_cond = f.create_condition(
            "decision_score",
            lambda i: i.get("decision_snapshot", {}).get("score", 0.0) >= 7.0,
            threshold=7.0,
        )
        cap_rule = f.create_rule("score_rule", [score_cond],
                                  PolicyAction.APPROVE, PolicyAction.REJECT)
        cap_pol  = f.create_policy("Capital Policy", PolicyType.CAPITAL_ALLOCATION,
                                    [cap_rule])

        # Risk policy — passes if volatility < 0.3
        risk_cond = f.create_condition(
            "volatility",
            lambda i: i.get("market_snapshot", {}).get("volatility", 1.0) < 0.3,
            threshold=0.3,
        )
        risk_rule = f.create_rule("volatility_rule", [risk_cond],
                                   PolicyAction.APPROVE, PolicyAction.BLOCK)
        risk_pol  = f.create_policy("Risk Policy", PolicyType.RISK,
                                    [risk_rule], priority=PolicyPriority.HIGH)

        # Compliance policy — always approve
        comp_pol = f.create_permissive_policy("Compliance", PolicyType.COMPLIANCE)

        e.register_policy(cap_pol)
        e.register_policy(risk_pol)
        e.register_policy(comp_pol)

        req = f.create_request(
            "pf-integration",
            inputs={
                "decision_snapshot": {"score": 8.5},
                "market_snapshot":   {"volatility": 0.15},
            },
        )
        r = e.submit(req)

        assert r.is_approved
        assert r.has_result
        assert r.result.outcome_count == 3

        # History populated
        h = e.history()
        assert len(h["events"]) > 0
        assert h["audits"] >= 1

        # Statistics
        snap = e.statistics()
        assert snap["evaluations_approved"] >= 1
        assert snap["policies_registered"]  == 3

        e.stop()

    def test_conflict_resolution_critical_block_wins(self):
        e = _started_engine()
        e.register_policy(_approve_policy("p-approve", priority=PolicyPriority.LOW))
        e.register_policy(_block_policy("p-block", priority=PolicyPriority.CRITICAL))
        r = e.submit(_request())
        assert r.is_blocked
        e.stop()

    def test_history_contains_all_event_types_on_submit(self):
        e = _started_engine()
        e.register_policy(_approve_policy())
        e.submit(_request())
        h     = e.history()
        types = {ev["event_type"] for ev in h["events"]}
        assert "portfolio_policy_evaluation_started"   in types
        assert "portfolio_policy_loaded"               in types
        assert "portfolio_policy_validated"            in types
        assert "portfolio_policy_evaluation_completed" in types
        e.stop()

    def test_new_instance_after_stop(self):
        e1 = _started_engine()
        e1.register_policy(_approve_policy())
        r1 = e1.submit(_request("pf-1"))
        assert r1.is_approved
        e1.stop()

        e2 = _started_engine()
        e2.register_policy(_approve_policy())
        r2 = e2.submit(_request("pf-2"))
        assert r2.is_approved
        e2.stop()
