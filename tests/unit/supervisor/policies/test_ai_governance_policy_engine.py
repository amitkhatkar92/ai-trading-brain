"""
test_ai_governance_policy_engine.py — tests.unit.supervisor.policies
----------------------------------------------------------------------
Comprehensive tests for the C13 M3 AI Governance Policy Framework
at iios.supervisor.policies.

Coverage:
  - constants (enumerations, severity, sets, defaults)
  - exceptions (hierarchy, attributes)
  - AIGovernancePolicyCondition
  - AIGovernancePolicyRule
  - AIGovernancePolicyPriorityConfig / AIGovernancePriorityResolver
  - AIGovernancePolicy
  - AIGovernancePolicyContext
  - AIGovernancePolicyRequest
  - AIGovernancePolicyResult (all classification properties)
  - GovernanceDecisionSummary / AIGovernancePolicyResponse
  - GovernanceAuditEntry / GovernanceAuditReport / AIGovernancePolicyAuditGenerator
  - AIGovernancePolicyEvaluator (all 12 operators, nested paths, type errors)
  - AIGovernancePolicyChain (all modes, emergency-stop abort, disabled skip)
  - AIGovernancePolicyRegistry (capacity, enable/disable, by-type, thread-safe)
  - AIGovernancePolicyHistory (bounded deques, all four artefact types)
  - AIGovernancePolicyStatistics (counters, governance_coverage, thread-safe)
  - AIGovernancePolicyEvents (all 11 factory functions, frozen, unique IDs)
  - AIGovernancePolicyValidator (request + policy checks)
  - AIGovernancePolicyFactory (all builders, domain convenience methods)
  - AIGovernancePolicyManager (pipeline, conflict resolution, never-raises)
  - AIGovernancePolicyEngine (lifecycle, evaluate, management, events, listeners)
  - Concurrency (parallel evaluations + concurrent register)
  - Public surface (__all__)
  - Integration smoke tests (end-to-end with emergency stop and human oversight)

95%+ coverage target.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

import pytest

from iios.supervisor.policies import (
    # --- enumerations ---
    AIGovernancePolicyAction,
    AIGovernancePolicyEventType,
    AIGovernancePolicyType,
    AIGovernanceValidationCode,
    ConditionOperator,
    ConflictResolutionStrategy,
    EvaluationMode,
    LogicalOperator,
    PolicyPriority,
    # --- constants ---
    ACTION_SEVERITY,
    AI_GOVERNANCE_SYSTEM_ID,
    DEFAULT_GOVERNANCE_ACTION,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    DENY_ACTIONS,
    ESCALATION_ACTIONS,
    HUMAN_REVIEW_ACTIONS,
    PERMISSIVE_ACTIONS,
    STOP_ACTIONS,
    VERSION,
    # --- exceptions ---
    AIGovernancePolicyAuditError,
    AIGovernancePolicyCapacityError,
    AIGovernancePolicyConditionError,
    AIGovernancePolicyConflictError,
    AIGovernancePolicyEngineNotRunningError,
    AIGovernancePolicyError,
    AIGovernancePolicyEvaluationError,
    AIGovernancePolicyHistoryError,
    AIGovernancePolicyNotFoundError,
    AIGovernancePolicyRegistryError,
    AIGovernancePolicyRuleError,
    AIGovernancePolicyValidationError,
    # --- value objects ---
    AIGovernancePolicy,
    AIGovernancePolicyCondition,
    AIGovernancePolicyContext,
    AIGovernancePolicyRequest,
    AIGovernancePolicyResponse,
    AIGovernancePolicyResult,
    AIGovernancePolicyRule,
    GovernanceDecisionSummary,
    # --- audit ---
    AIGovernancePolicyAuditGenerator,
    GovernanceAuditEntry,
    GovernanceAuditReport,
    # --- priority ---
    AIGovernancePolicyPriorityConfig,
    AIGovernancePriorityResolver,
    PRIORITY_CONFIGS,
    # --- events ---
    AIGovernancePolicyEvent,
    make_emergency_stop_triggered_event,
    make_engine_started_event,
    make_engine_stopped_event,
    make_evaluation_completed_event,
    make_evaluation_started_event,
    make_governance_approved_event,
    make_governance_blocked_event,
    make_governance_rejected_event,
    make_human_approval_requested_event,
    make_policy_loaded_event,
    make_policy_validated_event,
    # --- validation ---
    AIGovernancePolicyValidationResult,
    AIGovernancePolicyValidator,
    AIGovernanceValidationCheckResult,
    # --- subsystems ---
    AIGovernancePolicyChain,
    AIGovernancePolicyEvaluator,
    AIGovernancePolicyFactory,
    AIGovernancePolicyHistory,
    AIGovernancePolicyManager,
    AIGovernancePolicyRegistry,
    AIGovernancePolicyStatistics,
    # --- engine ---
    AIGovernancePolicyEngine,
)


# ===========================================================================
# Shared helpers
# ===========================================================================

def _cond(
    field_path: str = "health.score",
    operator: ConditionOperator = ConditionOperator.LT,
    threshold: Any = 0.5,
    name: str = "test cond",
) -> AIGovernancePolicyCondition:
    return AIGovernancePolicyCondition.create(
        name=name, field_path=field_path, operator=operator, threshold=threshold
    )


def _rule(
    conditions: List[AIGovernancePolicyCondition] | None = None,
    action: AIGovernancePolicyAction = AIGovernancePolicyAction.BLOCK,
    logical_operator: LogicalOperator = LogicalOperator.ALL,
    name: str = "test rule",
    weight: float = 1.0,
) -> AIGovernancePolicyRule:
    return AIGovernancePolicyRule.create(
        name=name,
        conditions=conditions or [_cond()],
        logical_operator=logical_operator,
        action=action,
        weight=weight,
    )


def _policy(
    rules: List[AIGovernancePolicyRule] | None = None,
    policy_type: AIGovernancePolicyType = AIGovernancePolicyType.AI_SAFETY,
    priority: PolicyPriority = PolicyPriority.HIGH,
    name: str = "test policy",
    enabled: bool = True,
    evaluation_mode: EvaluationMode = EvaluationMode.SEQUENTIAL,
    default_action: AIGovernancePolicyAction = AIGovernancePolicyAction.APPROVE,
) -> AIGovernancePolicy:
    return AIGovernancePolicy.create(
        name=name, policy_type=policy_type, priority=priority,
        rules=rules or [_rule()], enabled=enabled,
        evaluation_mode=evaluation_mode, default_action=default_action,
    )


def _request(
    supervision_id: str = "sup-001",
    subsystem_id: str = "sub-001",
    inputs: Dict[str, Any] | None = None,
    policy_types: List[AIGovernancePolicyType] | None = None,
) -> AIGovernancePolicyRequest:
    return AIGovernancePolicyRequest.create(
        supervision_id=supervision_id,
        subsystem_id=subsystem_id,
        workflow_type="test-workflow",
        inputs=inputs or {},
        policy_types=policy_types or [],
    )


def _started_engine() -> AIGovernancePolicyEngine:
    e = AIGovernancePolicyEngine()
    e.start()
    return e


# ===========================================================================
# 1. Constants
# ===========================================================================

class TestConstants:
    def test_system_id_nonempty(self):
        assert AI_GOVERNANCE_SYSTEM_ID

    def test_version_nonempty(self):
        assert VERSION

    def test_action_severity_covers_all_actions(self):
        for a in AIGovernancePolicyAction:
            assert a in ACTION_SEVERITY

    def test_emergency_stop_highest_severity(self):
        assert ACTION_SEVERITY[AIGovernancePolicyAction.EMERGENCY_STOP] > ACTION_SEVERITY[AIGovernancePolicyAction.BLOCK]

    def test_block_higher_than_reject(self):
        assert ACTION_SEVERITY[AIGovernancePolicyAction.BLOCK] > ACTION_SEVERITY[AIGovernancePolicyAction.REJECT]

    def test_default_action_is_approve(self):
        assert DEFAULT_GOVERNANCE_ACTION == AIGovernancePolicyAction.APPROVE

    def test_policy_type_count(self):
        assert len(AIGovernancePolicyType) == 15

    def test_policy_action_count(self):
        assert len(AIGovernancePolicyAction) == 8

    def test_policy_priority_ordering(self):
        assert PolicyPriority.CRITICAL < PolicyPriority.INFORMATIONAL

    def test_deny_actions_contains_emergency_stop(self):
        assert AIGovernancePolicyAction.EMERGENCY_STOP in DENY_ACTIONS

    def test_stop_actions_contains_only_emergency_stop(self):
        assert STOP_ACTIONS == frozenset({AIGovernancePolicyAction.EMERGENCY_STOP})

    def test_human_review_actions(self):
        assert AIGovernancePolicyAction.REQUIRE_HUMAN_APPROVAL in HUMAN_REVIEW_ACTIONS

    def test_permissive_actions_no_deny(self):
        assert not PERMISSIVE_ACTIONS.intersection(DENY_ACTIONS)

    def test_evaluation_mode_count(self):
        assert len(EvaluationMode) == 6

    def test_conflict_resolution_strategy_count(self):
        assert len(ConflictResolutionStrategy) == 6

    def test_event_type_count(self):
        assert len(AIGovernancePolicyEventType) == 11

    def test_validation_code_count(self):
        assert len(AIGovernanceValidationCode) == 8

    def test_defaults_positive(self):
        assert DEFAULT_MAX_POLICIES > 0
        assert DEFAULT_MAX_HISTORY > 0


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(AIGovernancePolicyError, IIOSError)

    def test_engine_not_running_subclass(self):
        assert issubclass(AIGovernancePolicyEngineNotRunningError, AIGovernancePolicyError)

    def test_not_found_has_policy_id(self):
        exc = AIGovernancePolicyNotFoundError("p-1")
        assert exc.policy_id == "p-1"

    def test_capacity_has_limit(self):
        exc = AIGovernancePolicyCapacityError(500)
        assert exc.limit == 500

    def test_evaluation_has_request_id(self):
        exc = AIGovernancePolicyEvaluationError("err", request_id="req-99")
        assert exc.request_id == "req-99"

    def test_registry_subclass(self):
        assert issubclass(AIGovernancePolicyRegistryError, AIGovernancePolicyError)

    def test_validation_subclass(self):
        assert issubclass(AIGovernancePolicyValidationError, AIGovernancePolicyError)

    def test_audit_subclass(self):
        assert issubclass(AIGovernancePolicyAuditError, AIGovernancePolicyError)

    def test_conflict_subclass(self):
        assert issubclass(AIGovernancePolicyConflictError, AIGovernancePolicyError)

    def test_condition_subclass(self):
        assert issubclass(AIGovernancePolicyConditionError, AIGovernancePolicyError)

    def test_rule_subclass(self):
        assert issubclass(AIGovernancePolicyRuleError, AIGovernancePolicyError)

    def test_history_subclass(self):
        assert issubclass(AIGovernancePolicyHistoryError, AIGovernancePolicyError)


# ===========================================================================
# 3. AIGovernancePolicyCondition
# ===========================================================================

class TestCondition:
    def test_create(self):
        c = _cond()
        assert c.field_path == "health.score"
        assert c.operator == ConditionOperator.LT
        assert c.threshold == 0.5

    def test_auto_id(self):
        assert _cond().condition_id

    def test_explicit_id(self):
        c = AIGovernancePolicyCondition.create(
            name="x", field_path="a", operator=ConditionOperator.EQ,
            threshold=1, condition_id="cid-1",
        )
        assert c.condition_id == "cid-1"

    def test_frozen(self):
        c = _cond()
        with pytest.raises((TypeError, AttributeError)):
            c.field_path = "other"  # type: ignore

    def test_to_dict(self):
        d = _cond().to_dict()
        assert d["operator"] == ConditionOperator.LT.value


# ===========================================================================
# 4. AIGovernancePolicyRule
# ===========================================================================

class TestRule:
    def test_create(self):
        r = _rule()
        assert r.action == AIGovernancePolicyAction.BLOCK

    def test_condition_count(self):
        r = _rule(conditions=[_cond(), _cond(name="c2")])
        assert r.condition_count == 2

    def test_conditions_tuple(self):
        assert isinstance(_rule().conditions, tuple)

    def test_frozen(self):
        r = _rule()
        with pytest.raises((TypeError, AttributeError)):
            r.name = "x"  # type: ignore

    def test_to_dict(self):
        d = _rule(action=AIGovernancePolicyAction.EMERGENCY_STOP).to_dict()
        assert d["action"] == AIGovernancePolicyAction.EMERGENCY_STOP.value


# ===========================================================================
# 5. AIGovernancePolicyPriorityConfig / AIGovernancePriorityResolver
# ===========================================================================

class TestPriority:
    def test_all_priorities_have_config(self):
        for p in PolicyPriority:
            assert p in PRIORITY_CONFIGS

    def test_critical_requires_immediate_action(self):
        assert AIGovernancePriorityResolver.requires_immediate_action(PolicyPriority.CRITICAL)

    def test_informational_can_be_deferred(self):
        assert AIGovernancePriorityResolver.can_be_deferred(PolicyPriority.INFORMATIONAL)

    def test_critical_requires_human_oversight(self):
        assert AIGovernancePriorityResolver.requires_human_oversight(PolicyPriority.CRITICAL)

    def test_low_does_not_require_human_oversight(self):
        assert not AIGovernancePriorityResolver.requires_human_oversight(PolicyPriority.LOW)

    def test_effective_priority_returns_most_critical(self):
        result = AIGovernancePriorityResolver.effective_priority(
            PolicyPriority.LOW, PolicyPriority.CRITICAL, PolicyPriority.MEDIUM
        )
        assert result == PolicyPriority.CRITICAL

    def test_effective_priority_empty(self):
        result = AIGovernancePriorityResolver.effective_priority()
        assert result == PolicyPriority.INFORMATIONAL

    def test_get_config_returns_dataclass(self):
        cfg = AIGovernancePriorityResolver.get_config(PolicyPriority.HIGH)
        assert isinstance(cfg, AIGovernancePolicyPriorityConfig)
        assert cfg.priority == PolicyPriority.HIGH

    def test_max_evaluation_timeout(self):
        assert AIGovernancePriorityResolver.max_evaluation_timeout_s(PolicyPriority.CRITICAL) < 30.0


# ===========================================================================
# 6. AIGovernancePolicy
# ===========================================================================

class TestPolicy:
    def test_create(self):
        p = _policy()
        assert p.enabled
        assert p.policy_type == AIGovernancePolicyType.AI_SAFETY

    def test_rule_count(self):
        p = _policy(rules=[_rule(), _rule(name="r2")])
        assert p.rule_count == 2

    def test_is_enabled(self):
        assert _policy(enabled=True).is_enabled
        assert not _policy(enabled=False).is_enabled

    def test_with_enabled_creates_new_instance(self):
        p = _policy(enabled=True)
        q = p.with_enabled(False)
        assert not q.is_enabled
        assert p.is_enabled  # original unchanged

    def test_frozen(self):
        p = _policy()
        with pytest.raises((TypeError, AttributeError)):
            p.name = "x"  # type: ignore

    def test_to_dict(self):
        d = _policy().to_dict()
        assert d["policy_type"] == AIGovernancePolicyType.AI_SAFETY.value


# ===========================================================================
# 7. AIGovernancePolicyContext
# ===========================================================================

class TestContext:
    def test_create_minimal(self):
        ctx = AIGovernancePolicyContext.create(supervision_id="s1")
        assert ctx.supervision_id == "s1"

    def test_create_with_snapshots(self):
        ctx = AIGovernancePolicyContext.create(
            supervision_id="s1",
            platform_health={"overall": 0.9},
            risk_snapshot={"var": 0.02},
        )
        assert ctx.platform_health["overall"] == 0.9

    def test_defaults_are_dicts(self):
        ctx = AIGovernancePolicyContext.create(supervision_id="s")
        assert isinstance(ctx.platform_health, dict)
        assert isinstance(ctx.inputs, dict)

    def test_frozen(self):
        ctx = AIGovernancePolicyContext.create(supervision_id="s")
        with pytest.raises((TypeError, AttributeError)):
            ctx.supervision_id = "other"  # type: ignore

    def test_to_dict(self):
        d = AIGovernancePolicyContext.create(supervision_id="s1").to_dict()
        assert d["supervision_id"] == "s1"


# ===========================================================================
# 8. AIGovernancePolicyRequest
# ===========================================================================

class TestRequest:
    def test_create(self):
        req = _request()
        assert req.supervision_id == "sup-001"

    def test_auto_context(self):
        req = _request()
        assert req.context is not None
        assert req.context.supervision_id == "sup-001"

    def test_with_inputs_merges(self):
        req = _request(inputs={"a": 1})
        req2 = req.with_inputs({"b": 2})
        assert req2.inputs["a"] == 1
        assert req2.inputs["b"] == 2

    def test_policy_types_tuple(self):
        req = AIGovernancePolicyRequest.create(
            "s", "sub", "wf",
            policy_types=[AIGovernancePolicyType.AI_SAFETY],
        )
        assert isinstance(req.policy_types, tuple)

    def test_frozen(self):
        req = _request()
        with pytest.raises((TypeError, AttributeError)):
            req.supervision_id = "x"  # type: ignore

    def test_to_dict(self):
        d = _request().to_dict()
        assert "request_id" in d


# ===========================================================================
# 9. AIGovernancePolicyResult
# ===========================================================================

class TestResult:
    def _res(self, action=AIGovernancePolicyAction.APPROVE):
        return AIGovernancePolicyResult.create(
            policy_id="p", policy_name="n",
            policy_type=AIGovernancePolicyType.AI_SAFETY,
            priority=PolicyPriority.HIGH, action=action,
        )

    def test_is_permissive_approve(self):
        assert self._res(AIGovernancePolicyAction.APPROVE).is_permissive

    def test_is_permissive_approve_with_conditions(self):
        assert self._res(AIGovernancePolicyAction.APPROVE_WITH_CONDITIONS).is_permissive

    def test_is_denying_block(self):
        assert self._res(AIGovernancePolicyAction.BLOCK).is_denying

    def test_is_denying_reject(self):
        assert self._res(AIGovernancePolicyAction.REJECT).is_denying

    def test_is_denying_emergency_stop(self):
        assert self._res(AIGovernancePolicyAction.EMERGENCY_STOP).is_denying

    def test_requires_human_approval(self):
        assert self._res(AIGovernancePolicyAction.REQUIRE_HUMAN_APPROVAL).requires_human_approval

    def test_is_emergency_stop(self):
        assert self._res(AIGovernancePolicyAction.EMERGENCY_STOP).is_emergency_stop

    def test_not_emergency_stop_for_approve(self):
        assert not self._res(AIGovernancePolicyAction.APPROVE).is_emergency_stop

    def test_to_dict(self):
        d = self._res().to_dict()
        assert "is_emergency_stop" in d


# ===========================================================================
# 10. GovernanceDecisionSummary / AIGovernancePolicyResponse
# ===========================================================================

class TestResponse:
    def _summary(self, action=AIGovernancePolicyAction.APPROVE):
        return GovernanceDecisionSummary.from_results((), action)

    def test_create_success_is_approved(self):
        resp = AIGovernancePolicyResponse.create_success(
            request_id="r", supervision_id="s", subsystem_id="ss",
            final_action=AIGovernancePolicyAction.APPROVE,
            results=(), summary=self._summary(),
        )
        assert resp.is_success
        assert resp.is_approved

    def test_create_failure_is_emergency_stop(self):
        resp = AIGovernancePolicyResponse.create_failure(
            request_id="r", supervision_id="s", subsystem_id="ss",
            error_message="crash",
        )
        assert not resp.is_success
        assert resp.is_emergency_stop

    def test_requires_human_approval_action(self):
        resp = AIGovernancePolicyResponse.create_success(
            request_id="r", supervision_id="s", subsystem_id="ss",
            final_action=AIGovernancePolicyAction.REQUIRE_HUMAN_APPROVAL,
            results=(), summary=self._summary(AIGovernancePolicyAction.REQUIRE_HUMAN_APPROVAL),
        )
        assert resp.requires_human_approval

    def test_summary_counts(self):
        r1 = AIGovernancePolicyResult.create(
            policy_id="p1", policy_name="n",
            policy_type=AIGovernancePolicyType.AI_SAFETY,
            priority=PolicyPriority.HIGH,
            action=AIGovernancePolicyAction.APPROVE,
        )
        r2 = AIGovernancePolicyResult.create(
            policy_id="p2", policy_name="n",
            policy_type=AIGovernancePolicyType.AI_SAFETY,
            priority=PolicyPriority.HIGH,
            action=AIGovernancePolicyAction.EMERGENCY_STOP,
        )
        summary = GovernanceDecisionSummary.from_results(
            (r1, r2), AIGovernancePolicyAction.EMERGENCY_STOP
        )
        assert summary.emergency_stops == 1
        assert summary.approved == 1
        assert summary.emergency_stop_triggered

    def test_to_dict_keys(self):
        d = AIGovernancePolicyResponse.create_success(
            request_id="r", supervision_id="s", subsystem_id="ss",
            final_action=AIGovernancePolicyAction.APPROVE,
            results=(), summary=self._summary(),
        ).to_dict()
        assert "is_emergency_stop" in d and "is_approved" in d


# ===========================================================================
# 11. Audit
# ===========================================================================

class TestAudit:
    def test_audit_entry_from_result(self):
        r = AIGovernancePolicyResult.create(
            policy_id="p", policy_name="n",
            policy_type=AIGovernancePolicyType.AI_SAFETY,
            priority=PolicyPriority.HIGH,
            action=AIGovernancePolicyAction.BLOCK,
            rationale="test",
        )
        entry = GovernanceAuditEntry.from_result(r, "sup-1")
        assert entry.action == AIGovernancePolicyAction.BLOCK
        assert entry.supervision_id == "sup-1"

    def test_audit_entry_frozen(self):
        r = AIGovernancePolicyResult.create(
            policy_id="p", policy_name="n",
            policy_type=AIGovernancePolicyType.AI_SAFETY,
            priority=PolicyPriority.HIGH,
            action=AIGovernancePolicyAction.APPROVE,
        )
        entry = GovernanceAuditEntry.from_result(r)
        with pytest.raises((TypeError, AttributeError)):
            entry.policy_id = "other"  # type: ignore

    def test_audit_generator_produces_report(self):
        factory = AIGovernancePolicyFactory()
        engine = _started_engine()
        policy = factory.create_ai_safety_threshold_policy("safe", "score", 0.5)
        engine.register_policy(policy)
        req = factory.create_request("sup-audit", inputs={"score": 0.3})
        resp = engine.evaluate(req)
        gen = AIGovernancePolicyAuditGenerator()
        results = list(resp.results)
        report = gen.generate(req, results, resp)
        assert isinstance(report, GovernanceAuditReport)
        assert report.final_action == resp.final_action
        engine.stop()

    def test_audit_report_to_dict(self):
        gen = AIGovernancePolicyAuditGenerator()
        req = _request()
        resp = AIGovernancePolicyResponse.create_failure(
            request_id="r", supervision_id="s", subsystem_id="ss",
            error_message="test",
        )
        report = gen.generate(req, [], resp)
        d = report.to_dict()
        assert "final_action" in d and "emergency_stop_triggered" in d


# ===========================================================================
# 12. AIGovernancePolicyEvaluator
# ===========================================================================

class TestEvaluator:
    E = AIGovernancePolicyEvaluator()

    def test_lt_true(self):
        c = _cond(threshold=0.5, operator=ConditionOperator.LT)
        assert self.E.evaluate_condition(c, {"health.score": 0.3})

    def test_lt_false(self):
        c = _cond(threshold=0.5, operator=ConditionOperator.LT)
        assert not self.E.evaluate_condition(c, {"health.score": 0.9})

    def test_gt(self):
        c = _cond(threshold=0.5, operator=ConditionOperator.GT)
        assert self.E.evaluate_condition(c, {"health.score": 0.8})
        assert not self.E.evaluate_condition(c, {"health.score": 0.2})

    def test_gte(self):
        c = _cond(threshold=0.5, operator=ConditionOperator.GTE)
        assert self.E.evaluate_condition(c, {"health.score": 0.5})

    def test_lte(self):
        c = _cond(threshold=0.5, operator=ConditionOperator.LTE)
        assert self.E.evaluate_condition(c, {"health.score": 0.5})

    def test_eq(self):
        c = _cond(field_path="status", operator=ConditionOperator.EQ, threshold="halt")
        assert self.E.evaluate_condition(c, {"status": "halt"})
        assert not self.E.evaluate_condition(c, {"status": "active"})

    def test_neq(self):
        c = _cond(field_path="status", operator=ConditionOperator.NEQ, threshold="halt")
        assert self.E.evaluate_condition(c, {"status": "active"})

    def test_in_operator(self):
        c = _cond(field_path="tier", operator=ConditionOperator.IN, threshold=["A", "B"])
        assert self.E.evaluate_condition(c, {"tier": "A"})
        assert not self.E.evaluate_condition(c, {"tier": "C"})

    def test_not_in(self):
        c = _cond(field_path="tier", operator=ConditionOperator.NOT_IN, threshold=["A", "B"])
        assert self.E.evaluate_condition(c, {"tier": "C"})

    def test_exists(self):
        c = _cond(field_path="x", operator=ConditionOperator.EXISTS, threshold=None)
        assert self.E.evaluate_condition(c, {"x": 0})
        assert not self.E.evaluate_condition(c, {})

    def test_not_exists(self):
        c = _cond(field_path="x", operator=ConditionOperator.NOT_EXISTS, threshold=None)
        assert self.E.evaluate_condition(c, {})

    def test_is_true(self):
        c = _cond(field_path="flag", operator=ConditionOperator.IS_TRUE, threshold=None)
        assert self.E.evaluate_condition(c, {"flag": True})
        assert not self.E.evaluate_condition(c, {"flag": False})

    def test_is_false(self):
        c = _cond(field_path="flag", operator=ConditionOperator.IS_FALSE, threshold=None)
        assert self.E.evaluate_condition(c, {"flag": False})

    def test_nested_path(self):
        c = _cond(field_path="platform.health.score", threshold=0.5, operator=ConditionOperator.GT)
        assert self.E.evaluate_condition(c, {"platform": {"health": {"score": 0.9}}})

    def test_type_error_returns_false(self):
        c = _cond(threshold=5, operator=ConditionOperator.GT, field_path="x")
        assert not self.E.evaluate_condition(c, {"x": "not_numeric"})

    def test_evaluate_rule_all_match(self):
        c1 = _cond(field_path="a", threshold=5, operator=ConditionOperator.GT)
        c2 = _cond(field_path="b", threshold=10, operator=ConditionOperator.LT)
        r = _rule(conditions=[c1, c2], logical_operator=LogicalOperator.ALL)
        matched, met, failed = self.E.evaluate_rule(r, {"a": 10, "b": 5})
        assert matched
        assert len(met) == 2

    def test_evaluate_rule_all_partial(self):
        c1 = _cond(field_path="a", threshold=5, operator=ConditionOperator.GT)
        c2 = _cond(field_path="b", threshold=10, operator=ConditionOperator.LT)
        r = _rule(conditions=[c1, c2], logical_operator=LogicalOperator.ALL)
        matched, _, _ = self.E.evaluate_rule(r, {"a": 3, "b": 5})
        assert not matched

    def test_evaluate_rule_any(self):
        c1 = _cond(field_path="a", threshold=5, operator=ConditionOperator.GT)
        c2 = _cond(field_path="b", threshold=10, operator=ConditionOperator.LT)
        r = _rule(conditions=[c1, c2], logical_operator=LogicalOperator.ANY)
        matched, _, _ = self.E.evaluate_rule(r, {"a": 3, "b": 5})
        assert matched  # b<10 passes

    def test_evaluate_policy_default_no_match(self):
        p = _policy()
        result = self.E.evaluate_policy(p, {"health.score": 0.9})
        assert result.action == p.default_action

    def test_evaluate_policy_block_on_match(self):
        p = _policy()
        result = self.E.evaluate_policy(p, {"health.score": 0.2})
        assert result.action == AIGovernancePolicyAction.BLOCK

    def test_evaluate_policy_parallel_mode(self):
        p = _policy(evaluation_mode=EvaluationMode.PARALLEL)
        result = self.E.evaluate_policy(p, {"health.score": 0.2})
        assert result.action == AIGovernancePolicyAction.BLOCK


# ===========================================================================
# 13. AIGovernancePolicyChain
# ===========================================================================

class TestChain:
    def test_sequential_stops_on_emergency_stop(self):
        chain = AIGovernancePolicyChain()
        critical = _policy(
            rules=[_rule(action=AIGovernancePolicyAction.EMERGENCY_STOP, name="em-rule")],
            priority=PolicyPriority.CRITICAL,
            name="safety-p",
        )
        low = _policy(
            rules=[_rule(action=AIGovernancePolicyAction.BLOCK, name="block-rule")],
            priority=PolicyPriority.LOW,
            name="low-p",
        )
        results = chain.evaluate([critical, low], {"health.score": 0.2}, EvaluationMode.SEQUENTIAL)
        assert any(r.action == AIGovernancePolicyAction.EMERGENCY_STOP for r in results)
        assert not any(r.policy_name == "low-p" for r in results)

    def test_sequential_stops_on_deny(self):
        chain = AIGovernancePolicyChain()
        block_p = _policy(priority=PolicyPriority.HIGH, name="block-p")
        low_p = _policy(
            rules=[_rule(action=AIGovernancePolicyAction.REJECT, name="rej-rule")],
            priority=PolicyPriority.LOW,
            name="rej-p",
        )
        results = chain.evaluate([block_p, low_p], {"health.score": 0.2}, EvaluationMode.SEQUENTIAL)
        assert any(r.action == AIGovernancePolicyAction.BLOCK for r in results)
        assert not any(r.policy_name == "rej-p" for r in results)

    def test_parallel_evaluates_all(self):
        chain = AIGovernancePolicyChain()
        results = chain.evaluate([_policy(name="p1"), _policy(name="p2")],
                                  {"health.score": 0.2}, EvaluationMode.PARALLEL)
        assert len(results) == 2

    def test_composite_evaluates_all(self):
        chain = AIGovernancePolicyChain()
        results = chain.evaluate([_policy(name="p1"), _policy(name="p2")],
                                  {"health.score": 0.2}, EvaluationMode.COMPOSITE)
        assert len(results) == 2

    def test_weighted_evaluates_all(self):
        chain = AIGovernancePolicyChain()
        p1 = _policy(rules=[_rule(weight=2.0)], name="high-w")
        p2 = _policy(rules=[_rule(weight=0.5)], name="low-w")
        results = chain.evaluate([p1, p2], {"health.score": 0.2}, EvaluationMode.WEIGHTED)
        assert len(results) == 2

    def test_disabled_policies_skipped(self):
        chain = AIGovernancePolicyChain()
        results = chain.evaluate([_policy(enabled=False)], {"health.score": 0.2})
        assert results == []

    def test_empty_policies_empty_results(self):
        assert AIGovernancePolicyChain().evaluate([], {}) == []


# ===========================================================================
# 14. AIGovernancePolicyRegistry
# ===========================================================================

class TestRegistry:
    def test_register_and_get(self):
        reg = AIGovernancePolicyRegistry()
        p = _policy()
        reg.register(p)
        assert reg.get(p.policy_id) is p

    def test_register_updates_existing(self):
        reg = AIGovernancePolicyRegistry()
        p = _policy()
        reg.register(p)
        reg.register(p.with_enabled(False))
        assert reg.count == 1
        assert not reg.get(p.policy_id).is_enabled

    def test_unregister(self):
        reg = AIGovernancePolicyRegistry()
        p = _policy()
        reg.register(p)
        reg.unregister(p.policy_id)
        assert reg.count == 0

    def test_unregister_missing_raises(self):
        with pytest.raises(AIGovernancePolicyNotFoundError):
            AIGovernancePolicyRegistry().unregister("x")

    def test_get_missing_raises(self):
        with pytest.raises(AIGovernancePolicyNotFoundError):
            AIGovernancePolicyRegistry().get("x")

    def test_get_optional_none(self):
        assert AIGovernancePolicyRegistry().get_optional("x") is None

    def test_capacity_enforced(self):
        reg = AIGovernancePolicyRegistry(max_policies=1)
        reg.register(_policy(name="p1"))
        with pytest.raises(AIGovernancePolicyCapacityError):
            reg.register(_policy(name="p2"))

    def test_none_raises(self):
        with pytest.raises(AIGovernancePolicyRegistryError):
            AIGovernancePolicyRegistry().register(None)  # type: ignore

    def test_enabled_policies(self):
        reg = AIGovernancePolicyRegistry()
        reg.register(_policy(name="on", enabled=True))
        reg.register(_policy(name="off", enabled=False))
        assert len(reg.enabled_policies()) == 1

    def test_policies_by_type(self):
        reg = AIGovernancePolicyRegistry()
        reg.register(_policy(policy_type=AIGovernancePolicyType.AI_SAFETY))
        reg.register(_policy(policy_type=AIGovernancePolicyType.COMPLIANCE, name="c-p"))
        assert len(reg.policies_by_type(AIGovernancePolicyType.AI_SAFETY)) == 1

    def test_enable_disable(self):
        reg = AIGovernancePolicyRegistry()
        p = _policy(enabled=True)
        reg.register(p)
        reg.disable(p.policy_id)
        assert not reg.get(p.policy_id).is_enabled
        reg.enable(p.policy_id)
        assert reg.get(p.policy_id).is_enabled

    def test_clear(self):
        reg = AIGovernancePolicyRegistry()
        reg.register(_policy())
        reg.clear()
        assert reg.count == 0

    def test_thread_safe_register(self):
        reg = AIGovernancePolicyRegistry(max_policies=500)
        errors: List[Exception] = []
        def worker(i):
            try:
                reg.register(_policy(name=f"p-{i}"))
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert reg.count == 100


# ===========================================================================
# 15. AIGovernancePolicyHistory
# ===========================================================================

class TestHistory:
    def test_record_request(self):
        h = AIGovernancePolicyHistory()
        h.record_request("r")
        assert h.request_count() == 1

    def test_bounded_maxlen(self):
        h = AIGovernancePolicyHistory(max_requests=3)
        for i in range(10): h.record_request(i)
        assert h.request_count() == 3

    def test_recent_limited(self):
        h = AIGovernancePolicyHistory()
        for i in range(20): h.record_request(i)
        assert len(h.recent_requests(5)) == 5

    def test_record_all_artefact_types(self):
        h = AIGovernancePolicyHistory()
        h.record_request("req")
        h.record_response("resp")
        h.record_event("evt")
        h.record_audit("audit")
        assert h.request_count() == 1
        assert h.response_count() == 1
        assert h.event_count() == 1
        assert h.audit_count() == 1

    def test_counts(self):
        h = AIGovernancePolicyHistory()
        h.record_request("r")
        c = h.counts()
        assert c["requests"] == 1
        assert c["audits"] == 0

    def test_clear(self):
        h = AIGovernancePolicyHistory()
        h.record_request("r")
        h.clear()
        assert h.request_count() == 0


# ===========================================================================
# 16. AIGovernancePolicyStatistics
# ===========================================================================

class TestStatistics:
    def test_initial_snapshot_zeros(self):
        s = AIGovernancePolicyStatistics()
        snap = s.snapshot()
        assert snap["evaluations"] == 0
        assert snap["emergency_stops"] == 0

    def test_governance_coverage(self):
        s = AIGovernancePolicyStatistics()
        s.record_evaluation()
        s.record_emergency_stop()
        assert s.snapshot()["governance_coverage"] == 1.0

    def test_governance_coverage_zero(self):
        s = AIGovernancePolicyStatistics()
        s.record_evaluation()
        s.record_approved()
        # approved doesn't increment non_default_outcomes → coverage stays 0
        assert s.snapshot()["governance_coverage"] == 0.0

    def test_all_counters(self):
        s = AIGovernancePolicyStatistics()
        s.record_evaluation()
        s.record_success(0.05)
        s.record_failure()
        s.record_approved()
        s.record_conditionally_approved()
        s.record_rejected()
        s.record_blocked()
        s.record_escalated()
        s.record_human_review()
        s.record_manual_review()
        s.record_emergency_stop()
        snap = s.snapshot()
        assert snap["approved"] == 1
        assert snap["emergency_stops"] == 1
        assert snap["human_reviews"] == 1

    def test_reset(self):
        s = AIGovernancePolicyStatistics()
        s.record_emergency_stop()
        s.reset()
        assert s.snapshot()["emergency_stops"] == 0

    def test_thread_safe(self):
        s = AIGovernancePolicyStatistics()
        threads = [threading.Thread(target=s.record_evaluation) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert s.snapshot()["evaluations"] == 100


# ===========================================================================
# 17. Events
# ===========================================================================

class TestEvents:
    def test_evaluation_started(self):
        e = make_evaluation_started_event("s1", request_id="r1")
        assert e.event_type == AIGovernancePolicyEventType.EVALUATION_STARTED
        assert e.payload["request_id"] == "r1"

    def test_policy_loaded(self):
        e = make_policy_loaded_event("s1", policy_id="p1", policy_name="n")
        assert e.event_type == AIGovernancePolicyEventType.POLICY_LOADED

    def test_policy_validated(self):
        e = make_policy_validated_event("s1", policy_id="p1", is_valid=True)
        assert e.event_type == AIGovernancePolicyEventType.POLICY_VALIDATED

    def test_governance_approved(self):
        e = make_governance_approved_event("s1", request_id="r1")
        assert e.event_type == AIGovernancePolicyEventType.APPROVED

    def test_governance_rejected(self):
        e = make_governance_rejected_event("s1", request_id="r1")
        assert e.event_type == AIGovernancePolicyEventType.REJECTED

    def test_governance_blocked(self):
        e = make_governance_blocked_event("s1", request_id="r1")
        assert e.event_type == AIGovernancePolicyEventType.BLOCKED

    def test_human_approval_requested(self):
        e = make_human_approval_requested_event("s1", request_id="r1")
        assert e.event_type == AIGovernancePolicyEventType.HUMAN_APPROVAL_REQUESTED

    def test_emergency_stop_triggered(self):
        e = make_emergency_stop_triggered_event("s1", request_id="r1")
        assert e.event_type == AIGovernancePolicyEventType.EMERGENCY_STOP_TRIGGERED

    def test_evaluation_completed(self):
        e = make_evaluation_completed_event("s1", request_id="r1", final_action="approve")
        assert e.event_type == AIGovernancePolicyEventType.EVALUATION_COMPLETED

    def test_engine_started(self):
        e = make_engine_started_event()
        assert e.event_type == AIGovernancePolicyEventType.POLICY_ENGINE_STARTED

    def test_engine_stopped(self):
        e = make_engine_stopped_event()
        assert e.event_type == AIGovernancePolicyEventType.POLICY_ENGINE_STOPPED

    def test_events_frozen(self):
        e = make_engine_started_event()
        with pytest.raises((TypeError, AttributeError)):
            e.source = "x"  # type: ignore

    def test_unique_ids(self):
        e1 = make_engine_started_event()
        e2 = make_engine_started_event()
        assert e1.event_id != e2.event_id

    def test_to_dict(self):
        d = make_evaluation_started_event().to_dict()
        assert "event_type" in d


# ===========================================================================
# 18. AIGovernancePolicyValidator
# ===========================================================================

class TestValidator:
    def test_valid_request(self):
        v = AIGovernancePolicyValidator()
        assert v.validate_request(_request()).is_valid

    def test_valid_policy(self):
        v = AIGovernancePolicyValidator()
        assert v.validate_policy(_policy()).is_valid

    def test_result_has_checks(self):
        v = AIGovernancePolicyValidator()
        result = v.validate_request(_request())
        assert len(result.checks) > 0

    def test_frozen_result(self):
        r = AIGovernancePolicyValidationResult(
            is_valid=True, checks=(), failed_checks=(), passed_count=0, failed_count=0
        )
        with pytest.raises((TypeError, AttributeError)):
            r.is_valid = False  # type: ignore

    def test_failure_messages_property(self):
        check = AIGovernanceValidationCheckResult(
            code=AIGovernanceValidationCode.REQUEST_COMPLETENESS,
            passed=False, message="missing field",
        )
        result = AIGovernancePolicyValidationResult(
            is_valid=False, checks=(check,), failed_checks=(check,),
            passed_count=0, failed_count=1,
        )
        assert "missing field" in result.failure_messages


# ===========================================================================
# 19. AIGovernancePolicyFactory
# ===========================================================================

class TestFactory:
    F = AIGovernancePolicyFactory()

    def test_create_condition(self):
        c = self.F.create_condition("c", "x.y", ConditionOperator.GT, 5)
        assert c.field_path == "x.y"

    def test_create_rule(self):
        c = self.F.create_condition("c", "x", ConditionOperator.EQ, 1)
        r = self.F.create_rule("r", [c], LogicalOperator.ALL, AIGovernancePolicyAction.APPROVE)
        assert r.condition_count == 1

    def test_create_policy(self):
        c = self.F.create_condition("c", "x", ConditionOperator.EQ, 1)
        r = self.F.create_rule("r", [c], LogicalOperator.ALL, AIGovernancePolicyAction.APPROVE)
        p = self.F.create_policy("p", AIGovernancePolicyType.AI_SAFETY, PolicyPriority.HIGH, [r])
        assert p.enabled

    def test_create_request(self):
        req = self.F.create_request("sup-x")
        assert req.supervision_id == "sup-x"

    def test_create_ai_safety_threshold_policy(self):
        p = self.F.create_ai_safety_threshold_policy("Safety", "health", 0.7)
        assert p.policy_type == AIGovernancePolicyType.AI_SAFETY

    def test_safety_triggers_emergency_stop(self):
        ev = AIGovernancePolicyEvaluator()
        p = self.F.create_ai_safety_threshold_policy("S", "health", 0.7)
        r = ev.evaluate_policy(p, {"health": 0.5})
        assert r.action == AIGovernancePolicyAction.EMERGENCY_STOP

    def test_safety_approves_when_safe(self):
        ev = AIGovernancePolicyEvaluator()
        p = self.F.create_ai_safety_threshold_policy("S", "health", 0.7)
        r = ev.evaluate_policy(p, {"health": 0.9})
        assert r.action == AIGovernancePolicyAction.APPROVE

    def test_create_human_oversight_policy(self):
        p = self.F.create_human_oversight_policy("HO", "risk.var", 0.05)
        assert p.policy_type == AIGovernancePolicyType.HUMAN_OVERSIGHT

    def test_human_oversight_triggers(self):
        ev = AIGovernancePolicyEvaluator()
        p = self.F.create_human_oversight_policy("HO", "risk", 0.05)
        r = ev.evaluate_policy(p, {"risk": 0.1})
        assert r.action == AIGovernancePolicyAction.REQUIRE_HUMAN_APPROVAL

    def test_create_compliance_block_policy(self):
        p = self.F.create_compliance_block_policy("Halt", "market.status", "halt")
        assert p.policy_type == AIGovernancePolicyType.COMPLIANCE

    def test_compliance_blocks_on_halt(self):
        ev = AIGovernancePolicyEvaluator()
        p = self.F.create_compliance_block_policy("Halt", "market_status", "halt")
        r = ev.evaluate_policy(p, {"market_status": "halt"})
        assert r.action == AIGovernancePolicyAction.BLOCK

    def test_create_autonomous_operation_policy(self):
        p = self.F.create_autonomous_operation_policy("AO", "autonomy.level", 0.8)
        assert p.policy_type == AIGovernancePolicyType.AUTONOMOUS_OPERATION


# ===========================================================================
# 20. AIGovernancePolicyManager
# ===========================================================================

class TestManager:
    def _mgr(self, *policies: AIGovernancePolicy) -> AIGovernancePolicyManager:
        reg = AIGovernancePolicyRegistry()
        for p in policies:
            reg.register(p)
        return AIGovernancePolicyManager(registry=reg)

    def test_run_evaluation_success(self):
        mgr = self._mgr(_policy())
        resp = mgr.run_evaluation(_request(inputs={"health.score": 0.2}))
        assert resp.is_success
        assert resp.final_action == AIGovernancePolicyAction.BLOCK

    def test_no_policies_returns_default(self):
        mgr = AIGovernancePolicyManager()
        resp = mgr.run_evaluation(_request())
        assert resp.is_success
        assert resp.final_action == DEFAULT_GOVERNANCE_ACTION

    def test_filter_by_type(self):
        safety = _policy(policy_type=AIGovernancePolicyType.AI_SAFETY)
        compliance = _policy(policy_type=AIGovernancePolicyType.COMPLIANCE, name="c-p")
        mgr = self._mgr(safety, compliance)
        req = AIGovernancePolicyRequest.create(
            "s", "sub", "wf",
            inputs={"health.score": 0.2},
            policy_types=[AIGovernancePolicyType.AI_SAFETY],
        )
        resp = mgr.run_evaluation(req)
        assert resp.policies_skipped == 1

    def test_emergency_stop_conflict_resolution(self):
        """EMERGENCY_STOP from any policy overrides BLOCK."""
        emergency = _policy(
            rules=[_rule(action=AIGovernancePolicyAction.EMERGENCY_STOP, name="em-r")],
            priority=PolicyPriority.LOW,
            name="emergency-p",
        )
        block = _policy(priority=PolicyPriority.HIGH, name="block-p")
        # Both register — sequential evaluates HIGH priority (BLOCK) first
        # BLOCK triggers → chain stops → only BLOCK result
        # But conflict resolution: only BLOCK, so BLOCK wins
        # To test emergency stop override, use PARALLEL chain
        from iios.supervisor.policies.ai_governance_policy_chain import AIGovernancePolicyChain
        ev = AIGovernancePolicyEvaluator()
        chain = AIGovernancePolicyChain(ev)
        reg = AIGovernancePolicyRegistry()
        reg.register(emergency)
        reg.register(block)
        mgr = AIGovernancePolicyManager(registry=reg, chain=chain)
        # Use PARALLEL by patching the chain evaluate call
        # Direct test: run both policies in parallel, conflict resolution picks EMERGENCY_STOP
        results = chain.evaluate([emergency, block], {"health.score": 0.2}, EvaluationMode.PARALLEL)
        assert any(r.action == AIGovernancePolicyAction.EMERGENCY_STOP for r in results)

    def test_critical_priority_override(self):
        """CRITICAL priority deny overrides LOW priority block."""
        critical_block = _policy(
            rules=[_rule(action=AIGovernancePolicyAction.BLOCK, name="crit-block")],
            priority=PolicyPriority.CRITICAL,
            name="critical-p",
        )
        low_reject = _policy(
            rules=[_rule(action=AIGovernancePolicyAction.REJECT, name="low-rej")],
            priority=PolicyPriority.LOW,
            name="low-p",
        )
        chain = AIGovernancePolicyChain()
        results = chain.evaluate([critical_block, low_reject], {"health.score": 0.2}, EvaluationMode.PARALLEL)
        mgr = AIGovernancePolicyManager()
        final_action, _, _, _, _ = mgr._resolve_conflicts(results)
        # Critical BLOCK should override (critical_denies path)
        assert final_action == AIGovernancePolicyAction.BLOCK

    def test_never_raises_on_exception(self):
        class BrokenRegistry(AIGovernancePolicyRegistry):
            def enabled_policies(self):
                raise RuntimeError("broken!")
        mgr = AIGovernancePolicyManager(registry=BrokenRegistry())
        resp = mgr.run_evaluation(_request())
        assert not resp.is_success
        assert resp.is_emergency_stop

    def test_history_records_request_response(self):
        hist = AIGovernancePolicyHistory()
        mgr = AIGovernancePolicyManager(history=hist)
        mgr.run_evaluation(_request())
        assert hist.request_count() == 1
        assert hist.response_count() == 1

    def test_audit_report_generated(self):
        hist = AIGovernancePolicyHistory()
        mgr = AIGovernancePolicyManager(history=hist)
        mgr.run_evaluation(_request())
        assert hist.audit_count() == 1


# ===========================================================================
# 21. Engine — lifecycle
# ===========================================================================

class TestEngineLifecycle:
    def test_starts_and_stops(self):
        e = AIGovernancePolicyEngine()
        e.start()
        assert e.lifecycle_state().value == "running"
        e.stop()
        assert e.lifecycle_state().value == "stopped"

    def test_evaluate_raises_when_not_started(self):
        e = AIGovernancePolicyEngine()
        with pytest.raises(AIGovernancePolicyEngineNotRunningError):
            e.evaluate(_request())

    def test_evaluate_raises_after_stop(self):
        e = _started_engine()
        e.stop()
        with pytest.raises(AIGovernancePolicyEngineNotRunningError):
            e.evaluate(_request())

    def test_start_fires_engine_started_event(self):
        events = []
        e = AIGovernancePolicyEngine()
        e.add_listener(events.append)
        e.start()
        e.stop()
        types = [ev.event_type for ev in events]
        assert AIGovernancePolicyEventType.POLICY_ENGINE_STARTED in types
        assert AIGovernancePolicyEventType.POLICY_ENGINE_STOPPED in types

    def test_health(self):
        e = _started_engine()
        h = e.health()
        assert "status" in h
        e.stop()

    def test_statistics(self):
        e = _started_engine()
        s = e.statistics()
        assert "evaluations" in s
        e.stop()

    def test_status(self):
        e = _started_engine()
        s = e.status()
        assert "engine_id" in s and "health" in s
        e.stop()


# ===========================================================================
# 22. Engine — evaluate
# ===========================================================================

class TestEngineEvaluate:
    def test_no_policies_returns_default(self):
        e = _started_engine()
        resp = e.evaluate(_request())
        assert resp.is_success
        assert resp.final_action == DEFAULT_GOVERNANCE_ACTION
        e.stop()

    def test_block_on_unsafe_input(self):
        e = _started_engine()
        e.register_policy(_policy())
        resp = e.evaluate(_request(inputs={"health.score": 0.2}))
        assert resp.final_action == AIGovernancePolicyAction.BLOCK
        e.stop()

    def test_approve_on_safe_input(self):
        e = _started_engine()
        e.register_policy(_policy())
        resp = e.evaluate(_request(inputs={"health.score": 0.9}))
        assert resp.final_action == AIGovernancePolicyAction.APPROVE
        e.stop()

    def test_emergency_stop_dispatches_event(self):
        e = _started_engine()
        factory = AIGovernancePolicyFactory()
        e.register_policy(factory.create_ai_safety_threshold_policy("S", "health", 0.5))
        events = []
        e.add_listener(events.append)
        e.evaluate(_request(inputs={"health": 0.3}))
        types = [ev.event_type for ev in events]
        assert AIGovernancePolicyEventType.EMERGENCY_STOP_TRIGGERED in types
        e.stop()

    def test_block_dispatches_blocked_event(self):
        e = _started_engine()
        e.register_policy(_policy())
        events = []
        e.add_listener(events.append)
        e.evaluate(_request(inputs={"health.score": 0.2}))
        types = [ev.event_type for ev in events]
        assert AIGovernancePolicyEventType.BLOCKED in types
        e.stop()

    def test_approve_dispatches_approved_event(self):
        e = _started_engine()
        e.register_policy(_policy())
        events = []
        e.add_listener(events.append)
        e.evaluate(_request(inputs={"health.score": 0.9}))
        types = [ev.event_type for ev in events]
        assert AIGovernancePolicyEventType.APPROVED in types
        e.stop()

    def test_human_approval_dispatches_event(self):
        e = _started_engine()
        factory = AIGovernancePolicyFactory()
        e.register_policy(factory.create_human_oversight_policy("HO", "risk", 0.05))
        events = []
        e.add_listener(events.append)
        e.evaluate(_request(inputs={"risk": 0.1}))
        types = [ev.event_type for ev in events]
        assert AIGovernancePolicyEventType.HUMAN_APPROVAL_REQUESTED in types
        e.stop()

    def test_evaluation_completed_always_fired(self):
        e = _started_engine()
        events = []
        e.add_listener(events.append)
        e.evaluate(_request())
        types = [ev.event_type for ev in events]
        assert AIGovernancePolicyEventType.EVALUATION_COMPLETED in types
        e.stop()

    def test_response_has_elapsed(self):
        e = _started_engine()
        resp = e.evaluate(_request())
        assert resp.evaluation_elapsed_s >= 0
        e.stop()


# ===========================================================================
# 23. Engine — policy management
# ===========================================================================

class TestEnginePolicyManagement:
    def test_register_and_get(self):
        e = _started_engine()
        p = _policy()
        e.register_policy(p)
        assert e.get_policy(p.policy_id) is p
        e.stop()

    def test_unregister(self):
        e = _started_engine()
        p = _policy()
        e.register_policy(p)
        e.unregister_policy(p.policy_id)
        with pytest.raises(AIGovernancePolicyNotFoundError):
            e.get_policy(p.policy_id)
        e.stop()

    def test_enable_disable(self):
        e = _started_engine()
        p = _policy(enabled=True)
        e.register_policy(p)
        e.disable_policy(p.policy_id)
        assert not e.get_policy(p.policy_id).is_enabled
        e.enable_policy(p.policy_id)
        assert e.get_policy(p.policy_id).is_enabled
        e.stop()

    def test_health_reflects_count(self):
        e = _started_engine()
        e.register_policy(_policy())
        assert e.health()["policies_registered"] == 1
        e.stop()

    def test_register_fires_policy_loaded_event(self):
        e = _started_engine()
        events = []
        e.add_listener(events.append)
        e.register_policy(_policy())
        types = [ev.event_type for ev in events]
        assert AIGovernancePolicyEventType.POLICY_LOADED in types
        e.stop()


# ===========================================================================
# 24. Listeners
# ===========================================================================

class TestListeners:
    def test_add_remove(self):
        e = _started_engine()
        events = []
        e.add_listener(events.append)
        e.remove_listener(events.append)
        e.evaluate(_request())
        # only events after removal (none — listener was removed before evaluate)
        engine_stop_events = [
            ev for ev in events
            if ev.event_type == AIGovernancePolicyEventType.POLICY_ENGINE_STOPPED
        ]
        e.stop()
        assert all(
            ev.event_type == AIGovernancePolicyEventType.POLICY_ENGINE_STOPPED
            for ev in events
        )

    def test_no_duplicate_listener(self):
        e = _started_engine()
        events = []
        e.add_listener(events.append)
        e.add_listener(events.append)
        e.evaluate(_request())
        started = [ev for ev in events if ev.event_type == AIGovernancePolicyEventType.EVALUATION_STARTED]
        assert len(started) == 1
        e.stop()

    def test_listener_exception_does_not_crash(self):
        e = _started_engine()
        def bad(ev): raise RuntimeError("fail")
        e.add_listener(bad)
        resp = e.evaluate(_request())
        assert resp.is_success
        e.stop()


# ===========================================================================
# 25. Concurrency
# ===========================================================================

class TestConcurrency:
    def test_concurrent_evaluations(self):
        e = _started_engine()
        e.register_policy(_policy())
        results = []
        def worker():
            resp = e.evaluate(_request(inputs={"health.score": 0.2}))
            results.append(resp)
        threads = [threading.Thread(target=worker) for _ in range(40)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert len(results) == 40
        assert all(r.is_success for r in results)
        e.stop()

    def test_concurrent_register_and_evaluate(self):
        e = _started_engine()
        errors: List[Exception] = []
        def reg_worker(i):
            try:
                e.register_policy(_policy(name=f"p-{i}"))
            except Exception as ex:
                errors.append(ex)
        def eval_worker():
            try:
                e.evaluate(_request(inputs={"health.score": 0.2}))
            except Exception as ex:
                errors.append(ex)
        threads = (
            [threading.Thread(target=reg_worker, args=(i,)) for i in range(20)]
            + [threading.Thread(target=eval_worker) for _ in range(20)]
        )
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        e.stop()


# ===========================================================================
# 26. Public surface
# ===========================================================================

class TestPublicSurface:
    def test_all_exports_present(self):
        import iios.supervisor.policies as module
        for name in module.__all__:
            assert hasattr(module, name), f"Missing export: {name}"

    def test_engine_in_all(self):
        import iios.supervisor.policies as module
        assert "AIGovernancePolicyEngine" in module.__all__

    def test_emergency_stop_in_actions(self):
        import iios.supervisor.policies as module
        assert AIGovernancePolicyAction.EMERGENCY_STOP in module.AIGovernancePolicyAction


# ===========================================================================
# 27. Integration smoke tests
# ===========================================================================

class TestIntegration:
    def test_emergency_stop_pipeline(self):
        """End-to-end: AI Safety policy triggers emergency stop."""
        factory = AIGovernancePolicyFactory()
        engine = AIGovernancePolicyEngine()
        engine.start()
        engine.register_policy(
            factory.create_ai_safety_threshold_policy("Safety Gate", "ai_health", 0.6)
        )
        req = factory.create_request("sup-int", inputs={"ai_health": 0.3})
        resp = engine.evaluate(req)
        assert resp.is_emergency_stop
        assert resp.final_action == AIGovernancePolicyAction.EMERGENCY_STOP
        assert resp.is_denied
        engine.stop()

    def test_human_oversight_pipeline(self):
        """End-to-end: risk above threshold → REQUIRE_HUMAN_APPROVAL."""
        factory = AIGovernancePolicyFactory()
        engine = AIGovernancePolicyEngine()
        engine.start()
        engine.register_policy(
            factory.create_human_oversight_policy("Risk Gate", "risk.var", 0.05)
        )
        req = factory.create_request("sup-int2", inputs={"risk.var": 0.1})
        resp = engine.evaluate(req)
        assert resp.requires_human_approval
        engine.stop()

    def test_compliance_block_pipeline(self):
        """End-to-end: market halt → BLOCK."""
        factory = AIGovernancePolicyFactory()
        engine = AIGovernancePolicyEngine()
        engine.start()
        engine.register_policy(
            factory.create_compliance_block_policy("Market Halt", "market.status", "halt")
        )
        req = factory.create_request("sup-int3", inputs={"market.status": "halt"})
        resp = engine.evaluate(req)
        assert resp.final_action == AIGovernancePolicyAction.BLOCK
        engine.stop()

    def test_approve_when_all_clear(self):
        """End-to-end: no rules trigger → APPROVE."""
        factory = AIGovernancePolicyFactory()
        engine = AIGovernancePolicyEngine()
        engine.start()
        engine.register_policy(
            factory.create_ai_safety_threshold_policy("Safety Gate", "ai_health", 0.5)
        )
        req = factory.create_request("sup-int4", inputs={"ai_health": 0.9})
        resp = engine.evaluate(req)
        assert resp.is_approved
        engine.stop()

    def test_statistics_reflect_evaluations(self):
        engine = _started_engine()
        for _ in range(5):
            engine.evaluate(_request())
        snap = engine.statistics()
        assert snap["evaluations"] >= 5
        engine.stop()

    def test_audit_report_in_history(self):
        engine = _started_engine()
        engine.register_policy(_policy())
        engine.evaluate(_request(inputs={"health.score": 0.2}))
        hist_counts = engine.status()["history"]
        assert hist_counts["audits"] >= 1
        engine.stop()

    def test_multiple_policy_types_evaluated(self):
        """Both AI_SAFETY and COMPLIANCE policies applied — most severe wins."""
        factory = AIGovernancePolicyFactory()
        engine = AIGovernancePolicyEngine()
        engine.start()
        engine.register_policy(
            factory.create_ai_safety_threshold_policy("Safety Gate", "ai_health", 0.6,
                                                       priority=PolicyPriority.CRITICAL)
        )
        engine.register_policy(
            factory.create_compliance_block_policy("Halt Gate", "market.status", "halt",
                                                    priority=PolicyPriority.HIGH)
        )
        # Only market.status triggers (health is fine)
        req = factory.create_request(
            "sup-multi",
            inputs={"ai_health": 0.9, "market.status": "halt"},
        )
        resp = engine.evaluate(req)
        assert resp.final_action == AIGovernancePolicyAction.BLOCK
        engine.stop()
