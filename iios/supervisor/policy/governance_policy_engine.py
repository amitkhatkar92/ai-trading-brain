"""
governance_policy_engine.py — iios.supervisor.policy
------------------------------------------------------
PRIMARY PUBLIC INTERFACE for the AI Governance Policy Framework.

Responsibilities (this module ONLY):
  - Accept governance policy evaluation requests via evaluate()
  - Wire all policy subsystems
  - Expose register_policy / unregister_policy / get_policy management
  - Expose health(), status(), statistics() introspection
  - Fire lifecycle audit events and dispatch domain events to listeners

This module NEVER:
  - Makes trading decisions
  - Executes trades
  - Communicates with brokers
  - Performs autonomous governance (M4 responsibility)

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
    POLICY_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    GovernancePolicyEngineNotRunningError,
    GovernancePolicyNotFoundError,
)
from .governance_policy import GovernancePolicy
from .governance_policy_chain import GovernancePolicyChain
from .governance_policy_evaluator import GovernancePolicyEvaluator
from .governance_policy_events import (
    make_engine_started_event,
    make_engine_stopped_event,
    make_evaluation_completed_event,
    make_evaluation_started_event,
    make_policy_registered_event,
    make_policy_unregistered_event,
)
from .governance_policy_factory import GovernancePolicyFactory
from .governance_policy_history import GovernancePolicyHistory
from .governance_policy_manager import GovernancePolicyManager
from .governance_policy_registry import GovernancePolicyRegistry
from .governance_policy_request import GovernancePolicyRequest
from .governance_policy_response import GovernancePolicyResponse
from .governance_policy_statistics import GovernancePolicyStatistics
from .governance_policy_validation import GovernancePolicyValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=POLICY_SYSTEM_ID)


class GovernancePolicyEngine(LifecycleAwareMixin):
    """
    Institutional AI Governance Policy Engine.

    Primary entry point: :meth:`evaluate` — accepts a
    :class:`GovernancePolicyRequest` and returns a
    :class:`GovernancePolicyResponse`.

    Parameters
    ----------
    registry :   Injected policy registry (optional).
    evaluator :  Injected policy evaluator (optional).
    chain :      Injected policy chain (optional).
    validator :  Injected policy validator (optional).
    statistics : Injected statistics (optional).
    history :    Injected history (optional).
    factory :    Injected factory (optional).
    manager :    Injected evaluation manager (optional).
    """

    def __init__(
        self,
        registry:   Optional[GovernancePolicyRegistry]   = None,
        evaluator:  Optional[GovernancePolicyEvaluator]  = None,
        chain:      Optional[GovernancePolicyChain]      = None,
        validator:  Optional[GovernancePolicyValidator]  = None,
        statistics: Optional[GovernancePolicyStatistics] = None,
        history:    Optional[GovernancePolicyHistory]    = None,
        factory:    Optional[GovernancePolicyFactory]    = None,
        manager:    Optional[GovernancePolicyManager]    = None,
    ) -> None:
        super().__init__()

        self._registry   = registry   or GovernancePolicyRegistry()
        self._evaluator  = evaluator  or GovernancePolicyEvaluator()
        self._chain      = chain      or GovernancePolicyChain(self._evaluator)
        self._validator  = validator  or GovernancePolicyValidator()
        self._stats      = statistics or GovernancePolicyStatistics()
        self._hist       = history    or GovernancePolicyHistory()
        self._factory    = factory    or GovernancePolicyFactory()
        self._manager    = manager    or GovernancePolicyManager(
            registry   = self._registry,
            evaluator  = self._evaluator,
            chain      = self._chain,
            validator  = self._validator,
            statistics = self._stats,
            history    = self._hist,
            factory    = self._factory,
        )

        self._listeners:     List[Callable] = []
        self._listener_lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # LifecycleAwareMixin hooks
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            POLICY_SYSTEM_ID, "stopped", "running", VERSION, actor=ACTOR_SYSTEM
        )
        event = make_engine_started_event()
        self._hist.record_event(event)
        self._notify_listeners(event)
        _log.info(f"GovernancePolicyEngine started (version={VERSION})")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            POLICY_SYSTEM_ID, "running", "stopped", VERSION, actor=ACTOR_SYSTEM
        )
        event = make_engine_stopped_event()
        self._hist.record_event(event)
        self._notify_listeners(event)
        _log.info("GovernancePolicyEngine stopped")

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise GovernancePolicyEngineNotRunningError()

    # ------------------------------------------------------------------
    # Primary evaluation interface
    # ------------------------------------------------------------------

    def evaluate(
        self, request: GovernancePolicyRequest
    ) -> GovernancePolicyResponse:
        """
        Evaluate a governance policy request.

        Parameters
        ----------
        request :
            Fully constructed :class:`GovernancePolicyRequest`.

        Returns
        -------
        GovernancePolicyResponse
            Always returns — never raises.

        Raises
        ------
        GovernancePolicyEngineNotRunningError
            When the engine has not been started.
        """
        self._assert_running()

        started_event = make_evaluation_started_event(
            request.supervision_id, request_id=request.request_id
        )
        self._hist.record_event(started_event)
        self._notify_listeners(started_event)

        response = self._manager.run_evaluation(request)

        completed_event = make_evaluation_completed_event(
            request.supervision_id,
            request_id   = request.request_id,
            final_action = response.final_action.value,
            elapsed_s    = response.evaluation_elapsed_s,
        )
        self._hist.record_event(completed_event)
        self._notify_listeners(completed_event)

        return response

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def register_policy(self, policy: GovernancePolicy) -> None:
        """Register a governance policy."""
        self._registry.register(policy)
        event = make_policy_registered_event(
            policy_id   = policy.policy_id,
            policy_name = policy.name,
        )
        self._hist.record_event(event)
        self._notify_listeners(event)
        _log.info(f"Policy registered: {policy.name} ({policy.policy_id})")

    def unregister_policy(self, policy_id: str) -> None:
        """Unregister a governance policy."""
        self._registry.unregister(policy_id)
        event = make_policy_unregistered_event(policy_id=policy_id)
        self._hist.record_event(event)
        self._notify_listeners(event)
        _log.info(f"Policy unregistered: {policy_id}")

    def get_policy(self, policy_id: str) -> GovernancePolicy:
        """Return a registered policy by ID."""
        return self._registry.get(policy_id)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        return {
            "status":             self.lifecycle_state().value,
            "policies_registered": self._registry.count,
            "policies_enabled":   self._registry.enabled_count,
        }

    def statistics(self) -> Dict[str, Any]:
        return self._stats.snapshot()

    def status(self) -> Dict[str, Any]:
        return {
            "engine_id":   POLICY_SYSTEM_ID,
            "version":     VERSION,
            "lifecycle":   self.lifecycle_state().value,
            "health":      self.health(),
            "statistics":  self._stats.snapshot(),
            "history":     self._hist.counts(),
        }

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    def add_listener(self, fn: Callable) -> None:
        with self._listener_lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable) -> None:
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
