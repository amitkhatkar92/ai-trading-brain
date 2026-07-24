"""
tests/unit/integration/test_integration_policies_m3.py
-------------------------------------------------------
C15 M3 — Integration Governance Policy Framework test suite.

Covers all 21 source files in iios/integration/policies/.
Target: 95%+ coverage.
"""
from __future__ import annotations

import threading
from typing import List

import pytest


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════


def _make_factory():
    from iios.integration.policies import IntegrationPolicyFactory
    return IntegrationPolicyFactory()


def _make_engine(started: bool = True, with_approve_all: bool = True):
    from iios.integration.policies import IntegrationPolicyEngine
    eng = IntegrationPolicyEngine()
    if started:
        eng.start()
        if with_approve_all:
            f = _make_factory()
            eng.load_policy(f.create_approve_all_policy())
    return eng


def _make_manager(started: bool = True, with_approve_all: bool = True):
    from iios.integration.policies import IntegrationPolicyManager
    mgr = IntegrationPolicyManager()
    if started:
        mgr.start()
        if with_approve_all:
            f = _make_factory()
            mgr.load_policy(f.create_approve_all_policy())
    return mgr


def _make_context(factory=None, connector_type: str = "rest_api", **kwargs):
    f = factory or _make_factory()
    return f.create_context(
        engine_request_id = "req-test-001",
        engine_session_id = "sess-test-001",
        connector_type    = connector_type,
        adapter_type      = "rest",
        protocol_type     = "https",
        endpoint          = "https://api.example.com",
        environment       = "production",
        **kwargs,
    )


def _make_request(factory=None, **ctx_kwargs):
    f = factory or _make_factory()
    ctx = _make_context(f, **ctx_kwargs)
    return f.create_request(ctx)


# ════════════════════════════════════════════════════════════════════════
# 1. Constants
# ════════════════════════════════════════════════════════════════════════


class TestConstants:
    def test_policy_type_count(self):
        from iios.integration.policies import PolicyType
        assert len(PolicyType) == 20

    def test_policy_action_count(self):
        from iios.integration.policies import PolicyAction
        assert len(PolicyAction) == 8

    def test_policy_priority_count(self):
        from iios.integration.policies import PolicyPriority
        assert len(PolicyPriority) == 5

    def test_policy_domain_count(self):
        from iios.integration.policies import PolicyDomain
        assert len(PolicyDomain) == 13

    def test_policy_chain_mode_count(self):
        from iios.integration.policies import PolicyChainMode
        assert len(PolicyChainMode) == 6

    def test_condition_operator_count(self):
        from iios.integration.policies import ConditionOperator
        assert len(ConditionOperator) == 10

    def test_policy_event_type_count(self):
        from iios.integration.policies import PolicyEventType
        assert len(PolicyEventType) == 9

    def test_action_precedence_length(self):
        from iios.integration.policies import ACTION_PRECEDENCE, PolicyAction
        assert len(ACTION_PRECEDENCE) == len(PolicyAction)

    def test_action_to_status_coverage(self):
        from iios.integration.policies import ACTION_TO_STATUS, PolicyAction
        for action in PolicyAction:
            assert action in ACTION_TO_STATUS

    def test_system_id(self):
        from iios.integration.policies import POLICY_SYSTEM_ID
        assert "integration" in POLICY_SYSTEM_ID

    def test_default_limits(self):
        from iios.integration.policies import (
            DEFAULT_MAX_POLICIES,
            DEFAULT_MAX_HISTORY,
            DEFAULT_MAX_AUDIT,
        )
        assert DEFAULT_MAX_POLICIES >= 100
        assert DEFAULT_MAX_HISTORY  >= 500
        assert DEFAULT_MAX_AUDIT    >= 1_000

    def test_pipeline_stages(self):
        from iios.integration.policies import PIPELINE_STAGES
        assert len(PIPELINE_STAGES) == 7


# ════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ════════════════════════════════════════════════════════════════════════


class TestExceptions:
    def test_base_ipg_000(self):
        from iios.integration.policies import IntegrationPolicyError
        exc = IntegrationPolicyError("test")
        assert "IPG-000" in exc.error_code

    def test_not_ready_ipg_001(self):
        from iios.integration.policies import PolicyEngineNotReadyError
        exc = PolicyEngineNotReadyError()
        assert "IPG-001" in exc.error_code

    def test_not_found_ipg_002(self):
        from iios.integration.policies import PolicyNotFoundError
        exc = PolicyNotFoundError("pol-abc")
        assert exc.policy_id == "pol-abc"
        assert "IPG-002" in exc.error_code

    def test_rule_error_ipg_003(self):
        from iios.integration.policies import PolicyRuleError
        exc = PolicyRuleError("rule-001", "missing action")
        assert exc.rule_id == "rule-001"
        assert "IPG-003" in exc.error_code

    def test_condition_error_ipg_004(self):
        from iios.integration.policies import PolicyConditionError
        exc = PolicyConditionError("cond-001", "bad operator")
        assert exc.condition_id == "cond-001"

    def test_validation_error_ipg_005(self):
        from iios.integration.policies import PolicyValidationError
        exc = PolicyValidationError("bad policy", failed_checks=["policy_has_name"])
        assert "policy_has_name" in exc.failed_checks

    def test_conflict_error_ipg_006(self):
        from iios.integration.policies import PolicyConflictError
        exc = PolicyConflictError("conflict", policy_ids=["p1", "p2"])
        assert "p1" in exc.policy_ids

    def test_evaluation_error_ipg_007(self):
        from iios.integration.policies import PolicyEvaluationError
        exc = PolicyEvaluationError("eval failed", request_id="req-001")
        assert exc.request_id == "req-001"

    def test_registration_error_ipg_008(self):
        from iios.integration.policies import PolicyRegistrationError
        exc = PolicyRegistrationError("registry full")
        assert "IPG-008" in exc.error_code

    def test_chain_error_ipg_009(self):
        from iios.integration.policies import PolicyChainError
        exc = PolicyChainError("chain failed")
        assert "IPG-009" in exc.error_code

    def test_hierarchy(self):
        from iios.integration.policies import (
            IntegrationPolicyError, PolicyNotFoundError,
        )
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(PolicyNotFoundError, IntegrationPolicyError)
        assert issubclass(IntegrationPolicyError, IIOSError)


# ════════════════════════════════════════════════════════════════════════
# 3. Condition
# ════════════════════════════════════════════════════════════════════════


class TestCondition:
    def test_create(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create(
            "env check", "environment", ConditionOperator.EQUALS, "production"
        )
        assert c.condition_id.startswith("cond-")
        assert c.operator == ConditionOperator.EQUALS

    def test_frozen(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create("x", "y", ConditionOperator.EXISTS)
        with pytest.raises((AttributeError, TypeError)):
            c.name = "changed"  # type: ignore

    def test_equals_passes(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create("t", "env", ConditionOperator.EQUALS, "prod")
        assert c.evaluate({"env": "prod"}) is True

    def test_equals_fails(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create("t", "env", ConditionOperator.EQUALS, "prod")
        assert c.evaluate({"env": "staging"}) is False

    def test_not_equals(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create("t", "env", ConditionOperator.NOT_EQUALS, "prod")
        assert c.evaluate({"env": "staging"}) is True
        assert c.evaluate({"env": "prod"})    is False

    def test_in_operator(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create(
            "t", "env", ConditionOperator.IN, ["prod", "staging"]
        )
        assert c.evaluate({"env": "prod"})    is True
        assert c.evaluate({"env": "testing"}) is False

    def test_not_in_operator(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create(
            "t", "env", ConditionOperator.NOT_IN, ["prod"]
        )
        assert c.evaluate({"env": "staging"}) is True
        assert c.evaluate({"env": "prod"})    is False

    def test_contains_operator(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create(
            "t", "endpoint", ConditionOperator.CONTAINS, "api"
        )
        assert c.evaluate({"endpoint": "https://api.example.com"}) is True
        assert c.evaluate({"endpoint": "https://data.example.com"}) is False

    def test_not_contains_operator(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create(
            "t", "endpoint", ConditionOperator.NOT_CONTAINS, "evil"
        )
        assert c.evaluate({"endpoint": "https://api.example.com"}) is True

    def test_greater_than(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create("t", "priority", ConditionOperator.GREATER_THAN, 5)
        assert c.evaluate({"priority": 8}) is True
        assert c.evaluate({"priority": 3}) is False

    def test_less_than(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create("t", "priority", ConditionOperator.LESS_THAN, 5)
        assert c.evaluate({"priority": 3}) is True
        assert c.evaluate({"priority": 8}) is False

    def test_exists_operator(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create("t", "token", ConditionOperator.EXISTS)
        assert c.evaluate({"token": "abc"}) is True
        assert c.evaluate({})              is False

    def test_not_exists_operator(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create("t", "token", ConditionOperator.NOT_EXISTS)
        assert c.evaluate({})              is True
        assert c.evaluate({"token": "x"}) is False

    def test_dot_path_resolution(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create(
            "t", "security_config.tls_enabled", ConditionOperator.EQUALS, True
        )
        assert c.evaluate({"security_config": {"tls_enabled": True}}) is True
        assert c.evaluate({"security_config": {"tls_enabled": False}}) is False

    def test_missing_nested_key(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create(
            "t", "auth_config.token", ConditionOperator.EQUALS, "secret"
        )
        assert c.evaluate({"auth_config": {}}) is False

    def test_to_dict(self):
        from iios.integration.policies import IntegrationPolicyCondition, ConditionOperator
        c = IntegrationPolicyCondition.create(
            "env check", "environment", ConditionOperator.EQUALS, "production"
        )
        d = c.to_dict()
        assert d["field_path"]     == "environment"
        assert d["operator"]       == "equals"
        assert d["expected_value"] == "production"


# ════════════════════════════════════════════════════════════════════════
# 4. Rule
# ════════════════════════════════════════════════════════════════════════


class TestRule:
    def test_create(self):
        from iios.integration.policies import IntegrationPolicyRule, PolicyAction
        r = IntegrationPolicyRule.create("allow", PolicyAction.APPROVE)
        assert r.rule_id.startswith("rule-")
        assert r.action == PolicyAction.APPROVE

    def test_frozen(self):
        from iios.integration.policies import IntegrationPolicyRule, PolicyAction
        r = IntegrationPolicyRule.create("allow", PolicyAction.APPROVE)
        with pytest.raises((AttributeError, TypeError)):
            r.name = "changed"  # type: ignore

    def test_no_conditions_always_fires(self):
        from iios.integration.policies import IntegrationPolicyRule, PolicyAction
        r = IntegrationPolicyRule.create("always", PolicyAction.APPROVE)
        assert r.evaluate({}) == PolicyAction.APPROVE

    def test_all_must_pass_mode(self):
        from iios.integration.policies import (
            IntegrationPolicyRule, IntegrationPolicyCondition,
            PolicyAction, ConditionOperator, PolicyEvaluationMode,
        )
        c1 = IntegrationPolicyCondition.create("c1", "env", ConditionOperator.EQUALS, "prod")
        c2 = IntegrationPolicyCondition.create("c2", "priority", ConditionOperator.LESS_THAN, 5)
        r  = IntegrationPolicyRule.create(
            "both", PolicyAction.BLOCK, [c1, c2],
            evaluation_mode = PolicyEvaluationMode.ALL_MUST_PASS,
        )
        assert r.evaluate({"env": "prod", "priority": 3})    == PolicyAction.BLOCK
        assert r.evaluate({"env": "prod", "priority": 8})    is None
        assert r.evaluate({"env": "staging", "priority": 3}) is None

    def test_any_must_pass_mode(self):
        from iios.integration.policies import (
            IntegrationPolicyRule, IntegrationPolicyCondition,
            PolicyAction, ConditionOperator, PolicyEvaluationMode,
        )
        c1 = IntegrationPolicyCondition.create("c1", "env", ConditionOperator.EQUALS, "prod")
        c2 = IntegrationPolicyCondition.create("c2", "priority", ConditionOperator.LESS_THAN, 5)
        r  = IntegrationPolicyRule.create(
            "any", PolicyAction.ESCALATE, [c1, c2],
            evaluation_mode = PolicyEvaluationMode.ANY_MUST_PASS,
        )
        assert r.evaluate({"env": "prod",    "priority": 9}) == PolicyAction.ESCALATE
        assert r.evaluate({"env": "staging", "priority": 2}) == PolicyAction.ESCALATE
        assert r.evaluate({"env": "staging", "priority": 9}) is None

    def test_none_must_pass_mode(self):
        from iios.integration.policies import (
            IntegrationPolicyRule, IntegrationPolicyCondition,
            PolicyAction, ConditionOperator, PolicyEvaluationMode,
        )
        c = IntegrationPolicyCondition.create("c", "blocked", ConditionOperator.EQUALS, True)
        r = IntegrationPolicyRule.create(
            "none", PolicyAction.APPROVE, [c],
            evaluation_mode = PolicyEvaluationMode.NONE_MUST_PASS,
        )
        assert r.evaluate({"blocked": False}) == PolicyAction.APPROVE
        assert r.evaluate({"blocked": True})  is None

    def test_to_dict(self):
        from iios.integration.policies import IntegrationPolicyRule, PolicyAction
        r = IntegrationPolicyRule.create("allow", PolicyAction.APPROVE)
        d = r.to_dict()
        assert d["action"] == "approve"
        assert "conditions" in d


# ════════════════════════════════════════════════════════════════════════
# 5. Policy
# ════════════════════════════════════════════════════════════════════════


class TestPolicy:
    def test_create(self):
        from iios.integration.policies import (
            IntegrationPolicy, PolicyType, PolicyDomain, PolicyPriority,
        )
        p = IntegrationPolicy.create(
            "Test Policy", PolicyType.AUTHENTICATION,
            domain=PolicyDomain.AUTHENTICATION, priority=PolicyPriority.HIGH,
        )
        assert p.policy_id.startswith("pol-")
        assert p.enabled is True
        assert p.version == "1.0.0"

    def test_frozen(self):
        from iios.integration.policies import IntegrationPolicy, PolicyType
        p = IntegrationPolicy.create("P", PolicyType.COMPLIANCE)
        with pytest.raises((AttributeError, TypeError)):
            p.name = "changed"  # type: ignore

    def test_disabled_policy_returns_none(self):
        from iios.integration.policies import IntegrationPolicy, PolicyType
        p = IntegrationPolicy.create("P", PolicyType.COMPLIANCE, enabled=False)
        assert p.evaluate({}) is None

    def test_no_rules_returns_none(self):
        from iios.integration.policies import IntegrationPolicy, PolicyType
        p = IntegrationPolicy.create("P", PolicyType.COMPLIANCE)
        assert p.evaluate({}) is None

    def test_highest_precedence_action_wins(self):
        from iios.integration.policies import (
            IntegrationPolicy, IntegrationPolicyRule,
            PolicyType, PolicyAction,
        )
        r_approve = IntegrationPolicyRule.create("approve", PolicyAction.APPROVE)
        r_block   = IntegrationPolicyRule.create("block",   PolicyAction.BLOCK)
        p = IntegrationPolicy.create("P", PolicyType.COMPLIANCE, rules=[r_approve, r_block])
        assert p.evaluate({}) == PolicyAction.BLOCK

    def test_to_dict(self):
        from iios.integration.policies import IntegrationPolicy, PolicyType
        p = IntegrationPolicy.create("P", PolicyType.COMPLIANCE, description="Test")
        d = p.to_dict()
        assert "policy_id"   in d
        assert "policy_type" in d
        assert d["description"] == "Test"


# ════════════════════════════════════════════════════════════════════════
# 6. Context
# ════════════════════════════════════════════════════════════════════════


class TestContext:
    def test_create(self):
        ctx = _make_context()
        assert ctx.context_id.startswith("pctx-")
        assert ctx.connector_type == "rest_api"
        assert ctx.environment    == "production"

    def test_frozen(self):
        ctx = _make_context()
        with pytest.raises((AttributeError, TypeError)):
            ctx.environment = "staging"  # type: ignore

    def test_as_flat_dict(self):
        ctx = _make_context()
        d   = ctx.as_flat_dict()
        assert "connector_type"   in d
        assert "security_config"  in d
        assert "compliance_config" in d

    def test_nested_config_preserved(self):
        ctx = _make_context(security_config={"tls_enabled": True})
        d   = ctx.as_flat_dict()
        assert d["security_config"]["tls_enabled"] is True

    def test_to_dict(self):
        ctx = _make_context()
        d   = ctx.to_dict()
        assert "context_id"  in d
        assert "created_at"  in d


# ════════════════════════════════════════════════════════════════════════
# 7. Request
# ════════════════════════════════════════════════════════════════════════


class TestRequest:
    def test_create(self):
        req = _make_request()
        assert req.request_id.startswith("preq-")
        assert req.correlation_id
        assert req.trace_id

    def test_frozen(self):
        req = _make_request()
        with pytest.raises((AttributeError, TypeError)):
            req.correlation_id = "x"  # type: ignore

    def test_all_domains_by_default(self):
        from iios.integration.policies import PolicyDomain
        req = _make_request()
        assert len(req.requested_domains) == len(PolicyDomain)

    def test_filtered_domains(self):
        from iios.integration.policies import PolicyDomain, IntegrationPolicyRequest
        f   = _make_factory()
        ctx = _make_context(f)
        req = IntegrationPolicyRequest.create(
            ctx, requested_domains=[PolicyDomain.SECURITY]
        )
        assert len(req.requested_domains) == 1
        assert PolicyDomain.SECURITY in req.requested_domains

    def test_to_dict(self):
        req = _make_request()
        d   = req.to_dict()
        assert "request_id"  in d
        assert "policy_context" in d


# ════════════════════════════════════════════════════════════════════════
# 8. Result and GovernanceDecision
# ════════════════════════════════════════════════════════════════════════


class TestResultAndDecision:
    def test_result_create(self):
        from iios.integration.policies import IntegrationPolicyResult, PolicyAction
        r = IntegrationPolicyResult.create("pol-001", "Test", PolicyAction.APPROVE)
        assert r.result_id.startswith("prslt-")
        assert r.is_approved is True
        assert r.is_blocking is False

    def test_result_blocking(self):
        from iios.integration.policies import IntegrationPolicyResult, PolicyAction
        for action in (PolicyAction.BLOCK, PolicyAction.REJECT, PolicyAction.EMERGENCY_STOP):
            r = IntegrationPolicyResult.create("p", "P", action)
            assert r.is_blocking is True

    def test_result_frozen(self):
        from iios.integration.policies import IntegrationPolicyResult, PolicyAction
        r = IntegrationPolicyResult.create("p", "P", PolicyAction.APPROVE)
        with pytest.raises((AttributeError, TypeError)):
            r.reason = "x"  # type: ignore

    def test_result_to_dict(self):
        from iios.integration.policies import IntegrationPolicyResult, PolicyAction
        r = IntegrationPolicyResult.create("p", "P", PolicyAction.ESCALATE)
        d = r.to_dict()
        assert d["action"] == "escalate"

    def test_governance_decision_approved(self):
        from iios.integration.policies import GovernanceDecision, PolicyAction
        d = GovernanceDecision.create("req-001", PolicyAction.APPROVE, [])
        assert d.approved is True
        assert d.decision_id.startswith("gdec-")

    def test_governance_decision_rejected(self):
        from iios.integration.policies import GovernanceDecision, PolicyAction
        d = GovernanceDecision.create("req-001", PolicyAction.BLOCK, [])
        assert d.approved is False

    def test_governance_decision_frozen(self):
        from iios.integration.policies import GovernanceDecision, PolicyAction
        d = GovernanceDecision.create("req-001", PolicyAction.APPROVE, [])
        with pytest.raises((AttributeError, TypeError)):
            d.approved = False  # type: ignore

    def test_governance_decision_to_dict(self):
        from iios.integration.policies import GovernanceDecision, PolicyAction
        d = GovernanceDecision.create("req-001", PolicyAction.APPROVE, [])
        dd = d.to_dict()
        assert "decision_id"  in dd
        assert "final_action" in dd
        assert "approved"     in dd


# ════════════════════════════════════════════════════════════════════════
# 9. Response
# ════════════════════════════════════════════════════════════════════════


class TestResponse:
    def _decision(self, action=None):
        from iios.integration.policies import GovernanceDecision, PolicyAction
        return GovernanceDecision.create(
            "req-001",
            action or PolicyAction.APPROVE,
            [],
        )

    def test_approved_response(self):
        from iios.integration.policies import IntegrationPolicyResponse
        resp = IntegrationPolicyResponse.approved(
            "req-001", self._decision(), evaluation_time_ms=42.0
        )
        assert resp.is_approved is True
        assert resp.is_rejected is False
        assert resp.evaluation_time_ms == 42.0

    def test_rejected_response(self):
        from iios.integration.policies import IntegrationPolicyResponse, PolicyAction
        resp = IntegrationPolicyResponse.rejected(
            "req-001", self._decision(PolicyAction.BLOCK)
        )
        assert resp.is_rejected is True

    def test_frozen(self):
        from iios.integration.policies import IntegrationPolicyResponse
        resp = IntegrationPolicyResponse.approved("req-001", self._decision())
        with pytest.raises((AttributeError, TypeError)):
            resp.request_id = "x"  # type: ignore

    def test_to_dict(self):
        from iios.integration.policies import IntegrationPolicyResponse
        resp = IntegrationPolicyResponse.approved("req-001", self._decision())
        d    = resp.to_dict()
        assert "response_id"  in d
        assert "decision"     in d
        assert "audit_id"     in d


# ════════════════════════════════════════════════════════════════════════
# 10. Priority and Conflict Resolution
# ════════════════════════════════════════════════════════════════════════


class TestPriority:
    def test_most_restrictive_default(self):
        from iios.integration.policies import (
            IntegrationPolicyPriority, IntegrationPolicyResult, PolicyAction,
        )
        resolver = IntegrationPolicyPriority()
        results  = [
            IntegrationPolicyResult.create("p1", "P1", PolicyAction.APPROVE),
            IntegrationPolicyResult.create("p2", "P2", PolicyAction.BLOCK),
        ]
        assert resolver.resolve(results) == PolicyAction.BLOCK

    def test_emergency_stop_overrides_all(self):
        from iios.integration.policies import (
            IntegrationPolicyPriority, IntegrationPolicyResult, PolicyAction,
            ConflictResolutionStrategy,
        )
        resolver = IntegrationPolicyPriority(
            ConflictResolutionStrategy.EMERGENCY_STOP_OVERRIDES_ALL
        )
        results = [
            IntegrationPolicyResult.create("p1", "P1", PolicyAction.BLOCK),
            IntegrationPolicyResult.create("p2", "P2", PolicyAction.EMERGENCY_STOP),
        ]
        assert resolver.resolve(results) == PolicyAction.EMERGENCY_STOP

    def test_most_permissive(self):
        from iios.integration.policies import (
            IntegrationPolicyPriority, IntegrationPolicyResult, PolicyAction,
            ConflictResolutionStrategy,
        )
        resolver = IntegrationPolicyPriority(
            ConflictResolutionStrategy.MOST_PERMISSIVE
        )
        results = [
            IntegrationPolicyResult.create("p1", "P1", PolicyAction.APPROVE),
            IntegrationPolicyResult.create("p2", "P2", PolicyAction.BLOCK),
        ]
        assert resolver.resolve(results) == PolicyAction.APPROVE

    def test_empty_results_approve(self):
        from iios.integration.policies import IntegrationPolicyPriority, PolicyAction
        resolver = IntegrationPolicyPriority()
        assert resolver.resolve([]) == PolicyAction.APPROVE

    def test_rank_ordering(self):
        from iios.integration.policies import IntegrationPolicyPriority, PolicyAction
        resolver = IntegrationPolicyPriority()
        assert resolver.rank(PolicyAction.EMERGENCY_STOP) > resolver.rank(PolicyAction.BLOCK)
        assert resolver.rank(PolicyAction.BLOCK) > resolver.rank(PolicyAction.REJECT)
        assert resolver.rank(PolicyAction.REJECT) > resolver.rank(PolicyAction.APPROVE)

    def test_critical_overrides_all(self):
        from iios.integration.policies import (
            IntegrationPolicyPriority, IntegrationPolicyResult, PolicyAction,
            ConflictResolutionStrategy, IntegrationPolicy, PolicyType, PolicyPriority,
        )
        resolver = IntegrationPolicyPriority(
            ConflictResolutionStrategy.CRITICAL_OVERRIDES_ALL
        )
        p_low    = IntegrationPolicy.create("Low P",  PolicyType.COMPLIANCE, priority=PolicyPriority.LOW)
        p_crit   = IntegrationPolicy.create("Crit P", PolicyType.COMPLIANCE, priority=PolicyPriority.CRITICAL)
        results  = [
            IntegrationPolicyResult.create("p1", "Low P",  PolicyAction.APPROVE),
            IntegrationPolicyResult.create("p2", "Crit P", PolicyAction.BLOCK),
        ]
        action = resolver.resolve(results, [p_low, p_crit])
        # Critical policy wins — BLOCK
        assert action == PolicyAction.BLOCK


# ════════════════════════════════════════════════════════════════════════
# 11. Evaluator
# ════════════════════════════════════════════════════════════════════════


class TestEvaluator:
    def test_approve_all_policy(self):
        from iios.integration.policies import IntegrationPolicyEvaluator
        f         = _make_factory()
        evaluator = IntegrationPolicyEvaluator()
        policies  = [f.create_approve_all_policy()]
        ctx       = _make_context(f)
        decision  = evaluator.evaluate(policies, ctx)
        assert decision.approved is True

    def test_reject_all_policy(self):
        from iios.integration.policies import IntegrationPolicyEvaluator
        f         = _make_factory()
        evaluator = IntegrationPolicyEvaluator()
        policies  = [f.create_reject_all_policy()]
        ctx       = _make_context(f)
        decision  = evaluator.evaluate(policies, ctx)
        assert decision.approved is False

    def test_empty_policies_approve(self):
        from iios.integration.policies import IntegrationPolicyEvaluator, PolicyAction
        evaluator = IntegrationPolicyEvaluator()
        ctx       = _make_context()
        decision  = evaluator.evaluate([], ctx)
        assert decision.final_action == PolicyAction.APPROVE

    def test_domain_filter(self):
        from iios.integration.policies import (
            IntegrationPolicyEvaluator, PolicyDomain,
        )
        f         = _make_factory()
        evaluator = IntegrationPolicyEvaluator()
        # reject_all is ENTERPRISE domain
        policies = [f.create_reject_all_policy()]
        ctx      = _make_context(f)
        # Filter to SECURITY domain only — no matching policies → approve
        decision = evaluator.evaluate(
            policies, ctx, requested_domains=[PolicyDomain.SECURITY]
        )
        assert decision.approved is True

    def test_disabled_policy_skipped(self):
        from iios.integration.policies import (
            IntegrationPolicyEvaluator, IntegrationPolicy, PolicyType,
            IntegrationPolicyRule, PolicyAction,
        )
        rule   = IntegrationPolicyRule.create("block all", PolicyAction.BLOCK)
        policy = IntegrationPolicy.create("Disabled Block", PolicyType.COMPLIANCE, enabled=False, rules=[rule])
        evaluator = IntegrationPolicyEvaluator()
        decision  = evaluator.evaluate([policy], _make_context())
        # Disabled policy → approve
        assert decision.approved is True

    def test_evaluate_single(self):
        from iios.integration.policies import (
            IntegrationPolicyEvaluator, PolicyAction,
        )
        f     = _make_factory()
        p     = f.create_approve_all_policy()
        ctx   = _make_context(f)
        result= IntegrationPolicyEvaluator().evaluate_single(p, ctx)
        assert result.action == PolicyAction.APPROVE

    def test_conditions_from_context(self):
        from iios.integration.policies import (
            IntegrationPolicyEvaluator, IntegrationPolicyCondition,
            IntegrationPolicyRule, IntegrationPolicy,
            PolicyType, PolicyAction, ConditionOperator,
        )
        cond = IntegrationPolicyCondition.create(
            "prod env", "environment", ConditionOperator.EQUALS, "production"
        )
        rule   = IntegrationPolicyRule.create("block prod", PolicyAction.BLOCK, [cond])
        policy = IntegrationPolicy.create("Prod Block", PolicyType.COMPLIANCE, rules=[rule])
        ev     = IntegrationPolicyEvaluator()
        ctx    = _make_context()   # environment="production"
        decision = ev.evaluate([policy], ctx)
        assert decision.final_action == PolicyAction.BLOCK

    def test_conditions_do_not_fire_on_wrong_env(self):
        from iios.integration.policies import (
            IntegrationPolicyEvaluator, IntegrationPolicyCondition,
            IntegrationPolicyRule, IntegrationPolicy,
            PolicyType, PolicyAction, ConditionOperator,
        )
        cond   = IntegrationPolicyCondition.create(
            "staging check", "environment", ConditionOperator.EQUALS, "staging"
        )
        rule   = IntegrationPolicyRule.create("block staging", PolicyAction.BLOCK, [cond])
        policy = IntegrationPolicy.create("Staging Block", PolicyType.COMPLIANCE, rules=[rule])
        ev     = IntegrationPolicyEvaluator()
        ctx    = _make_context()   # environment="production"
        decision = ev.evaluate([policy], ctx)
        # Condition does not fire → approve
        assert decision.approved is True


# ════════════════════════════════════════════════════════════════════════
# 12. Validator
# ════════════════════════════════════════════════════════════════════════


class TestValidator:
    def test_valid_policy_passes(self):
        from iios.integration.policies import IntegrationPolicyValidator
        f       = _make_factory()
        policy  = f.create_approve_all_policy()
        report  = IntegrationPolicyValidator().validate(policy)
        assert report.passed is True
        assert report.failed_checks == []

    def test_empty_name_fails(self):
        from iios.integration.policies import (
            IntegrationPolicyValidator, IntegrationPolicy, PolicyType,
        )
        p      = IntegrationPolicy.create("", PolicyType.COMPLIANCE)
        report = IntegrationPolicyValidator().validate(p)
        assert not report.passed
        assert "policy_has_name" in report.failed_checks

    def test_too_many_rules_fails(self):
        from iios.integration.policies import (
            IntegrationPolicyValidator, IntegrationPolicy, PolicyType,
            IntegrationPolicyRule, PolicyAction,
            DEFAULT_MAX_RULES_PER_POLICY,
        )
        rules = [
            IntegrationPolicyRule.create(f"rule-{i}", PolicyAction.APPROVE)
            for i in range(DEFAULT_MAX_RULES_PER_POLICY + 1)
        ]
        p      = IntegrationPolicy.create("Big Policy", PolicyType.COMPLIANCE, rules=rules)
        report = IntegrationPolicyValidator().validate(p)
        assert not report.passed
        assert "rule_count_within_limits" in report.failed_checks

    def test_validate_or_raise_on_failure(self):
        from iios.integration.policies import (
            IntegrationPolicyValidator, IntegrationPolicy, PolicyType,
            PolicyValidationError,
        )
        p = IntegrationPolicy.create("", PolicyType.COMPLIANCE)
        with pytest.raises(PolicyValidationError):
            IntegrationPolicyValidator().validate_or_raise(p)

    def test_report_to_dict(self):
        from iios.integration.policies import IntegrationPolicyValidator
        f      = _make_factory()
        policy = f.create_approve_all_policy()
        report = IntegrationPolicyValidator().validate(policy)
        d      = report.to_dict()
        assert "policy_id"     in d
        assert "passed"        in d
        assert "failed_checks" in d

    def test_7_checks_present(self):
        from iios.integration.policies import IntegrationPolicyValidator
        f      = _make_factory()
        policy = f.create_approve_all_policy()
        report = IntegrationPolicyValidator().validate(policy)
        assert len(report.results) == 7


# ════════════════════════════════════════════════════════════════════════
# 13. Registry
# ════════════════════════════════════════════════════════════════════════


class TestRegistry:
    def test_register_and_get(self):
        from iios.integration.policies import IntegrationPolicyRegistry
        f   = _make_factory()
        reg = IntegrationPolicyRegistry()
        p   = f.create_approve_all_policy()
        reg.register(p)
        assert reg.get(p.policy_id) is p

    def test_deregister(self):
        from iios.integration.policies import IntegrationPolicyRegistry
        f   = _make_factory()
        reg = IntegrationPolicyRegistry()
        p   = f.create_approve_all_policy()
        reg.register(p)
        assert reg.deregister(p.policy_id) is True
        assert reg.get(p.policy_id) is None

    def test_get_or_raise(self):
        from iios.integration.policies import IntegrationPolicyRegistry, PolicyNotFoundError
        reg = IntegrationPolicyRegistry()
        with pytest.raises(PolicyNotFoundError):
            reg.get_or_raise("nonexistent")

    def test_capacity_error(self):
        from iios.integration.policies import (
            IntegrationPolicyRegistry, PolicyRegistrationError,
        )
        f   = _make_factory()
        reg = IntegrationPolicyRegistry(max_policies=1)
        reg.register(f.create_approve_all_policy())
        with pytest.raises(PolicyRegistrationError):
            reg.register(f.create_reject_all_policy())

    def test_by_domain(self):
        from iios.integration.policies import (
            IntegrationPolicyRegistry, PolicyDomain,
        )
        f   = _make_factory()
        reg = IntegrationPolicyRegistry()
        p   = f.create_approve_all_policy()   # domain=ENTERPRISE
        reg.register(p)
        result = reg.by_domain(PolicyDomain.ENTERPRISE)
        assert p in result

    def test_by_type(self):
        from iios.integration.policies import (
            IntegrationPolicyRegistry, PolicyType,
        )
        f   = _make_factory()
        reg = IntegrationPolicyRegistry()
        p   = f.create_approve_all_policy()   # type=ENTERPRISE_INTEGRATION
        reg.register(p)
        result = reg.by_type(PolicyType.ENTERPRISE_INTEGRATION)
        assert p in result

    def test_all_enabled(self):
        from iios.integration.policies import (
            IntegrationPolicyRegistry, IntegrationPolicy, PolicyType,
        )
        f   = _make_factory()
        reg = IntegrationPolicyRegistry()
        p1  = f.create_approve_all_policy()
        p2  = IntegrationPolicy.create("Disabled", PolicyType.COMPLIANCE, enabled=False)
        reg.register(p1)
        reg.register(p2)
        enabled = reg.all_enabled()
        assert p1 in enabled
        assert p2 not in enabled

    def test_summary(self):
        from iios.integration.policies import IntegrationPolicyRegistry
        f   = _make_factory()
        reg = IntegrationPolicyRegistry()
        reg.register(f.create_approve_all_policy())
        s = reg.summary()
        assert s["total"]   == 1
        assert s["enabled"] == 1

    def test_count_and_clear(self):
        from iios.integration.policies import IntegrationPolicyRegistry
        f   = _make_factory()
        reg = IntegrationPolicyRegistry()
        reg.register(f.create_approve_all_policy())
        assert reg.count() == 1
        reg.clear()
        assert reg.count() == 0


# ════════════════════════════════════════════════════════════════════════
# 14. Policy Chain
# ════════════════════════════════════════════════════════════════════════


class TestPolicyChain:
    def test_sequential_approves(self):
        from iios.integration.policies import IntegrationPolicyChain, PolicyChainMode
        f     = _make_factory()
        chain = IntegrationPolicyChain(
            mode=PolicyChainMode.SEQUENTIAL,
            policies=[f.create_approve_all_policy()],
        )
        ctx  = _make_context(f)
        exec = chain.execute(ctx)
        assert exec.success is True
        assert exec.decision.approved is True

    def test_sequential_stops_on_block(self):
        from iios.integration.policies import (
            IntegrationPolicyChain, PolicyChainMode, PolicyAction,
        )
        f        = _make_factory()
        p_block  = f.create_reject_all_policy()
        p_approve= f.create_approve_all_policy()
        chain    = IntegrationPolicyChain(
            mode=PolicyChainMode.SEQUENTIAL,
            policies=[p_block, p_approve],
        )
        ctx  = _make_context(f)
        exec = chain.execute(ctx)
        # Block fires; approve never evaluated (only 1 result)
        assert exec.decision.final_action == PolicyAction.REJECT
        assert len(exec.results) == 1

    def test_parallel_evaluates_all(self):
        from iios.integration.policies import IntegrationPolicyChain, PolicyChainMode
        f     = _make_factory()
        chain = IntegrationPolicyChain(
            mode=PolicyChainMode.PARALLEL,
            policies=[f.create_approve_all_policy(), f.create_approve_all_policy()],
        )
        ctx  = _make_context(f)
        exec = chain.execute(ctx)
        assert len(exec.results) == 2

    def test_conditional_skips_when_false(self):
        from iios.integration.policies import IntegrationPolicyChain, PolicyChainMode
        f     = _make_factory()
        chain = IntegrationPolicyChain(
            mode      = PolicyChainMode.CONDITIONAL,
            policies  = [f.create_reject_all_policy()],
            condition = lambda ctx: False,  # never triggers
        )
        ctx  = _make_context(f)
        exec = chain.execute(ctx)
        # Conditional skipped → auto-approve
        assert exec.decision.approved is True

    def test_conditional_evaluates_when_true(self):
        from iios.integration.policies import IntegrationPolicyChain, PolicyChainMode
        f     = _make_factory()
        chain = IntegrationPolicyChain(
            mode      = PolicyChainMode.CONDITIONAL,
            policies  = [f.create_reject_all_policy()],
            condition = lambda ctx: True,
        )
        ctx  = _make_context(f)
        exec = chain.execute(ctx)
        assert exec.decision.approved is False

    def test_composite_mode(self):
        from iios.integration.policies import IntegrationPolicyChain, PolicyChainMode
        f     = _make_factory()
        chain = IntegrationPolicyChain(
            mode=PolicyChainMode.COMPOSITE,
            policies=[f.create_approve_all_policy()],
        )
        ctx  = _make_context(f)
        exec = chain.execute(ctx)
        assert exec.success is True

    def test_priority_mode_evaluates_by_priority(self):
        from iios.integration.policies import IntegrationPolicyChain, PolicyChainMode
        f     = _make_factory()
        chain = IntegrationPolicyChain(
            mode=PolicyChainMode.PRIORITY,
            policies=[f.create_approve_all_policy(), f.create_approve_all_policy()],
        )
        ctx  = _make_context(f)
        exec = chain.execute(ctx)
        assert exec.success is True

    def test_add_policy(self):
        from iios.integration.policies import IntegrationPolicyChain
        f     = _make_factory()
        chain = IntegrationPolicyChain()
        assert chain.policy_count == 0
        chain.add_policy(f.create_approve_all_policy())
        assert chain.policy_count == 1

    def test_execution_to_dict(self):
        from iios.integration.policies import IntegrationPolicyChain
        f     = _make_factory()
        chain = IntegrationPolicyChain(policies=[f.create_approve_all_policy()])
        ctx   = _make_context(f)
        exec  = chain.execute(ctx)
        d     = exec.to_dict()
        assert "execution_id" in d
        assert "chain_mode"   in d
        assert "decision"     in d


# ════════════════════════════════════════════════════════════════════════
# 15. Audit
# ════════════════════════════════════════════════════════════════════════


class TestAudit:
    def _entry(self):
        from iios.integration.policies import (
            IntegrationAuditEntry, GovernanceDecision, PolicyAction,
        )
        decision = GovernanceDecision.create("req-001", PolicyAction.APPROVE, [])
        return IntegrationAuditEntry.create(
            request_id         = "req-001",
            context_id         = "ctx-001",
            decision           = decision,
            policy_results     = [],
            evaluation_time_ms = 10.0,
        )

    def test_record_and_get(self):
        from iios.integration.policies import IntegrationPolicyAudit
        audit = IntegrationPolicyAudit()
        entry = self._entry()
        audit.record(entry)
        found = audit.get(entry.audit_id)
        assert found is entry

    def test_by_request(self):
        from iios.integration.policies import IntegrationPolicyAudit
        audit = IntegrationPolicyAudit()
        entry = self._entry()
        audit.record(entry)
        found = audit.by_request("req-001")
        assert entry in found

    def test_recent(self):
        from iios.integration.policies import IntegrationPolicyAudit
        audit = IntegrationPolicyAudit()
        for _ in range(30):
            audit.record(self._entry())
        assert len(audit.recent(n=10)) == 10

    def test_report(self):
        from iios.integration.policies import IntegrationPolicyAudit
        audit = IntegrationPolicyAudit()
        audit.record(self._entry())
        report = audit.report()
        assert report.total_evaluations == 1
        assert report.total_approved    == 1

    def test_report_to_dict(self):
        from iios.integration.policies import IntegrationPolicyAudit
        audit = IntegrationPolicyAudit()
        d     = audit.report().to_dict()
        assert "total_evaluations" in d
        assert "avg_evaluation_ms" in d

    def test_bounded(self):
        from iios.integration.policies import IntegrationPolicyAudit
        audit = IntegrationPolicyAudit(max_entries=3)
        for _ in range(5):
            audit.record(self._entry())
        assert audit.count() == 3

    def test_entry_to_dict(self):
        entry = self._entry()
        d     = entry.to_dict()
        assert "audit_id"   in d
        assert "final_action" in d

    def test_clear(self):
        from iios.integration.policies import IntegrationPolicyAudit
        audit = IntegrationPolicyAudit()
        audit.record(self._entry())
        audit.clear()
        assert audit.count() == 0


# ════════════════════════════════════════════════════════════════════════
# 16. Statistics
# ════════════════════════════════════════════════════════════════════════


class TestStatistics:
    def test_all_9_counters(self):
        from iios.integration.policies import IntegrationPolicyStatistics
        stats = IntegrationPolicyStatistics()
        stats.record_evaluated()
        stats.record_approved()
        stats.record_rejected()
        stats.record_blocked()
        stats.record_security_review()
        stats.record_escalation()
        stats.record_emergency_stop()
        stats.record_evaluation_time(50.0)

        r = stats.report()
        assert r.policies_evaluated    == 1
        assert r.policies_approved     == 1
        assert r.policies_rejected     == 1
        assert r.policies_blocked      == 1
        assert r.security_reviews      == 1
        assert r.escalations           == 1
        assert r.emergency_stops       == 1
        assert r.average_evaluation_ms == 50.0

    def test_governance_coverage_approved_over_evaluated(self):
        from iios.integration.policies import IntegrationPolicyStatistics
        stats = IntegrationPolicyStatistics()
        stats.record_evaluated()
        stats.record_evaluated()
        stats.record_approved()
        r = stats.report()
        assert r.governance_coverage == 0.5

    def test_coverage_defaults_1_when_no_evaluations(self):
        from iios.integration.policies import IntegrationPolicyStatistics
        stats = IntegrationPolicyStatistics()
        r     = stats.report()
        assert r.governance_coverage == 1.0

    def test_reset(self):
        from iios.integration.policies import IntegrationPolicyStatistics
        stats = IntegrationPolicyStatistics()
        stats.record_evaluated()
        stats.reset()
        r = stats.report()
        assert r.policies_evaluated == 0

    def test_report_to_dict(self):
        from iios.integration.policies import IntegrationPolicyStatistics
        stats = IntegrationPolicyStatistics()
        d     = stats.report().to_dict()
        assert "policies_evaluated"    in d
        assert "governance_coverage"   in d
        assert "average_evaluation_ms" in d

    def test_avg_zero_with_no_times(self):
        from iios.integration.policies import IntegrationPolicyStatistics
        stats = IntegrationPolicyStatistics()
        assert stats.report().average_evaluation_ms == 0.0


# ════════════════════════════════════════════════════════════════════════
# 17. History
# ════════════════════════════════════════════════════════════════════════


class TestHistory:
    def test_record_and_retrieve_request(self):
        from iios.integration.policies import IntegrationPolicyHistory
        h   = IntegrationPolicyHistory()
        req = _make_request()
        h.record_request(req)
        assert h.get_request(req.request_id) is req

    def test_record_and_retrieve_response(self):
        from iios.integration.policies import (
            IntegrationPolicyHistory, IntegrationPolicyResponse, GovernanceDecision, PolicyAction,
        )
        h    = IntegrationPolicyHistory()
        req  = _make_request()
        dec  = GovernanceDecision.create(req.request_id, PolicyAction.APPROVE, [])
        resp = IntegrationPolicyResponse.approved(req.request_id, dec)
        h.record_response(resp)
        assert h.get_response(resp.response_id) is resp

    def test_response_for_request(self):
        from iios.integration.policies import (
            IntegrationPolicyHistory, IntegrationPolicyResponse, GovernanceDecision, PolicyAction,
        )
        h    = IntegrationPolicyHistory()
        req  = _make_request()
        dec  = GovernanceDecision.create(req.request_id, PolicyAction.APPROVE, [])
        resp = IntegrationPolicyResponse.approved(req.request_id, dec)
        h.record_response(resp)
        assert h.response_for_request(req.request_id) is resp

    def test_recent_requests(self):
        from iios.integration.policies import IntegrationPolicyHistory
        h = IntegrationPolicyHistory()
        for _ in range(30):
            h.record_request(_make_request())
        assert len(h.recent_requests(n=10)) == 10

    def test_bounded(self):
        from iios.integration.policies import IntegrationPolicyHistory
        h = IntegrationPolicyHistory(max_history=3)
        for _ in range(5):
            h.record_request(_make_request())
        assert h.request_count() == 3

    def test_clear(self):
        from iios.integration.policies import IntegrationPolicyHistory
        h = IntegrationPolicyHistory()
        h.record_request(_make_request())
        h.clear()
        assert h.request_count()  == 0
        assert h.response_count() == 0


# ════════════════════════════════════════════════════════════════════════
# 18. Events
# ════════════════════════════════════════════════════════════════════════


class TestEvents:
    def test_event_create(self):
        from iios.integration.policies import IntegrationPolicyEvent, PolicyEventType
        evt = IntegrationPolicyEvent.create(
            PolicyEventType.GOVERNANCE_STARTED, "eng-001", "req-001"
        )
        assert evt.event_id.startswith("pevnt-")
        assert evt.engine_id == "eng-001"

    def test_event_frozen(self):
        from iios.integration.policies import IntegrationPolicyEvent, PolicyEventType
        evt = IntegrationPolicyEvent.create(
            PolicyEventType.GOVERNANCE_COMPLETED, "e", "r"
        )
        with pytest.raises((AttributeError, TypeError)):
            evt.engine_id = "x"  # type: ignore

    def test_all_9_events_emittable(self):
        from iios.integration.policies import (
            IntegrationPolicyEventBus, PolicyEventType,
        )
        bus      = IntegrationPolicyEventBus()
        received = []
        bus.add_listener(received.append)
        for evt_type in PolicyEventType:
            bus.emit(evt_type, "eng", "req")
        assert len(received) == 9

    def test_listener_exception_suppressed(self):
        from iios.integration.policies import (
            IntegrationPolicyEventBus, PolicyEventType,
        )
        bus = IntegrationPolicyEventBus()
        bus.add_listener(lambda e: 1 / 0)
        # Must not raise
        bus.emit(PolicyEventType.EMERGENCY_STOP_TRIGGERED, "e", "r")

    def test_remove_listener(self):
        from iios.integration.policies import (
            IntegrationPolicyEventBus, PolicyEventType,
        )
        received = []
        bus      = IntegrationPolicyEventBus()
        fn       = received.append
        bus.add_listener(fn)
        bus.remove_listener(fn)
        bus.emit(PolicyEventType.GOVERNANCE_COMPLETED, "e", "r")
        assert len(received) == 0

    def test_listener_count(self):
        from iios.integration.policies import IntegrationPolicyEventBus
        bus = IntegrationPolicyEventBus()
        assert bus.listener_count() == 0
        bus.add_listener(lambda e: None)
        assert bus.listener_count() == 1

    def test_event_to_dict(self):
        from iios.integration.policies import IntegrationPolicyEvent, PolicyEventType
        evt = IntegrationPolicyEvent.create(
            PolicyEventType.INTEGRATION_APPROVED, "e", "r", {"k": "v"}
        )
        d = evt.to_dict()
        assert "event_type" in d
        assert d["payload"] == {"k": "v"}


# ════════════════════════════════════════════════════════════════════════
# 19. Engine Lifecycle
# ════════════════════════════════════════════════════════════════════════


class TestEngineLifecycle:
    def test_starts_not_ready(self):
        from iios.integration.policies import IntegrationPolicyEngine
        eng = IntegrationPolicyEngine()
        assert eng.is_ready is False

    def test_start_makes_ready(self):
        from iios.integration.policies import IntegrationPolicyEngine
        eng = IntegrationPolicyEngine()
        eng.start()
        assert eng.is_ready is True

    def test_stop_clears_ready(self):
        from iios.integration.policies import IntegrationPolicyEngine
        eng = IntegrationPolicyEngine()
        eng.start()
        eng.stop()
        assert eng.is_ready is False

    def test_evaluate_before_start_raises(self):
        from iios.integration.policies import (
            IntegrationPolicyEngine, PolicyEngineNotReadyError,
        )
        eng = IntegrationPolicyEngine()
        with pytest.raises(PolicyEngineNotReadyError):
            eng.evaluate(_make_request())

    def test_evaluate_after_stop_raises(self):
        from iios.integration.policies import (
            IntegrationPolicyEngine, PolicyEngineNotReadyError,
        )
        eng = IntegrationPolicyEngine()
        eng.start()
        eng.stop()
        with pytest.raises(PolicyEngineNotReadyError):
            eng.evaluate(_make_request())

    def test_manager_start_stop(self):
        from iios.integration.policies import IntegrationPolicyManager
        mgr = IntegrationPolicyManager()
        mgr.start()
        assert mgr.is_started
        mgr.stop()
        assert not mgr.is_started

    def test_double_start_idempotent(self):
        from iios.integration.policies import IntegrationPolicyManager
        mgr = IntegrationPolicyManager()
        mgr.start()
        mgr.start()   # must not raise
        mgr.stop()


# ════════════════════════════════════════════════════════════════════════
# 20. Engine Evaluation
# ════════════════════════════════════════════════════════════════════════


class TestEngineEvaluation:
    def test_approve_all_returns_approved(self):
        eng  = _make_engine()
        resp = eng.evaluate(_make_request())
        assert resp.is_approved is True

    def test_reject_all_returns_rejected(self):
        from iios.integration.policies import IntegrationPolicyEngine
        f   = _make_factory()
        eng = IntegrationPolicyEngine()
        eng.start()
        eng.load_policy(f.create_reject_all_policy())
        resp = eng.evaluate(_make_request(f))
        assert resp.is_rejected is True

    def test_response_has_audit_id(self):
        eng  = _make_engine()
        resp = eng.evaluate(_make_request())
        assert resp.audit_id

    def test_response_has_latency(self):
        eng  = _make_engine()
        resp = eng.evaluate(_make_request())
        assert resp.evaluation_time_ms >= 0

    def test_audit_entry_created(self):
        eng  = _make_engine()
        eng.evaluate(_make_request())
        assert eng.audit.count() >= 1

    def test_stats_updated_after_evaluate(self):
        eng  = _make_engine()
        eng.evaluate(_make_request())
        r = eng.stats.report()
        assert r.policies_evaluated  >= 1
        assert r.policies_approved   >= 1

    def test_history_records_request_response(self):
        eng  = _make_engine()
        req  = _make_request()
        eng.evaluate(req)
        assert eng.history.request_count()  >= 1
        assert eng.history.response_count() >= 1

    def test_events_emitted_on_evaluate(self):
        from iios.integration.policies import PolicyEventType
        eng      = _make_engine()
        received = []
        eng.event_bus.add_listener(received.append)
        eng.evaluate(_make_request())
        event_types = {e.event_type for e in received}
        assert PolicyEventType.GOVERNANCE_COMPLETED in event_types

    def test_query_cached_response(self):
        eng  = _make_engine()
        req  = _make_request()
        resp = eng.evaluate(req)
        cached = eng.query(req.request_id)
        assert cached is resp

    def test_query_unknown_returns_none(self):
        eng = _make_engine()
        assert eng.query("nonexistent-req-id") is None

    def test_emergency_stop_policy(self):
        from iios.integration.policies import IntegrationPolicyEngine, PolicyAction
        f   = _make_factory()
        eng = IntegrationPolicyEngine()
        eng.start()
        eng.load_policy(f.create_emergency_stop_policy())
        ctx = f.create_context(
            "req-001", "sess-001", "rest_api",
            environment = "emergency",   # triggers the stop
        )
        req  = f.create_request(ctx)
        resp = eng.evaluate(req)
        assert resp.decision.final_action == PolicyAction.EMERGENCY_STOP

    def test_security_approval_policy(self):
        from iios.integration.policies import IntegrationPolicyEngine, PolicyAction
        f   = _make_factory()
        eng = IntegrationPolicyEngine()
        eng.start()
        eng.load_policy(f.create_security_approval_policy())
        ctx = f.create_context(
            "req-001", "sess-001", "rest_api",
            security_config = {"requires_approval": True},
        )
        req  = f.create_request(ctx)
        resp = eng.evaluate(req)
        assert resp.decision.final_action == PolicyAction.REQUIRE_SECURITY_APPROVAL

    def test_validate_policy(self):
        eng    = _make_engine()
        f      = _make_factory()
        policy = f.create_approve_all_policy()
        report = eng.validate_policy(policy)
        assert report.passed

    def test_status_dict(self):
        eng = _make_engine()
        s   = eng.status()
        assert s["ready"]          is True
        assert s["policy_count"]   >= 1
        assert "statistics"        in s

    def test_chain_evaluation(self):
        from iios.integration.policies import (
            IntegrationPolicyEngine, IntegrationPolicyChain, PolicyChainMode,
        )
        f   = _make_factory()
        eng = IntegrationPolicyEngine()
        eng.start()
        chain = IntegrationPolicyChain(
            mode=PolicyChainMode.SEQUENTIAL,
            policies=[f.create_approve_all_policy()],
        )
        ctx      = _make_context(f)
        decision = eng.evaluate_chain(chain, ctx)
        assert decision.approved is True

    def test_manager_evaluate_context(self):
        mgr = _make_manager()
        ctx = _make_context()
        resp= mgr.evaluate_context(ctx)
        assert resp.is_approved is True
        mgr.stop()

    def test_manager_get_statistics(self):
        mgr = _make_manager()
        mgr.evaluate_context(_make_context())
        stats = mgr.get_statistics()
        assert stats.policies_evaluated >= 1
        mgr.stop()

    def test_manager_get_status(self):
        mgr = _make_manager()
        s   = mgr.get_status()
        assert s["ready"]          is True
        assert s["policy_count"]   >= 1
        mgr.stop()

    def test_load_and_remove_policy(self):
        from iios.integration.policies import IntegrationPolicyEngine
        f   = _make_factory()
        eng = IntegrationPolicyEngine()
        eng.start()
        p = f.create_approve_all_policy()
        eng.load_policy(p)
        assert eng.registry.count() == 1
        eng.remove_policy(p.policy_id)
        assert eng.registry.count() == 0


# ════════════════════════════════════════════════════════════════════════
# 21. Factory
# ════════════════════════════════════════════════════════════════════════


class TestFactory:
    def test_create_condition(self):
        from iios.integration.policies import ConditionOperator
        f = _make_factory()
        c = f.create_condition("env", "environment", ConditionOperator.EQUALS, "prod")
        assert c.field_path == "environment"

    def test_create_rule(self):
        from iios.integration.policies import PolicyAction
        f = _make_factory()
        r = f.create_rule("allow", PolicyAction.APPROVE)
        assert r.action == PolicyAction.APPROVE

    def test_create_policy(self):
        from iios.integration.policies import PolicyType
        f = _make_factory()
        p = f.create_policy("Test", PolicyType.COMPLIANCE)
        assert p.policy_id.startswith("pol-")

    def test_create_chain(self):
        from iios.integration.policies import PolicyChainMode
        f     = _make_factory()
        chain = f.create_chain(mode=PolicyChainMode.PARALLEL)
        assert chain.mode == PolicyChainMode.PARALLEL

    def test_create_context(self):
        f   = _make_factory()
        ctx = f.create_context("req-001", "sess-001", "kafka")
        assert ctx.connector_type == "kafka"

    def test_create_request(self):
        f   = _make_factory()
        ctx = _make_context(f)
        req = f.create_request(ctx)
        assert req.request_id.startswith("preq-")

    def test_approve_all_policy(self):
        from iios.integration.policies import PolicyAction
        f = _make_factory()
        p = f.create_approve_all_policy()
        assert p.evaluate({}) == PolicyAction.APPROVE

    def test_reject_all_policy(self):
        from iios.integration.policies import PolicyAction
        f = _make_factory()
        p = f.create_reject_all_policy()
        assert p.evaluate({}) == PolicyAction.REJECT

    def test_emergency_stop_policy(self):
        from iios.integration.policies import PolicyAction
        f = _make_factory()
        p = f.create_emergency_stop_policy(field_path="env", trigger_value="stop")
        assert p.evaluate({"env": "stop"})   == PolicyAction.EMERGENCY_STOP
        assert p.evaluate({"env": "normal"}) is None

    def test_security_approval_policy(self):
        from iios.integration.policies import PolicyAction
        f = _make_factory()
        p = f.create_security_approval_policy()
        result = p.evaluate({"security_config": {"requires_approval": True}})
        assert result == PolicyAction.REQUIRE_SECURITY_APPROVAL


# ════════════════════════════════════════════════════════════════════════
# 22. Concurrency
# ════════════════════════════════════════════════════════════════════════


class TestConcurrency:
    def test_concurrent_evaluate(self):
        eng     = _make_engine()
        results = []
        errors  = []

        def evaluate():
            try:
                resp = eng.evaluate(_make_request())
                results.append(resp)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=evaluate) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors       == []
        assert len(results) == 20
        assert all(r.is_approved for r in results)

    def test_concurrent_policy_registration(self):
        from iios.integration.policies import IntegrationPolicyRegistry
        f      = _make_factory()
        reg    = IntegrationPolicyRegistry(max_policies=200)
        errors = []

        def register():
            try:
                reg.register(f.create_approve_all_policy())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=register) for _ in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []

    def test_concurrent_statistics(self):
        from iios.integration.policies import IntegrationPolicyStatistics
        stats = IntegrationPolicyStatistics()

        def increment():
            for _ in range(200):
                stats.record_evaluated()

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert stats.report().policies_evaluated == 2000

    def test_concurrent_audit(self):
        from iios.integration.policies import (
            IntegrationPolicyAudit, IntegrationAuditEntry, GovernanceDecision, PolicyAction,
        )
        audit  = IntegrationPolicyAudit(max_entries=1000)
        errors = []

        def write():
            try:
                dec   = GovernanceDecision.create("req", PolicyAction.APPROVE, [])
                entry = IntegrationAuditEntry.create("req", "ctx", dec, [], 1.0)
                audit.record(entry)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=write) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []


# ════════════════════════════════════════════════════════════════════════
# 23. Stress Testing
# ════════════════════════════════════════════════════════════════════════


class TestStressTesting:
    def test_evaluate_1000_requests(self):
        eng = _make_engine()
        for _ in range(1000):
            resp = eng.evaluate(_make_request())
            assert resp.is_approved is True
        r = eng.stats.report()
        assert r.policies_evaluated >= 1000

    def test_history_bounded_under_load(self):
        from iios.integration.policies import IntegrationPolicyHistory
        h = IntegrationPolicyHistory(max_history=100)
        for _ in range(500):
            h.record_request(_make_request())
        assert h.request_count() == 100

    def test_audit_bounded_under_load(self):
        from iios.integration.policies import (
            IntegrationPolicyAudit, IntegrationAuditEntry, GovernanceDecision, PolicyAction,
        )
        audit = IntegrationPolicyAudit(max_entries=50)
        for _ in range(200):
            dec   = GovernanceDecision.create("req", PolicyAction.APPROVE, [])
            entry = IntegrationAuditEntry.create("req", "ctx", dec, [], 1.0)
            audit.record(entry)
        assert audit.count() == 50

    def test_event_bus_high_throughput(self):
        from iios.integration.policies import (
            IntegrationPolicyEventBus, PolicyEventType,
        )
        bus      = IntegrationPolicyEventBus()
        received = []
        bus.add_listener(received.append)
        for _ in range(500):
            bus.emit(PolicyEventType.GOVERNANCE_COMPLETED, "eng", "req")
        assert len(received) == 500


# ════════════════════════════════════════════════════════════════════════
# 24. Regression
# ════════════════════════════════════════════════════════════════════════


class TestRegression:
    def test_policies_module_importable(self):
        import iios.integration.policies as m
        assert hasattr(m, "IntegrationPolicyEngine")
        assert hasattr(m, "IntegrationPolicyManager")

    def test_engine_module_still_importable(self):
        import iios.integration.engine as m
        assert hasattr(m, "IntegrationEngine")

    def test_lifecycle_module_still_importable(self):
        import iios.integration.lifecycle as m
        assert hasattr(m, "IntegrationLifecycle")

    def test_knowledge_modules_importable(self):
        import iios.knowledge
        assert iios.knowledge is not None

    def test_supervisor_importable(self):
        import iios.supervisor
        assert iios.supervisor is not None

    def test_all_exports_present(self):
        from iios.integration.policies import __all__
        import iios.integration.policies as m
        for name in __all__:
            assert hasattr(m, name), f"Missing export: {name!r}"

    def test_no_network_code_in_engine(self):
        """Policy engine must not import any network/vendor clients."""
        import inspect
        import iios.integration.policies.integration_policy_engine as mod
        src = inspect.getsource(mod)
        for forbidden in ("requests.get", "httpx", "aiohttp", "kafka", "pika", "socket"):
            assert forbidden not in src, f"Forbidden import found: {forbidden!r}"

    def test_no_network_code_in_evaluator(self):
        import inspect
        import iios.integration.policies.integration_policy_evaluator as mod
        src = inspect.getsource(mod)
        for forbidden in ("requests", "httpx", "socket", "urllib"):
            assert forbidden not in src, f"Forbidden import found: {forbidden!r}"

    def test_engine_module_no_circular_import(self):
        """Policies must not import from integration.engine (avoid circular)."""
        import inspect
        import iios.integration.policies.integration_policy_engine as mod
        src = inspect.getsource(mod)
        assert "iios.integration.engine" not in src
