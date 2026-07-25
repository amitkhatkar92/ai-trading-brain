"""
tests/unit/workflow/test_workflow_policies_m3.py
-------------------------------------------------
Comprehensive tests for C16 M3: Workflow Governance Policy Framework.

Coverage target: 95%+
"""
import re
import threading
import time
import uuid

import pytest

# ── module imports ────────────────────────────────────────────────────────────
from iios.workflow.policies import (
    # Constants & enums
    ACTION_PRECEDENCE,
    ConditionOperator,
    GovernanceDecision,
    PolicyAction,
    PolicyChainMode,
    PolicyDomain,
    PolicyEventType,
    PolicyPriorityLevel,
    PolicyType,
    action_to_decision,
    higher_authority,
    # Exceptions
    WorkflowEmergencyStopError,
    WorkflowGovernanceDecisionError,
    WorkflowPolicyAuditError,
    WorkflowPolicyChainError,
    WorkflowPolicyConflictError,
    WorkflowPolicyEngineError,
    WorkflowPolicyError,
    WorkflowPolicyEvaluationError,
    WorkflowPolicyNotFoundError,
    WorkflowPolicyRegistryError,
    WorkflowPolicyValidationError,
    # Domain objects
    PolicyCondition,
    PolicyPriorityItem,
    PolicyRule,
    PolicyValidationResult,
    WorkflowPolicy,
    WorkflowPolicyAudit,
    WorkflowPolicyAuditRecord,
    WorkflowPolicyChain,
    WorkflowPolicyContext,
    WorkflowPolicyEngine,
    WorkflowPolicyEvaluator,
    WorkflowPolicyEvent,
    WorkflowPolicyEventBus,
    WorkflowPolicyFactory,
    WorkflowPolicyHistory,
    WorkflowPolicyManager,
    WorkflowPolicyRegistry,
    WorkflowPolicyRequest,
    WorkflowPolicyResponse,
    WorkflowPolicyResult,
    WorkflowPolicyStatistics,
    WorkflowPolicyStatisticsReport,
    WorkflowPolicyValidator,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def simple_context():
    return WorkflowPolicyContext.create(
        workflow_id   = "wf-test-001",
        workflow_type = "sequential",
    )


@pytest.fixture()
def rich_context():
    return WorkflowPolicyContext.create(
        workflow_id         = "wf-rich-001",
        workflow_type       = "parallel",
        enterprise_id       = "ent-corp",
        environment         = "production",
        security_context    = {"authenticated": True, "user_role": "admin", "threat_level": "low"},
        compliance_context  = {"risk_score": 0.3, "jurisdiction": "US"},
        resource_context    = {"cpu_limit": 4, "memory_gb": 16},
        metadata            = {"order_value": 5000},
    )


@pytest.fixture()
def approve_all_policy():
    return WorkflowPolicyFactory.create_approve_all_policy("test-approve-all")


@pytest.fixture()
def reject_all_policy():
    return WorkflowPolicyFactory.create_reject_all_policy("test-reject-all")


@pytest.fixture()
def started_manager(approve_all_policy):
    mgr = WorkflowPolicyManager()
    mgr.start()
    mgr.register_policy(approve_all_policy)
    yield mgr
    mgr.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Constants & Enums
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_policy_type_count(self):
        assert len(PolicyType) == 14

    def test_policy_action_count(self):
        assert len(PolicyAction) == 8

    def test_governance_decision_count(self):
        assert len(GovernanceDecision) >= 9

    def test_condition_operator_count(self):
        assert len(ConditionOperator) == 15

    def test_action_precedence_all_actions(self):
        for action in PolicyAction:
            assert action in ACTION_PRECEDENCE, f"{action} missing from precedence table"

    def test_emergency_stop_highest_precedence(self):
        assert ACTION_PRECEDENCE[PolicyAction.EMERGENCY_STOP] == 0

    def test_approve_lowest_precedence(self):
        assert ACTION_PRECEDENCE[PolicyAction.APPROVE] == max(ACTION_PRECEDENCE.values())

    def test_higher_authority_returns_emergency_over_approve(self):
        result = higher_authority(PolicyAction.EMERGENCY_STOP, PolicyAction.APPROVE)
        assert result == PolicyAction.EMERGENCY_STOP

    def test_higher_authority_symmetric(self):
        a = higher_authority(PolicyAction.BLOCK, PolicyAction.REJECT)
        b = higher_authority(PolicyAction.REJECT, PolicyAction.BLOCK)
        assert a == b == PolicyAction.BLOCK

    def test_action_to_decision_approve(self):
        assert action_to_decision(PolicyAction.APPROVE) == GovernanceDecision.APPROVED

    def test_action_to_decision_emergency_stop(self):
        d = action_to_decision(PolicyAction.EMERGENCY_STOP)
        assert d == GovernanceDecision.EMERGENCY_STOPPED

    def test_policy_priority_level_ordering(self):
        assert PolicyPriorityLevel.CRITICAL.value < PolicyPriorityLevel.HIGH.value
        assert PolicyPriorityLevel.HIGH.value < PolicyPriorityLevel.MEDIUM.value

    def test_policy_domain_count(self):
        assert len(PolicyDomain) == 12

    def test_policy_chain_mode_values(self):
        assert PolicyChainMode.SEQUENTIAL.value == "sequential"
        assert PolicyChainMode.PARALLEL.value == "parallel"
        assert PolicyChainMode.COMPOSITE.value == "composite"

    def test_policy_event_type_count(self):
        assert len(PolicyEventType) == 9


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_exception_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(WorkflowPolicyError, IIOSError)

    def test_all_exceptions_inherit_from_base(self):
        for exc_cls in [
            WorkflowPolicyNotFoundError,
            WorkflowPolicyValidationError,
            WorkflowPolicyEvaluationError,
            WorkflowPolicyConflictError,
            WorkflowGovernanceDecisionError,
            WorkflowPolicyChainError,
            WorkflowPolicyRegistryError,
            WorkflowPolicyAuditError,
            WorkflowPolicyEngineError,
            WorkflowEmergencyStopError,
        ]:
            assert issubclass(exc_cls, WorkflowPolicyError)

    def test_not_found_has_policy_id(self):
        err = WorkflowPolicyNotFoundError("pol-abc")
        assert "pol-abc" in str(err)

    def test_validation_error_has_issues(self):
        issues = ["name is empty", "domain invalid"]
        err = WorkflowPolicyValidationError("bad policy", issues=issues)
        assert err.issues == issues

    def test_emergency_stop_error(self):
        err = WorkflowEmergencyStopError("pol-x")
        assert "pol-x" in str(err)

    def test_exception_codes_are_wgp(self):
        err = WorkflowPolicyError("msg")
        assert "WGP" in err.code

    def test_exception_str_contains_message(self):
        err = WorkflowPolicyEngineError("engine failed")
        assert "engine failed" in str(err)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PolicyCondition
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyCondition:
    def test_create_with_defaults(self):
        c = PolicyCondition.create(
            field    = "security_context.authenticated",
            operator = ConditionOperator.EQUALS,
            value    = True,
        )
        assert c.field == "security_context.authenticated"
        assert c.operator == ConditionOperator.EQUALS
        assert c.value is True
        assert c.condition_id.startswith("pcond-")

    def test_custom_id(self):
        c = PolicyCondition.create(
            field    = "f",
            operator = ConditionOperator.IS_NOT_NULL,
            value    = None,
            condition_id = "pcond-custom",
        )
        assert c.condition_id == "pcond-custom"

    def test_equals_true(self):
        c = PolicyCondition.create("x", ConditionOperator.EQUALS, 42)
        assert c.evaluate({"x": 42}) is True

    def test_equals_false(self):
        c = PolicyCondition.create("x", ConditionOperator.EQUALS, 42)
        assert c.evaluate({"x": 43}) is False

    def test_not_equals(self):
        c = PolicyCondition.create("x", ConditionOperator.NOT_EQUALS, 1)
        assert c.evaluate({"x": 2}) is True
        assert c.evaluate({"x": 1}) is False

    def test_greater_than(self):
        c = PolicyCondition.create("v", ConditionOperator.GREATER_THAN, 0.5)
        assert c.evaluate({"v": 0.8}) is True
        assert c.evaluate({"v": 0.3}) is False

    def test_less_than(self):
        c = PolicyCondition.create("v", ConditionOperator.LESS_THAN, 100)
        assert c.evaluate({"v": 50}) is True
        assert c.evaluate({"v": 100}) is False

    def test_gte(self):
        c = PolicyCondition.create("v", ConditionOperator.GREATER_THAN_OR_EQUAL, 10)
        assert c.evaluate({"v": 10}) is True
        assert c.evaluate({"v": 9}) is False

    def test_lte(self):
        c = PolicyCondition.create("v", ConditionOperator.LESS_THAN_OR_EQUAL, 10)
        assert c.evaluate({"v": 10}) is True
        assert c.evaluate({"v": 11}) is False

    def test_in_operator(self):
        c = PolicyCondition.create("role", ConditionOperator.IN, ["admin", "operator"])
        assert c.evaluate({"role": "admin"}) is True
        assert c.evaluate({"role": "viewer"}) is False

    def test_not_in_operator(self):
        c = PolicyCondition.create("role", ConditionOperator.NOT_IN, ["admin"])
        assert c.evaluate({"role": "viewer"}) is True
        assert c.evaluate({"role": "admin"}) is False

    def test_contains_string(self):
        c = PolicyCondition.create("tags", ConditionOperator.CONTAINS, "GDPR")
        assert c.evaluate({"tags": ["GDPR", "ISO27001"]}) is True
        assert c.evaluate({"tags": ["ISO27001"]}) is False

    def test_not_contains(self):
        c = PolicyCondition.create("tags", ConditionOperator.NOT_CONTAINS, "PII")
        assert c.evaluate({"tags": ["GDPR"]}) is True
        assert c.evaluate({"tags": ["PII", "GDPR"]}) is False

    def test_is_null(self):
        c = PolicyCondition.create("val", ConditionOperator.IS_NULL, None)
        assert c.evaluate({"val": None}) is True
        assert c.evaluate({"val": 0}) is False

    def test_is_not_null(self):
        c = PolicyCondition.create("val", ConditionOperator.IS_NOT_NULL, None)
        assert c.evaluate({"val": "something"}) is True
        assert c.evaluate({}) is False   # missing → None → is_null

    def test_starts_with(self):
        c = PolicyCondition.create("id", ConditionOperator.STARTS_WITH, "wf-")
        assert c.evaluate({"id": "wf-001"}) is True
        assert c.evaluate({"id": "order-001"}) is False

    def test_ends_with(self):
        c = PolicyCondition.create("id", ConditionOperator.ENDS_WITH, "-done")
        assert c.evaluate({"id": "step-done"}) is True
        assert c.evaluate({"id": "step-running"}) is False

    def test_matches_regex(self):
        c = PolicyCondition.create("code", ConditionOperator.MATCHES, r"^\d{4}$")
        assert c.evaluate({"code": "1234"}) is True
        assert c.evaluate({"code": "12345"}) is False

    def test_dot_notation_nested(self):
        c = PolicyCondition.create(
            "security_context.user_role",
            ConditionOperator.EQUALS,
            "admin",
        )
        data = {"security_context": {"user_role": "admin"}}
        assert c.evaluate(data) is True

    def test_dot_notation_missing_returns_false(self):
        c = PolicyCondition.create(
            "security_context.missing_field",
            ConditionOperator.EQUALS,
            "value",
        )
        data = {"security_context": {}}
        assert c.evaluate(data) is False

    def test_to_dict(self):
        c = PolicyCondition.create("x", ConditionOperator.EQUALS, 1)
        d = c.to_dict()
        assert d["field"]    == "x"
        assert d["operator"] == ConditionOperator.EQUALS.value
        assert d["value"]    == 1

    def test_frozen(self):
        c = PolicyCondition.create("f", ConditionOperator.EQUALS, 1)
        with pytest.raises((TypeError, AttributeError)):
            c.field = "other"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PolicyRule
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyRule:
    def _make_cond(self, field, value):
        return PolicyCondition.create(field, ConditionOperator.EQUALS, value)

    def test_create(self):
        rule = PolicyRule.create(
            name   = "test-rule",
            action = PolicyAction.APPROVE,
        )
        assert rule.rule_id.startswith("prule-")
        assert rule.name == "test-rule"
        assert rule.action == PolicyAction.APPROVE
        assert rule.enabled is True

    def test_applies_no_conditions_always_true(self):
        rule = PolicyRule.create("r", PolicyAction.APPROVE)
        assert rule.applies({}) is True

    def test_applies_single_condition_true(self):
        cond = self._make_cond("x", 1)
        rule = PolicyRule.create("r", PolicyAction.APPROVE, conditions=[cond])
        assert rule.applies({"x": 1}) is True

    def test_applies_single_condition_false(self):
        cond = self._make_cond("x", 1)
        rule = PolicyRule.create("r", PolicyAction.APPROVE, conditions=[cond])
        assert rule.applies({"x": 2}) is False

    def test_applies_and_logic(self):
        c1 = self._make_cond("a", 1)
        c2 = self._make_cond("b", 2)
        rule = PolicyRule.create("r", PolicyAction.APPROVE, conditions=[c1, c2])
        assert rule.applies({"a": 1, "b": 2}) is True
        assert rule.applies({"a": 1, "b": 9}) is False

    def test_disabled_rule_never_applies(self):
        rule = PolicyRule.create("r", PolicyAction.APPROVE, enabled=False)
        assert rule.applies({}) is False

    def test_to_dict(self):
        rule = PolicyRule.create("r", PolicyAction.REJECT)
        d = rule.to_dict()
        assert d["name"]   == "r"
        assert d["action"] == PolicyAction.REJECT.value

    def test_frozen(self):
        rule = PolicyRule.create("r", PolicyAction.APPROVE)
        with pytest.raises((TypeError, AttributeError)):
            rule.name = "changed"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. WorkflowPolicyContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyContext:
    def test_create_minimal(self):
        ctx = WorkflowPolicyContext.create("wf-1", "sequential")
        assert ctx.workflow_id == "wf-1"
        assert ctx.context_id.startswith("pctx-")
        assert ctx.correlation_id  # auto-generated
        assert ctx.trace_id        # auto-generated

    def test_to_flat_dict_top_level(self):
        ctx = WorkflowPolicyContext.create("wf-1", "parallel")
        flat = ctx.to_flat_dict()
        assert flat["workflow_id"]   == "wf-1"
        assert flat["workflow_type"] == "parallel"

    def test_to_flat_dict_nested(self):
        ctx = WorkflowPolicyContext.create(
            "wf-1", "seq",
            security_context = {"user_role": "admin"},
        )
        flat = ctx.to_flat_dict()
        assert flat["security_context.user_role"] == "admin"

    def test_to_flat_dict_multiple_nested(self):
        ctx = WorkflowPolicyContext.create(
            "wf-1", "seq",
            compliance_context = {"risk_score": 0.5, "jurisdiction": "US"},
        )
        flat = ctx.to_flat_dict()
        assert flat["compliance_context.risk_score"]   == 0.5
        assert flat["compliance_context.jurisdiction"] == "US"

    def test_to_dict(self):
        ctx = WorkflowPolicyContext.create("wf-1", "seq")
        d = ctx.to_dict()
        assert d["workflow_id"] == "wf-1"

    def test_auto_correlation_id(self):
        ctx = WorkflowPolicyContext.create("wf-1", "seq")
        assert len(ctx.correlation_id) > 0

    def test_explicit_correlation_id(self):
        ctx = WorkflowPolicyContext.create("wf-1", "seq", correlation_id="corr-xyz")
        assert ctx.correlation_id == "corr-xyz"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. WorkflowPolicy
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicy:
    def test_create_minimal(self):
        p = WorkflowPolicy.create("Test Policy", PolicyType.WORKFLOW_GOVERNANCE)
        assert p.policy_id.startswith("pol-")
        assert p.name == "Test Policy"
        assert p.enabled is True
        assert p.default_action == PolicyAction.APPROVE

    def test_rules_sorted_by_priority(self):
        low_cond  = PolicyCondition.create("x", ConditionOperator.EQUALS, 1)
        high_cond = PolicyCondition.create("x", ConditionOperator.EQUALS, 2)
        low_rule  = PolicyRule.create("low",  PolicyAction.APPROVE, priority=PolicyPriorityLevel.LOW)
        high_rule = PolicyRule.create("high", PolicyAction.REJECT,  priority=PolicyPriorityLevel.CRITICAL)
        p = WorkflowPolicy.create(
            "Ordered", PolicyType.WORKFLOW_GOVERNANCE,
            rules = [low_rule, high_rule],
        )
        assert p.rules[0].priority == PolicyPriorityLevel.CRITICAL

    def test_evaluate_no_rules_default_action(self, simple_context):
        p = WorkflowPolicy.create("P", PolicyType.WORKFLOW_GOVERNANCE)
        action, reasoning, rule_id = p.evaluate(simple_context)
        assert action == PolicyAction.APPROVE
        assert rule_id is None

    def test_evaluate_matching_rule(self, simple_context):
        flat = simple_context.to_flat_dict()
        # Use a field we know exists
        field = "workflow_id"
        val   = flat[field]
        cond  = PolicyCondition.create(field, ConditionOperator.EQUALS, val)
        rule  = PolicyRule.create("match", PolicyAction.REJECT, conditions=[cond])
        p     = WorkflowPolicy.create("P", PolicyType.WORKFLOW_GOVERNANCE, rules=[rule])
        action, reasoning, rule_id = p.evaluate(simple_context)
        assert action  == PolicyAction.REJECT
        assert rule_id == rule.rule_id

    def test_evaluate_disabled_policy(self, simple_context):
        rule = PolicyRule.create("r", PolicyAction.REJECT)
        p    = WorkflowPolicy.create("P", PolicyType.WORKFLOW_GOVERNANCE, rules=[rule], enabled=False)
        action, _, _ = p.evaluate(simple_context)
        assert action == PolicyAction.APPROVE   # default, disabled

    def test_rule_count(self):
        r1 = PolicyRule.create("r1", PolicyAction.APPROVE)
        r2 = PolicyRule.create("r2", PolicyAction.REJECT)
        p  = WorkflowPolicy.create("P", PolicyType.WORKFLOW_GOVERNANCE, rules=[r1, r2])
        assert p.rule_count == 2

    def test_is_critical(self):
        p = WorkflowPolicy.create("P", PolicyType.WORKFLOW_GOVERNANCE, priority=PolicyPriorityLevel.CRITICAL)
        assert p.is_critical

    def test_to_dict(self):
        p = WorkflowPolicy.create("P", PolicyType.WORKFLOW_GOVERNANCE)
        d = p.to_dict()
        assert d["name"] == "P"
        assert "policy_type" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 7. WorkflowPolicyRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyRequest:
    def test_create(self, simple_context):
        req = WorkflowPolicyRequest.create("wf-1", simple_context)
        assert req.request_id.startswith("preq-")
        assert req.workflow_id == "wf-1"

    def test_type_filter(self, simple_context):
        req = WorkflowPolicyRequest.create(
            "wf-1", simple_context,
            policy_types = [PolicyType.SECURITY],
        )
        assert req.has_type_filter
        assert not req.has_domain_filter

    def test_domain_filter(self, simple_context):
        req = WorkflowPolicyRequest.create(
            "wf-1", simple_context,
            policy_domains = [PolicyDomain.SECURITY_GOVERNANCE],
        )
        assert req.has_domain_filter
        assert not req.has_type_filter

    def test_no_filter(self, simple_context):
        req = WorkflowPolicyRequest.create("wf-1", simple_context)
        assert not req.has_type_filter
        assert not req.has_domain_filter

    def test_inherits_correlation_from_context(self, simple_context):
        req = WorkflowPolicyRequest.create("wf-1", simple_context)
        assert req.correlation_id == simple_context.correlation_id

    def test_to_dict(self, simple_context):
        req = WorkflowPolicyRequest.create("wf-1", simple_context)
        d = req.to_dict()
        assert d["workflow_id"] == "wf-1"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. WorkflowPolicyResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyResult:
    def _make(self, action=PolicyAction.APPROVE):
        return WorkflowPolicyResult.create(
            policy_id   = "pol-abc",
            policy_name = "Test",
            policy_type = PolicyType.WORKFLOW_GOVERNANCE,
            domain      = PolicyDomain.WORKFLOW_GOVERNANCE,
            priority    = PolicyPriorityLevel.MEDIUM,
            action      = action,
            reasoning   = "test reasoning",
        )

    def test_create(self):
        r = self._make()
        assert r.result_id.startswith("pres-")
        assert r.action == PolicyAction.APPROVE

    def test_is_approval_approve(self):
        assert self._make(PolicyAction.APPROVE).is_approval

    def test_is_approval_with_conditions(self):
        assert self._make(PolicyAction.APPROVE_WITH_CONDITIONS).is_approval

    def test_is_rejection_reject(self):
        assert self._make(PolicyAction.REJECT).is_rejection

    def test_is_rejection_block(self):
        assert self._make(PolicyAction.BLOCK).is_rejection

    def test_is_rejection_emergency(self):
        assert self._make(PolicyAction.EMERGENCY_STOP).is_rejection

    def test_to_dict(self):
        r = self._make()
        d = r.to_dict()
        assert d["action"] == PolicyAction.APPROVE.value


# ═══════════════════════════════════════════════════════════════════════════════
# 9. WorkflowPolicyResponse
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyResponse:
    def _req(self):
        ctx = WorkflowPolicyContext.create("wf-1", "seq")
        return WorkflowPolicyRequest.create("wf-1", ctx)

    def test_approved(self):
        resp = WorkflowPolicyResponse.approved(self._req(), [])
        assert resp.is_approved
        assert resp.can_proceed
        assert resp.decision == GovernanceDecision.APPROVED

    def test_rejected(self):
        resp = WorkflowPolicyResponse.rejected(self._req(), [], "bad policy")
        assert resp.is_rejected
        assert not resp.can_proceed

    def test_blocked(self):
        resp = WorkflowPolicyResponse.blocked(self._req(), [], "blocked")
        assert resp.is_blocked

    def test_emergency_stopped(self):
        resp = WorkflowPolicyResponse.emergency_stopped(self._req(), [], "halt!")
        assert resp.is_emergency_stop

    def test_approved_with_conditions(self):
        resp = WorkflowPolicyResponse.approved_with_conditions(
            self._req(), [], ["cond-1"]
        )
        assert resp.is_approved
        assert "cond-1" in resp.conditions_applied

    def test_to_dict_keys(self):
        resp = WorkflowPolicyResponse.approved(self._req(), [])
        d = resp.to_dict()
        assert "decision" in d
        assert "is_approved" in d
        assert "can_proceed" in d

    def test_response_id_prefix(self):
        resp = WorkflowPolicyResponse.approved(self._req(), [])
        assert resp.response_id.startswith("presp-")


# ═══════════════════════════════════════════════════════════════════════════════
# 10. PolicyPriorityItem
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyPriorityItem:
    def test_create(self):
        p = WorkflowPolicy.create("P", PolicyType.WORKFLOW_GOVERNANCE,
                                  priority=PolicyPriorityLevel.HIGH)
        item = PolicyPriorityItem.create(p, sequence=0)
        assert item.item_id.startswith("ppi-")
        assert item.priority == PolicyPriorityLevel.HIGH.value

    def test_ordering_by_priority(self):
        p_high = WorkflowPolicy.create("H", PolicyType.WORKFLOW_GOVERNANCE,
                                       priority=PolicyPriorityLevel.HIGH)
        p_low  = WorkflowPolicy.create("L", PolicyType.WORKFLOW_GOVERNANCE,
                                       priority=PolicyPriorityLevel.LOW)
        item_h = PolicyPriorityItem.create(p_high, 0)
        item_l = PolicyPriorityItem.create(p_low,  1)
        assert item_h < item_l   # CRITICAL(1) < LOW(3)

    def test_to_dict(self):
        p    = WorkflowPolicy.create("P", PolicyType.WORKFLOW_GOVERNANCE)
        item = PolicyPriorityItem.create(p, 0)
        d    = item.to_dict()
        assert d["policy_id"] == p.policy_id


# ═══════════════════════════════════════════════════════════════════════════════
# 11. WorkflowPolicyEvaluator
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyEvaluator:
    def test_evaluate_approve_all(self, simple_context):
        policy    = WorkflowPolicyFactory.create_approve_all_policy("P")
        evaluator = WorkflowPolicyEvaluator()
        result    = evaluator.evaluate(policy, simple_context)
        assert result.action == PolicyAction.APPROVE

    def test_evaluate_reject_all(self, simple_context):
        policy    = WorkflowPolicyFactory.create_reject_all_policy("P")
        evaluator = WorkflowPolicyEvaluator()
        result    = evaluator.evaluate(policy, simple_context)
        assert result.action == PolicyAction.REJECT

    def test_evaluate_rule_match(self, simple_context):
        flat  = simple_context.to_flat_dict()
        field = "workflow_id"
        cond  = PolicyCondition.create(field, ConditionOperator.EQUALS, flat[field])
        rule  = PolicyRule.create("r", PolicyAction.BLOCK, conditions=[cond])
        policy = WorkflowPolicy.create("P", PolicyType.WORKFLOW_GOVERNANCE, rules=[rule])
        evaluator = WorkflowPolicyEvaluator()
        result = evaluator.evaluate(policy, simple_context)
        assert result.action == PolicyAction.BLOCK
        assert result.matched_rule_id == rule.rule_id

    def test_evaluate_no_match_uses_default(self, simple_context):
        cond   = PolicyCondition.create("workflow_id", ConditionOperator.EQUALS, "nonexistent")
        rule   = PolicyRule.create("r", PolicyAction.REJECT, conditions=[cond])
        policy = WorkflowPolicy.create(
            "P", PolicyType.WORKFLOW_GOVERNANCE,
            rules=[rule], default_action=PolicyAction.APPROVE
        )
        evaluator = WorkflowPolicyEvaluator()
        result    = evaluator.evaluate(policy, simple_context)
        assert result.action == PolicyAction.APPROVE
        assert result.matched_rule_id is None


# ═══════════════════════════════════════════════════════════════════════════════
# 12. WorkflowPolicyValidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyValidator:
    def test_valid_policy_passes(self):
        policy    = WorkflowPolicyFactory.create_approve_all_policy("Valid")
        validator = WorkflowPolicyValidator()
        result    = validator.validate(policy)
        assert result.valid
        assert len(result.issues) == 0

    def test_empty_name_fails(self):
        import dataclasses
        policy    = WorkflowPolicy.create("X", PolicyType.WORKFLOW_GOVERNANCE)
        policy    = dataclasses.replace(policy, name="")
        validator = WorkflowPolicyValidator()
        result    = validator.validate(policy)
        assert not result.valid
        assert any("name" in i for i in result.issues)

    def test_validate_or_raise_raises(self):
        import dataclasses
        policy    = WorkflowPolicy.create("X", PolicyType.WORKFLOW_GOVERNANCE)
        policy    = dataclasses.replace(policy, name="")
        validator = WorkflowPolicyValidator()
        with pytest.raises(WorkflowPolicyValidationError):
            validator.validate_or_raise(policy)

    def test_validate_result_to_dict(self):
        policy    = WorkflowPolicyFactory.create_approve_all_policy("P")
        validator = WorkflowPolicyValidator()
        result    = validator.validate(policy)
        d = result.to_dict()
        assert "valid" in d
        assert "issues" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 13. WorkflowPolicyRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyRegistry:
    def test_register_and_get(self, approve_all_policy):
        reg = WorkflowPolicyRegistry()
        reg.register(approve_all_policy)
        fetched = reg.get(approve_all_policy.policy_id)
        assert fetched.policy_id == approve_all_policy.policy_id

    def test_get_not_found(self):
        reg = WorkflowPolicyRegistry()
        with pytest.raises(WorkflowPolicyNotFoundError):
            reg.get("nonexistent-id")

    def test_get_or_none(self, approve_all_policy):
        reg = WorkflowPolicyRegistry()
        assert reg.get_or_none("missing") is None
        reg.register(approve_all_policy)
        assert reg.get_or_none(approve_all_policy.policy_id) is not None

    def test_exists(self, approve_all_policy):
        reg = WorkflowPolicyRegistry()
        assert not reg.exists(approve_all_policy.policy_id)
        reg.register(approve_all_policy)
        assert reg.exists(approve_all_policy.policy_id)

    def test_get_by_type(self):
        reg = WorkflowPolicyRegistry()
        p   = WorkflowPolicy.create("P", PolicyType.SECURITY)
        reg.register(p)
        results = reg.get_by_type(PolicyType.SECURITY)
        assert any(r.policy_id == p.policy_id for r in results)

    def test_get_by_domain(self):
        reg = WorkflowPolicyRegistry()
        p   = WorkflowPolicy.create(
            "P", PolicyType.WORKFLOW_GOVERNANCE,
            domain=PolicyDomain.RISK_GOVERNANCE,
        )
        reg.register(p)
        results = reg.get_by_domain(PolicyDomain.RISK_GOVERNANCE)
        assert any(r.policy_id == p.policy_id for r in results)

    def test_deregister(self, approve_all_policy):
        reg = WorkflowPolicyRegistry()
        reg.register(approve_all_policy)
        removed = reg.deregister(approve_all_policy.policy_id)
        assert removed is True
        assert not reg.exists(approve_all_policy.policy_id)

    def test_deregister_not_found(self):
        reg = WorkflowPolicyRegistry()
        assert reg.deregister("ghost") is False

    def test_policy_count(self, approve_all_policy):
        reg = WorkflowPolicyRegistry()
        assert reg.policy_count() == 0
        reg.register(approve_all_policy)
        assert reg.policy_count() == 1

    def test_clear(self, approve_all_policy):
        reg = WorkflowPolicyRegistry()
        reg.register(approve_all_policy)
        n = reg.clear()
        assert n == 1
        assert reg.policy_count() == 0

    def test_capacity_limit(self):
        reg = WorkflowPolicyRegistry(max_policies=2)
        reg.register(WorkflowPolicy.create("P1", PolicyType.WORKFLOW_GOVERNANCE))
        reg.register(WorkflowPolicy.create("P2", PolicyType.WORKFLOW_GOVERNANCE))
        with pytest.raises(WorkflowPolicyRegistryError):
            reg.register(WorkflowPolicy.create("P3", PolicyType.WORKFLOW_GOVERNANCE))

    def test_all_policies(self):
        reg = WorkflowPolicyRegistry()
        p1  = WorkflowPolicy.create("P1", PolicyType.WORKFLOW_GOVERNANCE)
        p2  = WorkflowPolicy.create("P2", PolicyType.SECURITY)
        reg.register(p1); reg.register(p2)
        all_p = reg.all_policies()
        assert len(all_p) == 2

    def test_enabled_policies(self):
        import dataclasses
        reg = WorkflowPolicyRegistry()
        p1  = WorkflowPolicy.create("P1", PolicyType.WORKFLOW_GOVERNANCE)
        p2  = WorkflowPolicy.create("P2", PolicyType.WORKFLOW_GOVERNANCE)
        p2  = dataclasses.replace(p2, enabled=False)
        reg.register(p1); reg.register(p2)
        enabled = reg.enabled_policies()
        assert len(enabled) == 1
        assert enabled[0].policy_id == p1.policy_id

    def test_thread_safety(self):
        reg = WorkflowPolicyRegistry(max_policies=200)
        errors = []

        def worker():
            try:
                p = WorkflowPolicy.create(str(uuid.uuid4()), PolicyType.WORKFLOW_GOVERNANCE)
                reg.register(p)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


# ═══════════════════════════════════════════════════════════════════════════════
# 14. WorkflowPolicyChain
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyChain:
    def test_empty_policies_returns_approve(self, simple_context):
        chain = WorkflowPolicyChain()
        action, results, reasoning = chain.evaluate([], simple_context)
        assert action == PolicyAction.APPROVE
        assert results == []

    def test_single_approve_policy(self, simple_context):
        p     = WorkflowPolicyFactory.create_approve_all_policy("P")
        chain = WorkflowPolicyChain()
        action, _, _ = chain.evaluate([p], simple_context)
        assert action == PolicyAction.APPROVE

    def test_single_reject_policy(self, simple_context):
        p     = WorkflowPolicyFactory.create_reject_all_policy("P")
        chain = WorkflowPolicyChain()
        action, _, _ = chain.evaluate([p], simple_context)
        assert action == PolicyAction.REJECT

    def test_conflict_resolution_block_beats_approve(self, simple_context):
        p_approve = WorkflowPolicyFactory.create_approve_all_policy("A")
        p_block   = WorkflowPolicy.create(
            "B", PolicyType.SECURITY,
            default_action=PolicyAction.BLOCK,
        )
        chain = WorkflowPolicyChain()
        action, _, _ = chain.evaluate([p_approve, p_block], simple_context)
        assert action == PolicyAction.BLOCK

    def test_conflict_resolution_emergency_beats_block(self, simple_context):
        p_block = WorkflowPolicy.create("B", PolicyType.SECURITY,
                                        default_action=PolicyAction.BLOCK)
        p_emerg = WorkflowPolicy.create("E", PolicyType.RISK,
                                        default_action=PolicyAction.EMERGENCY_STOP)
        chain = WorkflowPolicyChain()
        action, _, _ = chain.evaluate([p_block, p_emerg], simple_context)
        assert action == PolicyAction.EMERGENCY_STOP

    def test_parallel_mode_evaluates_all(self, simple_context):
        p1 = WorkflowPolicyFactory.create_approve_all_policy("A1")
        p2 = WorkflowPolicyFactory.create_approve_all_policy("A2")
        chain = WorkflowPolicyChain(mode=PolicyChainMode.PARALLEL)
        action, results, _ = chain.evaluate([p1, p2], simple_context)
        assert len(results) == 2
        assert action == PolicyAction.APPROVE

    def test_composite_mode(self, simple_context):
        p = WorkflowPolicyFactory.create_approve_all_policy("P")
        chain = WorkflowPolicyChain(mode=PolicyChainMode.COMPOSITE)
        action, _, _ = chain.evaluate([p], simple_context)
        assert action == PolicyAction.APPROVE

    def test_mode_property(self):
        c = WorkflowPolicyChain(mode=PolicyChainMode.PARALLEL)
        assert c.mode == PolicyChainMode.PARALLEL


# ═══════════════════════════════════════════════════════════════════════════════
# 15. WorkflowPolicyAudit
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyAudit:
    def _pair(self, wf_id="wf-1"):
        ctx  = WorkflowPolicyContext.create(wf_id, "seq")
        req  = WorkflowPolicyRequest.create(wf_id, ctx)
        resp = WorkflowPolicyResponse.approved(req, [])
        return req, resp

    def test_record_and_get(self):
        audit = WorkflowPolicyAudit()
        req, resp = self._pair()
        rec = audit.record(req, resp)
        fetched = audit.get(rec.audit_id)
        assert fetched.audit_id == rec.audit_id

    def test_get_not_found(self):
        audit = WorkflowPolicyAudit()
        with pytest.raises(WorkflowPolicyAuditError):
            audit.get("ghost-id")

    def test_recent(self):
        audit = WorkflowPolicyAudit()
        for i in range(5):
            req, resp = self._pair(f"wf-{i}")
            audit.record(req, resp)
        recent = audit.recent(3)
        assert len(recent) == 3

    def test_by_workflow(self):
        audit = WorkflowPolicyAudit()
        req, resp = self._pair("wf-target")
        audit.record(req, resp)
        # Add a different workflow
        req2, resp2 = self._pair("wf-other")
        audit.record(req2, resp2)
        records = audit.by_workflow("wf-target")
        assert len(records) == 1
        assert records[0].workflow_id == "wf-target"

    def test_audit_count(self):
        audit = WorkflowPolicyAudit()
        assert audit.audit_count() == 0
        req, resp = self._pair()
        audit.record(req, resp)
        assert audit.audit_count() == 1

    def test_clear(self):
        audit = WorkflowPolicyAudit()
        req, resp = self._pair()
        audit.record(req, resp)
        n = audit.clear()
        assert n == 1
        assert audit.audit_count() == 0

    def test_bounded(self):
        audit = WorkflowPolicyAudit(max_records=3)
        for i in range(5):
            req, resp = self._pair(f"wf-{i}")
            audit.record(req, resp)
        assert audit.audit_count() == 3

    def test_audit_record_to_dict(self):
        audit = WorkflowPolicyAudit()
        req, resp = self._pair()
        rec = audit.record(req, resp)
        d = rec.to_dict()
        assert "audit_id" in d
        assert "decision" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 16. WorkflowPolicyStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyStatistics:
    def test_initial_report_zeros(self):
        stats  = WorkflowPolicyStatistics()
        report = stats.report()
        assert report.policies_evaluated == 0
        assert report.governance_coverage == 0.0

    def test_record_approved(self):
        stats = WorkflowPolicyStatistics()
        stats.record_evaluation(GovernanceDecision.APPROVED, 10.0)
        report = stats.report()
        assert report.policies_evaluated == 1
        assert report.policies_approved  == 1

    def test_record_rejected(self):
        stats = WorkflowPolicyStatistics()
        stats.record_evaluation(GovernanceDecision.REJECTED, 5.0)
        assert stats.report().policies_rejected == 1

    def test_record_blocked(self):
        stats = WorkflowPolicyStatistics()
        stats.record_evaluation(GovernanceDecision.BLOCKED, 5.0)
        assert stats.report().policies_blocked == 1

    def test_record_emergency(self):
        stats = WorkflowPolicyStatistics()
        stats.record_evaluation(GovernanceDecision.EMERGENCY_STOPPED, 5.0)
        assert stats.report().emergency_stops == 1

    def test_record_manual_approval(self):
        stats = WorkflowPolicyStatistics()
        stats.record_evaluation(GovernanceDecision.REQUIRES_MANUAL_APPROVAL, 5.0)
        assert stats.report().manual_approvals == 1

    def test_record_executive_approval(self):
        stats = WorkflowPolicyStatistics()
        stats.record_evaluation(GovernanceDecision.REQUIRES_EXECUTIVE_APPROVAL, 5.0)
        assert stats.report().executive_approvals == 1

    def test_average_time(self):
        stats = WorkflowPolicyStatistics()
        stats.record_evaluation(GovernanceDecision.APPROVED, 10.0)
        stats.record_evaluation(GovernanceDecision.APPROVED, 20.0)
        report = stats.report()
        assert report.average_evaluation_time_ms == 15.0

    def test_governance_coverage(self):
        stats = WorkflowPolicyStatistics()
        stats.record_evaluation(GovernanceDecision.APPROVED, 5.0, had_applicable_policies=True)
        stats.record_evaluation(GovernanceDecision.APPROVED, 5.0, had_applicable_policies=False)
        report = stats.report()
        assert report.governance_coverage == 0.5

    def test_reset(self):
        stats = WorkflowPolicyStatistics()
        stats.record_evaluation(GovernanceDecision.APPROVED, 10.0)
        stats.reset()
        assert stats.report().policies_evaluated == 0

    def test_report_to_dict(self):
        stats  = WorkflowPolicyStatistics()
        report = stats.report()
        d = report.to_dict()
        assert "policies_evaluated" in d
        assert "governance_coverage" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 17. WorkflowPolicyHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyHistory:
    def _req_resp(self, wf="wf-1"):
        ctx  = WorkflowPolicyContext.create(wf, "seq")
        req  = WorkflowPolicyRequest.create(wf, ctx)
        resp = WorkflowPolicyResponse.approved(req, [])
        return req, resp

    def test_record_and_get_request(self):
        hist = WorkflowPolicyHistory()
        req, _ = self._req_resp()
        hist.record_request(req)
        fetched = hist.get_request(req.request_id)
        assert fetched.request_id == req.request_id

    def test_record_and_get_response(self):
        hist = WorkflowPolicyHistory()
        req, resp = self._req_resp()
        hist.record_response(resp)
        fetched = hist.get_response(resp.response_id)
        assert fetched.response_id == resp.response_id

    def test_recent_requests(self):
        hist = WorkflowPolicyHistory()
        for i in range(5):
            req, _ = self._req_resp(f"wf-{i}")
            hist.record_request(req)
        recent = hist.recent_requests(3)
        assert len(recent) == 3

    def test_by_workflow(self):
        hist = WorkflowPolicyHistory()
        req1, _ = self._req_resp("wf-target")
        req2, _ = self._req_resp("wf-other")
        hist.record_request(req1)
        hist.record_request(req2)
        results = hist.by_workflow("wf-target")
        assert len(results) == 1

    def test_counts(self):
        hist = WorkflowPolicyHistory()
        req, resp = self._req_resp()
        assert hist.request_count()  == 0
        assert hist.response_count() == 0
        hist.record_request(req)
        hist.record_response(resp)
        assert hist.request_count()  == 1
        assert hist.response_count() == 1

    def test_clear(self):
        hist = WorkflowPolicyHistory()
        req, _ = self._req_resp()
        hist.record_request(req)
        n = hist.clear()
        assert n == 1
        assert hist.request_count() == 0

    def test_bounded(self):
        hist = WorkflowPolicyHistory(max_entries=3)
        for i in range(5):
            req, _ = self._req_resp(f"wf-{i}")
            hist.record_request(req)
        assert hist.request_count() == 3


# ═══════════════════════════════════════════════════════════════════════════════
# 18. WorkflowPolicyEventBus
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyEventBus:
    def test_add_listener_and_emit(self):
        bus    = WorkflowPolicyEventBus()
        events = []
        bus.add_listener(PolicyEventType.WORKFLOW_APPROVED, events.append)
        evt = WorkflowPolicyEvent.create(
            PolicyEventType.WORKFLOW_APPROVED, "engine-1", workflow_id="wf-1"
        )
        notified = bus.emit(evt)
        assert notified == 1
        assert len(events) == 1

    def test_emit_wrong_type_not_received(self):
        bus    = WorkflowPolicyEventBus()
        events = []
        bus.add_listener(PolicyEventType.WORKFLOW_APPROVED, events.append)
        evt = WorkflowPolicyEvent.create(
            PolicyEventType.WORKFLOW_REJECTED, "engine-1"
        )
        notified = bus.emit(evt)
        assert notified == 0
        assert len(events) == 0

    def test_remove_listener(self):
        bus      = WorkflowPolicyEventBus()
        listener = lambda e: None
        bus.add_listener(PolicyEventType.WORKFLOW_APPROVED, listener)
        removed = bus.remove_listener(PolicyEventType.WORKFLOW_APPROVED, listener)
        assert removed is True
        assert bus.listener_count(PolicyEventType.WORKFLOW_APPROVED) == 0

    def test_remove_not_registered(self):
        bus = WorkflowPolicyEventBus()
        removed = bus.remove_listener(PolicyEventType.WORKFLOW_APPROVED, lambda e: None)
        assert removed is False

    def test_listener_count_all(self):
        bus = WorkflowPolicyEventBus()
        bus.add_listener(PolicyEventType.WORKFLOW_APPROVED, lambda e: None)
        bus.add_listener(PolicyEventType.WORKFLOW_REJECTED, lambda e: None)
        assert bus.listener_count() == 2

    def test_listener_error_does_not_propagate(self):
        bus = WorkflowPolicyEventBus()
        def bad(e): raise RuntimeError("boom")
        bus.add_listener(PolicyEventType.WORKFLOW_APPROVED, bad)
        evt = WorkflowPolicyEvent.create(PolicyEventType.WORKFLOW_APPROVED, "e1")
        notified = bus.emit(evt)   # should not raise
        assert notified == 0       # listener errored

    def test_clear(self):
        bus = WorkflowPolicyEventBus()
        bus.add_listener(PolicyEventType.WORKFLOW_APPROVED, lambda e: None)
        bus.clear()
        assert bus.listener_count() == 0

    def test_event_create(self):
        evt = WorkflowPolicyEvent.create(
            PolicyEventType.WORKFLOW_APPROVED, "eng-1",
            request_id="req-1", workflow_id="wf-1", payload={"k": "v"}
        )
        assert evt.event_id.startswith("wpevt-")
        assert evt.event_type == PolicyEventType.WORKFLOW_APPROVED
        d = evt.to_dict()
        assert "event_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 19. WorkflowPolicyFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyFactory:
    def test_approve_all(self):
        p = WorkflowPolicyFactory.create_approve_all_policy("P")
        assert p.default_action == PolicyAction.APPROVE

    def test_reject_all(self):
        p = WorkflowPolicyFactory.create_reject_all_policy("P")
        assert p.default_action == PolicyAction.REJECT

    def test_security_policy(self):
        p = WorkflowPolicyFactory.create_security_policy("S")
        assert p.policy_type == PolicyType.SECURITY
        assert p.domain      == PolicyDomain.SECURITY_GOVERNANCE

    def test_compliance_policy(self):
        p = WorkflowPolicyFactory.create_compliance_policy("C")
        assert p.policy_type == PolicyType.COMPLIANCE
        assert p.domain      == PolicyDomain.COMPLIANCE_GOVERNANCE

    def test_risk_policy(self):
        p = WorkflowPolicyFactory.create_risk_policy("R")
        assert p.policy_type == PolicyType.RISK
        assert p.domain      == PolicyDomain.RISK_GOVERNANCE

    def test_create_context(self):
        ctx = WorkflowPolicyFactory.create_context(
            "wf-1", security_context={"authenticated": True}
        )
        assert ctx.workflow_id == "wf-1"
        assert ctx.security_context["authenticated"] is True

    def test_create_request_no_context(self):
        req = WorkflowPolicyFactory.create_request("wf-1")
        assert req.workflow_id == "wf-1"
        assert req.context is not None

    def test_create_request_with_context(self):
        ctx = WorkflowPolicyFactory.create_context("wf-1")
        req = WorkflowPolicyFactory.create_request("wf-1", ctx)
        assert req.context.context_id == ctx.context_id


# ═══════════════════════════════════════════════════════════════════════════════
# 20. WorkflowPolicyEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyEngine:
    def _started_engine(self):
        engine = WorkflowPolicyEngine()
        engine.initialize()
        return engine

    def test_initialize(self):
        engine = WorkflowPolicyEngine()
        assert not engine.is_running
        engine.initialize()
        assert engine.is_running
        engine.stop()
        assert not engine.is_running

    def test_double_initialize_safe(self):
        engine = self._started_engine()
        engine.initialize()   # idempotent
        assert engine.is_running
        engine.stop()

    def test_register_and_evaluate_approve(self):
        engine = self._started_engine()
        policy = WorkflowPolicyFactory.create_approve_all_policy("P")
        engine.register_policy(policy)
        req  = WorkflowPolicyFactory.create_request("wf-1")
        resp = engine.evaluate_governance(req)
        assert resp.is_approved
        engine.stop()

    def test_no_policies_default_approve(self):
        engine = self._started_engine()
        req  = WorkflowPolicyFactory.create_request("wf-1")
        resp = engine.evaluate_governance(req)
        assert resp.is_approved
        engine.stop()

    def test_register_policy_invalid_raises(self):
        import dataclasses
        engine = self._started_engine()
        policy = WorkflowPolicy.create("P", PolicyType.WORKFLOW_GOVERNANCE)
        policy = dataclasses.replace(policy, name="")
        with pytest.raises(WorkflowPolicyValidationError):
            engine.register_policy(policy)
        engine.stop()

    def test_evaluate_reject_policy(self):
        engine = self._started_engine()
        policy = WorkflowPolicyFactory.create_reject_all_policy("P")
        engine.register_policy(policy)
        req  = WorkflowPolicyFactory.create_request("wf-1")
        resp = engine.evaluate_governance(req)
        assert resp.is_rejected
        engine.stop()

    def test_evaluate_emergency_stop(self):
        engine = self._started_engine()
        policy = WorkflowPolicy.create(
            "E", PolicyType.RISK, default_action=PolicyAction.EMERGENCY_STOP
        )
        engine.register_policy(policy)
        req  = WorkflowPolicyFactory.create_request("wf-1")
        resp = engine.evaluate_governance(req)
        assert resp.is_emergency_stop
        engine.stop()

    def test_health(self):
        engine = self._started_engine()
        h = engine.health()
        assert "engine_id" in h
        assert h["is_running"] is True
        engine.stop()

    def test_statistics(self):
        engine = self._started_engine()
        policy = WorkflowPolicyFactory.create_approve_all_policy("P")
        engine.register_policy(policy)
        req = WorkflowPolicyFactory.create_request("wf-1")
        engine.evaluate_governance(req)
        stats = engine.statistics()
        assert stats["policies_evaluated"] == 1
        engine.stop()

    def test_history_tracks_requests(self):
        engine = self._started_engine()
        policy = WorkflowPolicyFactory.create_approve_all_policy("P")
        engine.register_policy(policy)
        req = WorkflowPolicyFactory.create_request("wf-1")
        engine.evaluate_governance(req)
        hist = engine.history()
        assert hist.request_count() >= 1
        engine.stop()

    def test_event_bus_accessible(self):
        engine = self._started_engine()
        bus = engine.event_bus()
        assert isinstance(bus, WorkflowPolicyEventBus)
        engine.stop()

    def test_engine_emits_approval_event(self):
        engine = self._started_engine()
        events = []
        engine.event_bus().add_listener(PolicyEventType.WORKFLOW_APPROVED, events.append)
        policy = WorkflowPolicyFactory.create_approve_all_policy("P")
        engine.register_policy(policy)
        req = WorkflowPolicyFactory.create_request("wf-1")
        engine.evaluate_governance(req)
        assert len(events) >= 1
        engine.stop()

    def test_engine_emits_rejection_event(self):
        engine = self._started_engine()
        events = []
        engine.event_bus().add_listener(PolicyEventType.WORKFLOW_REJECTED, events.append)
        policy = WorkflowPolicyFactory.create_reject_all_policy("P")
        engine.register_policy(policy)
        req = WorkflowPolicyFactory.create_request("wf-1")
        engine.evaluate_governance(req)
        assert len(events) >= 1
        engine.stop()

    def test_validate_policy(self):
        engine = self._started_engine()
        policy = WorkflowPolicyFactory.create_approve_all_policy("P")
        result = engine.validate_policy(policy)
        assert result["valid"] is True
        engine.stop()

    def test_type_filter(self):
        engine = self._started_engine()
        p_sec = WorkflowPolicyFactory.create_security_policy("S")
        p_rej = WorkflowPolicyFactory.create_reject_all_policy("R")
        engine.register_policy(p_sec)
        engine.register_policy(p_rej)
        # Request only security type — reject policy (WORKFLOW_GOVERNANCE type) excluded
        ctx = WorkflowPolicyFactory.create_context("wf-1")
        req = WorkflowPolicyRequest.create(
            "wf-1", ctx, policy_types=[PolicyType.SECURITY]
        )
        resp = engine.evaluate_governance(req)
        # Security policy has default APPROVE
        assert resp.is_approved
        engine.stop()

    def test_concurrent_evaluations(self):
        engine = self._started_engine()
        policy = WorkflowPolicyFactory.create_approve_all_policy("P")
        engine.register_policy(policy)
        errors  = []
        results = []

        def worker():
            try:
                req  = WorkflowPolicyFactory.create_request("wf-concurrent")
                resp = engine.evaluate_governance(req)
                results.append(resp.is_approved)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert all(results)
        engine.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# 21. WorkflowPolicyManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPolicyManager:
    def test_not_started_evaluate_raises(self):
        mgr = WorkflowPolicyManager()
        ctx = WorkflowPolicyFactory.create_context("wf-1")
        req = WorkflowPolicyRequest.create("wf-1", ctx)
        with pytest.raises(WorkflowPolicyEngineError):
            mgr.evaluate(req)

    def test_start_stop(self):
        mgr = WorkflowPolicyManager()
        assert not mgr.is_started
        mgr.start()
        assert mgr.is_started
        mgr.stop()
        assert not mgr.is_started

    def test_double_start_safe(self):
        mgr = WorkflowPolicyManager()
        mgr.start()
        mgr.start()   # idempotent
        assert mgr.is_started
        mgr.stop()

    def test_evaluate_after_start(self, approve_all_policy):
        mgr = WorkflowPolicyManager()
        mgr.start()
        mgr.register_policy(approve_all_policy)
        req  = WorkflowPolicyFactory.create_request("wf-1")
        resp = mgr.evaluate(req)
        assert resp.is_approved
        mgr.stop()

    def test_register_policy_not_started_raises(self, approve_all_policy):
        mgr = WorkflowPolicyManager()
        with pytest.raises(WorkflowPolicyEngineError):
            mgr.register_policy(approve_all_policy)

    def test_health(self):
        mgr = WorkflowPolicyManager()
        mgr.start()
        h = mgr.health()
        assert "is_running" in h
        assert h["is_running"] is True
        mgr.stop()

    def test_statistics(self, approve_all_policy):
        mgr = WorkflowPolicyManager()
        mgr.start()
        mgr.register_policy(approve_all_policy)
        req = WorkflowPolicyFactory.create_request("wf-1")
        mgr.evaluate(req)
        stats = mgr.statistics()
        assert stats["policies_evaluated"] == 1
        mgr.stop()

    def test_history(self, approve_all_policy):
        mgr = WorkflowPolicyManager()
        mgr.start()
        mgr.register_policy(approve_all_policy)
        req = WorkflowPolicyFactory.create_request("wf-1")
        mgr.evaluate(req)
        assert mgr.history().request_count() >= 1
        mgr.stop()

    def test_event_bus(self):
        mgr = WorkflowPolicyManager()
        mgr.start()
        assert isinstance(mgr.event_bus(), WorkflowPolicyEventBus)
        mgr.stop()

    def test_validate_policy(self, approve_all_policy):
        mgr = WorkflowPolicyManager()
        mgr.start()
        result = mgr.validate_policy(approve_all_policy)
        assert result["valid"] is True
        mgr.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# 22. End-to-end integration tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    def test_complex_risk_governance(self):
        """High risk_score should be blocked."""
        mgr = WorkflowPolicyManager()
        mgr.start()

        # Risk gate
        risk_cond = PolicyCondition.create(
            "compliance_context.risk_score",
            ConditionOperator.GREATER_THAN, 0.8,
        )
        risk_rule   = PolicyRule.create("high-risk-block", PolicyAction.BLOCK,
                                        conditions=[risk_cond],
                                        priority=PolicyPriorityLevel.CRITICAL)
        risk_policy = WorkflowPolicy.create(
            "Risk Gate", PolicyType.RISK,
            domain=PolicyDomain.RISK_GOVERNANCE,
            priority=PolicyPriorityLevel.CRITICAL,
            rules=[risk_rule],
        )
        mgr.register_policy(risk_policy)

        ctx = WorkflowPolicyFactory.create_context(
            "wf-high-risk",
            compliance_context={"risk_score": 0.95},
        )
        req  = WorkflowPolicyFactory.create_request("wf-high-risk", ctx)
        resp = mgr.evaluate(req)
        assert resp.is_blocked
        assert not resp.can_proceed

        # Low risk should pass
        ctx2  = WorkflowPolicyFactory.create_context(
            "wf-low-risk",
            compliance_context={"risk_score": 0.2},
        )
        req2  = WorkflowPolicyFactory.create_request("wf-low-risk", ctx2)
        resp2 = mgr.evaluate(req2)
        assert resp2.is_approved

        mgr.stop()

    def test_multi_policy_conflict_resolution(self):
        """REJECT from security beats APPROVE from default."""
        mgr = WorkflowPolicyManager()
        mgr.start()

        mgr.register_policy(WorkflowPolicyFactory.create_approve_all_policy("Default"))

        threat_cond = PolicyCondition.create(
            "security_context.threat_level",
            ConditionOperator.EQUALS, "critical",
        )
        threat_rule = PolicyRule.create(
            "threat-reject", PolicyAction.REJECT,
            conditions=[threat_cond], priority=PolicyPriorityLevel.CRITICAL,
        )
        security_policy = WorkflowPolicyFactory.create_security_policy(
            "Threat Gate", rules=[threat_rule]
        )
        mgr.register_policy(security_policy)

        ctx  = WorkflowPolicyFactory.create_context(
            "wf-threat",
            security_context={"threat_level": "critical"},
        )
        req  = WorkflowPolicyFactory.create_request("wf-threat", ctx)
        resp = mgr.evaluate(req)
        assert resp.is_rejected
        mgr.stop()

    def test_event_bus_integration(self):
        """Engine emits proper events during full evaluation."""
        mgr    = WorkflowPolicyManager()
        mgr.start()

        events_received = []
        mgr.event_bus().add_listener(
            PolicyEventType.WORKFLOW_APPROVED,
            events_received.append,
        )
        mgr.event_bus().add_listener(
            PolicyEventType.WORKFLOW_GOVERNANCE_COMPLETED,
            events_received.append,
        )

        mgr.register_policy(WorkflowPolicyFactory.create_approve_all_policy("P"))
        req = WorkflowPolicyFactory.create_request("wf-event-test")
        mgr.evaluate(req)

        assert len(events_received) >= 2
        mgr.stop()

    def test_audit_trail_populated(self):
        """Audit records are created for every evaluation."""
        mgr = WorkflowPolicyManager()
        mgr.start()
        mgr.register_policy(WorkflowPolicyFactory.create_approve_all_policy("P"))

        for i in range(5):
            req = WorkflowPolicyFactory.create_request(f"wf-{i}")
            mgr.evaluate(req)

        # History tracks requests/responses
        assert mgr.history().request_count() >= 5
        mgr.stop()

    def test_statistics_accumulate(self):
        mgr = WorkflowPolicyManager()
        mgr.start()
        mgr.register_policy(WorkflowPolicyFactory.create_approve_all_policy("P"))
        mgr.register_policy(WorkflowPolicyFactory.create_reject_all_policy("R"))

        for i in range(10):
            req = WorkflowPolicyFactory.create_request(f"wf-{i}")
            mgr.evaluate(req)

        stats = mgr.statistics()
        assert stats["policies_evaluated"] == 10
        # reject_all wins over approve_all → all rejected
        assert stats["policies_rejected"] == 10
        mgr.stop()

    def test_thread_safety_concurrent_evaluation(self):
        mgr = WorkflowPolicyManager()
        mgr.start()
        mgr.register_policy(WorkflowPolicyFactory.create_approve_all_policy("P"))

        errors  = []
        results = []

        def worker(i):
            try:
                req  = WorkflowPolicyFactory.create_request(f"wf-{i}")
                resp = mgr.evaluate(req)
                results.append(resp.is_approved)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert all(results)
        mgr.stop()
