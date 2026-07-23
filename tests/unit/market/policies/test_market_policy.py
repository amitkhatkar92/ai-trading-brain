"""
tests/unit/market/policies/test_market_policy.py
==================================================
Unit tests for C12 M3 — Market Policy Framework.
Target: 95%+ coverage across all 22 source files.

Test classes
------------
TestConstants                 — enumerations and defaults
TestExceptions                — exception hierarchy
TestMarketPolicyCondition     — condition value object
TestMarketPolicyRule          — rule value object
TestMarketPolicy              — policy value object
TestMarketPolicyResult        — result value object
TestMarketPolicyContext       — context value object
TestMarketPolicyRequest       — request value object
TestMarketEvaluationSummary   — response summary
TestMarketPolicyResponse      — response value object
TestMarketPolicyAuditReport   — audit value object
TestMarketPolicyAuditor       — audit report builder
TestMarketPolicyStatistics    — statistics collector
TestMarketPolicyHistory       — history ring-buffer
TestMarketPolicyEvents        — event factory functions
TestMarketPolicyEvaluator     — condition/rule/policy evaluator
TestMarketPolicyValidator     — policy and request validation
TestMarketPolicyPriority      — conflict resolution
TestMarketPolicyChain         — multi-policy chain evaluation
TestMarketPolicyRegistry      — thread-safe registry
TestMarketPolicyFactory       — object factory
TestMarketPolicyManager       — evaluation pipeline
TestMarketPolicyEngine        — primary public interface
TestConcurrency               — thread-safety
TestRegression                — end-to-end scenarios
"""
from __future__ import annotations

import threading
import time
from typing import List

import pytest

from iios.market.policies import (
    ACTION_SEVERITY,
    DEFAULT_POLICY_ACTION,
    DENY_ACTIONS,
    PERMISSIVE_ACTIONS,
    POLICY_SYSTEM_ID,
    VERSION,
    ConditionOperator,
    EvaluationMode,
    LogicalOperator,
    MarketEvaluationSummary,
    MarketPolicy,
    MarketPolicyAuditError,
    MarketPolicyAuditReport,
    MarketPolicyAuditor,
    MarketPolicyCapacityError,
    MarketPolicyChain,
    MarketPolicyCondition,
    MarketPolicyConfigurationError,
    MarketPolicyConflictError,
    MarketPolicyContext,
    MarketPolicyEngine,
    MarketPolicyEngineNotRunningError,
    MarketPolicyEngineStatus,
    MarketPolicyError,
    MarketPolicyEvaluationError,
    MarketPolicyEvaluator,
    MarketPolicyEvent,
    MarketPolicyFactory,
    MarketPolicyHistory,
    MarketPolicyManager,
    MarketPolicyNotFoundError,
    MarketPolicyPriorityResolver,
    MarketPolicyRegistry,
    MarketPolicyRegistryError,
    MarketPolicyRequest,
    MarketPolicyResponse,
    MarketPolicyResult,
    MarketPolicyRule,
    MarketPolicyStatistics,
    MarketPolicyType,
    MarketPolicyValidationCheckResult,
    MarketPolicyValidationError,
    MarketPolicyValidationResult,
    MarketPolicyValidator,
    PolicyAction,
    PolicyEventType,
    PolicyPriority,
    ValidationCode,
    make_market_policy_approved,
    make_market_policy_blocked,
    make_market_policy_escalated,
    make_market_policy_evaluation_completed,
    make_market_policy_evaluation_started,
    make_market_policy_loaded,
    make_market_policy_rejected,
    make_market_policy_validated,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _cond(field_path: str, op: ConditionOperator, threshold=None) -> MarketPolicyCondition:
    return MarketPolicyCondition.create(
        name=f"c_{field_path}", field_path=field_path, operator=op, threshold=threshold
    )


def _rule(
    conditions,
    action: PolicyAction = PolicyAction.REJECT,
    op: LogicalOperator = LogicalOperator.ALL,
) -> MarketPolicyRule:
    return MarketPolicyRule.create(
        name="test_rule",
        conditions=tuple(conditions),
        logical_operator=op,
        action=action,
    )


def _policy(
    policy_type: MarketPolicyType = MarketPolicyType.MARKET_HOURS_POLICY,
    priority: PolicyPriority = PolicyPriority.MEDIUM,
    rules=None,
    default_action: PolicyAction = PolicyAction.APPROVE,
    evaluation_mode: EvaluationMode = EvaluationMode.SEQUENTIAL,
) -> MarketPolicy:
    return MarketPolicy.create(
        name="Test Policy",
        policy_type=policy_type,
        priority=priority,
        rules=rules or [],
        default_action=default_action,
        evaluation_mode=evaluation_mode,
    )


def _request(
    exchange: str = "NSE",
    inputs: dict | None = None,
    metadata: dict | None = None,
) -> MarketPolicyRequest:
    return MarketPolicyRequest.create(
        evaluation_id="EVAL-001",
        market_analysis_id="MKT-001",
        exchange=exchange,
        inputs=inputs or {},
        metadata=metadata or {},
    )


def _started_engine(**kwargs) -> MarketPolicyEngine:
    e = MarketPolicyEngine(**kwargs)
    e.start()
    return e


# ===========================================================================
# TestConstants
# ===========================================================================

class TestConstants:
    def test_policy_system_id(self):
        assert POLICY_SYSTEM_ID == "iios:market:policies"

    def test_version(self):
        assert VERSION == "1.0.0"

    def test_default_policy_action(self):
        assert DEFAULT_POLICY_ACTION == PolicyAction.APPROVE

    def test_deny_actions(self):
        assert PolicyAction.REJECT in DENY_ACTIONS
        assert PolicyAction.BLOCK in DENY_ACTIONS
        assert PolicyAction.APPROVE not in DENY_ACTIONS

    def test_permissive_actions(self):
        assert PolicyAction.APPROVE in PERMISSIVE_ACTIONS
        assert PolicyAction.APPROVE_WITH_CONDITIONS in PERMISSIVE_ACTIONS
        assert PolicyAction.REJECT not in PERMISSIVE_ACTIONS

    def test_action_severity_ordering(self):
        assert ACTION_SEVERITY[PolicyAction.APPROVE] < ACTION_SEVERITY[PolicyAction.REJECT]
        assert ACTION_SEVERITY[PolicyAction.REJECT] < ACTION_SEVERITY[PolicyAction.BLOCK]

    def test_all_policy_types(self):
        expected = {
            "market_data_policy", "exchange_access_policy", "trading_session_policy",
            "market_hours_policy", "economic_event_policy", "corporate_action_policy",
            "data_freshness_policy", "market_regime_policy", "volatility_policy",
            "sector_coverage_policy", "index_coverage_policy", "breadth_coverage_policy",
            "market_health_policy", "regulatory_policy", "enterprise_governance_policy",
        }
        assert {t.value for t in MarketPolicyType} == expected

    def test_all_policy_actions(self):
        assert len(list(PolicyAction)) == 7

    def test_priority_ordering(self):
        assert PolicyPriority.CRITICAL < PolicyPriority.HIGH < PolicyPriority.MEDIUM
        assert PolicyPriority.MEDIUM < PolicyPriority.LOW < PolicyPriority.INFORMATIONAL

    def test_evaluation_modes(self):
        modes = {e.value for e in EvaluationMode}
        assert "sequential" in modes
        assert "parallel" in modes
        assert "weighted" in modes

    def test_validation_codes(self):
        assert len(list(ValidationCode)) == 8

    def test_policy_event_types(self):
        assert len(list(PolicyEventType)) == 8


# ===========================================================================
# TestExceptions
# ===========================================================================

class TestExceptions:
    def test_base_exception(self):
        exc = MarketPolicyError("test")
        assert exc.error_code == "MP-000"
        assert "test" in str(exc)

    def test_not_running(self):
        exc = MarketPolicyEngineNotRunningError()
        assert exc.error_code == "MP-001"
        assert "not running" in str(exc).lower()

    def test_not_found(self):
        exc = MarketPolicyNotFoundError("POL-001")
        assert exc.error_code == "MP-002"
        assert exc.policy_id == "POL-001"
        assert "POL-001" in str(exc)

    def test_validation_error(self):
        exc = MarketPolicyValidationError("bad config", policy_id="P1")
        assert exc.error_code == "MP-003"
        assert exc.policy_id == "P1"

    def test_evaluation_error(self):
        exc = MarketPolicyEvaluationError("failed", policy_id="P2")
        assert exc.error_code == "MP-004"
        assert exc.policy_id == "P2"

    def test_conflict_error(self):
        exc = MarketPolicyConflictError("irresolvable")
        assert exc.error_code == "MP-005"

    def test_registry_error(self):
        exc = MarketPolicyRegistryError("registry problem")
        assert exc.error_code == "MP-006"

    def test_configuration_error(self):
        exc = MarketPolicyConfigurationError("bad config")
        assert exc.error_code == "MP-007"

    def test_audit_error(self):
        exc = MarketPolicyAuditError("audit fail")
        assert exc.error_code == "MP-008"

    def test_capacity_error(self):
        exc = MarketPolicyCapacityError(500)
        assert exc.error_code == "MP-009"
        assert exc.limit == 500

    def test_hierarchy(self):
        assert issubclass(MarketPolicyEngineNotRunningError, MarketPolicyError)
        assert issubclass(MarketPolicyValidationError, MarketPolicyError)
        assert issubclass(MarketPolicyCapacityError, MarketPolicyError)


# ===========================================================================
# TestMarketPolicyCondition
# ===========================================================================

class TestMarketPolicyCondition:
    def test_create(self):
        c = MarketPolicyCondition.create(
            "test", "exchange_open", ConditionOperator.IS_TRUE
        )
        assert c.name == "test"
        assert c.field_path == "exchange_open"
        assert c.operator == ConditionOperator.IS_TRUE
        assert c.condition_id

    def test_with_threshold(self):
        c = MarketPolicyCondition.create("vix", "vix_level", ConditionOperator.GT, threshold=30.0)
        assert c.threshold == 30.0

    def test_custom_condition_id(self):
        c = MarketPolicyCondition.create("c", "f", ConditionOperator.EQ, condition_id="COND-1")
        assert c.condition_id == "COND-1"

    def test_frozen(self):
        c = MarketPolicyCondition.create("c", "f", ConditionOperator.EQ)
        with pytest.raises((AttributeError, TypeError)):
            c.name = "changed"

    def test_to_dict(self):
        c = MarketPolicyCondition.create("c", "f", ConditionOperator.GTE, threshold=5)
        d = c.to_dict()
        assert d["field_path"] == "f"
        assert d["operator"] == "gte"
        assert d["threshold"] == 5


# ===========================================================================
# TestMarketPolicyRule
# ===========================================================================

class TestMarketPolicyRule:
    def test_create(self):
        cond = _cond("x", ConditionOperator.EXISTS)
        r = MarketPolicyRule.create(
            "test_rule", (cond,), LogicalOperator.ALL, PolicyAction.REJECT
        )
        assert r.name == "test_rule"
        assert r.action == PolicyAction.REJECT
        assert r.condition_count == 1

    def test_weight_default(self):
        r = _rule([_cond("x", ConditionOperator.EXISTS)])
        assert r.weight == 1.0

    def test_custom_weight(self):
        r = MarketPolicyRule.create(
            "w", (_cond("x", ConditionOperator.EXISTS),),
            LogicalOperator.ALL, PolicyAction.BLOCK, weight=2.5
        )
        assert r.weight == 2.5

    def test_frozen(self):
        r = _rule([_cond("x", ConditionOperator.EXISTS)])
        with pytest.raises((AttributeError, TypeError)):
            r.weight = 99.0

    def test_to_dict(self):
        r = _rule([_cond("x", ConditionOperator.EXISTS)])
        d = r.to_dict()
        assert d["action"] == "reject"
        assert len(d["conditions"]) == 1


# ===========================================================================
# TestMarketPolicy
# ===========================================================================

class TestMarketPolicy:
    def test_create(self):
        p = _policy()
        assert p.name == "Test Policy"
        assert p.policy_type == MarketPolicyType.MARKET_HOURS_POLICY
        assert p.enabled is True
        assert p.policy_id

    def test_rule_count(self):
        r = _rule([_cond("x", ConditionOperator.EXISTS)])
        p = _policy(rules=[r])
        assert p.rule_count == 1

    def test_with_enabled(self):
        p = _policy()
        p2 = p.with_enabled(False)
        assert p.enabled is True
        assert p2.enabled is False
        assert p2.policy_id == p.policy_id

    def test_frozen(self):
        p = _policy()
        with pytest.raises((AttributeError, TypeError)):
            p.enabled = False

    def test_to_dict(self):
        r = _rule([_cond("x", ConditionOperator.EXISTS)])
        p = _policy(rules=[r])
        d = p.to_dict()
        assert d["policy_type"] == "market_hours_policy"
        assert len(d["rules"]) == 1

    def test_all_policy_types(self):
        for pt in MarketPolicyType:
            p = MarketPolicy.create("p", pt, PolicyPriority.LOW, [])
            assert p.policy_type == pt

    def test_tags(self):
        p = MarketPolicy.create("p", MarketPolicyType.REGULATORY_POLICY,
                                 PolicyPriority.LOW, [], tags=["nse", "sebi"])
        assert "nse" in p.tags


# ===========================================================================
# TestMarketPolicyResult
# ===========================================================================

class TestMarketPolicyResult:
    def test_create(self):
        r = MarketPolicyResult.create(
            "POL-1", "Test", MarketPolicyType.EXCHANGE_ACCESS_POLICY,
            PolicyPriority.HIGH, PolicyAction.APPROVE
        )
        assert r.result_id
        assert r.action == PolicyAction.APPROVE
        assert r.is_permissive
        assert not r.is_denying

    def test_is_denying(self):
        r = MarketPolicyResult.create(
            "P", "T", MarketPolicyType.MARKET_HOURS_POLICY,
            PolicyPriority.HIGH, PolicyAction.REJECT
        )
        assert r.is_denying
        assert not r.is_permissive

    def test_block_is_denying(self):
        r = MarketPolicyResult.create(
            "P", "T", MarketPolicyType.VOLATILITY_POLICY,
            PolicyPriority.CRITICAL, PolicyAction.BLOCK
        )
        assert r.is_denying

    def test_conditions(self):
        r = MarketPolicyResult.create(
            "P", "T", MarketPolicyType.DATA_FRESHNESS_POLICY,
            PolicyPriority.LOW, PolicyAction.APPROVE,
            conditions_met=("C1", "C2"), conditions_failed=("C3",)
        )
        assert "C1" in r.conditions_met
        assert "C3" in r.conditions_failed

    def test_to_dict(self):
        r = MarketPolicyResult.create(
            "P", "T", MarketPolicyType.SECTOR_COVERAGE_POLICY,
            PolicyPriority.MEDIUM, PolicyAction.ESCALATE,
            rationale="test reason"
        )
        d = r.to_dict()
        assert d["action"] == "escalate"
        assert d["rationale"] == "test reason"


# ===========================================================================
# TestMarketPolicyContext
# ===========================================================================

class TestMarketPolicyContext:
    def test_create(self):
        ctx = MarketPolicyContext.create("EVAL-001", "MKT-001", "NSE")
        assert ctx.evaluation_id == "EVAL-001"
        assert ctx.market_analysis_id == "MKT-001"
        assert ctx.exchange == "NSE"
        assert ctx.context_id

    def test_policy_types_filter(self):
        ctx = MarketPolicyContext.create(
            "E", "M", "BSE",
            policy_types=(
                MarketPolicyType.MARKET_HOURS_POLICY,
                MarketPolicyType.VOLATILITY_POLICY,
            )
        )
        assert len(ctx.policy_types) == 2

    def test_frozen(self):
        ctx = MarketPolicyContext.create("E", "M", "NSE")
        with pytest.raises((AttributeError, TypeError)):
            ctx.exchange = "BSE"

    def test_to_dict(self):
        ctx = MarketPolicyContext.create("E", "M", "NSE")
        d = ctx.to_dict()
        assert d["exchange"] == "NSE"
        assert d["market_analysis_id"] == "M"


# ===========================================================================
# TestMarketPolicyRequest
# ===========================================================================

class TestMarketPolicyRequest:
    def test_create(self):
        req = MarketPolicyRequest.create("EVAL-1", "MKT-1", "NSE")
        assert req.evaluation_id == "EVAL-1"
        assert req.market_analysis_id == "MKT-1"
        assert req.exchange == "NSE"
        assert req.request_id
        assert req.context is not None

    def test_with_inputs(self):
        req = MarketPolicyRequest.create("E", "M", "NSE", inputs={"vix": 20})
        req2 = req.with_inputs({"vix": 25, "breadth": 0.6})
        assert req2.inputs["vix"] == 25
        assert req2.inputs["breadth"] == 0.6
        # original unchanged
        assert req.inputs["vix"] == 20

    def test_custom_context(self):
        ctx = MarketPolicyContext.create("E", "M", "NSE", source="analytics")
        req = MarketPolicyRequest.create("E", "M", "NSE", context=ctx)
        assert req.context.source == "analytics"

    def test_frozen(self):
        req = MarketPolicyRequest.create("E", "M", "NSE")
        with pytest.raises((AttributeError, TypeError)):
            req.exchange = "BSE"

    def test_to_dict(self):
        req = MarketPolicyRequest.create("E", "M", "NSE", inputs={"k": "v"})
        d = req.to_dict()
        assert d["exchange"] == "NSE"
        assert "k" in d["input_keys"]


# ===========================================================================
# TestMarketEvaluationSummary
# ===========================================================================

class TestMarketEvaluationSummary:
    def test_from_results_empty(self):
        s = MarketEvaluationSummary.from_results((), PolicyAction.APPROVE)
        assert s.total_policies == 0
        assert s.final_action == PolicyAction.APPROVE

    def test_from_results_counts(self):
        results = (
            MarketPolicyResult.create(
                "P1", "n", MarketPolicyType.MARKET_HOURS_POLICY,
                PolicyPriority.HIGH, PolicyAction.APPROVE
            ),
            MarketPolicyResult.create(
                "P2", "n", MarketPolicyType.VOLATILITY_POLICY,
                PolicyPriority.CRITICAL, PolicyAction.REJECT
            ),
        )
        s = MarketEvaluationSummary.from_results(results, PolicyAction.REJECT)
        assert s.total_policies == 2
        assert s.approved == 1
        assert s.rejected == 1

    def test_to_dict(self):
        s = MarketEvaluationSummary.from_results((), PolicyAction.APPROVE)
        d = s.to_dict()
        assert d["final_action"] == "approve"
        assert "summary_id" in d


# ===========================================================================
# TestMarketPolicyResponse
# ===========================================================================

class TestMarketPolicyResponse:
    def _make_summary(self):
        return MarketEvaluationSummary.from_results((), PolicyAction.APPROVE)

    def test_create_success(self):
        s = self._make_summary()
        r = MarketPolicyResponse.create_success(
            "REQ-1", "EVAL-1", "MKT-1", "NSE",
            PolicyAction.APPROVE, (), s, 0.01
        )
        assert r.is_success
        assert r.is_approved
        assert not r.is_denied
        assert r.response_id

    def test_create_failure(self):
        r = MarketPolicyResponse.create_failure(
            "REQ-1", "EVAL-1", "MKT-1", "NSE", "error msg", 0.01
        )
        assert not r.is_success
        assert r.error_message == "error msg"

    def test_is_denied(self):
        s = self._make_summary()
        r = MarketPolicyResponse.create_success(
            "REQ-1", "EVAL-1", "MKT-1", "NSE",
            PolicyAction.REJECT, (), s, 0.01
        )
        assert r.is_denied

    def test_requires_escalation(self):
        s = self._make_summary()
        r = MarketPolicyResponse.create_success(
            "REQ-1", "EVAL-1", "MKT-1", "NSE",
            PolicyAction.ESCALATE, (), s, 0.01
        )
        assert r.requires_escalation

    def test_to_dict(self):
        s = self._make_summary()
        r = MarketPolicyResponse.create_success(
            "REQ-1", "EVAL-1", "MKT-1", "NSE",
            PolicyAction.APPROVE, (), s, 0.01
        )
        d = r.to_dict()
        assert d["final_action"] == "approve"
        assert d["exchange"] == "NSE"


# ===========================================================================
# TestMarketPolicyAuditReport
# ===========================================================================

class TestMarketPolicyAuditReport:
    def test_to_dict(self):
        r = MarketPolicyAuditReport(
            audit_id="A1",
            request_id="R1",
            evaluation_id="E1",
            market_analysis_id="M1",
            exchange="NSE",
            policies_loaded=2,
            policies_evaluated=2,
            evaluation_details=(),
            conflict_resolution_applied=False,
            conflict_strategy_used="",
            final_action=PolicyAction.APPROVE,
            final_rationale="ok",
            elapsed_s=0.05,
        )
        d = r.to_dict()
        assert d["audit_id"] == "A1"
        assert d["exchange"] == "NSE"
        assert d["final_action"] == "approve"


# ===========================================================================
# TestMarketPolicyAuditor
# ===========================================================================

class TestMarketPolicyAuditor:
    def test_create_report(self):
        req = _request()
        auditor = MarketPolicyAuditor()
        report = auditor.create_report(req, [], PolicyAction.APPROVE, 0, 0.01)
        assert report.request_id == req.request_id
        assert report.exchange == "NSE"
        assert report.policies_evaluated == 0
        assert report.final_action == PolicyAction.APPROVE

    def test_create_report_with_results(self):
        req = _request()
        result = MarketPolicyResult.create(
            "P1", "Pol", MarketPolicyType.MARKET_HOURS_POLICY,
            PolicyPriority.HIGH, PolicyAction.REJECT
        )
        auditor = MarketPolicyAuditor()
        report = auditor.create_report(
            req, [result], PolicyAction.REJECT, 1, 0.02,
            conflict_resolution_applied=True,
            conflict_strategy_used="explicit_deny",
            final_rationale="rejected"
        )
        assert report.policies_evaluated == 1
        assert len(report.evaluation_details) == 1
        assert report.conflict_resolution_applied is True

    def test_custom_audit_id(self):
        req = _request()
        auditor = MarketPolicyAuditor()
        report = auditor.create_report(req, [], PolicyAction.APPROVE, 0, 0.01,
                                        audit_id="AUDIT-CUSTOM")
        assert report.audit_id == "AUDIT-CUSTOM"


# ===========================================================================
# TestMarketPolicyStatistics
# ===========================================================================

class TestMarketPolicyStatistics:
    def test_initial_zero(self):
        s = MarketPolicyStatistics()
        snap = s.snapshot()
        assert snap["evaluations_total"] == 0
        assert snap["approved"] == 0

    def test_record_evaluation(self):
        s = MarketPolicyStatistics()
        s.record_evaluation()
        s.record_evaluation()
        assert s.snapshot()["evaluations_total"] == 2

    def test_record_all_actions(self):
        s = MarketPolicyStatistics()
        s.record_approved()
        s.record_conditionally_approved()
        s.record_rejected()
        s.record_blocked()
        s.record_escalated()
        s.record_deferred()
        s.record_manual_review()
        snap = s.snapshot()
        assert snap["approved"] == 1
        assert snap["conditionally_approved"] == 1
        assert snap["rejected"] == 1
        assert snap["blocked"] == 1
        assert snap["escalated"] == 1
        assert snap["deferred"] == 1
        assert snap["manual_review_required"] == 1

    def test_average_evaluation_time(self):
        s = MarketPolicyStatistics()
        s.record_evaluation_time(0.10)
        s.record_evaluation_time(0.20)
        snap = s.snapshot()
        assert abs(snap["average_evaluation_time_s"] - 0.15) < 0.001

    def test_policy_coverage(self):
        s = MarketPolicyStatistics()
        s.record_evaluation()
        s.record_policies_evaluated(5)
        snap = s.snapshot()
        assert snap["policy_coverage"] == 5.0

    def test_throughput_positive(self):
        s = MarketPolicyStatistics()
        s.record_evaluation()
        time.sleep(0.01)
        snap = s.snapshot()
        assert snap["evaluation_throughput_per_s"] > 0

    def test_reset(self):
        s = MarketPolicyStatistics()
        s.record_approved()
        s.reset()
        assert s.snapshot()["approved"] == 0


# ===========================================================================
# TestMarketPolicyHistory
# ===========================================================================

class TestMarketPolicyHistory:
    def test_record_and_retrieve(self):
        h = MarketPolicyHistory()
        h.record_event("ev1")
        h.record_request("req1")
        h.record_response("resp1")
        h.record_audit("audit1")
        assert h.counts() == {"events": 1, "requests": 1, "responses": 1, "audits": 1}

    def test_bounded(self):
        h = MarketPolicyHistory(max_events=3)
        for i in range(10):
            h.record_event(i)
        assert len(h.recent_events(100)) == 3

    def test_recent_n(self):
        h = MarketPolicyHistory()
        for i in range(20):
            h.record_request(i)
        recent = h.recent_requests(5)
        assert len(recent) == 5
        assert recent[-1] == 19

    def test_clear(self):
        h = MarketPolicyHistory()
        h.record_event("x")
        h.clear()
        assert h.counts()["events"] == 0


# ===========================================================================
# TestMarketPolicyEvents
# ===========================================================================

class TestMarketPolicyEvents:
    def test_evaluation_started(self):
        ev = make_market_policy_evaluation_started("E1", "R1", market_analysis_id="M1", exchange="NSE")
        assert ev.event_type == PolicyEventType.EVALUATION_STARTED
        assert ev.evaluation_id == "E1"
        assert ev.exchange == "NSE"
        assert ev.event_id

    def test_policy_loaded(self):
        ev = make_market_policy_loaded("E1", "R1", "P1")
        assert ev.event_type == PolicyEventType.POLICY_LOADED
        assert ev.policy_id == "P1"

    def test_policy_validated(self):
        ev = make_market_policy_validated("E1", "R1", "P1")
        assert ev.event_type == PolicyEventType.POLICY_VALIDATED

    def test_policy_approved(self):
        ev = make_market_policy_approved("E1", "R1", "P1", PolicyAction.APPROVE)
        assert ev.event_type == PolicyEventType.POLICY_APPROVED
        assert ev.final_action == PolicyAction.APPROVE

    def test_policy_rejected(self):
        ev = make_market_policy_rejected("E1", "R1", "P1")
        assert ev.event_type == PolicyEventType.POLICY_REJECTED
        assert ev.final_action == PolicyAction.REJECT

    def test_policy_blocked(self):
        ev = make_market_policy_blocked("E1", "R1", "P1")
        assert ev.event_type == PolicyEventType.POLICY_BLOCKED
        assert ev.final_action == PolicyAction.BLOCK

    def test_policy_escalated(self):
        ev = make_market_policy_escalated("E1", "R1", "P1")
        assert ev.event_type == PolicyEventType.POLICY_ESCALATED
        assert ev.final_action == PolicyAction.ESCALATE

    def test_evaluation_completed(self):
        ev = make_market_policy_evaluation_completed("E1", "R1", PolicyAction.APPROVE)
        assert ev.event_type == PolicyEventType.EVALUATION_COMPLETED
        assert ev.final_action == PolicyAction.APPROVE

    def test_to_dict(self):
        ev = make_market_policy_evaluation_started("E1", "R1")
        d = ev.to_dict()
        assert d["event_type"] == "market_policy_evaluation_started"
        assert d["evaluation_id"] == "E1"

    def test_frozen(self):
        ev = make_market_policy_evaluation_started("E1", "R1")
        with pytest.raises((AttributeError, TypeError)):
            ev.event_id = "x"


# ===========================================================================
# TestMarketPolicyEvaluator
# ===========================================================================

class TestMarketPolicyEvaluator:
    def setup_method(self):
        self.ev = MarketPolicyEvaluator()

    def test_gt_true(self):
        c = _cond("vix", ConditionOperator.GT, 25.0)
        assert self.ev.evaluate_condition(c, {"vix": 30.0})

    def test_gt_false(self):
        c = _cond("vix", ConditionOperator.GT, 25.0)
        assert not self.ev.evaluate_condition(c, {"vix": 20.0})

    def test_gte(self):
        c = _cond("x", ConditionOperator.GTE, 10)
        assert self.ev.evaluate_condition(c, {"x": 10})
        assert not self.ev.evaluate_condition(c, {"x": 9})

    def test_lt(self):
        c = _cond("x", ConditionOperator.LT, 5)
        assert self.ev.evaluate_condition(c, {"x": 3})

    def test_lte(self):
        c = _cond("x", ConditionOperator.LTE, 5)
        assert self.ev.evaluate_condition(c, {"x": 5})

    def test_eq(self):
        c = _cond("exchange", ConditionOperator.EQ, "NSE")
        assert self.ev.evaluate_condition(c, {"exchange": "NSE"})
        assert not self.ev.evaluate_condition(c, {"exchange": "BSE"})

    def test_neq(self):
        c = _cond("exchange", ConditionOperator.NEQ, "NSE")
        assert self.ev.evaluate_condition(c, {"exchange": "BSE"})

    def test_in(self):
        c = _cond("exchange", ConditionOperator.IN, ["NSE", "BSE"])
        assert self.ev.evaluate_condition(c, {"exchange": "NSE"})
        assert not self.ev.evaluate_condition(c, {"exchange": "MCX"})

    def test_not_in(self):
        c = _cond("exchange", ConditionOperator.NOT_IN, ["NSE", "BSE"])
        assert self.ev.evaluate_condition(c, {"exchange": "MCX"})

    def test_exists(self):
        c = _cond("vix", ConditionOperator.EXISTS)
        assert self.ev.evaluate_condition(c, {"vix": 20})
        assert not self.ev.evaluate_condition(c, {})

    def test_not_exists(self):
        c = _cond("vix", ConditionOperator.NOT_EXISTS)
        assert self.ev.evaluate_condition(c, {})
        assert not self.ev.evaluate_condition(c, {"vix": 20})

    def test_is_true(self):
        c = _cond("flag", ConditionOperator.IS_TRUE)
        assert self.ev.evaluate_condition(c, {"flag": True})
        assert not self.ev.evaluate_condition(c, {"flag": False})

    def test_is_false(self):
        c = _cond("flag", ConditionOperator.IS_FALSE)
        assert self.ev.evaluate_condition(c, {"flag": False})
        assert not self.ev.evaluate_condition(c, {"flag": True})

    def test_nested_field_path(self):
        c = _cond("market.vix", ConditionOperator.GT, 25)
        assert self.ev.evaluate_condition(c, {"market": {"vix": 30}})
        assert not self.ev.evaluate_condition(c, {"market": {"vix": 10}})

    def test_flat_dotted_key(self):
        c = _cond("market.vix", ConditionOperator.EQ, 30)
        assert self.ev.evaluate_condition(c, {"market.vix": 30})

    def test_type_error_returns_false(self):
        c = _cond("x", ConditionOperator.GT, "str")
        assert not self.ev.evaluate_condition(c, {"x": 10})

    def test_rule_all_operator_all_match(self):
        c1 = _cond("a", ConditionOperator.GT, 5)
        c2 = _cond("b", ConditionOperator.LT, 10)
        r = _rule([c1, c2], PolicyAction.REJECT, LogicalOperator.ALL)
        matched, met, failed = self.ev.evaluate_rule(r, {"a": 10, "b": 5})
        assert matched
        assert len(met) == 2
        assert len(failed) == 0

    def test_rule_all_operator_partial_match(self):
        c1 = _cond("a", ConditionOperator.GT, 5)
        c2 = _cond("b", ConditionOperator.LT, 10)
        r = _rule([c1, c2], PolicyAction.REJECT, LogicalOperator.ALL)
        matched, met, failed = self.ev.evaluate_rule(r, {"a": 3, "b": 5})
        assert not matched

    def test_rule_any_operator(self):
        c1 = _cond("a", ConditionOperator.GT, 5)
        c2 = _cond("b", ConditionOperator.LT, 10)
        r = _rule([c1, c2], PolicyAction.REJECT, LogicalOperator.ANY)
        matched, met, _ = self.ev.evaluate_rule(r, {"a": 3, "b": 5})
        assert matched  # b < 10 is True

    def test_policy_sequential_first_match_wins(self):
        c = _cond("x", ConditionOperator.GT, 0)
        r1 = _rule([c], PolicyAction.APPROVE)
        r2 = _rule([c], PolicyAction.REJECT)
        p = _policy(rules=[r1, r2])
        result = self.ev.evaluate_policy(p, {"x": 1})
        assert result.action == PolicyAction.APPROVE

    def test_policy_parallel_most_severe(self):
        c = _cond("x", ConditionOperator.GT, 0)
        r1 = _rule([c], PolicyAction.APPROVE)
        r2 = _rule([c], PolicyAction.REJECT)
        p = _policy(rules=[r1, r2], evaluation_mode=EvaluationMode.PARALLEL)
        result = self.ev.evaluate_policy(p, {"x": 1})
        assert result.action == PolicyAction.REJECT

    def test_policy_default_action_when_no_rule_matches(self):
        c = _cond("x", ConditionOperator.GT, 100)
        r = _rule([c], PolicyAction.REJECT)
        p = _policy(rules=[r], default_action=PolicyAction.APPROVE)
        result = self.ev.evaluate_policy(p, {"x": 0})
        assert result.action == PolicyAction.APPROVE

    def test_policy_empty_rules_default(self):
        p = _policy(default_action=PolicyAction.DEFER)
        result = self.ev.evaluate_policy(p, {})
        assert result.action == PolicyAction.DEFER


# ===========================================================================
# TestMarketPolicyValidator
# ===========================================================================

class TestMarketPolicyValidator:
    def setup_method(self):
        self.v = MarketPolicyValidator()

    def test_valid_policy(self):
        p = _policy()
        res = self.v.validate_policy(p)
        assert res.is_valid
        assert len(res.failed_checks) == 0

    def test_invalid_weight(self):
        r = MarketPolicyRule.create(
            "bad", (_cond("x", ConditionOperator.EXISTS),),
            LogicalOperator.ALL, PolicyAction.REJECT, weight=0.0
        )
        p = _policy(rules=[r])
        res = self.v.validate_policy(p)
        assert not res.is_valid
        assert ValidationCode.RULE_CONSISTENCY in res.failure_codes

    def test_empty_field_path(self):
        c = MarketPolicyCondition.create("c", "", ConditionOperator.EXISTS)
        r = _rule([c])
        p = _policy(rules=[r])
        res = self.v.validate_policy(p)
        assert not res.is_valid
        assert ValidationCode.CONDITION_VALIDITY in res.failure_codes

    def test_valid_request(self):
        req = _request()
        res = self.v.validate_request(req)
        assert res.is_valid

    def test_validate_or_raise_valid(self):
        self.v.validate_or_raise(_policy())

    def test_validate_or_raise_invalid(self):
        r = MarketPolicyRule.create(
            "bad", (_cond("x", ConditionOperator.EXISTS),),
            LogicalOperator.ALL, PolicyAction.REJECT, weight=-1.0
        )
        p = _policy(rules=[r])
        with pytest.raises(MarketPolicyValidationError):
            self.v.validate_or_raise(p)

    def test_failure_messages(self):
        r = MarketPolicyRule.create(
            "bad", (_cond("x", ConditionOperator.EXISTS),),
            LogicalOperator.ALL, PolicyAction.REJECT, weight=0.0
        )
        p = _policy(rules=[r])
        res = self.v.validate_policy(p)
        assert len(res.failure_messages) >= 1

    def test_passed_checks_included(self):
        p = _policy()
        res = self.v.validate_policy(p)
        assert len(res.passed_checks) == 7  # all 7 checks pass


# ===========================================================================
# TestMarketPolicyPriority
# ===========================================================================

class TestMarketPolicyPriority:
    def _result(self, action, priority=PolicyPriority.MEDIUM):
        return MarketPolicyResult.create(
            "P", "T", MarketPolicyType.MARKET_HOURS_POLICY, priority, action
        )

    def test_empty_returns_none(self):
        assert MarketPolicyPriorityResolver.resolve([]) is None

    def test_single_result(self):
        r = self._result(PolicyAction.APPROVE)
        assert MarketPolicyPriorityResolver.resolve([r]) is r

    def test_block_overrides_all(self):
        block = self._result(PolicyAction.BLOCK)
        reject = self._result(PolicyAction.REJECT)
        approve = self._result(PolicyAction.APPROVE)
        dom = MarketPolicyPriorityResolver.resolve([approve, reject, block])
        assert dom.action == PolicyAction.BLOCK

    def test_critical_overrides_high(self):
        high_reject = self._result(PolicyAction.REJECT, PolicyPriority.HIGH)
        critical_approve = self._result(PolicyAction.APPROVE, PolicyPriority.CRITICAL)
        dom = MarketPolicyPriorityResolver.resolve([high_reject, critical_approve])
        # critical is picked because no BLOCK, and CRITICAL priority fires
        # Among critical only: most severe action
        assert dom.priority == PolicyPriority.CRITICAL

    def test_reject_overrides_approve(self):
        approve = self._result(PolicyAction.APPROVE)
        reject = self._result(PolicyAction.REJECT)
        dom = MarketPolicyPriorityResolver.resolve([approve, reject])
        assert dom.action == PolicyAction.REJECT

    def test_escalate_overrides_conditional(self):
        cond = self._result(PolicyAction.APPROVE_WITH_CONDITIONS)
        escalate = self._result(PolicyAction.ESCALATE)
        dom = MarketPolicyPriorityResolver.resolve([cond, escalate])
        assert dom.action == PolicyAction.ESCALATE

    def test_highest_priority_when_equal_severity(self):
        r_low = self._result(PolicyAction.APPROVE, PolicyPriority.LOW)
        r_high = self._result(PolicyAction.APPROVE, PolicyPriority.HIGH)
        dom = MarketPolicyPriorityResolver.resolve([r_low, r_high])
        assert dom.priority == PolicyPriority.HIGH


# ===========================================================================
# TestMarketPolicyChain
# ===========================================================================

class TestMarketPolicyChain:
    def setup_method(self):
        self.chain = MarketPolicyChain()

    def _reject_policy(self, priority=PolicyPriority.MEDIUM):
        c = _cond("x", ConditionOperator.GT, 0)
        r = _rule([c], PolicyAction.REJECT)
        return _policy(priority=priority, rules=[r])

    def _approve_policy(self, priority=PolicyPriority.LOW):
        c = _cond("x", ConditionOperator.GT, 0)
        r = _rule([c], PolicyAction.APPROVE)
        return _policy(
            policy_type=MarketPolicyType.VOLATILITY_POLICY,
            priority=priority, rules=[r]
        )

    def test_empty_policies(self):
        assert self.chain.evaluate([], {}) == []

    def test_disabled_policies_skipped(self):
        p = _policy()
        p_disabled = p.with_enabled(False)
        assert self.chain.evaluate([p_disabled], {"x": 1}) == []

    def test_sequential_stops_at_deny(self):
        p1 = self._reject_policy(PolicyPriority.HIGH)
        p2 = self._approve_policy(PolicyPriority.LOW)
        results = self.chain.evaluate(
            [p1, p2], {"x": 1}, EvaluationMode.SEQUENTIAL
        )
        assert len(results) == 1
        assert results[0].action == PolicyAction.REJECT

    def test_parallel_evaluates_all(self):
        p1 = self._reject_policy(PolicyPriority.HIGH)
        p2 = self._approve_policy(PolicyPriority.LOW)
        results = self.chain.evaluate(
            [p1, p2], {"x": 1}, EvaluationMode.PARALLEL
        )
        assert len(results) == 2

    def test_composite_evaluates_all(self):
        p1 = self._reject_policy()
        p2 = self._approve_policy()
        results = self.chain.evaluate(
            [p1, p2], {"x": 1}, EvaluationMode.COMPOSITE
        )
        assert len(results) == 2

    def test_weighted_reorders_by_severity(self):
        p1 = self._approve_policy()
        p2 = self._reject_policy()
        results = self.chain.evaluate(
            [p1, p2], {"x": 1}, EvaluationMode.WEIGHTED
        )
        assert len(results) == 2
        # most severe should come first
        assert results[0].action == PolicyAction.REJECT

    def test_nested_conditional_uses_parallel(self):
        p1 = self._reject_policy()
        p2 = self._approve_policy()
        r1 = self.chain.evaluate([p1, p2], {"x": 1}, EvaluationMode.NESTED)
        r2 = self.chain.evaluate([p1, p2], {"x": 1}, EvaluationMode.CONDITIONAL)
        assert len(r1) == 2
        assert len(r2) == 2


# ===========================================================================
# TestMarketPolicyRegistry
# ===========================================================================

class TestMarketPolicyRegistry:
    def test_register_and_get(self):
        reg = MarketPolicyRegistry()
        p = _policy()
        reg.register(p)
        assert reg.get(p.policy_id) is p

    def test_not_found(self):
        reg = MarketPolicyRegistry()
        with pytest.raises(MarketPolicyNotFoundError):
            reg.get("nonexistent")

    def test_get_optional(self):
        reg = MarketPolicyRegistry()
        assert reg.get_optional("x") is None

    def test_contains(self):
        reg = MarketPolicyRegistry()
        p = _policy()
        reg.register(p)
        assert reg.contains(p.policy_id)
        assert not reg.contains("other")

    def test_unregister(self):
        reg = MarketPolicyRegistry()
        p = _policy()
        reg.register(p)
        reg.unregister(p.policy_id)
        assert not reg.contains(p.policy_id)

    def test_unregister_not_found(self):
        reg = MarketPolicyRegistry()
        with pytest.raises(MarketPolicyNotFoundError):
            reg.unregister("ghost")

    def test_register_none_raises(self):
        reg = MarketPolicyRegistry()
        with pytest.raises(MarketPolicyRegistryError):
            reg.register(None)

    def test_capacity_error(self):
        reg = MarketPolicyRegistry(max_policies=1)
        p1 = _policy()
        p2 = MarketPolicy.create("P2", MarketPolicyType.VOLATILITY_POLICY, PolicyPriority.LOW, [])
        reg.register(p1)
        with pytest.raises(MarketPolicyCapacityError):
            reg.register(p2)

    def test_update_existing_no_capacity_error(self):
        reg = MarketPolicyRegistry(max_policies=1)
        p = _policy()
        reg.register(p)
        # updating same policy_id should not raise
        reg.register(p.with_enabled(False))

    def test_list_all(self):
        reg = MarketPolicyRegistry()
        for _ in range(3):
            reg.register(
                MarketPolicy.create("P", MarketPolicyType.MARKET_HOURS_POLICY, PolicyPriority.LOW, [])
            )
        assert len(reg.list_all()) == 3

    def test_list_enabled(self):
        reg = MarketPolicyRegistry()
        p_on = _policy()
        p_off = MarketPolicy.create(
            "P_off", MarketPolicyType.MARKET_HOURS_POLICY, PolicyPriority.LOW, [],
            enabled=False
        )
        p_on2 = MarketPolicy.create("P2", MarketPolicyType.VOLATILITY_POLICY, PolicyPriority.LOW, [])
        reg.register(p_on)
        reg.register(p_off)
        reg.register(p_on2)
        enabled = reg.list_enabled()
        assert len(enabled) == 2

    def test_list_by_type(self):
        reg = MarketPolicyRegistry()
        p1 = MarketPolicy.create("P1", MarketPolicyType.MARKET_HOURS_POLICY, PolicyPriority.LOW, [])
        p2 = MarketPolicy.create("P2", MarketPolicyType.VOLATILITY_POLICY, PolicyPriority.LOW, [])
        reg.register(p1)
        reg.register(p2)
        mh = reg.list_by_type(MarketPolicyType.MARKET_HOURS_POLICY)
        assert len(mh) == 1

    def test_list_enabled_by_type(self):
        reg = MarketPolicyRegistry()
        p1 = MarketPolicy.create("P1", MarketPolicyType.MARKET_HOURS_POLICY, PolicyPriority.LOW, [])
        p2 = MarketPolicy.create(
            "P2", MarketPolicyType.MARKET_HOURS_POLICY, PolicyPriority.LOW, [],
            enabled=False
        )
        reg.register(p1)
        reg.register(p2)
        enabled = reg.list_enabled_by_type(MarketPolicyType.MARKET_HOURS_POLICY)
        assert len(enabled) == 1

    def test_count_and_enabled_count(self):
        reg = MarketPolicyRegistry()
        p = _policy()
        p_off = MarketPolicy.create(
            "P_off", MarketPolicyType.VOLATILITY_POLICY, PolicyPriority.LOW, [],
            enabled=False
        )
        reg.register(p)
        reg.register(p_off)
        assert reg.count == 2
        assert reg.enabled_count == 1

    def test_clear(self):
        reg = MarketPolicyRegistry()
        reg.register(_policy())
        reg.clear()
        assert reg.count == 0


# ===========================================================================
# TestMarketPolicyFactory
# ===========================================================================

class TestMarketPolicyFactory:
    def setup_method(self):
        self.f = MarketPolicyFactory()

    def test_create_context(self):
        ctx = self.f.create_context("E1", "M1", "NSE")
        assert ctx.evaluation_id == "E1"
        assert ctx.exchange == "NSE"

    def test_create_request(self):
        req = self.f.create_request("E1", "M1", "NSE", inputs={"vix": 25})
        assert req.inputs["vix"] == 25

    def test_create_simple_policy(self):
        p = self.f.create_simple_policy(
            "Test", MarketPolicyType.REGULATORY_POLICY
        )
        assert p.enabled
        assert p.rule_count == 0
        assert p.default_action == PolicyAction.APPROVE

    def test_create_simple_policy_disabled(self):
        p = self.f.create_simple_policy(
            "Off", MarketPolicyType.MARKET_HEALTH_POLICY, enabled=False
        )
        assert not p.enabled

    def test_create_policy_result(self):
        r = self.f.create_policy_result(
            "P1", "Policy", MarketPolicyType.INDEX_COVERAGE_POLICY,
            PolicyPriority.HIGH, PolicyAction.REJECT,
            rationale="test"
        )
        assert r.action == PolicyAction.REJECT
        assert r.rationale == "test"


# ===========================================================================
# TestMarketPolicyManager
# ===========================================================================

class TestMarketPolicyManager:
    def _make_manager(self, policies=None):
        reg = MarketPolicyRegistry()
        for p in (policies or []):
            reg.register(p)
        ev = MarketPolicyEvaluator()
        chain = MarketPolicyChain(ev)
        return MarketPolicyManager(
            registry=reg,
            evaluator=ev,
            chain=chain,
            validator=MarketPolicyValidator(),
            auditor=MarketPolicyAuditor(),
            statistics=MarketPolicyStatistics(),
            history=MarketPolicyHistory(),
            factory=MarketPolicyFactory(),
        )

    def test_no_policies_default_approve(self):
        mgr = self._make_manager()
        req = _request()
        resp = mgr.run_evaluation(req)
        assert resp.is_approved
        assert resp.is_success
        assert resp.policies_evaluated == 0

    def test_policy_reject(self):
        c = _cond("open", ConditionOperator.IS_FALSE)
        r = _rule([c], PolicyAction.REJECT)
        p = _policy(rules=[r])
        mgr = self._make_manager([p])
        req = _request(inputs={"open": False})
        resp = mgr.run_evaluation(req)
        assert resp.final_action == PolicyAction.REJECT

    def test_invalid_request_failure_response(self):
        mgr = self._make_manager()
        # Create invalid request with empty exchange
        req = MarketPolicyRequest(
            request_id="",
            evaluation_id="",
            market_analysis_id="",
            exchange="",
            context=MarketPolicyContext.create("", "", ""),
        )
        resp = mgr.run_evaluation(req)
        assert not resp.is_success

    def test_history_records(self):
        hist = MarketPolicyHistory()
        reg = MarketPolicyRegistry()
        mgr = MarketPolicyManager(
            registry=reg,
            evaluator=MarketPolicyEvaluator(),
            chain=MarketPolicyChain(),
            validator=MarketPolicyValidator(),
            auditor=MarketPolicyAuditor(),
            statistics=MarketPolicyStatistics(),
            history=hist,
            factory=MarketPolicyFactory(),
        )
        mgr.run_evaluation(_request())
        counts = hist.counts()
        assert counts["requests"] == 1
        assert counts["responses"] == 1
        assert counts["audits"] == 1

    def test_policy_type_filter(self):
        c = _cond("x", ConditionOperator.GT, 0)
        r = _rule([c], PolicyAction.REJECT)
        p_mh = _policy(policy_type=MarketPolicyType.MARKET_HOURS_POLICY, rules=[r])
        p_vol = MarketPolicy.create(
            "Vol", MarketPolicyType.VOLATILITY_POLICY, PolicyPriority.HIGH, [r]
        )
        mgr = self._make_manager([p_mh, p_vol])
        # Only evaluate MARKET_HOURS_POLICY
        ctx = MarketPolicyContext.create(
            "E", "M", "NSE",
            policy_types=(MarketPolicyType.MARKET_HOURS_POLICY,)
        )
        req = MarketPolicyRequest.create(
            "E", "M", "NSE", context=ctx, inputs={"x": 1}
        )
        resp = mgr.run_evaluation(req)
        assert resp.policies_evaluated == 1

    def test_parallel_mode_via_metadata(self):
        c = _cond("x", ConditionOperator.GT, 0)
        r_reject = _rule([c], PolicyAction.REJECT)
        r_block = _rule([c], PolicyAction.BLOCK)
        p1 = _policy(priority=PolicyPriority.CRITICAL, rules=[r_reject])
        p2 = MarketPolicy.create(
            "B", MarketPolicyType.VOLATILITY_POLICY, PolicyPriority.HIGH, [r_block]
        )
        mgr = self._make_manager([p1, p2])
        req = _request(inputs={"x": 1}, metadata={"evaluation_mode": "parallel"})
        resp = mgr.run_evaluation(req)
        assert resp.final_action == PolicyAction.BLOCK

    def test_statistics_updated(self):
        stats = MarketPolicyStatistics()
        reg = MarketPolicyRegistry()
        mgr = MarketPolicyManager(
            registry=reg,
            evaluator=MarketPolicyEvaluator(),
            chain=MarketPolicyChain(),
            validator=MarketPolicyValidator(),
            auditor=MarketPolicyAuditor(),
            statistics=stats,
            history=MarketPolicyHistory(),
            factory=MarketPolicyFactory(),
        )
        mgr.run_evaluation(_request())
        snap = stats.snapshot()
        assert snap["evaluations_total"] == 1
        assert snap["approved"] == 1


# ===========================================================================
# TestMarketPolicyEngine
# ===========================================================================

class TestMarketPolicyEngine:
    def test_start_stop(self):
        e = MarketPolicyEngine()
        e.start()
        assert e.lifecycle_state().value == "running"
        e.stop()
        assert e.lifecycle_state().value != "running"

    def test_not_running_raises(self):
        e = MarketPolicyEngine()
        with pytest.raises(MarketPolicyEngineNotRunningError):
            e.evaluate(_request())

    def test_evaluate_no_policies_approve(self):
        e = _started_engine()
        resp = e.evaluate(_request())
        assert resp.is_approved
        e.stop()

    def test_register_and_evaluate(self):
        e = _started_engine()
        c = _cond("exchange_open", ConditionOperator.IS_FALSE)
        r = _rule([c], PolicyAction.REJECT)
        p = _policy(rules=[r])
        e.register_policy(p)
        resp = e.evaluate(_request(inputs={"exchange_open": False}))
        assert resp.final_action == PolicyAction.REJECT
        e.stop()

    def test_unregister_policy(self):
        e = _started_engine()
        p = _policy()
        e.register_policy(p)
        e.unregister_policy(p.policy_id)
        assert not e._registry.contains(p.policy_id)
        e.stop()

    def test_get_policy(self):
        e = _started_engine()
        p = _policy()
        e.register_policy(p)
        assert e.get_policy(p.policy_id) is p
        e.stop()

    def test_list_policies(self):
        e = _started_engine()
        p1 = MarketPolicy.create("P1", MarketPolicyType.MARKET_HOURS_POLICY, PolicyPriority.LOW, [])
        p2 = MarketPolicy.create("P2", MarketPolicyType.VOLATILITY_POLICY, PolicyPriority.LOW, [])
        e.register_policy(p1)
        e.register_policy(p2)
        all_p = e.list_policies()
        assert len(all_p) == 2
        mh_only = e.list_policies(MarketPolicyType.MARKET_HOURS_POLICY)
        assert len(mh_only) == 1
        e.stop()

    def test_validate_policy(self):
        e = _started_engine()
        res = e.validate_policy(_policy())
        assert res.is_valid
        e.stop()

    def test_validate_request(self):
        e = _started_engine()
        res = e.validate_request(_request())
        assert res.is_valid
        e.stop()

    def test_statistics(self):
        e = _started_engine()
        e.evaluate(_request())
        st = e.statistics()
        assert st["evaluations_total"] == 1
        e.stop()

    def test_history(self):
        e = _started_engine()
        e.evaluate(_request())
        h = e.history()
        assert h["requests"] >= 1
        e.stop()

    def test_status(self):
        e = _started_engine()
        p = _policy()
        e.register_policy(p)
        st = e.status()
        assert isinstance(st, MarketPolicyEngineStatus)
        assert st.policies_registered == 1
        assert st.policies_enabled == 1
        e.stop()

    def test_listener_receives_events(self):
        events: List[MarketPolicyEvent] = []
        e = _started_engine()
        e.add_listener(events.append)
        e.evaluate(_request())
        assert len(events) >= 2  # started + completed
        e.stop()

    def test_remove_listener(self):
        events: List[MarketPolicyEvent] = []
        e = _started_engine()
        e.add_listener(events.append)
        e.remove_listener(events.append)
        e.evaluate(_request())
        assert events == []
        e.stop()

    def test_faulty_listener_does_not_crash(self):
        def bad_listener(ev):
            raise RuntimeError("listener error")

        e = _started_engine()
        e.add_listener(bad_listener)
        resp = e.evaluate(_request())
        assert resp.is_success
        e.stop()

    def test_add_same_listener_once(self):
        e = _started_engine()
        fn = lambda ev: None
        e.add_listener(fn)
        e.add_listener(fn)
        assert len(e._listeners) == 1
        e.stop()

    def test_register_not_running(self):
        e = MarketPolicyEngine()
        with pytest.raises(MarketPolicyEngineNotRunningError):
            e.register_policy(_policy())

    def test_evaluate_all_policy_types(self):
        e = _started_engine()
        for pt in MarketPolicyType:
            p = MarketPolicy.create("P", pt, PolicyPriority.LOW, [])
            e.register_policy(p)
        resp = e.evaluate(_request())
        assert resp.is_success
        e.stop()

    def test_block_overrides_in_parallel(self):
        e = _started_engine()
        c = _cond("halt", ConditionOperator.IS_TRUE)
        r_reject = _rule([c], PolicyAction.REJECT)
        r_block = _rule([c], PolicyAction.BLOCK)
        p1 = _policy(priority=PolicyPriority.CRITICAL, rules=[r_reject])
        p2 = MarketPolicy.create(
            "B", MarketPolicyType.VOLATILITY_POLICY, PolicyPriority.HIGH, [r_block]
        )
        e.register_policy(p1)
        e.register_policy(p2)
        resp = e.evaluate(_request(
            inputs={"halt": True},
            metadata={"evaluation_mode": "parallel"}
        ))
        assert resp.final_action == PolicyAction.BLOCK
        e.stop()

    def test_multiple_evaluations_stats(self):
        e = _started_engine()
        for _ in range(5):
            e.evaluate(_request())
        st = e.statistics()
        assert st["evaluations_total"] == 5
        e.stop()


# ===========================================================================
# TestConcurrency
# ===========================================================================

class TestConcurrency:
    def test_concurrent_evaluations(self):
        e = _started_engine()
        errors: List[Exception] = []
        results: List[MarketPolicyResponse] = []
        lock = threading.Lock()

        def run():
            try:
                req = MarketPolicyRequest.create("E", "M", "NSE")
                resp = e.evaluate(req)
                with lock:
                    results.append(resp)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=run) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(results) == 20
        e.stop()

    def test_concurrent_registry_operations(self):
        reg = MarketPolicyRegistry(max_policies=200)
        errors = []
        lock = threading.Lock()

        def register_policies(start_idx):
            for i in range(start_idx, start_idx + 10):
                try:
                    p = MarketPolicy.create(
                        f"P{i}", MarketPolicyType.MARKET_HOURS_POLICY,
                        PolicyPriority.LOW, [], policy_id=f"POL-{i}"
                    )
                    reg.register(p)
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=register_policies, args=(i * 10,))
                   for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert reg.count == 50

    def test_concurrent_statistics(self):
        stats = MarketPolicyStatistics()
        lock = threading.Lock()
        errors = []

        def update():
            try:
                for _ in range(100):
                    stats.record_evaluation()
                    stats.record_approved()
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=update) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        snap = stats.snapshot()
        assert snap["evaluations_total"] == 500
        assert snap["approved"] == 500


# ===========================================================================
# TestRegression
# ===========================================================================

class TestRegression:
    def test_full_evaluation_pipeline(self):
        """Full happy-path: single exchange hours policy rejects closed market."""
        e = _started_engine()
        c = MarketPolicyCondition.create(
            "closed_check", "exchange_open",
            ConditionOperator.IS_FALSE
        )
        r = MarketPolicyRule.create(
            "reject_closed", (c,), LogicalOperator.ALL, PolicyAction.REJECT
        )
        p = MarketPolicy.create(
            "Exchange Hours", MarketPolicyType.MARKET_HOURS_POLICY,
            PolicyPriority.CRITICAL, [r]
        )
        e.register_policy(p)

        # closed market
        resp = e.evaluate(MarketPolicyRequest.create(
            "EVAL-CLOSED", "MKT-001", "NSE", inputs={"exchange_open": False}
        ))
        assert resp.final_action == PolicyAction.REJECT
        assert not resp.is_approved
        assert resp.is_success

        # open market
        resp2 = e.evaluate(MarketPolicyRequest.create(
            "EVAL-OPEN", "MKT-002", "NSE", inputs={"exchange_open": True}
        ))
        assert resp2.is_approved

        e.stop()

    def test_audit_trail_completeness(self):
        """Audit report includes all required fields."""
        e = _started_engine()
        c = _cond("x", ConditionOperator.GT, 0)
        r = _rule([c], PolicyAction.APPROVE)
        p = _policy(rules=[r])
        e.register_policy(p)
        e.evaluate(_request(inputs={"x": 1}))
        hist = e._history.recent_audits(1)
        assert len(hist) == 1
        audit = hist[0]
        assert audit.exchange == "NSE"
        assert audit.elapsed_s >= 0
        e.stop()

    def test_multiple_policy_types(self):
        """Multiple policy types all evaluated in parallel."""
        e = _started_engine()
        c = _cond("ok", ConditionOperator.IS_TRUE)
        r = _rule([c], PolicyAction.APPROVE)

        for pt in [
            MarketPolicyType.MARKET_HOURS_POLICY,
            MarketPolicyType.EXCHANGE_ACCESS_POLICY,
            MarketPolicyType.VOLATILITY_POLICY,
            MarketPolicyType.REGULATORY_POLICY,
        ]:
            p = MarketPolicy.create("P", pt, PolicyPriority.LOW, [r])
            e.register_policy(p)

        resp = e.evaluate(_request(
            inputs={"ok": True},
            metadata={"evaluation_mode": "parallel"}
        ))
        assert resp.is_approved
        assert resp.policies_evaluated == 4
        e.stop()

    def test_escalation_flow(self):
        """ESCALATE action triggers escalation flag on response."""
        e = _started_engine()
        c = _cond("event_risk", ConditionOperator.IS_TRUE)
        r = _rule([c], PolicyAction.ESCALATE)
        p = _policy(rules=[r])
        e.register_policy(p)

        resp = e.evaluate(_request(inputs={"event_risk": True}))
        assert resp.requires_escalation
        assert resp.final_action == PolicyAction.ESCALATE
        e.stop()

    def test_conditional_approve_response(self):
        """APPROVE_WITH_CONDITIONS approval propagates."""
        e = _started_engine()
        c = _cond("low_liquidity", ConditionOperator.IS_TRUE)
        r = _rule([c], PolicyAction.APPROVE_WITH_CONDITIONS)
        p = _policy(rules=[r])
        e.register_policy(p)

        resp = e.evaluate(_request(inputs={"low_liquidity": True}))
        assert resp.is_approved
        assert resp.final_action == PolicyAction.APPROVE_WITH_CONDITIONS
        e.stop()

    def test_policy_summary_counts(self):
        """Summary accurately counts action types."""
        e = _started_engine()
        c = _cond("x", ConditionOperator.GT, 0)
        r1 = _rule([c], PolicyAction.APPROVE)
        r2 = _rule([c], PolicyAction.REJECT)
        p1 = _policy(priority=PolicyPriority.HIGH, rules=[r1])
        p2 = MarketPolicy.create(
            "P2", MarketPolicyType.VOLATILITY_POLICY, PolicyPriority.LOW, [r2]
        )
        e.register_policy(p1)
        e.register_policy(p2)

        resp = e.evaluate(_request(
            inputs={"x": 1},
            metadata={"evaluation_mode": "parallel"}
        ))
        assert resp.summary.approved + resp.summary.rejected == 2
        e.stop()

    def test_response_to_dict_roundtrip(self):
        """to_dict() contains all top-level keys."""
        e = _started_engine()
        resp = e.evaluate(_request())
        d = resp.to_dict()
        for key in ["response_id", "request_id", "evaluation_id",
                    "market_analysis_id", "exchange", "final_action",
                    "policies_evaluated", "is_success", "summary", "results"]:
            assert key in d, f"Missing key: {key}"
        e.stop()

    def test_engine_status_fields(self):
        """Status snapshot has expected fields."""
        e = _started_engine()
        st = e.status()
        assert st.engine_id == POLICY_SYSTEM_ID
        assert st.framework_version == VERSION
        assert isinstance(st.statistics, dict)
        e.stop()

    def test_data_freshness_policy_domain(self):
        """Data freshness policy type is evaluable."""
        e = _started_engine()
        c = MarketPolicyCondition.create(
            "stale", "data_age_hours", ConditionOperator.GT, threshold=2.0
        )
        r = MarketPolicyRule.create(
            "stale_data", (c,), LogicalOperator.ALL, PolicyAction.DEFER
        )
        p = MarketPolicy.create(
            "Data Freshness", MarketPolicyType.DATA_FRESHNESS_POLICY,
            PolicyPriority.HIGH, [r]
        )
        e.register_policy(p)
        resp = e.evaluate(_request(inputs={"data_age_hours": 3.5}))
        assert resp.final_action == PolicyAction.DEFER
        e.stop()
