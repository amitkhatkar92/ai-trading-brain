"""
ai_governance_policy_engine.py — iios.supervisor.policies
-----------------------------------------------------------
PRIMARY PUBLIC INTERFACE for the AI Governance Policy Framework.

Responsibilities (this module ONLY):
  - Accept governance evaluation requests via :meth:`evaluate`
  - Wire all governance subsystems
  - Expose policy registration / management
  - Expose health(), statistics(), status() introspection
  - Fire lifecycle audit events and dispatch domain events to listeners

This module MUST NOT:
  - Perform AI reasoning or LLM inference
  - Detect anomalies
  - Perform self-healing
  - Coordinate autonomous agents
  - Execute trades
  - Communicate with brokers

These responsibilities belong to the Autonomous Governance Framework (M4).

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    AI_GOVERNANCE_SYSTEM_ID,
    AIGovernancePolicyAction,
    AIGovernancePolicyEventType,
    DENY_ACTIONS,
    HUMAN_REVIEW_ACTIONS,
    STOP_ACTIONS,
    VERSION,
)
from .exceptions import (
    AIGovernancePolicyEngineNotRunningError,
    AIGovernancePolicyNotFoundError,
)
from .ai_governance_policy import AIGovernancePolicy
from .ai_governance_policy_audit import AIGovernancePolicyAuditGenerator
from .ai_governance_policy_chain import AIGovernancePolicyChain
from .ai_governance_policy_evaluator import AIGovernancePolicyEvaluator
from .ai_governance_policy_events import (
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
)
from .ai_governance_policy_factory import AIGovernancePolicyFactory
from .ai_governance_policy_history import AIGovernancePolicyHistory
from .ai_governance_policy_manager import AIGovernancePolicyManager
from .ai_governance_policy_registry import AIGovernancePolicyRegistry
from .ai_governance_policy_request import AIGovernancePolicyRequest
from .ai_governance_policy_response import AIGovernancePolicyResponse
from .ai_governance_policy_statistics import AIGovernancePolicyStatistics
from .ai_governance_policy_validator import AIGovernancePolicyValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=AI_GOVERNANCE_SYSTEM_ID)


class AIGovernancePolicyEngine(LifecycleAwareMixin):
    """
    Institutional AI Governance Policy Engine.

    Primary entry point: :meth:`evaluate` — accepts an
    :class:`AIGovernancePolicyRequest` and returns an
    :class:`AIGovernancePolicyResponse`.

    All autonomous AI operations across the IIOS platform must pass through
    this engine before execution.  The engine performs NO AI reasoning —
    it evaluates only pre-configured structural governance policies.

    Parameters
    ----------
    registry :   Injected policy registry (optional).
    evaluator :  Injected policy evaluator (optional).
    chain :      Injected policy chain (optional).
    validator :  Injected policy validator (optional).
    statistics : Injected statistics accumulator (optional).
    history :    Injected evaluation history (optional).
    factory :    Injected object factory (optional).
    audit_gen :  Injected audit report generator (optional).
    manager :    Injected evaluation orchestrator (optional).
    """

    def __init__(
        self,
        registry:   Optional[AIGovernancePolicyRegistry]       = None,
        evaluator:  Optional[AIGovernancePolicyEvaluator]      = None,
        chain:      Optional[AIGovernancePolicyChain]           = None,
        validator:  Optional[AIGovernancePolicyValidator]      = None,
        statistics: Optional[AIGovernancePolicyStatistics]     = None,
        history:    Optional[AIGovernancePolicyHistory]        = None,
        factory:    Optional[AIGovernancePolicyFactory]        = None,
        audit_gen:  Optional[AIGovernancePolicyAuditGenerator] = None,
        manager:    Optional[AIGovernancePolicyManager]        = None,
    ) -> None:
        super().__init__()

        self._registry   = registry   or AIGovernancePolicyRegistry()
        self._evaluator  = evaluator  or AIGovernancePolicyEvaluator()
        self._chain      = chain      or AIGovernancePolicyChain(self._evaluator)
        self._validator  = validator  or AIGovernancePolicyValidator()
        self._stats      = statistics or AIGovernancePolicyStatistics()
        self._hist       = history    or AIGovernancePolicyHistory()
        self._factory    = factory    or AIGovernancePolicyFactory()
        self._audit_gen  = audit_gen  or AIGovernancePolicyAuditGenerator()
        self._manager    = manager    or AIGovernancePolicyManager(
            registry   = self._registry,
            evaluator  = self._evaluator,
            chain      = self._chain,
            validator  = self._validator,
            statistics = self._stats,
            history    = self._hist,
            factory    = self._factory,
            audit_gen  = self._audit_gen,
        )

        self._listeners:     List[Callable] = []
        self._listener_lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # LifecycleAwareMixin hooks
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            AI_GOVERNANCE_SYSTEM_ID, "stopped", "running", VERSION, actor=ACTOR_SYSTEM
        )
        event = make_engine_started_event()
        self._hist.record_event(event)
        self._notify_listeners(event)
        _log.info(f"AIGovernancePolicyEngine started (version={VERSION})")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            AI_GOVERNANCE_SYSTEM_ID, "running", "stopped", VERSION, actor=ACTOR_SYSTEM
        )
        event = make_engine_stopped_event()
        self._hist.record_event(event)
        self._notify_listeners(event)
        _log.info("AIGovernancePolicyEngine stopped")

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise AIGovernancePolicyEngineNotRunningError()

    # ------------------------------------------------------------------
    # Primary evaluation interface
    # ------------------------------------------------------------------

    def evaluate(
        self, request: AIGovernancePolicyRequest
    ) -> AIGovernancePolicyResponse:
        """
        Evaluate a governance policy request.

        The engine dispatches domain events based on the final action:
        - APPROVE / APPROVE_WITH_CONDITIONS → GovernanceApproved
        - REJECT                            → GovernanceRejected
        - BLOCK                             → GovernanceBlocked
        - REQUIRE_HUMAN_APPROVAL            → HumanApprovalRequested
        - EMERGENCY_STOP                    → EmergencyStopTriggered
        - Other                             → GovernanceCompleted

        Parameters
        ----------
        request : AIGovernancePolicyRequest

        Returns
        -------
        AIGovernancePolicyResponse — always returns, never raises.

        Raises
        ------
        AIGovernancePolicyEngineNotRunningError
            When the engine has not been started.
        """
        self._assert_running()

        started_event = make_evaluation_started_event(
            request.supervision_id,
            request_id    = request.request_id,
            workflow_type = request.workflow_type,
        )
        self._hist.record_event(started_event)
        self._notify_listeners(started_event)

        response = self._manager.run_evaluation(request)

        # Dispatch domain-specific event based on final action
        action = response.final_action
        if action in STOP_ACTIONS:
            domain_event = make_emergency_stop_triggered_event(
                request.supervision_id,
                request_id          = request.request_id,
                dominant_policy_id  = response.summary.dominant_policy_id,
                rationale           = response.summary.rationale,
            )
        elif action == AIGovernancePolicyAction.REJECT:
            domain_event = make_governance_rejected_event(
                request.supervision_id,
                request_id         = request.request_id,
                dominant_policy_id = response.summary.dominant_policy_id,
                rationale          = response.summary.rationale,
            )
        elif action == AIGovernancePolicyAction.BLOCK:
            domain_event = make_governance_blocked_event(
                request.supervision_id,
                request_id         = request.request_id,
                dominant_policy_id = response.summary.dominant_policy_id,
                rationale          = response.summary.rationale,
            )
        elif action in HUMAN_REVIEW_ACTIONS:
            domain_event = make_human_approval_requested_event(
                request.supervision_id,
                request_id         = request.request_id,
                dominant_policy_id = response.summary.dominant_policy_id,
                rationale          = response.summary.rationale,
            )
        else:
            domain_event = make_governance_approved_event(
                request.supervision_id,
                request_id         = request.request_id,
                final_action       = action.value,
                policies_evaluated = response.policies_evaluated,
            )

        self._hist.record_event(domain_event)
        self._notify_listeners(domain_event)

        completed_event = make_evaluation_completed_event(
            request.supervision_id,
            request_id   = request.request_id,
            final_action = action.value,
            elapsed_s    = response.evaluation_elapsed_s,
            is_success   = response.is_success,
        )
        self._hist.record_event(completed_event)
        self._notify_listeners(completed_event)

        return response

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def register_policy(self, policy: AIGovernancePolicy) -> None:
        """Register a governance policy."""
        self._registry.register(policy)
        event = make_policy_loaded_event(
            policy_id   = policy.policy_id,
            policy_name = policy.name,
            policy_type = policy.policy_type.value,
        )
        self._hist.record_event(event)
        self._notify_listeners(event)
        _log.info(f"Governance policy registered: {policy.name} ({policy.policy_id})")

    def unregister_policy(self, policy_id: str) -> None:
        """Unregister a governance policy."""
        self._registry.unregister(policy_id)
        _log.info(f"Governance policy unregistered: {policy_id}")

    def get_policy(self, policy_id: str) -> AIGovernancePolicy:
        """Return a registered policy by ID."""
        return self._registry.get(policy_id)

    def enable_policy(self, policy_id: str) -> None:
        """Enable a registered policy."""
        self._registry.enable(policy_id)

    def disable_policy(self, policy_id: str) -> None:
        """Disable a registered policy."""
        self._registry.disable(policy_id)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        return {
            "status":              self.lifecycle_state().value,
            "policies_registered": self._registry.count,
            "policies_enabled":    self._registry.enabled_count,
        }

    def statistics(self) -> Dict[str, Any]:
        return self._stats.snapshot()

    def status(self) -> Dict[str, Any]:
        return {
            "engine_id":  AI_GOVERNANCE_SYSTEM_ID,
            "version":    VERSION,
            "lifecycle":  self.lifecycle_state().value,
            "health":     self.health(),
            "statistics": self._stats.snapshot(),
            "history":    self._hist.counts(),
        }

    # ------------------------------------------------------------------
    # Listener management
    # ------------------------------------------------------------------

    def add_listener(self, fn: Callable) -> None:
        """Register an event listener function."""
        with self._listener_lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable) -> None:
        """Unregister an event listener function."""
        with self._listener_lock:
            try:
                self._listeners.remove(fn)
            except ValueError:
                pass

    def _notify_listeners(self, event: object) -> None:
        with self._listener_lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:  # pylint: disable=broad-except
                pass
