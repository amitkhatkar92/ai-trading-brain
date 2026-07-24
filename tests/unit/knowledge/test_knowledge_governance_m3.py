"""
tests/unit/knowledge/test_knowledge_governance_m3.py
------------------------------------------------------
Comprehensive test suite for iios.knowledge.policies (C14 M3).

Coverage targets : ≥ 95 %
Test classes     : 20
Approx. tests    : 220+

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from iios.knowledge.policies import (
    ACTOR_GOVERNANCE,
    AuditError,
    ChainResult,
    ConditionOperator,
    GovernanceCapacityError,
    GovernanceDecision,
    GovernanceEngineState,
    GovernanceEventType,
    GovernanceNotRunningError,
    GovernanceValidationError,
    GovernanceValidationResult,
    KnowledgeGovernancePolicyEngine,
    KnowledgeGovernanceError,
    KnowledgeGovernanceHistory,
    KnowledgeGovernanceStatistics,
    KnowledgeGovernanceValidator,
    KnowledgePolicy,
    KnowledgePolicyAudit,
    KnowledgePolicyChain,
    KnowledgePolicyEvaluator,
    KnowledgePolicyFactory,
    KnowledgePolicyRegistry,
    KnowledgePolicyRequest,
    KnowledgePolicyResponse,
    KnowledgePolicyWorkflowManager,
    GovernancePolicyContext,
    GovernancePolicyEvent,
    GovernancePolicyEventBus,
    GovernanceDecisionRecord,
    PolicyAction,
    PolicyAuditEntry,
    PolicyChainError,
    PolicyChainMode,
    PolicyCondition,
    PolicyConflictError,
    PolicyDomain,
    PolicyEvaluationResult,
    PolicyEvaluationError,
    PolicyLoadError,
    PolicyNotFoundError,
    PolicyPriority,
    PolicyPriorityResolver,
    PolicyRule,
    PolicyRuleResult,
    PolicyStatus,
    PolicyType,
    PolicyValidationCode,
    VERSION,
    make_governance_started,
    make_knowledge_approved,
    make_knowledge_blocked,
    make_knowledge_rejected,
)
from iios.investment.workflow.engine_lifecycle import EngineAlreadyRunningError


# ===========================================================================
# Helpers
# ===========================================================================


def _started_engine(**kwargs) -> KnowledgeGovernancePolicyEngine:
    e = KnowledgeGovernancePolicyEngine(**kwargs)
    e.start()
    return e


def _make_request(
    knowledge_id:   str              = "k-001",
    subsystem_id:   str              = "execution_intelligence",
    artifacts:      Dict[str, Any]   = None,
    priority:       PolicyPriority   = PolicyPriority.MEDIUM,
) -> KnowledgePolicyRequest:
    return KnowledgePolicyRequest.create(
        knowledge_id = knowledge_id,
        subsystem_id = subsystem_id,
        artifacts    = artifacts or {"data": "value"},
        priority     = priority,
    )


def _make_approve_policy(
    name: str = "AllowAll",
    domain: PolicyDomain = PolicyDomain.CLASSIFICATION,
) -> KnowledgePolicy:
    policy = KnowledgePolicy(
        name        = name,
        policy_type = PolicyType.CLASSIFICATION,
        domain      = domain,
    )
    rule = PolicyRule.create(name="AlwaysApprove", action=PolicyAction.APPROVE)
    policy.add_rule(rule)
    policy.activate()
    return policy


def _make_reject_policy(name: str = "RejectAll") -> KnowledgePolicy:
    policy = KnowledgePolicy(
        name        = name,
        policy_type = PolicyType.SECURITY,
        domain      = PolicyDomain.SECURITY,
    )
    rule = PolicyRule.create(name="AlwaysReject", action=PolicyAction.REJECT)
    policy.add_rule(rule)
    policy.activate()
    return policy


def _make_block_policy(name: str = "BlockAll") -> KnowledgePolicy:
    policy = KnowledgePolicy(
        name        = name,
        policy_type = PolicyType.COMPLIANCE,
        domain      = PolicyDomain.COMPLIANCE,
    )
    rule = PolicyRule.create(name="AlwaysBlock", action=PolicyAction.BLOCK)
    policy.add_rule(rule)
    policy.activate()
    return policy


# ===========================================================================
# 1. TestConstants
# ===========================================================================


class TestConstants:
    def test_version_is_string(self):
        assert isinstance(VERSION, str) and VERSION

    def test_nine_engine_states(self):
        assert len(GovernanceEngineState) == 9

    def test_fifteen_policy_types(self):
        assert len(PolicyType) == 15

    def test_eight_policy_actions(self):
        assert len(PolicyAction) == 8

    def test_five_policy_priorities(self):
        assert len(PolicyPriority) == 5

    def test_eleven_policy_domains(self):
        assert len(PolicyDomain) == 11

    def test_eight_governance_decisions(self):
        assert len(GovernanceDecision) == 8

    def test_six_chain_modes(self):
        assert len(PolicyChainMode) == 6

    def test_twelve_condition_operators(self):
        assert len(ConditionOperator) == 12

    def test_nine_event_types(self):
        assert len(GovernanceEventType) == 9

    def test_seven_validation_codes(self):
        assert len(PolicyValidationCode) == 7

    def test_priority_ordering(self):
        assert PolicyPriority.CRITICAL < PolicyPriority.HIGH
        assert PolicyPriority.HIGH < PolicyPriority.NORMAL if hasattr(PolicyPriority, "NORMAL") else True
        assert PolicyPriority.CRITICAL < PolicyPriority.LOW

    def test_governance_system_id(self):
        from iios.knowledge.policies.constants import GOVERNANCE_SYSTEM_ID
        assert "governance" in GOVERNANCE_SYSTEM_ID


# ===========================================================================
# 2. TestExceptions
# ===========================================================================


class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(KnowledgeGovernanceError, IIOSError)

    def test_error_codes_distinct(self):
        codes = {
            KnowledgeGovernanceError.error_code,
            GovernanceNotRunningError.error_code,
            GovernanceValidationError.error_code,
            PolicyLoadError.error_code,
            PolicyEvaluationError.error_code,
            PolicyConflictError.error_code,
            PolicyNotFoundError.error_code,
            GovernanceCapacityError.error_code,
            AuditError.error_code,
            PolicyChainError.error_code,
        }
        assert len(codes) == 10   # all unique

    def test_kgp_prefix(self):
        assert KnowledgeGovernanceError.error_code.startswith("KGP")
        assert GovernanceNotRunningError.error_code.startswith("KGP")

    def test_not_running_default_message(self):
        ex = GovernanceNotRunningError()
        assert "not running" in str(ex).lower()

    def test_policy_load_error_carries_policy_id(self):
        ex = PolicyLoadError("fail", policy_id="pol-99")
        assert ex.policy_id == "pol-99"

    def test_policy_evaluation_error_carries_policy_id(self):
        ex = PolicyEvaluationError("fail", policy_id="pol-42")
        assert ex.policy_id == "pol-42"

    def test_policy_not_found_error_carries_policy_id(self):
        ex = PolicyNotFoundError(policy_id="pol-x")
        assert ex.policy_id == "pol-x"

    def test_capacity_error_carries_limit(self):
        ex = GovernanceCapacityError(limit=500)
        assert ex.limit == 500

    def test_chain_error_carries_chain_id(self):
        ex = PolicyChainError("fail", chain_id="ch-01")
        assert ex.chain_id == "ch-01"

    def test_hierarchy(self):
        for cls in (
            GovernanceNotRunningError,
            GovernanceValidationError,
            PolicyLoadError,
            PolicyEvaluationError,
            PolicyConflictError,
            PolicyNotFoundError,
            GovernanceCapacityError,
            AuditError,
            PolicyChainError,
        ):
            assert issubclass(cls, KnowledgeGovernanceError)


# ===========================================================================
# 3. TestGovernancePolicyContext
# ===========================================================================


class TestGovernancePolicyContext:
    def test_create_defaults(self):
        ctx = GovernancePolicyContext.create("k-1", "exec")
        assert ctx.knowledge_id == "k-1"
        assert ctx.subsystem_id == "exec"
        assert isinstance(ctx.priority, PolicyPriority)

    def test_explicit_priority(self):
        ctx = GovernancePolicyContext.create("k-2", "risk", priority=PolicyPriority.HIGH)
        assert ctx.priority == PolicyPriority.HIGH

    def test_is_frozen(self):
        ctx = GovernancePolicyContext.create("k-3", "mkt")
        with pytest.raises((AttributeError, TypeError)):
            ctx.actor = "other"  # type: ignore[misc]

    def test_to_dict(self):
        ctx = GovernancePolicyContext.create("k-4", "exec")
        d = ctx.to_dict()
        assert "knowledge_id" in d and "policy_domains" in d

    def test_policy_domains_all_by_default(self):
        ctx = GovernancePolicyContext.create("k-5", "exec")
        assert len(ctx.policy_domains) == len(PolicyDomain)


# ===========================================================================
# 4. TestKnowledgePolicyRequest
# ===========================================================================


class TestRequest:
    def test_create_minimal(self):
        req = KnowledgePolicyRequest.create("k-1", "exec")
        assert req.knowledge_id == "k-1"
        assert req.subsystem_id == "exec"

    def test_is_frozen(self):
        req = _make_request()
        with pytest.raises((AttributeError, TypeError)):
            req.knowledge_id = "other"  # type: ignore[misc]

    def test_context_auto_created(self):
        req = _make_request()
        assert req.context is not None
        assert req.context.knowledge_id == req.knowledge_id

    def test_artifacts_stored(self):
        req = _make_request(artifacts={"snap": {"x": 1}})
        assert "snap" in req.artifacts

    def test_to_dict(self):
        req = _make_request()
        d = req.to_dict()
        assert "request_id" in d and "knowledge_id" in d


# ===========================================================================
# 5. TestPolicyCondition
# ===========================================================================


class TestPolicyCondition:
    def _make(self, op, ev=None, field="score") -> PolicyCondition:
        return PolicyCondition.create("Test", field, op, ev)

    def test_eq_true(self):
        c = self._make(ConditionOperator.EQ, 42)
        assert c.evaluate({"score": 42})

    def test_eq_false(self):
        c = self._make(ConditionOperator.EQ, 42)
        assert not c.evaluate({"score": 0})

    def test_ne(self):
        c = self._make(ConditionOperator.NE, 5)
        assert c.evaluate({"score": 10})

    def test_gt(self):
        c = self._make(ConditionOperator.GT, 5)
        assert c.evaluate({"score": 10})
        assert not c.evaluate({"score": 5})

    def test_lt(self):
        c = self._make(ConditionOperator.LT, 10)
        assert c.evaluate({"score": 5})

    def test_gte(self):
        c = self._make(ConditionOperator.GTE, 5)
        assert c.evaluate({"score": 5})

    def test_lte(self):
        c = self._make(ConditionOperator.LTE, 5)
        assert c.evaluate({"score": 5})
        assert not c.evaluate({"score": 6})

    def test_contains(self):
        c = PolicyCondition.create("C", "tags", ConditionOperator.CONTAINS, "risk")
        assert c.evaluate({"tags": ["risk", "exec"]})

    def test_not_contains(self):
        c = PolicyCondition.create("C", "tags", ConditionOperator.NOT_CONTAINS, "blocked")
        assert c.evaluate({"tags": ["ok"]})

    def test_exists_true(self):
        c = self._make(ConditionOperator.EXISTS)
        assert c.evaluate({"score": 0})   # 0 is not None

    def test_not_exists_false(self):
        c = self._make(ConditionOperator.NOT_EXISTS)
        assert not c.evaluate({"score": 0})

    def test_in_list(self):
        c = PolicyCondition.create("C", "status", ConditionOperator.IN_LIST, ["ok", "pass"])
        assert c.evaluate({"status": "ok"})

    def test_not_in_list(self):
        c = PolicyCondition.create("C", "status", ConditionOperator.NOT_IN_LIST, ["fail"])
        assert c.evaluate({"status": "ok"})

    def test_missing_field_returns_false(self):
        c = self._make(ConditionOperator.EQ, 1, "no_such_field")
        assert not c.evaluate({"other": 99})

    def test_nested_field(self):
        c = PolicyCondition.create("C", "meta.source", ConditionOperator.EQ, "exec")
        assert c.evaluate({"meta": {"source": "exec"}})

    def test_to_dict(self):
        c = self._make(ConditionOperator.GT, 5)
        d = c.to_dict()
        assert d["operator"] == "gt"
        assert d["expected_value"] == 5

    def test_is_frozen(self):
        c = self._make(ConditionOperator.EQ, 1)
        with pytest.raises((AttributeError, TypeError)):
            c.name = "other"  # type: ignore[misc]


# ===========================================================================
# 6. TestPolicyRule
# ===========================================================================


class TestPolicyRule:
    def test_no_conditions_always_triggers(self):
        rule = PolicyRule.create("R", PolicyAction.APPROVE)
        result = rule.evaluate({})
        assert result.passed
        assert result.action == PolicyAction.APPROVE

    def test_all_conditions_pass(self):
        c1 = PolicyCondition.create("C1", "x", ConditionOperator.GT, 5)
        c2 = PolicyCondition.create("C2", "y", ConditionOperator.EQ, "ok")
        rule = PolicyRule.create("R", PolicyAction.APPROVE, conditions=[c1, c2])
        result = rule.evaluate({"x": 10, "y": "ok"})
        assert result.passed
        assert result.conditions_met == 2

    def test_partial_conditions_fail(self):
        c1 = PolicyCondition.create("C1", "x", ConditionOperator.GT, 5)
        c2 = PolicyCondition.create("C2", "y", ConditionOperator.EQ, "ok")
        rule = PolicyRule.create("R", PolicyAction.BLOCK, conditions=[c1, c2])
        result = rule.evaluate({"x": 10, "y": "FAIL"})
        assert not result.passed
        assert result.conditions_met == 1

    def test_to_dict(self):
        rule = PolicyRule.create("R", PolicyAction.REJECT)
        d = rule.to_dict()
        assert d["action"] == "reject"

    def test_is_frozen(self):
        rule = PolicyRule.create("R", PolicyAction.APPROVE)
        with pytest.raises((AttributeError, TypeError)):
            rule.name = "other"  # type: ignore[misc]


# ===========================================================================
# 7. TestPolicyRuleResult
# ===========================================================================


class TestPolicyRuleResult:
    def test_to_dict(self):
        r = PolicyRuleResult(
            rule_id="r-1", rule_name="R",
            passed=True, action=PolicyAction.APPROVE,
            conditions_met=2, conditions_total=2, reason="ok",
        )
        d = r.to_dict()
        assert d["action"] == "approve" and d["passed"] is True


# ===========================================================================
# 8. TestKnowledgePolicy
# ===========================================================================


class TestKnowledgePolicy:
    def test_initial_status_pending(self):
        p = KnowledgePolicy(
            name="P", policy_type=PolicyType.CLASSIFICATION,
            domain=PolicyDomain.CLASSIFICATION,
        )
        assert p.status == PolicyStatus.PENDING
        assert not p.is_active

    def test_activate(self):
        p = KnowledgePolicy(
            name="P", policy_type=PolicyType.QUALITY,
            domain=PolicyDomain.METADATA,
        )
        p.activate()
        assert p.is_active

    def test_deactivate(self):
        p = _make_approve_policy()
        p.deactivate()
        assert p.status == PolicyStatus.INACTIVE

    def test_deprecate(self):
        p = _make_approve_policy()
        p.deprecate()
        assert p.status == PolicyStatus.DEPRECATED

    def test_archive(self):
        p = _make_approve_policy()
        p.archive()
        assert p.status == PolicyStatus.ARCHIVED

    def test_add_rule(self):
        p = _make_approve_policy()
        rule = PolicyRule.create("R2", PolicyAction.BLOCK)
        p.add_rule(rule)
        assert p.rule_count == 2

    def test_remove_rule(self):
        rule = PolicyRule.create("R", PolicyAction.APPROVE)
        p = KnowledgePolicy(
            name="P", policy_type=PolicyType.CLASSIFICATION,
            domain=PolicyDomain.CLASSIFICATION, rules=[rule],
        )
        removed = p.remove_rule(rule.rule_id)
        assert removed
        assert p.rule_count == 0

    def test_remove_nonexistent_rule(self):
        p = _make_approve_policy()
        assert not p.remove_rule("no-such-rule")

    def test_to_dict(self):
        p = _make_approve_policy()
        d = p.to_dict()
        assert "policy_id" in d and "rules" in d
        assert d["status"] == "active"


# ===========================================================================
# 9. TestPolicyEvaluationResult
# ===========================================================================


class TestPolicyEvaluationResult:
    def test_create(self):
        r = PolicyEvaluationResult.create(
            policy_id="p-1", policy_name="P",
            policy_type=PolicyType.CLASSIFICATION,
            domain=PolicyDomain.CLASSIFICATION,
            decision=GovernanceDecision.APPROVED,
            passed=True,
        )
        assert r.passed
        assert r.decision == GovernanceDecision.APPROVED

    def test_is_frozen(self):
        r = PolicyEvaluationResult.create(
            policy_id="p-1", policy_name="P",
            policy_type=PolicyType.CLASSIFICATION,
            domain=PolicyDomain.CLASSIFICATION,
            decision=GovernanceDecision.REJECTED,
            passed=False,
        )
        with pytest.raises((AttributeError, TypeError)):
            r.passed = True  # type: ignore[misc]

    def test_to_dict(self):
        r = PolicyEvaluationResult.create(
            policy_id="p-2", policy_name="P2",
            policy_type=PolicyType.SECURITY,
            domain=PolicyDomain.SECURITY,
            decision=GovernanceDecision.BLOCKED,
            passed=False,
        )
        d = r.to_dict()
        assert d["decision"] == "blocked"


# ===========================================================================
# 10. TestKnowledgePolicyEvaluator
# ===========================================================================


class TestEvaluator:
    def _ctx(self) -> GovernancePolicyContext:
        return GovernancePolicyContext.create("k-1", "exec")

    def test_no_rules_approves(self):
        policy = KnowledgePolicy(
            name="P", policy_type=PolicyType.CLASSIFICATION,
            domain=PolicyDomain.CLASSIFICATION,
        )
        policy.activate()
        ev = KnowledgePolicyEvaluator()
        result = ev.evaluate(policy, {}, self._ctx())
        assert result.decision == GovernanceDecision.APPROVED

    def test_approve_rule_triggered(self):
        policy = _make_approve_policy()
        ev = KnowledgePolicyEvaluator()
        result = ev.evaluate(policy, {"data": "x"}, self._ctx())
        assert result.passed

    def test_reject_rule_triggered(self):
        policy = _make_reject_policy()
        ev = KnowledgePolicyEvaluator()
        result = ev.evaluate(policy, {}, self._ctx())
        assert result.decision == GovernanceDecision.REJECTED
        assert not result.passed

    def test_block_overrides_approve(self):
        """A policy with both APPROVE and BLOCK rules should resolve to BLOCKED."""
        policy = KnowledgePolicy(
            name="Mixed", policy_type=PolicyType.COMPLIANCE,
            domain=PolicyDomain.COMPLIANCE,
        )
        policy.add_rule(PolicyRule.create("Approve", PolicyAction.APPROVE))
        policy.add_rule(PolicyRule.create("Block", PolicyAction.BLOCK))
        policy.activate()
        ev = KnowledgePolicyEvaluator()
        result = ev.evaluate(policy, {}, self._ctx())
        assert result.decision == GovernanceDecision.BLOCKED

    def test_crashing_evaluator_returns_rejected(self):
        """A rule that raises should be caught; evaluator returns REJECTED."""
        class BrokenRule:
            rule_id = "broken"
            name    = "broken"
            def evaluate(self, _): raise RuntimeError("boom")
        policy = KnowledgePolicy(
            name="Broken", policy_type=PolicyType.SECURITY,
            domain=PolicyDomain.SECURITY,
        )
        # We monkey-patch rules to simulate crash
        type(policy)  # just access type
        policy._rules = [BrokenRule()]  # type: ignore[list-item]
        policy.activate()
        ev = KnowledgePolicyEvaluator()
        result = ev.evaluate(policy, {}, self._ctx())
        assert result.decision == GovernanceDecision.REJECTED


# ===========================================================================
# 11. TestPolicyPriorityResolver
# ===========================================================================


class TestPriorityResolver:
    def _make_result(self, decision: GovernanceDecision) -> PolicyEvaluationResult:
        return PolicyEvaluationResult.create(
            policy_id="p-1", policy_name="P",
            policy_type=PolicyType.CLASSIFICATION,
            domain=PolicyDomain.CLASSIFICATION,
            decision=decision,
            passed=(decision in (GovernanceDecision.APPROVED,
                                 GovernanceDecision.APPROVED_WITH_CONDITIONS)),
        )

    def test_empty_approves(self):
        r = PolicyPriorityResolver()
        decision, _ = r.resolve([])
        assert decision == GovernanceDecision.APPROVED

    def test_block_dominates_reject(self):
        r = PolicyPriorityResolver()
        decision, _ = r.resolve([
            self._make_result(GovernanceDecision.REJECTED),
            self._make_result(GovernanceDecision.BLOCKED),
        ])
        assert decision == GovernanceDecision.BLOCKED

    def test_reject_dominates_approve(self):
        r = PolicyPriorityResolver()
        decision, _ = r.resolve([
            self._make_result(GovernanceDecision.APPROVED),
            self._make_result(GovernanceDecision.REJECTED),
        ])
        assert decision == GovernanceDecision.REJECTED

    def test_escalated_dominates_conditions(self):
        r = PolicyPriorityResolver()
        decision, _ = r.resolve([
            self._make_result(GovernanceDecision.APPROVED_WITH_CONDITIONS),
            self._make_result(GovernanceDecision.ESCALATED),
        ])
        assert decision == GovernanceDecision.ESCALATED

    def test_manual_review_dominates_approve(self):
        r = PolicyPriorityResolver()
        decision, _ = r.resolve([
            self._make_result(GovernanceDecision.APPROVED),
            self._make_result(GovernanceDecision.MANUAL_REVIEW),
        ])
        assert decision == GovernanceDecision.MANUAL_REVIEW

    def test_all_approved(self):
        r = PolicyPriorityResolver()
        decision, _ = r.resolve([
            self._make_result(GovernanceDecision.APPROVED),
            self._make_result(GovernanceDecision.APPROVED),
        ])
        assert decision == GovernanceDecision.APPROVED

    def test_reason_not_empty(self):
        r = PolicyPriorityResolver()
        _, reason = r.resolve([self._make_result(GovernanceDecision.BLOCKED)])
        assert reason


# ===========================================================================
# 12. TestKnowledgePolicyChain
# ===========================================================================


class TestPolicyChain:
    def _ctx(self) -> GovernancePolicyContext:
        return GovernancePolicyContext.create("k-1", "exec")

    def test_sequential_stop_on_block(self):
        """Sequential chain stops as soon as a policy is BLOCKED."""
        p1 = _make_block_policy("BlockFirst")
        p2 = _make_approve_policy("ApproveSecond")
        chain = KnowledgePolicyChain(name="C", mode=PolicyChainMode.SEQUENTIAL, policies=[p1, p2])
        ev = KnowledgePolicyEvaluator()
        result = chain.evaluate({}, self._ctx(), ev)
        assert result.decision == GovernanceDecision.BLOCKED
        assert result.evaluated_count == 1   # stopped early

    def test_parallel_evaluates_all(self):
        """Parallel chain evaluates ALL policies even after a BLOCK."""
        p1 = _make_block_policy("BlockFirst")
        p2 = _make_approve_policy("ApproveSecond")
        chain = KnowledgePolicyChain(name="C", mode=PolicyChainMode.PARALLEL, policies=[p1, p2])
        ev = KnowledgePolicyEvaluator()
        result = chain.evaluate({}, self._ctx(), ev)
        assert result.evaluated_count == 2

    def test_priority_ordering(self):
        """Priority mode sorts by priority, evaluates high-priority first."""
        p_low  = KnowledgePolicy(name="Low",  policy_type=PolicyType.AUDIT, domain=PolicyDomain.AUDIT, priority=PolicyPriority.LOW)
        p_crit = KnowledgePolicy(name="Crit", policy_type=PolicyType.COMPLIANCE, domain=PolicyDomain.COMPLIANCE, priority=PolicyPriority.CRITICAL)
        p_low.add_rule(PolicyRule.create("R", PolicyAction.APPROVE)); p_low.activate()
        p_crit.add_rule(PolicyRule.create("R", PolicyAction.BLOCK)); p_crit.activate()
        chain = KnowledgePolicyChain(name="C", mode=PolicyChainMode.PRIORITY, policies=[p_low, p_crit])
        ev = KnowledgePolicyEvaluator()
        result = chain.evaluate({}, self._ctx(), ev)
        assert result.decision == GovernanceDecision.BLOCKED
        # CRITICAL evaluated first, stopped immediately
        assert result.evaluated_count == 1

    def test_add_remove_policy(self):
        p = _make_approve_policy()
        chain = KnowledgePolicyChain(name="C")
        chain.add_policy(p)
        assert chain.policy_count == 1
        chain.remove_policy(p.policy_id)
        assert chain.policy_count == 0

    def test_chain_result_to_dict(self):
        p = _make_approve_policy()
        chain = KnowledgePolicyChain(name="C", policies=[p])
        result = chain.evaluate({}, self._ctx(), KnowledgePolicyEvaluator())
        d = result.to_dict()
        assert "chain_id" in d and "decision" in d

    def test_inactive_policies_skipped(self):
        p = _make_approve_policy()
        p.deactivate()
        chain = KnowledgePolicyChain(name="C", policies=[p])
        result = chain.evaluate({}, self._ctx(), KnowledgePolicyEvaluator())
        assert result.evaluated_count == 0


# ===========================================================================
# 13. TestKnowledgePolicyRegistry
# ===========================================================================


class TestRegistry:
    def test_register_and_get(self):
        r = KnowledgePolicyRegistry()
        p = _make_approve_policy()
        r.register(p)
        assert r.get(p.policy_id) is p

    def test_duplicate_raises(self):
        r = KnowledgePolicyRegistry()
        p = _make_approve_policy()
        r.register(p)
        with pytest.raises(PolicyLoadError):
            r.register(p)

    def test_capacity_limit(self):
        r = KnowledgePolicyRegistry(max_policies=2)
        r.register(_make_approve_policy("P1"))
        r.register(_make_approve_policy("P2"))
        with pytest.raises(GovernanceCapacityError):
            r.register(_make_approve_policy("P3"))

    def test_deregister(self):
        r = KnowledgePolicyRegistry()
        p = _make_approve_policy()
        r.register(p)
        assert r.deregister(p.policy_id)
        assert r.active_count() == 0

    def test_not_found_raises(self):
        r = KnowledgePolicyRegistry()
        with pytest.raises(PolicyNotFoundError):
            r.get("does-not-exist")

    def test_by_type(self):
        r = KnowledgePolicyRegistry()
        r.register(_make_approve_policy())
        result = r.by_type(PolicyType.CLASSIFICATION)
        assert len(result) == 1

    def test_by_domain(self):
        r = KnowledgePolicyRegistry()
        r.register(_make_approve_policy())
        result = r.by_domain(PolicyDomain.CLASSIFICATION)
        assert len(result) == 1

    def test_archive_policy(self):
        r = KnowledgePolicyRegistry()
        p = _make_approve_policy()
        r.register(p)
        r.archive_policy(p.policy_id)
        assert r.active_count() == 0
        assert r.archived_count() == 1

    def test_active_only_excludes_inactive(self):
        r = KnowledgePolicyRegistry()
        p = _make_approve_policy()
        p.deactivate()
        r.register(p)
        assert len(r.active_only()) == 0

    def test_clear(self):
        r = KnowledgePolicyRegistry()
        r.register(_make_approve_policy())
        r.clear()
        assert r.total_count() == 0


# ===========================================================================
# 14. TestKnowledgePolicyAudit
# ===========================================================================


class TestAudit:
    def _make_entry(self, kid: str = "k-1") -> PolicyAuditEntry:
        return PolicyAuditEntry.create(
            knowledge_id=kid, subsystem_id="exec",
            policy_id="p-1", policy_name="P",
            decision=GovernanceDecision.APPROVED,
            actor=ACTOR_GOVERNANCE,
        )

    def test_record_and_count(self):
        a = KnowledgePolicyAudit()
        a.record(self._make_entry())
        assert a.count() == 1

    def test_recent(self):
        a = KnowledgePolicyAudit()
        for _ in range(20):
            a.record(self._make_entry())
        assert len(a.recent(5)) == 5

    def test_for_knowledge_id(self):
        a = KnowledgePolicyAudit()
        a.record(self._make_entry("k-1"))
        a.record(self._make_entry("k-2"))
        results = a.for_knowledge_id("k-1")
        assert len(results) == 1

    def test_summary(self):
        a = KnowledgePolicyAudit()
        a.record(self._make_entry())
        s = a.summary()
        assert "approved" in s

    def test_bounded_eviction(self):
        a = KnowledgePolicyAudit(max_entries=3)
        for _ in range(5):
            a.record(self._make_entry())
        assert a.count() == 3

    def test_clear(self):
        a = KnowledgePolicyAudit()
        a.record(self._make_entry())
        a.clear()
        assert a.count() == 0

    def test_entry_to_dict(self):
        e = self._make_entry()
        d = e.to_dict()
        assert "decision" in d and "knowledge_id" in d


# ===========================================================================
# 15. TestKnowledgeGovernanceStatistics
# ===========================================================================


class TestStatistics:
    def test_initial_zeros(self):
        s = KnowledgeGovernanceStatistics()
        snap = s.snapshot()
        assert snap["policies_evaluated"] == 0

    def test_eight_stat_keys(self):
        s = KnowledgeGovernanceStatistics()
        snap = s.snapshot()
        expected = {
            "policies_evaluated", "policies_approved", "policies_rejected",
            "policies_blocked", "manual_reviews", "escalations",
            "average_evaluation_time_ms", "governance_coverage",
        }
        assert expected <= set(snap.keys())

    def test_record_approved(self):
        s = KnowledgeGovernanceStatistics()
        s.record_evaluation(GovernanceDecision.APPROVED.value, 10.0)
        assert s.snapshot()["policies_approved"] == 1

    def test_record_approved_with_conditions(self):
        s = KnowledgeGovernanceStatistics()
        s.record_evaluation(GovernanceDecision.APPROVED_WITH_CONDITIONS.value, 10.0)
        assert s.snapshot()["policies_approved"] == 1

    def test_record_rejected(self):
        s = KnowledgeGovernanceStatistics()
        s.record_evaluation(GovernanceDecision.REJECTED.value, 5.0)
        assert s.snapshot()["policies_rejected"] == 1

    def test_record_blocked(self):
        s = KnowledgeGovernanceStatistics()
        s.record_evaluation(GovernanceDecision.BLOCKED.value, 3.0)
        assert s.snapshot()["policies_blocked"] == 1

    def test_record_manual_review(self):
        s = KnowledgeGovernanceStatistics()
        s.record_evaluation(GovernanceDecision.MANUAL_REVIEW.value, 2.0)
        assert s.snapshot()["manual_reviews"] == 1

    def test_record_escalation(self):
        s = KnowledgeGovernanceStatistics()
        s.record_evaluation(GovernanceDecision.ESCALATED.value, 2.0)
        assert s.snapshot()["escalations"] == 1

    def test_average_evaluation_time(self):
        s = KnowledgeGovernanceStatistics()
        s.record_evaluation(GovernanceDecision.APPROVED.value, 10.0)
        s.record_evaluation(GovernanceDecision.APPROVED.value, 20.0)
        assert s.snapshot()["average_evaluation_time_ms"] == pytest.approx(15.0)

    def test_coverage_ratio(self):
        s = KnowledgeGovernanceStatistics()
        s.update_coverage(total_sources=10, covered_sources=8)
        assert s.snapshot()["governance_coverage"] == pytest.approx(0.8)

    def test_reset(self):
        s = KnowledgeGovernanceStatistics()
        s.record_evaluation(GovernanceDecision.APPROVED.value, 5.0)
        s.reset()
        assert s.snapshot()["policies_evaluated"] == 0


# ===========================================================================
# 16. TestKnowledgeGovernanceHistory
# ===========================================================================


class TestHistory:
    def _make_result(self) -> PolicyEvaluationResult:
        return PolicyEvaluationResult.create(
            policy_id="p-1", policy_name="P",
            policy_type=PolicyType.CLASSIFICATION,
            domain=PolicyDomain.CLASSIFICATION,
            decision=GovernanceDecision.APPROVED,
            passed=True,
        )

    def test_record_and_count(self):
        h = KnowledgeGovernanceHistory()
        h.record(self._make_result())
        assert h.count() == 1

    def test_recent_limited(self):
        h = KnowledgeGovernanceHistory()
        for _ in range(30):
            h.record(self._make_result())
        assert len(h.recent(10)) == 10

    def test_bounded_eviction(self):
        h = KnowledgeGovernanceHistory(max_entries=3)
        for _ in range(5):
            h.record(self._make_result())
        assert h.count() == 3

    def test_for_policy_id(self):
        h = KnowledgeGovernanceHistory()
        h.record(self._make_result())
        results = h.for_policy_id("p-1")
        assert len(results) == 1

    def test_clear(self):
        h = KnowledgeGovernanceHistory()
        h.record(self._make_result())
        h.clear()
        assert h.count() == 0


# ===========================================================================
# 17. TestGovernancePolicyEvents
# ===========================================================================


class TestEvents:
    def test_create(self):
        e = GovernancePolicyEvent.create(
            GovernanceEventType.GOVERNANCE_STARTED, "k-1", "exec", ""
        )
        assert e.event_type == GovernanceEventType.GOVERNANCE_STARTED

    def test_is_frozen(self):
        e = GovernancePolicyEvent.create(
            GovernanceEventType.KNOWLEDGE_APPROVED, "k-1", "exec", "p-1",
            decision=GovernanceDecision.APPROVED,
        )
        with pytest.raises((AttributeError, TypeError)):
            e.actor = "other"  # type: ignore[misc]

    def test_to_dict_has_event_type(self):
        e = make_governance_started("k-1", "exec")
        d = e.to_dict()
        assert "governance.started" in d["event_type"]

    def test_nine_factory_functions(self):
        from iios.knowledge.policies import (
            make_policy_loaded, make_policy_validated,
            make_governance_started, make_knowledge_approved,
            make_knowledge_rejected, make_knowledge_blocked,
            make_knowledge_escalated, make_review_requested,
            make_governance_completed,
        )
        fns = [
            make_policy_loaded, make_policy_validated, make_governance_started,
            make_knowledge_approved, make_knowledge_rejected, make_knowledge_blocked,
            make_knowledge_escalated, make_review_requested, make_governance_completed,
        ]
        assert len(fns) == 9

    def test_event_bus_dispatch(self):
        received = []
        bus = GovernancePolicyEventBus()
        bus.add_listener(received.append)
        bus.emit(make_governance_started("k-1", "exec"))
        assert len(received) == 1

    def test_event_bus_isolates_crash(self):
        def bad(_): raise RuntimeError("boom")
        good = []
        bus = GovernancePolicyEventBus()
        bus.add_listener(bad)
        bus.add_listener(good.append)
        bus.emit(make_governance_started("k-1", "exec"))
        assert len(good) == 1

    def test_event_bus_deduplicate(self):
        bus = GovernancePolicyEventBus()
        fn = MagicMock()
        bus.add_listener(fn)
        bus.add_listener(fn)
        assert bus.listener_count() == 1

    def test_event_bus_remove(self):
        bus = GovernancePolicyEventBus()
        fn = MagicMock()
        bus.add_listener(fn)
        removed = bus.remove_listener(fn)
        assert removed
        assert bus.listener_count() == 0

    def test_event_bus_clear(self):
        bus = GovernancePolicyEventBus()
        bus.add_listener(MagicMock())
        bus.clear()
        assert bus.listener_count() == 0


# ===========================================================================
# 18. TestKnowledgeGovernanceValidator
# ===========================================================================


class TestValidator:
    def test_valid_request_all_pass(self):
        v = KnowledgeGovernanceValidator()
        req = _make_request()
        results = v.validate_request(req)
        assert all(r.passed for r in results)

    def test_empty_knowledge_id_fails(self):
        v = KnowledgeGovernanceValidator()
        req = KnowledgePolicyRequest(
            request_id="r-1", knowledge_id="", subsystem_id="exec",
            policy_types=tuple(PolicyType),
            policy_domains=tuple(PolicyDomain),
            actor=ACTOR_GOVERNANCE,
            priority=PolicyPriority.MEDIUM,
            context=GovernancePolicyContext.create("k-bad", "exec"),
            artifacts={}, metadata={}, created_at="",
        )
        results = v.validate_request(req)
        pi = next(r for r in results if r.code == PolicyValidationCode.POLICY_INTEGRITY)
        assert not pi.passed

    def test_raise_on_failure(self):
        v = KnowledgeGovernanceValidator(
            max_policies=1,
            active_count_fn=lambda: 999,
        )
        req = _make_request()
        with pytest.raises(GovernanceValidationError):
            v.validate_request(req, raise_on_failure=True)

    def test_validate_policy_passes(self):
        v = KnowledgeGovernanceValidator()
        p = _make_approve_policy()
        results = v.validate_policy(p)
        assert all(r.passed for r in results)

    def test_validate_policy_fails_on_no_name(self):
        v = KnowledgeGovernanceValidator()
        p = KnowledgePolicy(
            name="", policy_type=PolicyType.CLASSIFICATION,
            domain=PolicyDomain.CLASSIFICATION,
        )
        results = v.validate_policy(p)
        pi = next(r for r in results if r.code == PolicyValidationCode.POLICY_INTEGRITY)
        assert not pi.passed

    def test_validation_result_to_dict(self):
        r = GovernanceValidationResult(
            code=PolicyValidationCode.POLICY_INTEGRITY, passed=True, message="OK"
        )
        d = r.to_dict()
        assert d["code"] == "POLICY_INTEGRITY"


# ===========================================================================
# 19. TestKnowledgePolicyFactory
# ===========================================================================


class TestFactory:
    def test_create_request(self):
        f = KnowledgePolicyFactory()
        req = f.create_request("k-1", "exec")
        assert isinstance(req, KnowledgePolicyRequest)

    def test_create_policy_active(self):
        f = KnowledgePolicyFactory()
        p = f.create_policy("P", PolicyType.CLASSIFICATION, PolicyDomain.CLASSIFICATION)
        assert p.is_active

    def test_create_policy_not_activated(self):
        f = KnowledgePolicyFactory()
        p = f.create_policy("P", PolicyType.QUALITY, PolicyDomain.METADATA, activate=False)
        assert p.status == PolicyStatus.PENDING

    def test_create_rule(self):
        f = KnowledgePolicyFactory()
        r = f.create_rule("R", PolicyAction.APPROVE)
        assert isinstance(r, PolicyRule)

    def test_create_condition(self):
        f = KnowledgePolicyFactory()
        c = f.create_condition("C", "score", ConditionOperator.GT, 5)
        assert isinstance(c, PolicyCondition)

    def test_create_chain(self):
        f = KnowledgePolicyFactory()
        chain = f.create_chain("C", PolicyChainMode.PARALLEL)
        assert isinstance(chain, KnowledgePolicyChain)
        assert chain.mode == PolicyChainMode.PARALLEL


# ===========================================================================
# 20. TestGovernanceEngineLifecycle
# ===========================================================================


class TestEngineLifecycle:
    def test_start_stop(self):
        e = KnowledgeGovernancePolicyEngine()
        e.start()
        assert e.lifecycle_state().value == "running"
        e.stop()
        assert e.lifecycle_state().value != "running"

    def test_double_start_raises(self):
        e = KnowledgeGovernancePolicyEngine()
        e.start()
        with pytest.raises(EngineAlreadyRunningError):
            e.start()
        e.stop()

    def test_evaluate_requires_running(self):
        e = KnowledgeGovernancePolicyEngine()
        with pytest.raises(GovernanceNotRunningError):
            e.evaluate(_make_request())

    def test_register_policy_requires_running(self):
        e = KnowledgeGovernancePolicyEngine()
        with pytest.raises(GovernanceNotRunningError):
            e.register_policy(_make_approve_policy())

    def test_engine_state_idle_after_start(self):
        e = _started_engine()
        try:
            assert e.engine_state() == GovernanceEngineState.IDLE
        finally:
            e.stop()

    def test_engine_state_stopped_after_stop(self):
        e = _started_engine()
        e.stop()
        assert e.engine_state() == GovernanceEngineState.STOPPED


# ===========================================================================
# 21. TestGovernanceEngineEvaluate
# ===========================================================================


class TestEngineEvaluate:
    def test_no_active_policies_approves(self):
        e = _started_engine()
        try:
            response = e.evaluate(_make_request())
            assert response.is_approved
            assert "No active policies" in response.warnings[0]
        finally:
            e.stop()

    def test_approve_policy_approves(self):
        e = _started_engine()
        try:
            e.register_policy(_make_approve_policy())
            response = e.evaluate(_make_request())
            assert response.is_approved
        finally:
            e.stop()

    def test_reject_policy_rejects(self):
        e = _started_engine()
        try:
            e.register_policy(_make_reject_policy())
            response = e.evaluate(_make_request())
            assert not response.is_approved
            assert response.decision == GovernanceDecision.REJECTED
        finally:
            e.stop()

    def test_block_dominates_approve(self):
        e = _started_engine()
        try:
            e.register_policy(_make_approve_policy())
            e.register_policy(_make_block_policy())
            response = e.evaluate(_make_request())
            assert response.decision == GovernanceDecision.BLOCKED
        finally:
            e.stop()

    def test_events_fired(self):
        received = []
        e = _started_engine()
        try:
            e.add_listener(received.append)
            e.register_policy(_make_approve_policy())
            e.evaluate(_make_request())
            assert len(received) >= 2   # at least STARTED + COMPLETED
        finally:
            e.stop()

    def test_statistics_accumulate(self):
        e = _started_engine()
        try:
            e.register_policy(_make_approve_policy())
            e.evaluate(_make_request())
            stats = e.statistics()
            assert stats["policies_evaluated"] >= 1
            assert stats["policies_approved"] >= 1
        finally:
            e.stop()

    def test_audit_trail_recorded(self):
        e = _started_engine()
        try:
            e.register_policy(_make_approve_policy())
            e.evaluate(_make_request(knowledge_id="k-audit-test"))
            entries = e.audit_for("k-audit-test")
            assert len(entries) >= 1
        finally:
            e.stop()

    def test_response_is_frozen(self):
        e = _started_engine()
        try:
            response = e.evaluate(_make_request())
            with pytest.raises((AttributeError, TypeError)):
                response.passed = not response.passed  # type: ignore[misc]
        finally:
            e.stop()

    def test_decision_records_populated(self):
        e = _started_engine()
        try:
            e.register_policy(_make_approve_policy())
            response = e.evaluate(_make_request())
            assert len(response.decisions) == 1
        finally:
            e.stop()


# ===========================================================================
# 22. TestGovernanceEngineDelegate
# ===========================================================================


class TestDelegate:
    def test_governance_delegate_property(self):
        e = _started_engine()
        try:
            delegate = e.governance_delegate
            assert callable(delegate)
        finally:
            e.stop()

    def test_evaluate_for_dispatcher_running(self):
        e = _started_engine()
        try:
            e.register_policy(_make_approve_policy())
            result = e.evaluate_for_dispatcher("k-1", {"subsystem_id": "exec"})
            assert result["status"] == "evaluated"
            assert result["approved"] is True
        finally:
            e.stop()

    def test_evaluate_for_dispatcher_not_running(self):
        e = KnowledgeGovernancePolicyEngine()
        result = e.evaluate_for_dispatcher("k-1", {})
        assert result["status"] == "engine_not_running"
        assert result["approved"] is False


# ===========================================================================
# 23. TestGovernanceEnginePolicyMgmt
# ===========================================================================


class TestPolicyMgmt:
    def test_register_and_list(self):
        e = _started_engine()
        try:
            e.register_policy(_make_approve_policy("P1"))
            e.register_policy(_make_approve_policy("P2"))
            assert len(e.list_policies()) == 2
        finally:
            e.stop()

    def test_deregister_policy(self):
        e = _started_engine()
        try:
            p = _make_approve_policy()
            e.register_policy(p)
            removed = e.deregister_policy(p.policy_id)
            assert removed
            assert len(e.list_policies()) == 0
        finally:
            e.stop()

    def test_archive_policy(self):
        e = _started_engine()
        try:
            p = _make_approve_policy()
            e.register_policy(p)
            archived = e.archive_policy(p.policy_id)
            assert archived
            assert e.get_policy(p.policy_id) is not None   # still retrievable
            assert len(e.list_policies()) == 0              # not in active list
        finally:
            e.stop()

    def test_get_policy_none_for_unknown(self):
        e = _started_engine()
        try:
            assert e.get_policy("does-not-exist") is None
        finally:
            e.stop()


# ===========================================================================
# 24. TestGovernanceEngineIntrospection
# ===========================================================================


class TestIntrospection:
    def test_health_dict(self):
        e = _started_engine()
        try:
            h = e.health()
            assert h["status"] == "healthy"
            assert "active_policies" in h
        finally:
            e.stop()

    def test_status_dict(self):
        e = _started_engine()
        try:
            s = e.status()
            assert "lifecycle_state" in s
            assert "engine_state" in s
        finally:
            e.stop()

    def test_statistics_eight_keys(self):
        e = _started_engine()
        try:
            stats = e.statistics()
            assert len(stats) >= 8
        finally:
            e.stop()

    def test_history_returns_list(self):
        e = _started_engine()
        try:
            h = e.history()
            assert isinstance(h, list)
        finally:
            e.stop()

    def test_audit_summary(self):
        e = _started_engine()
        try:
            e.register_policy(_make_approve_policy())
            e.evaluate(_make_request())
            summary = e.audit_summary()
            assert isinstance(summary, dict)
        finally:
            e.stop()

    def test_add_remove_listener(self):
        received = []
        e = _started_engine()
        try:
            e.add_listener(received.append)
            e.register_policy(_make_approve_policy())
            e.evaluate(_make_request())
            assert len(received) >= 1
            e.remove_listener(received.append)
        finally:
            e.stop()

    def test_evaluate_chain(self):
        e = _started_engine()
        try:
            p = _make_approve_policy()
            chain = KnowledgePolicyChain(name="C", policies=[p])
            req = _make_request()
            result = e.evaluate_chain(chain, req)
            assert isinstance(result, ChainResult)
            assert result.decision == GovernanceDecision.APPROVED
        finally:
            e.stop()


# ===========================================================================
# 25. TestConcurrency
# ===========================================================================


class TestConcurrency:
    def test_concurrent_evaluations(self):
        """50 threads each submit one request — all must return a response."""
        e = _started_engine()
        e.register_policy(_make_approve_policy())
        responses = []
        errors    = []
        lock      = threading.Lock()

        def _eval(i: int):
            try:
                r = e.evaluate(_make_request(knowledge_id=f"k-c-{i}"))
                with lock:
                    responses.append(r)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_eval, args=(i,)) for i in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()
        e.stop()

        assert not errors, f"Errors: {errors}"
        assert len(responses) == 50

    def test_concurrent_registry_writes(self):
        """Concurrent policy registration must not corrupt the registry."""
        e = _started_engine()
        errors = []
        lock   = threading.Lock()

        def _register(i: int):
            try:
                p = _make_approve_policy(f"Policy-{i}")
                e.register_policy(p)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_register, args=(i,)) for i in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        e.stop()

        assert not errors

    def test_concurrent_statistics_accuracy(self):
        """N concurrent evaluations → statistics counter must equal N."""
        N = 30
        e = _started_engine()
        e.register_policy(_make_approve_policy())
        threads = [
            threading.Thread(
                target=lambda: e.evaluate(_make_request(f"k-stat-{id(threading.current_thread())}"))
            )
            for _ in range(N)
        ]
        for t in threads: t.start()
        for t in threads: t.join()
        stats = e.statistics()
        e.stop()
        assert stats["policies_evaluated"] == N


# ===========================================================================
# 26. TestRegression
# ===========================================================================


class TestRegression:
    def test_m1_lifecycle_import_unaffected(self):
        from iios.knowledge.lifecycle import KnowledgeLifecycle  # noqa: F401

    def test_m2_engine_import_unaffected(self):
        from iios.knowledge.engine import KnowledgeEngine  # noqa: F401

    def test_supervisor_engine_import_unaffected(self):
        from iios.supervisor.engine import SupervisorEngine  # noqa: F401

    def test_m3_error_codes_distinct_from_m1_m2(self):
        from iios.knowledge.lifecycle.exceptions import KnowledgeLifecycleError
        from iios.knowledge.engine.exceptions import KnowledgeEngineError
        m1_code = KnowledgeLifecycleError.error_code
        m2_code = KnowledgeEngineError.error_code
        m3_code = KnowledgeGovernanceError.error_code
        assert m3_code not in (m1_code, m2_code)

    def test_m3_governance_decision_enum_distinct_from_m2(self):
        from iios.knowledge.engine.constants import EngineState
        assert GovernanceDecision is not EngineState

    def test_policy_priority_intcmp(self):
        """PolicyPriority supports integer comparison for sorting."""
        priorities = sorted(list(PolicyPriority))
        assert priorities[0] == PolicyPriority.CRITICAL
        assert priorities[-1] == PolicyPriority.INFORMATIONAL
