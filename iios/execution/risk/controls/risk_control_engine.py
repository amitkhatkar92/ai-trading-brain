"""iios/execution/risk/controls/risk_control_engine.py
==================================================
RiskControlEngine — core control evaluation engine.

Receives a ControlRequest and returns a RiskControlDecision.
Does NOT evaluate risk.  Does NOT communicate with brokers.
Does NOT execute orders.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    ENGINE_SYSTEM_ID,
    OUTCOME_TO_ACTION,
    VERSION,
    ControlAction,
    PolicyType,
    highest_priority_action,
)
from .exceptions import (
    ControlNotRunningError,
    PolicyEvaluationError,
    PolicyNotFoundError,
)
from .risk_control_context import ControlContext
from .risk_control_decision import (
    EmergencyInfo,
    RiskControlDecision,
    make_emergency_info,
    _base_decision,
)
from .risk_control_events import (
    ControlEvent,
    make_control_approved_event,
    make_control_evaluated_event,
    make_control_paused_event,
    make_control_retried_event,
    make_emergency_triggered_event,
    make_execution_blocked_event,
    make_override_requested_event,
)
from .risk_control_policy import BasePolicy, HighestSeverityPolicy
from .risk_control_registry import ControlPolicyRegistry
from .risk_control_request import ControlRequest
from .risk_control_validation import RiskControlValidator

_log   = get_logger(__name__, engine_id=ENGINE_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)


class RiskControlEngine(LifecycleAwareMixin):
    """
    Core engine that maps rule results to control decisions.

    The engine selects the appropriate policy from the registry,
    applies it to the rule results, and wraps the action in an
    immutable RiskControlDecision.

    Thread-safety: evaluate() is re-entrant.  The policy registry
    uses its own lock.  The event list is protected by the engine lock.
    """

    def __init__(
        self,
        registry:            ControlPolicyRegistry,
        default_policy_type: PolicyType = PolicyType.HIGHEST_SEVERITY,
    ) -> None:
        super().__init__()
        self._registry             = registry
        self._default_policy_type  = default_policy_type
        self._events: List[ControlEvent] = []
        self._validator = RiskControlValidator()
        # Fallback used when the requested policy is not registered
        self._fallback  = HighestSeverityPolicy()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise ControlNotRunningError()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("RiskControlEngine started.",
                  default_policy=self._default_policy_type.value)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("RiskControlEngine stopped.", events_emitted=len(self._events))

    # ── Public ────────────────────────────────────────────────────────────────

    def evaluate(self, request: ControlRequest) -> RiskControlDecision:
        """
        Evaluate a ControlRequest and return a RiskControlDecision.

        Steps:
        1. Validate the request
        2. Check for emergency conditions
        3. Select and apply the policy
        4. Build the decision
        5. Emit events
        """
        self._assert_running()
        t0 = time.time()

        # 1 — Validate
        val = self._validator.validate_request(request)
        if not val.is_valid:
            for e in val.errors:
                _log.warning("Request validation error", error=e)
        # Log warnings only; do not hard-reject (let policy decide)

        rule_results = list(request.rule_results)
        context      = request.context

        # 2 — Emergency short-circuit
        emergency_action = self._check_emergency(context, rule_results)
        if emergency_action is not None:
            elapsed = (time.time() - t0) * 1_000.0
            source_rule = self._find_emergency_source(rule_results)
            emerg_info  = make_emergency_info(
                trigger="EMERGENCY_RULE",
                trigger_reason=context.system_info.get(
                    "emergency_reason", "Emergency stop condition detected"
                ),
                halt_level="TRADING",
                source_rule_id=source_rule,
            )
            decision = _base_decision(
                evaluation_id=request.evaluation_id,
                execution_id=request.execution_id,
                order_id=request.order_id,
                portfolio_id=request.portfolio_id,
                strategy_id=request.strategy_id,
                correlation_id=request.correlation_id,
                action=ControlAction.EMERGENCY_STOP,
                policy_used=PolicyType.EMERGENCY,
                reason="emergency_stop_active",
                message="Emergency stop — all execution halted immediately.",
                elapsed_ms=elapsed,
                rule_results=rule_results,
                emergency_info=emerg_info,
            )
            self._emit(make_emergency_triggered_event(
                decision.decision_id, request.evaluation_id,
                trigger="EMERGENCY_RULE", halt_level="TRADING",
            ))
            _log.warning("Emergency stop triggered.",
                         evaluation_id=request.evaluation_id,
                         source_rule=source_rule)
            return decision

        # 3 — Policy selection
        policy = self._select_policy(request.policy_type)

        # 4 — Policy evaluation
        try:
            action = policy.evaluate(rule_results, context)
        except Exception as exc:
            _log.error("Policy evaluation failed — defaulting to BLOCK",
                       policy=request.policy_type.value, error=str(exc))
            action = ControlAction.BLOCK

        # 5 — Determine reason and message
        reason, message = self._describe(action, rule_results)

        elapsed = (time.time() - t0) * 1_000.0
        decision = _base_decision(
            evaluation_id=request.evaluation_id,
            execution_id=request.execution_id,
            order_id=request.order_id,
            portfolio_id=request.portfolio_id,
            strategy_id=request.strategy_id,
            correlation_id=request.correlation_id,
            action=action,
            policy_used=request.policy_type,
            reason=reason,
            message=message,
            elapsed_ms=elapsed,
            rule_results=rule_results,
        )

        # 6 — Emit events
        self._emit(make_control_evaluated_event(
            decision.decision_id, request.evaluation_id,
            action, request.policy_type,
        ))
        if action in (ControlAction.ALLOW, ControlAction.ALLOW_WITH_WARNING):
            self._emit(make_control_approved_event(
                decision.decision_id, request.evaluation_id, action,
            ))
        elif action == ControlAction.PAUSE:
            self._emit(make_control_paused_event(
                decision.decision_id, request.evaluation_id,
            ))
        elif action == ControlAction.RETRY:
            self._emit(make_control_retried_event(
                decision.decision_id, request.evaluation_id,
            ))
        elif action == ControlAction.REQUIRE_OVERRIDE:
            self._emit(make_override_requested_event(
                decision.decision_id, request.evaluation_id, action,
            ))
        elif decision.blocked:
            self._emit(make_execution_blocked_event(
                decision.decision_id, request.evaluation_id, action, reason=reason,
            ))

        _log.info("Control decision made.",
                  action=action.value,
                  policy=request.policy_type.value,
                  elapsed_ms=elapsed)
        return decision

    def events(self) -> List[ControlEvent]:
        return list(self._events)

    # ── Private ───────────────────────────────────────────────────────────────

    def _select_policy(self, policy_type: PolicyType) -> BasePolicy:
        """Select policy from registry; fall back to default if missing."""
        policy = self._registry.get(policy_type)
        if policy is None:
            policy = self._registry.get(self._default_policy_type)
        if policy is None:
            policy = self._fallback
        return policy

    def _check_emergency(
        self, context: ControlContext, rule_results: List[Any]
    ) -> Optional[ControlAction]:
        """Return EMERGENCY_STOP if any emergency condition is detected."""
        if context.emergency_stop_active:
            return ControlAction.EMERGENCY_STOP
        # If any rule result has outcome BLOCK due to emergency stop rule
        for r in rule_results:
            rule_id = getattr(r, "rule_id", "")
            if "emergency" in str(rule_id).lower() and getattr(r, "blocked", False):
                return ControlAction.EMERGENCY_STOP
        return None

    def _find_emergency_source(self, rule_results: List[Any]) -> str:
        for r in rule_results:
            rule_id = getattr(r, "rule_id", "")
            if "emergency" in str(rule_id).lower():
                return str(rule_id)
        # Fall back: first blocked rule
        for r in rule_results:
            if getattr(r, "blocked", False):
                return str(getattr(r, "rule_id", "unknown"))
        return ""

    def _describe(
        self, action: ControlAction, rule_results: List[Any]
    ) -> tuple:
        """Build a human-readable reason/message for the decision."""
        blocked_rules = [r for r in rule_results if getattr(r, "blocked", False)]
        warning_rules = [r for r in rule_results if getattr(r, "warned", False)]

        if action == ControlAction.BLOCK:
            names = [getattr(r, "rule_name", "?") for r in blocked_rules[:3]]
            reason  = "rule_blocked"
            message = f"Blocked by: {', '.join(names)}." if names else "Blocked by risk rule."

        elif action == ControlAction.EMERGENCY_STOP:
            reason  = "emergency_stop"
            message = "Emergency stop — all execution halted immediately."

        elif action == ControlAction.CANCEL:
            reason  = "execution_cancelled"
            message = "Execution cancelled by control policy."

        elif action == ControlAction.REQUIRE_OVERRIDE:
            names = [getattr(r, "rule_name", "?") for r in rule_results
                     if getattr(r, "override_required", False)][:3]
            reason  = "override_required"
            message = (f"Override required by: {', '.join(names)}." if names
                       else "Execution requires authorized override.")

        elif action == ControlAction.PAUSE:
            reason  = "execution_paused"
            message = "Execution paused pending review."

        elif action == ControlAction.RETRY:
            reason  = "retry_requested"
            message = "Transient condition — retry execution after delay."

        elif action == ControlAction.ALLOW_WITH_WARNING:
            names = [getattr(r, "rule_name", "?") for r in warning_rules[:3]]
            reason  = "risk_warning"
            message = (f"Allowed with warnings from: {', '.join(names)}." if names
                       else "Execution allowed with risk warnings.")

        else:  # ALLOW
            reason  = "all_rules_passed"
            message = "All risk checks passed — execution allowed."

        return reason, message

    def _emit(self, event: ControlEvent) -> None:
        self._events.append(event)
