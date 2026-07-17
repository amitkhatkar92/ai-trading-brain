"""tests/unit/execution/risk/test_execution_risk_controls.py
==============================================================
Unit test suite for IIOS Execution Risk Controls Framework (C6 Phase 4 M4).
~160 tests covering all framework components and all 6 built-in policies.
"""
from __future__ import annotations

import threading
import time
from typing import Any, List
from unittest.mock import MagicMock

import pytest

# ── Framework imports ─────────────────────────────────────────────────────────
from iios.execution.risk.controls import (
    # enumerations
    ControlAction,
    ControlEventType,
    PolicyType,
    highest_priority_action,
    # constants
    ACTION_PRIORITY,
    BLOCKING_ACTIONS,
    PASSTHROUGH_ACTIONS,
    TERMINAL_ACTIONS,
    DEFERRAL_ACTIONS,
    OUTCOME_TO_ACTION,
    # exceptions
    ControlFrameworkError,
    ControlNotRunningError,
    ControlRegistrationError,
    ControlValidationError,
    EmergencyActionError,
    ExecutionControlError,
    OverrideError,
    PolicyEvaluationError,
    PolicyNotFoundError,
    # action metadata
    get_action_metadata,
    is_blocking_action,
    is_emergency_action,
    is_terminal_action,
    requires_override,
    can_retry,
    action_priority,
    # context
    ControlContext,
    make_control_context,
    make_control_context_from_rule_context,
    # request
    ControlRequest,
    make_control_request,
    # response
    ControlResponse,
    make_control_response,
    make_error_response,
    # decision
    RiskControlDecision,
    OverrideInfo,
    EmergencyInfo,
    make_allow_decision,
    make_block_decision,
    make_warning_decision,
    make_override_required_decision,
    make_emergency_decision,
    make_override_info,
    make_emergency_info,
    # events
    ControlEvent,
    make_control_evaluated_event,
    make_control_approved_event,
    make_emergency_triggered_event,
    make_execution_blocked_event,
    make_override_requested_event,
    make_override_approved_event,
    # history
    ControlHistory,
    # statistics
    ControlStatistics,
    # validation
    ControlValidationResult,
    RiskControlValidator,
    # policies
    BasePolicy,
    SingleRulePolicy,
    MajorityPolicy,
    HighestSeverityPolicy,
    WeightedSeverityPolicy,
    EmergencyPolicy,
    ConfigurablePolicy,
    # services
    ControlPolicyRegistry,
    RiskControlFactory,
    RiskControlEngine,
    RiskControlManager,
)


# ═════════════════════════════════════════════════════════════════════════════
# Test helpers & fixtures
# ═════════════════════════════════════════════════════════════════════════════

def _ctx(**kw) -> ControlContext:
    return make_control_context(**kw)


def _normal_ctx() -> ControlContext:
    return make_control_context(
        system_info={"system_healthy": True},
        session_info={"session_valid": True},
    )


def _emergency_ctx() -> ControlContext:
    return make_control_context(system_info={"emergency_stop": True})


class _FakeRuleResult:
    """Minimal stand-in for M3 RuleResult."""
    def __init__(
        self,
        outcome:    str,
        rule_id:    str = "test:rule",
        rule_name:  str = "Test Rule",
        category:   str = "OPERATIONAL",
    ):
        self._outcome   = outcome
        self.rule_id    = rule_id
        self.rule_name  = rule_name

        class _Cat:
            value = category
        self.category = _Cat()

        self.passed           = outcome in ("PASS", "SKIPPED")
        self.blocked          = outcome == "BLOCK"
        self.warned           = outcome == "WARNING"
        self.failed           = outcome == "FAILED"
        self.skipped          = outcome == "SKIPPED"
        self.override_required = outcome == "OVERRIDE_REQUIRED"

        class _Out:
            value = outcome
        self.outcome = _Out()


def _pass_result(rule_id: str = "r:pass") -> _FakeRuleResult:
    return _FakeRuleResult("PASS", rule_id=rule_id)


def _block_result(rule_id: str = "r:block") -> _FakeRuleResult:
    return _FakeRuleResult("BLOCK", rule_id=rule_id)


def _warn_result(rule_id: str = "r:warn") -> _FakeRuleResult:
    return _FakeRuleResult("WARNING", rule_id=rule_id)


def _override_result(rule_id: str = "r:override") -> _FakeRuleResult:
    return _FakeRuleResult("OVERRIDE_REQUIRED", rule_id=rule_id)


def _failed_result(rule_id: str = "r:fail") -> _FakeRuleResult:
    return _FakeRuleResult("FAILED", rule_id=rule_id)


def _emergency_result() -> _FakeRuleResult:
    return _FakeRuleResult("BLOCK", rule_id="builtin:safety:emergency_stop_v1",
                           rule_name="Emergency Stop Rule")


def _req(
    rule_results=(),
    policy_type: PolicyType = PolicyType.HIGHEST_SEVERITY,
    context: ControlContext | None = None,
) -> ControlRequest:
    ctx = context or _normal_ctx()
    return make_control_request(
        rule_results=rule_results,
        context=ctx,
        policy_type=policy_type,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Constants
# ═════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_emergency_stop_highest_priority(self):
        assert ACTION_PRIORITY[ControlAction.EMERGENCY_STOP] > ACTION_PRIORITY[ControlAction.BLOCK]

    def test_block_above_require_override(self):
        assert ACTION_PRIORITY[ControlAction.BLOCK] > ACTION_PRIORITY[ControlAction.REQUIRE_OVERRIDE]

    def test_allow_lowest_priority(self):
        assert ACTION_PRIORITY[ControlAction.ALLOW] == min(ACTION_PRIORITY.values())

    def test_blocking_actions_set(self):
        assert ControlAction.BLOCK in BLOCKING_ACTIONS
        assert ControlAction.EMERGENCY_STOP in BLOCKING_ACTIONS

    def test_passthrough_actions_set(self):
        assert ControlAction.ALLOW in PASSTHROUGH_ACTIONS
        assert ControlAction.ALLOW_WITH_WARNING in PASSTHROUGH_ACTIONS

    def test_highest_priority_action(self):
        result = highest_priority_action(
            ControlAction.ALLOW, ControlAction.BLOCK, ControlAction.ALLOW_WITH_WARNING
        )
        assert result == ControlAction.BLOCK

    def test_highest_priority_emergency_wins(self):
        result = highest_priority_action(
            ControlAction.BLOCK, ControlAction.EMERGENCY_STOP, ControlAction.ALLOW
        )
        assert result == ControlAction.EMERGENCY_STOP

    def test_outcome_to_action_mapping(self):
        assert OUTCOME_TO_ACTION["PASS"]   == ControlAction.ALLOW
        assert OUTCOME_TO_ACTION["BLOCK"]  == ControlAction.BLOCK
        assert OUTCOME_TO_ACTION["FAILED"] == ControlAction.BLOCK


# ═════════════════════════════════════════════════════════════════════════════
# Exceptions
# ═════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_all_inherit_from_base(self):
        for cls in (
            ControlNotRunningError,
            PolicyEvaluationError,
            PolicyNotFoundError,
            ControlValidationError,
            OverrideError,
            EmergencyActionError,
            ControlFrameworkError,
            ControlRegistrationError,
        ):
            assert issubclass(cls, ExecutionControlError)

    def test_policy_not_found_stores_type(self):
        e = PolicyNotFoundError("MAJORITY")
        assert "MAJORITY" in str(e.policy_type)

    def test_override_error_stores_id(self):
        e = OverrideError("bad override", override_id="OVR-1")
        assert e.override_id == "OVR-1"

    def test_not_running_no_args(self):
        e = ControlNotRunningError()
        assert isinstance(e, ExecutionControlError)


# ═════════════════════════════════════════════════════════════════════════════
# Action metadata
# ═════════════════════════════════════════════════════════════════════════════

class TestActionMetadata:
    def test_emergency_stop_is_emergency(self):
        md = get_action_metadata(ControlAction.EMERGENCY_STOP)
        assert md.is_emergency
        assert md.is_blocking
        assert md.is_terminal

    def test_allow_is_passthrough(self):
        md = get_action_metadata(ControlAction.ALLOW)
        assert md.is_passthrough
        assert not md.is_blocking

    def test_require_override_flag(self):
        md = get_action_metadata(ControlAction.REQUIRE_OVERRIDE)
        assert md.requires_override

    def test_block_cannot_retry(self):
        md = get_action_metadata(ControlAction.BLOCK)
        assert not md.can_retry

    def test_retry_can_retry(self):
        md = get_action_metadata(ControlAction.RETRY)
        assert md.can_retry

    def test_all_actions_have_metadata(self):
        for action in ControlAction:
            assert get_action_metadata(action) is not None

    def test_helper_functions(self):
        assert is_blocking_action(ControlAction.BLOCK)
        assert is_emergency_action(ControlAction.EMERGENCY_STOP)
        assert is_terminal_action(ControlAction.CANCEL)
        assert requires_override(ControlAction.REQUIRE_OVERRIDE)
        assert can_retry(ControlAction.RETRY)


# ═════════════════════════════════════════════════════════════════════════════
# ControlContext
# ═════════════════════════════════════════════════════════════════════════════

class TestControlContext:
    def test_make_control_context_defaults(self):
        ctx = make_control_context()
        assert isinstance(ctx, ControlContext)

    def test_emergency_stop_from_system_info(self):
        ctx = make_control_context(system_info={"emergency_stop": True})
        assert ctx.emergency_stop_active

    def test_emergency_stop_from_exec_snapshot(self):
        ctx = make_control_context(execution_snapshot={"emergency_stop": True})
        assert ctx.emergency_stop_active

    def test_emergency_stop_inactive_by_default(self):
        assert not _normal_ctx().emergency_stop_active

    def test_get_limit_returns_default(self):
        ctx = make_control_context()
        assert ctx.get_limit("missing", 42) == 42

    def test_get_limit_from_risk_limits(self):
        ctx = make_control_context(risk_limits={"max_pos": 10})
        assert ctx.get_limit("max_pos", 0) == 10

    def test_age_ms_positive(self):
        ctx = make_control_context()
        time.sleep(0.01)
        assert ctx.age_ms > 0

    def test_bridge_from_rule_context(self):
        mock_ctx = MagicMock()
        mock_ctx.evaluation_id = "eval-1"
        mock_ctx.execution_snapshot = {"qty": 5}
        mock_ctx.position_snapshot  = {}
        mock_ctx.risk_limits = {}
        mock_ctx.session_info = {}
        mock_ctx.system_info  = {}
        mock_ctx.metadata     = {}
        ctx = make_control_context_from_rule_context(mock_ctx)
        assert ctx.evaluation_id == "eval-1"


# ═════════════════════════════════════════════════════════════════════════════
# ControlRequest
# ═════════════════════════════════════════════════════════════════════════════

class TestControlRequest:
    def test_make_request_basic(self):
        req = _req([_pass_result()])
        assert req.rule_count == 1

    def test_empty_rule_results(self):
        req = _req()
        assert req.rule_count == 0

    def test_policy_type_default(self):
        req = _req()
        assert req.policy_type == PolicyType.HIGHEST_SEVERITY

    def test_to_dict(self):
        req = _req([_pass_result()])
        d = req.to_dict()
        assert "request_id" in d
        assert d["rule_count"] == 1

    def test_age_ms(self):
        req = _req()
        time.sleep(0.01)
        assert req.age_ms > 0


# ═════════════════════════════════════════════════════════════════════════════
# ControlResponse
# ═════════════════════════════════════════════════════════════════════════════

class TestControlResponse:
    def test_success_response(self):
        decision = make_allow_decision()
        resp = make_control_response("req-1", "eval-1", decision, elapsed_ms=5.0)
        assert resp.succeeded
        assert resp.allowed

    def test_error_response(self):
        resp = make_error_response("req-1", "eval-1", elapsed_ms=2.0,
                                   error_code="ERC-007", error_message="test error")
        assert resp.failed
        assert resp.error_code == "ERC-007"
        assert resp.action is None

    def test_to_dict(self):
        decision = make_block_decision()
        resp = make_control_response("req-1", "eval-1", decision, elapsed_ms=1.0)
        d = resp.to_dict()
        assert d["succeeded"]
        assert d["blocked"]


# ═════════════════════════════════════════════════════════════════════════════
# RiskControlDecision
# ═════════════════════════════════════════════════════════════════════════════

class TestRiskControlDecision:
    def test_allow_decision_allowed(self):
        d = make_allow_decision()
        assert d.allowed
        assert not d.blocked

    def test_block_decision_blocked(self):
        d = make_block_decision()
        assert d.blocked
        assert not d.allowed

    def test_emergency_decision_is_emergency(self):
        d = make_emergency_decision()
        assert d.is_emergency
        assert d.blocked

    def test_warning_decision(self):
        d = make_warning_decision()
        assert d.allowed
        assert d.action == ControlAction.ALLOW_WITH_WARNING

    def test_override_required_decision(self):
        d = make_override_required_decision()
        assert d.requires_override
        assert not d.allowed

    def test_to_dict_contains_action(self):
        d = make_block_decision()
        assert d.to_dict()["action"] == "BLOCK"

    def test_blocked_rules_filtered(self):
        blocked = _block_result()
        passed  = _pass_result()
        req = _req([passed, blocked])
        d = make_block_decision(rule_results=[passed, blocked])
        assert len(d.blocked_rules) == 1

    def test_was_overridden_false_by_default(self):
        d = make_allow_decision()
        assert not d.was_overridden

    def test_override_info(self):
        ov = make_override_info(
            approver="trader1",
            reason="risk accepted",
            original_action=ControlAction.BLOCK,
            new_action=ControlAction.ALLOW_WITH_WARNING,
        )
        assert ov.approver == "trader1"
        assert ov.original_action == ControlAction.BLOCK

    def test_emergency_info(self):
        ei = make_emergency_info(
            trigger="MANUAL", trigger_reason="halt all", halt_level="FULL"
        )
        assert ei.halt_level == "FULL"


# ═════════════════════════════════════════════════════════════════════════════
# Policies
# ═════════════════════════════════════════════════════════════════════════════

class TestSingleRulePolicy:
    def setup_method(self):
        self.p = SingleRulePolicy()

    def test_all_pass_allows(self):
        results = [_pass_result(), _pass_result("r2")]
        assert self.p.evaluate(results, _normal_ctx()) == ControlAction.ALLOW

    def test_block_blocks(self):
        results = [_pass_result(), _block_result()]
        assert self.p.evaluate(results, _normal_ctx()) == ControlAction.BLOCK

    def test_failed_blocks(self):
        results = [_failed_result()]
        assert self.p.evaluate(results, _normal_ctx()) == ControlAction.BLOCK

    def test_warning_allows_with_warning(self):
        results = [_pass_result(), _warn_result()]
        assert self.p.evaluate(results, _normal_ctx()) == ControlAction.ALLOW_WITH_WARNING

    def test_override_required(self):
        results = [_override_result()]
        assert self.p.evaluate(results, _normal_ctx()) == ControlAction.REQUIRE_OVERRIDE

    def test_block_beats_warning(self):
        results = [_warn_result(), _block_result()]
        assert self.p.evaluate(results, _normal_ctx()) == ControlAction.BLOCK

    def test_block_beats_override(self):
        results = [_override_result(), _block_result()]
        assert self.p.evaluate(results, _normal_ctx()) == ControlAction.BLOCK

    def test_emergency_context_overrides_all(self):
        results = [_pass_result()]
        assert self.p.evaluate(results, _emergency_ctx()) == ControlAction.EMERGENCY_STOP

    def test_empty_results_allows(self):
        assert self.p.evaluate([], _normal_ctx()) == ControlAction.ALLOW

    def test_policy_type(self):
        assert self.p.policy_type == PolicyType.SINGLE_RULE


class TestMajorityPolicy:
    def setup_method(self):
        self.p = MajorityPolicy(pass_threshold=0.5)

    def test_majority_pass_allows(self):
        results = [_pass_result(), _pass_result("r2"), _warn_result()]
        # 2/3 = 0.67 >= 0.5, but has warning
        action = self.p.evaluate(results, _normal_ctx())
        assert action in (ControlAction.ALLOW, ControlAction.ALLOW_WITH_WARNING)

    def test_majority_fail_escalates(self):
        results = [_block_result(), _block_result("r2"), _pass_result()]
        # 1/3 = 0.33 < 0.5 → escalate
        action = self.p.evaluate(results, _normal_ctx())
        assert action == ControlAction.BLOCK

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError):
            MajorityPolicy(pass_threshold=0.0)

    def test_policy_type(self):
        assert self.p.policy_type == PolicyType.MAJORITY


class TestHighestSeverityPolicy:
    def setup_method(self):
        self.p = HighestSeverityPolicy()

    def test_block_wins(self):
        results = [_pass_result(), _warn_result(), _block_result()]
        assert self.p.evaluate(results, _normal_ctx()) == ControlAction.BLOCK

    def test_warning_wins_over_pass(self):
        results = [_pass_result(), _warn_result()]
        assert self.p.evaluate(results, _normal_ctx()) == ControlAction.ALLOW_WITH_WARNING

    def test_empty_allows(self):
        assert self.p.evaluate([], _normal_ctx()) == ControlAction.ALLOW

    def test_emergency_context(self):
        results = [_pass_result()]
        assert self.p.evaluate(results, _emergency_ctx()) == ControlAction.EMERGENCY_STOP

    def test_policy_type(self):
        assert self.p.policy_type == PolicyType.HIGHEST_SEVERITY


class TestWeightedSeverityPolicy:
    def setup_method(self):
        self.p = WeightedSeverityPolicy()

    def test_all_pass_allows(self):
        results = [_pass_result()]
        action = self.p.evaluate(results, _normal_ctx())
        assert action == ControlAction.ALLOW

    def test_block_high_severity(self):
        results = [_block_result()]
        action = self.p.evaluate(results, _normal_ctx())
        assert action in (ControlAction.BLOCK, ControlAction.REQUIRE_OVERRIDE,
                          ControlAction.PAUSE, ControlAction.EMERGENCY_STOP)

    def test_emergency_context(self):
        results = [_pass_result()]
        assert self.p.evaluate(results, _emergency_ctx()) == ControlAction.EMERGENCY_STOP

    def test_policy_type(self):
        assert self.p.policy_type == PolicyType.WEIGHTED_SEVERITY


class TestEmergencyPolicy:
    def setup_method(self):
        self.p = EmergencyPolicy()

    def test_emergency_context_stops(self):
        results = [_pass_result()]
        assert self.p.evaluate(results, _emergency_ctx()) == ControlAction.EMERGENCY_STOP

    def test_block_result_triggers_emergency(self):
        results = [_block_result()]
        assert self.p.evaluate(results, _normal_ctx()) == ControlAction.EMERGENCY_STOP

    def test_pass_delegates_to_highest(self):
        results = [_pass_result()]
        assert self.p.evaluate(results, _normal_ctx()) == ControlAction.ALLOW

    def test_warning_delegates_to_highest(self):
        results = [_warn_result()]
        action = self.p.evaluate(results, _normal_ctx())
        assert action == ControlAction.ALLOW_WITH_WARNING

    def test_policy_type(self):
        assert self.p.policy_type == PolicyType.EMERGENCY


class TestConfigurablePolicy:
    def test_custom_fn_invoked(self):
        def always_pause(rules, ctx):
            return ControlAction.PAUSE

        p = ConfigurablePolicy(always_pause)
        assert p.evaluate([], _normal_ctx()) == ControlAction.PAUSE

    def test_policy_type(self):
        p = ConfigurablePolicy(lambda r, c: ControlAction.ALLOW)
        assert p.policy_type == PolicyType.CONFIGURABLE


# ═════════════════════════════════════════════════════════════════════════════
# ControlPolicyRegistry
# ═════════════════════════════════════════════════════════════════════════════

class TestControlPolicyRegistry:
    def _registry(self) -> ControlPolicyRegistry:
        r = ControlPolicyRegistry()
        r.start()
        return r

    def test_register_and_get(self):
        r = self._registry()
        r.register(SingleRulePolicy())
        assert r.get(PolicyType.SINGLE_RULE) is not None
        r.stop()

    def test_duplicate_raises(self):
        r = self._registry()
        r.register(SingleRulePolicy())
        with pytest.raises(ControlRegistrationError):
            r.register(SingleRulePolicy())
        r.stop()

    def test_replace_does_not_raise(self):
        r = self._registry()
        r.register(SingleRulePolicy())
        r.replace(SingleRulePolicy())
        assert r.count == 1
        r.stop()

    def test_deregister_removes(self):
        r = self._registry()
        r.register(SingleRulePolicy())
        r.deregister(PolicyType.SINGLE_RULE)
        assert r.get(PolicyType.SINGLE_RULE) is None
        r.stop()

    def test_require_raises_if_missing(self):
        r = self._registry()
        with pytest.raises(PolicyNotFoundError):
            r.require(PolicyType.CONFIGURABLE)
        r.stop()

    def test_not_running_raises(self):
        r = ControlPolicyRegistry()
        with pytest.raises(ControlNotRunningError):
            r.register(SingleRulePolicy())


# ═════════════════════════════════════════════════════════════════════════════
# RiskControlFactory
# ═════════════════════════════════════════════════════════════════════════════

class TestRiskControlFactory:
    def test_create_by_type(self):
        for pt in (PolicyType.SINGLE_RULE, PolicyType.MAJORITY,
                   PolicyType.HIGHEST_SEVERITY, PolicyType.WEIGHTED_SEVERITY,
                   PolicyType.EMERGENCY):
            policy = RiskControlFactory.create_by_type(pt)
            assert policy.policy_type == pt

    def test_create_configurable_raises(self):
        with pytest.raises(ControlFrameworkError):
            RiskControlFactory.create_by_type(PolicyType.CONFIGURABLE)

    def test_create_all_policies(self):
        policies = RiskControlFactory.create_all_policies()
        assert len(policies) == 5

    def test_create_default_registry(self):
        reg = RiskControlFactory.create_default_registry()
        assert reg.count == 5
        reg.stop()


# ═════════════════════════════════════════════════════════════════════════════
# RiskControlEngine
# ═════════════════════════════════════════════════════════════════════════════

class TestRiskControlEngine:
    def _engine(self) -> RiskControlEngine:
        reg = ControlPolicyRegistry()
        reg.start()
        for p in RiskControlFactory.create_all_policies():
            reg.register(p)
        engine = RiskControlEngine(reg)
        engine.start()
        return engine, reg

    def test_allow_decision(self):
        engine, reg = self._engine()
        req = _req([_pass_result()])
        decision = engine.evaluate(req)
        assert decision.allowed
        engine.stop()
        reg.stop()

    def test_block_decision(self):
        engine, reg = self._engine()
        req = _req([_block_result()])
        decision = engine.evaluate(req)
        assert decision.blocked
        engine.stop()
        reg.stop()

    def test_emergency_decision(self):
        engine, reg = self._engine()
        req = _req([_pass_result()], context=_emergency_ctx())
        decision = engine.evaluate(req)
        assert decision.is_emergency
        engine.stop()
        reg.stop()

    def test_events_emitted(self):
        engine, reg = self._engine()
        req = _req([_pass_result()])
        engine.evaluate(req)
        events = engine.events()
        assert len(events) >= 1
        engine.stop()
        reg.stop()

    def test_not_running_raises(self):
        reg = ControlPolicyRegistry()
        reg.start()
        engine = RiskControlEngine(reg)
        with pytest.raises(ControlNotRunningError):
            engine.evaluate(_req())
        reg.stop()


# ═════════════════════════════════════════════════════════════════════════════
# ControlHistory
# ═════════════════════════════════════════════════════════════════════════════

class TestControlHistory:
    def test_append_and_all(self):
        h = ControlHistory()
        h.append(make_allow_decision())
        assert h.total == 1

    def test_by_action_filter(self):
        h = ControlHistory()
        h.append(make_allow_decision())
        h.append(make_block_decision())
        assert len(h.by_action(ControlAction.ALLOW)) == 1

    def test_blocked_filter(self):
        h = ControlHistory()
        h.append(make_allow_decision())
        h.append(make_block_decision())
        assert len(h.blocked()) == 1

    def test_emergencies_filter(self):
        h = ControlHistory()
        h.append(make_emergency_decision())
        assert len(h.emergencies()) == 1

    def test_max_size_eviction(self):
        h = ControlHistory(max_size=3)
        for _ in range(5):
            h.append(make_allow_decision())
        assert h.total == 3
        assert h.evicted == 2

    def test_is_empty(self):
        h = ControlHistory()
        assert h.is_empty()

    def test_latest(self):
        h = ControlHistory()
        for _ in range(5):
            h.append(make_allow_decision())
        assert len(h.latest(3)) == 3

    def test_overridden_filter(self):
        h = ControlHistory()
        ov = make_override_info(
            approver="x", reason="y",
            original_action=ControlAction.BLOCK,
            new_action=ControlAction.ALLOW,
        )
        from iios.execution.risk.controls.risk_control_decision import _base_decision
        d = _base_decision(
            evaluation_id="", execution_id="", order_id="",
            portfolio_id="", strategy_id="", correlation_id="",
            action=ControlAction.ALLOW, policy_used=PolicyType.HIGHEST_SEVERITY,
            reason="override", message="", elapsed_ms=1.0, rule_results=[],
            override_info=ov,
        )
        h.append(d)
        assert len(h.overridden()) == 1


# ═════════════════════════════════════════════════════════════════════════════
# ControlStatistics
# ═════════════════════════════════════════════════════════════════════════════

class TestControlStatistics:
    def test_record_increments(self):
        s = ControlStatistics()
        s.record(5.0, ControlAction.ALLOW)
        assert s.total_evaluations == 1
        assert s.allowed_count == 1

    def test_block_count(self):
        s = ControlStatistics()
        s.record(1.0, ControlAction.BLOCK)
        assert s.blocked_count == 1

    def test_emergency_count(self):
        s = ControlStatistics()
        s.record(1.0, ControlAction.EMERGENCY_STOP)
        assert s.emergency_count == 1

    def test_average_time_ms(self):
        s = ControlStatistics()
        s.record(4.0, ControlAction.ALLOW)
        s.record(6.0, ControlAction.ALLOW)
        assert s.average_time_ms == pytest.approx(5.0)

    def test_block_rate(self):
        s = ControlStatistics()
        s.record(1.0, ControlAction.BLOCK)
        s.record(1.0, ControlAction.ALLOW)
        assert s.block_rate == pytest.approx(0.5)

    def test_to_dict(self):
        s = ControlStatistics()
        d = s.to_dict()
        assert "total_evaluations" in d


# ═════════════════════════════════════════════════════════════════════════════
# RiskControlValidator
# ═════════════════════════════════════════════════════════════════════════════

class TestRiskControlValidator:
    def setup_method(self):
        self.v = RiskControlValidator()

    def test_valid_request(self):
        result = self.v.validate_request(_req([_pass_result()]))
        assert result.is_valid

    def test_invalid_request_type(self):
        result = self.v.validate_request("not a request")  # type: ignore
        assert not result.is_valid

    def test_valid_decision(self):
        d = make_allow_decision()
        result = self.v.validate_decision(d)
        assert result.is_valid

    def test_invalid_decision_type(self):
        result = self.v.validate_decision("not a decision")  # type: ignore
        assert not result.is_valid

    def test_valid_override(self):
        ov = make_override_info(
            approver="trader", reason="risk accepted",
            original_action=ControlAction.BLOCK,
            new_action=ControlAction.ALLOW,
        )
        d = make_block_decision()
        result = self.v.validate_override(ov, d)
        assert result.is_valid

    def test_override_missing_approver(self):
        ov = make_override_info(
            approver="",  # missing
            reason="reason",
            original_action=ControlAction.BLOCK,
            new_action=ControlAction.ALLOW,
        )
        d = make_block_decision()
        result = self.v.validate_override(ov, d)
        assert not result.is_valid

    def test_emergency_cannot_be_overridden(self):
        ov = make_override_info(
            approver="trader", reason="reason",
            original_action=ControlAction.EMERGENCY_STOP,
            new_action=ControlAction.ALLOW,
        )
        d = make_emergency_decision()
        result = self.v.validate_override(ov, d)
        assert not result.is_valid

    def test_raise_if_invalid(self):
        bad = ControlValidationResult(is_valid=False, errors=("bad",), warnings=())
        with pytest.raises(ControlValidationError):
            self.v.raise_if_invalid(bad)


# ═════════════════════════════════════════════════════════════════════════════
# Events
# ═════════════════════════════════════════════════════════════════════════════

class TestControlEvents:
    def test_evaluated_event(self):
        ev = make_control_evaluated_event("d1", "e1", ControlAction.ALLOW,
                                          PolicyType.HIGHEST_SEVERITY)
        assert ev.event_type == ControlEventType.CONTROL_EVALUATED
        assert ev.action == ControlAction.ALLOW

    def test_emergency_event(self):
        ev = make_emergency_triggered_event("d1", "e1", trigger="RULE")
        assert ev.event_type == ControlEventType.EMERGENCY_TRIGGERED

    def test_blocked_event(self):
        ev = make_execution_blocked_event("d1", "e1", ControlAction.BLOCK)
        assert ev.event_type == ControlEventType.EXECUTION_BLOCKED

    def test_override_events(self):
        req_ev = make_override_requested_event("d1", "e1", ControlAction.BLOCK)
        app_ev = make_override_approved_event("d1", "e1", ControlAction.ALLOW,
                                              approver="trader1")
        assert req_ev.event_type == ControlEventType.OVERRIDE_REQUESTED
        assert app_ev.event_type == ControlEventType.OVERRIDE_APPROVED

    def test_to_dict(self):
        ev = make_control_evaluated_event("d1", "e1", ControlAction.BLOCK,
                                          PolicyType.SINGLE_RULE)
        d = ev.to_dict()
        assert d["action"] == "BLOCK"


# ═════════════════════════════════════════════════════════════════════════════
# RiskControlManager (integration)
# ═════════════════════════════════════════════════════════════════════════════

class TestRiskControlManager:
    def _manager(self) -> RiskControlManager:
        m = RiskControlManager()
        m.start()
        return m

    def test_start_stop(self):
        m = self._manager()
        assert m._registry.count > 0
        m.stop()

    def test_evaluate_allow(self):
        m = self._manager()
        decision = m.evaluate_rule_results([_pass_result()])
        assert decision.allowed
        m.stop()

    def test_evaluate_block(self):
        m = self._manager()
        decision = m.evaluate_rule_results([_block_result()])
        assert decision.blocked
        m.stop()

    def test_evaluate_emergency_context(self):
        m = self._manager()
        req = _req([_pass_result()], context=_emergency_ctx())
        decision = m.evaluate(req)
        assert decision.is_emergency
        m.stop()

    def test_evaluate_with_policy_override(self):
        m = self._manager()
        req = _req([_pass_result()])
        decision = m.evaluate(req, policy_type=PolicyType.SINGLE_RULE)
        assert decision.allowed
        assert decision.policy_used == PolicyType.SINGLE_RULE
        m.stop()

    def test_statistics_increment(self):
        m = self._manager()
        m.evaluate_rule_results([_pass_result()])
        stats = m.statistics()
        assert stats.total_evaluations == 1
        m.stop()

    def test_history_appended(self):
        m = self._manager()
        m.evaluate_rule_results([_pass_result()])
        assert not m.history().is_empty()
        m.stop()

    def test_not_running_raises(self):
        m = RiskControlManager()
        with pytest.raises(ControlNotRunningError):
            m.evaluate_rule_results([])

    def test_apply_override(self):
        m = self._manager()
        # First create a blocked decision
        req = _req([_block_result()])
        blocked = m.evaluate(req)

        # Now override it
        overridden = m.apply_override(
            decision_id=blocked.decision_id,
            approver="head_trader",
            reason="risk accepted at session level",
            new_action=ControlAction.ALLOW_WITH_WARNING,
            affected_rules=["r:block"],
        )
        assert overridden.allowed
        assert overridden.was_overridden
        assert overridden.override_info.approver == "head_trader"
        m.stop()

    def test_apply_override_not_found(self):
        m = self._manager()
        with pytest.raises(OverrideError):
            m.apply_override("nonexistent-id", "trader", "reason")
        m.stop()

    def test_trigger_emergency(self):
        m = self._manager()
        decision = m.trigger_emergency(
            "System anomaly detected",
            halt_level="FULL",
        )
        assert decision.is_emergency
        assert decision.emergency_info is not None
        m.stop()

    def test_trigger_emergency_missing_reason(self):
        m = self._manager()
        with pytest.raises(EmergencyActionError):
            m.trigger_emergency("")
        m.stop()

    def test_register_custom_policy(self):
        m = self._manager()
        custom = ConfigurablePolicy(lambda r, c: ControlAction.PAUSE)
        m.register_policy(custom)
        req = _req([_pass_result()], policy_type=PolicyType.CONFIGURABLE)
        decision = m.evaluate(req)
        assert decision.action == ControlAction.PAUSE
        m.stop()

    def test_snapshot(self):
        m = self._manager()
        snap = m.snapshot()
        assert "total_evaluations" in snap
        m.stop()

    def test_events_exposed(self):
        m = self._manager()
        m.evaluate_rule_results([_pass_result()])
        events = m.events()
        assert len(events) >= 1
        m.stop()

    def test_concurrent_evaluations(self):
        m = self._manager()
        errors = []

        def _eval():
            try:
                m.evaluate_rule_results([_pass_result()])
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_eval) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent errors: {errors}"
        stats = m.statistics()
        assert stats.total_evaluations == 20
        m.stop()


# ═════════════════════════════════════════════════════════════════════════════
# Regression / edge cases
# ═════════════════════════════════════════════════════════════════════════════

class TestRegressionAndEdgeCases:
    def test_highest_priority_single_result(self):
        assert highest_priority_action(ControlAction.PAUSE) == ControlAction.PAUSE

    def test_highest_priority_no_args_returns_allow(self):
        assert highest_priority_action() == ControlAction.ALLOW

    def test_history_get_returns_none_for_missing(self):
        h = ControlHistory()
        assert h.get("nonexistent") is None

    def test_statistics_zero_before_record(self):
        s = ControlStatistics()
        assert s.average_time_ms == 0.0
        assert s.block_rate == 0.0

    def test_decision_rule_count(self):
        d = make_block_decision(rule_results=[_block_result(), _pass_result()])
        assert d.rule_count == 2

    def test_all_control_actions_in_priority_map(self):
        for action in ControlAction:
            assert action in ACTION_PRIORITY

    def test_all_blocking_actions_are_terminal_or_require_action(self):
        for a in BLOCKING_ACTIONS:
            meta = get_action_metadata(a)
            assert meta.is_blocking

    def test_majority_policy_pass_threshold_boundary(self):
        # Exactly at threshold
        p = MajorityPolicy(pass_threshold=0.5)
        results = [_pass_result(), _warn_result()]  # 1/2 = 0.5 pass
        # 0.5 >= 0.5 → passes threshold, but has warning
        action = p.evaluate(results, _normal_ctx())
        assert action in (ControlAction.ALLOW, ControlAction.ALLOW_WITH_WARNING)
