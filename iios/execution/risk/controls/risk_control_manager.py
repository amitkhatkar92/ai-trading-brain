"""iios/execution/risk/controls/risk_control_manager.py
==================================================
RiskControlManager — LifecycleAwareMixin high-level coordinator.

The manager is the single public interface for the Controls Framework.
It owns the engine, registry, statistics, history, and events.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

import copy
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    DEFAULT_DECISION_TIMEOUT_MS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    MANAGER_SYSTEM_ID,
    VERSION,
    ControlAction,
    PolicyType,
)
from .exceptions import (
    ControlNotRunningError,
    EmergencyActionError,
    OverrideError,
)
from .risk_control_context import ControlContext, make_control_context
from .risk_control_decision import (
    EmergencyInfo,
    OverrideInfo,
    RiskControlDecision,
    _base_decision,
    make_emergency_info,
    make_override_info,
)
from .risk_control_engine import RiskControlEngine
from .risk_control_events import (
    ControlEvent,
    make_emergency_triggered_event,
    make_override_approved_event,
    make_override_requested_event,
)
from .risk_control_factory import RiskControlFactory
from .risk_control_history import ControlHistory
from .risk_control_policy import BasePolicy
from .risk_control_registry import ControlPolicyRegistry
from .risk_control_request import ControlRequest, make_control_request
from .risk_control_statistics import ControlStatistics
from .risk_control_validation import RiskControlValidator

_log   = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID)


class RiskControlManager(LifecycleAwareMixin):
    """
    High-level coordinator for the Execution Risk Controls Framework.

    Responsibilities
    ----------------
    - Register / deregister control policies
    - Route ControlRequests to RiskControlEngine
    - Apply authorized overrides
    - Trigger emergency actions
    - Accumulate statistics and history
    - Emit and expose domain events

    Non-responsibilities
    --------------------
    - Does NOT evaluate risk
    - Does NOT execute or cancel orders
    - Does NOT communicate with brokers
    - Does NOT modify rule outcomes

    Thread safety
    -------------
    All public methods are thread-safe.
    """

    def __init__(
        self,
        max_history:         int   = DEFAULT_MAX_HISTORY,
        default_policy_type: PolicyType = PolicyType.HIGHEST_SEVERITY,
        timeout_ms:          float = DEFAULT_DECISION_TIMEOUT_MS,
    ) -> None:
        super().__init__()
        self._default_policy_type = default_policy_type

        self._registry   = ControlPolicyRegistry()
        self._engine     = RiskControlEngine(self._registry, default_policy_type)
        self._statistics = ControlStatistics()
        self._history    = ControlHistory(max_size=max_history)
        self._events:    List[ControlEvent] = []
        self._lock       = threading.Lock()
        self._validator  = RiskControlValidator()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise ControlNotRunningError()

    def _on_start(self) -> None:
        self._registry.start()
        self._engine.start()

        # Pre-populate with all built-in policies
        for policy in RiskControlFactory.create_all_policies():
            self._registry.register(policy)

        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("RiskControlManager started.",
                  default_policy=self._default_policy_type.value,
                  policies_registered=self._registry.count)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("RiskControlManager stopped.",
                  total_evaluations=self._statistics.total_evaluations)
        self._engine.stop()
        self._registry.stop()

    # ── Policy management ─────────────────────────────────────────────────────

    def register_policy(self, policy: BasePolicy) -> None:
        """Register a custom policy (replaces existing same type)."""
        self._assert_running()
        self._registry.replace(policy)

    def deregister_policy(self, policy_type: PolicyType) -> None:
        """Remove a policy from the registry."""
        self._assert_running()
        self._registry.deregister(policy_type)

    # ── Evaluation ────────────────────────────────────────────────────────────

    def evaluate(
        self,
        request:       ControlRequest,
        *,
        policy_type:   Optional[PolicyType] = None,
    ) -> RiskControlDecision:
        """
        Evaluate a ControlRequest and return a RiskControlDecision.

        Parameters
        ----------
        request     : ControlRequest
        policy_type : Override the request's policy_type (optional).
        """
        self._assert_running()

        # Apply policy override if supplied
        if policy_type is not None and policy_type != request.policy_type:
            from dataclasses import replace
            request = replace(request, policy_type=policy_type)

        t0 = time.time()
        decision = self._engine.evaluate(request)
        elapsed  = (time.time() - t0) * 1_000.0

        # Accumulate statistics (thread-safe)
        with self._lock:
            self._statistics.record(
                elapsed,
                decision.action,
                request.policy_type.value,
            )
            # Absorb engine events
            self._events.extend(self._engine.events())
            self._engine._events.clear()

        self._history.append(decision)
        return decision

    def evaluate_rule_results(
        self,
        rule_results,
        *,
        evaluation_id: str = "",
        execution_id:  str = "",
        order_id:      str = "",
        portfolio_id:  str = "",
        strategy_id:   str = "",
        correlation_id: str = "",
        policy_type:   PolicyType | None = None,
        context_kw:    Dict[str, Any] | None = None,
    ) -> RiskControlDecision:
        """
        Convenience method: builds a ControlRequest from raw rule results
        and evaluates it.
        """
        self._assert_running()
        ctx = make_control_context(
            evaluation_id=evaluation_id,
            execution_id=execution_id,
            order_id=order_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            correlation_id=correlation_id,
            **(context_kw or {}),
        )
        req = make_control_request(
            rule_results=rule_results,
            context=ctx,
            evaluation_id=evaluation_id,
            execution_id=execution_id,
            order_id=order_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            correlation_id=correlation_id,
            policy_type=policy_type or self._default_policy_type,
        )
        return self.evaluate(req)

    # ── Override workflow ─────────────────────────────────────────────────────

    def apply_override(
        self,
        decision_id:    str,
        approver:       str,
        reason:         str,
        new_action:     ControlAction = ControlAction.ALLOW_WITH_WARNING,
        affected_rules: Optional[List[str]] = None,
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> RiskControlDecision:
        """
        Apply an authorized override to a previously blocked decision.

        Looks the decision up in history, validates the override, creates
        a new decision with the override applied, and stores it.

        Parameters
        ----------
        decision_id   : The decision_id of the target decision.
        approver      : Human approver identifier.
        reason        : Written justification for the override.
        new_action    : Action to replace the original (default ALLOW_WITH_WARNING).
        affected_rules: Rule IDs that the override covers.
        """
        self._assert_running()

        original = self._history.get(decision_id)
        if original is None:
            raise OverrideError(
                f"Decision '{decision_id}' not found in history",
                override_id="",
            )

        override_info = make_override_info(
            approver=approver,
            reason=reason,
            original_action=original.action,
            new_action=new_action,
            affected_rule_ids=affected_rules or [],
            metadata=metadata,
        )

        # Validate the override
        val = self._validator.validate_override(override_info, original)
        self._validator.raise_if_invalid(val, "apply_override")

        t0 = time.time()
        overridden = _base_decision(
            evaluation_id=original.evaluation_id,
            execution_id=original.execution_id,
            order_id=original.order_id,
            portfolio_id=original.portfolio_id,
            strategy_id=original.strategy_id,
            correlation_id=original.correlation_id,
            action=new_action,
            policy_used=original.policy_used,
            reason="override_applied",
            message=f"Decision overridden by '{approver}': {reason}",
            elapsed_ms=(time.time() - t0) * 1_000.0,
            rule_results=original.rule_results,
            override_info=override_info,
        )

        self._history.append(overridden)

        event = make_override_approved_event(
            overridden.decision_id,
            overridden.evaluation_id,
            new_action,
            approver=approver,
            override_id=override_info.override_id,
        )
        with self._lock:
            self._events.append(event)
            self._statistics.record(0.0, new_action, "OVERRIDE")

        _log.info("Override applied.",
                  original_action=original.action.value,
                  new_action=new_action.value,
                  approver=approver)
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID,
            EngineState.RUNNING,
            EngineState.RUNNING,
            VERSION,
        )
        return overridden

    # ── Emergency workflow ────────────────────────────────────────────────────

    def trigger_emergency(
        self,
        reason:         str,
        halt_level:     str = "TRADING",
        trigger:        str = "MANUAL_HALT",
        *,
        evaluation_id:  str = "",
        execution_id:   str = "",
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> RiskControlDecision:
        """
        Trigger an immediate emergency stop.

        Produces an EMERGENCY_STOP decision that bypasses normal policy
        evaluation.  Records statistics and history.
        """
        self._assert_running()

        if not reason:
            raise EmergencyActionError("reason is required for emergency stop")

        emerg_info = make_emergency_info(
            trigger=trigger,
            trigger_reason=reason,
            halt_level=halt_level,
        )

        t0       = time.time()
        decision = _base_decision(
            evaluation_id=evaluation_id,
            execution_id=execution_id,
            order_id="",
            portfolio_id="",
            strategy_id="",
            correlation_id="",
            action=ControlAction.EMERGENCY_STOP,
            policy_used=PolicyType.EMERGENCY,
            reason="manual_emergency_stop",
            message=f"Manual emergency stop: {reason}",
            elapsed_ms=(time.time() - t0) * 1_000.0,
            rule_results=[],
            emergency_info=emerg_info,
            metadata=metadata,
        )

        self._history.append(decision)

        event = make_emergency_triggered_event(
            decision.decision_id, evaluation_id,
            trigger=trigger, halt_level=halt_level,
        )
        with self._lock:
            self._events.append(event)
            self._statistics.record(0.0, ControlAction.EMERGENCY_STOP, "EMERGENCY")

        _log.warning("Emergency stop triggered manually.",
                     reason=reason, halt_level=halt_level)
        return decision

    # ── Observability ─────────────────────────────────────────────────────────

    def statistics(self) -> ControlStatistics:
        """Return a shallow copy of current statistics."""
        with self._lock:
            return copy.copy(self._statistics)

    def history(self) -> ControlHistory:
        return self._history

    def events(self) -> List[ControlEvent]:
        with self._lock:
            return list(self._events)

    def registry(self) -> ControlPolicyRegistry:
        return self._registry

    def snapshot(self) -> Dict[str, Any]:
        """Return a lightweight status snapshot."""
        stats = self.statistics()
        return {
            "policy_count":      self._registry.count,
            "history_count":     len(self._history),
            "total_evaluations": stats.total_evaluations,
            "blocked_count":     stats.blocked_count,
            "emergency_count":   stats.emergency_count,
            "average_time_ms":   stats.average_time_ms,
        }
