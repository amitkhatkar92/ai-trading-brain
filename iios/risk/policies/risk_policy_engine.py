"""
risk_policy_engine.py — iios.risk.policies
============================================
Primary public interface for the Risk Policy Framework.

Wraps all subsystems behind the LifecycleAwareMixin and exposes the
canonical ``evaluate()`` entry point.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import dataclasses
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import POLICY_SYSTEM_ID, VERSION, PolicyType
from .exceptions import RiskPolicyEngineNotRunningError
from .risk_policy import RiskPolicy
from .risk_policy_audit import RiskPolicyAuditor
from .risk_policy_chain import RiskPolicyChain
from .risk_policy_evaluator import RiskPolicyEvaluator
from .risk_policy_events import (
    make_evaluation_completed,
    make_evaluation_started,
)
from .risk_policy_factory import RiskPolicyFactory
from .risk_policy_history import RiskPolicyHistory
from .risk_policy_manager import RiskPolicyManager
from .risk_policy_registry import RiskPolicyRegistry
from .risk_policy_request import RiskPolicyRequest
from .risk_policy_response import RiskPolicyResponse
from .risk_policy_statistics import RiskPolicyStatistics
from .risk_policy_validator import RiskPolicyValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=POLICY_SYSTEM_ID)


# ---------------------------------------------------------------------------
# Engine status value object
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class RiskPolicyEngineStatus:
    """Snapshot of engine state at a point in time."""
    engine_id:          str
    state:              str
    policies_registered: int
    policies_enabled:   int
    statistics:         Dict[str, Any]
    health:             Dict[str, Any]
    started_at:         float
    framework_version:  str = VERSION


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class RiskPolicyEngine(LifecycleAwareMixin):
    """
    Institutional Risk Policy Engine — primary public interface.

    Wires together all Risk Policy subsystems and provides the single
    entry point ``evaluate()`` for policy-governed risk decisions.

    Lifecycle: start() → evaluate() → stop()

    Parameters
    ----------
    registry :   Optional injected policy registry.
    evaluator :  Optional injected condition/rule evaluator.
    chain :      Optional injected chain evaluator.
    validator :  Optional injected policy validator.
    auditor :    Optional injected auditor.
    statistics : Optional injected statistics collector.
    history :    Optional injected history store.
    factory :    Optional injected object factory.
    manager :    Optional injected evaluation manager.
    """

    VERSION:   str = VERSION
    SYSTEM_ID: str = POLICY_SYSTEM_ID

    def __init__(
        self,
        registry:   Optional[RiskPolicyRegistry]   = None,
        evaluator:  Optional[RiskPolicyEvaluator]  = None,
        chain:      Optional[RiskPolicyChain]       = None,
        validator:  Optional[RiskPolicyValidator]   = None,
        auditor:    Optional[RiskPolicyAuditor]     = None,
        statistics: Optional[RiskPolicyStatistics]  = None,
        history:    Optional[RiskPolicyHistory]     = None,
        factory:    Optional[RiskPolicyFactory]     = None,
        manager:    Optional[RiskPolicyManager]     = None,
    ) -> None:
        super().__init__()

        # ── Subsystems ──────────────────────────────────────────────
        self._registry   = registry   or RiskPolicyRegistry()
        self._evaluator  = evaluator  or RiskPolicyEvaluator()
        self._chain      = chain      or RiskPolicyChain(self._evaluator)
        self._validator  = validator  or RiskPolicyValidator()
        self._auditor    = auditor    or RiskPolicyAuditor()
        self._stats      = statistics or RiskPolicyStatistics()
        self._history    = history    or RiskPolicyHistory()
        self._factory    = factory    or RiskPolicyFactory()

        self._manager = manager or RiskPolicyManager(
            registry   = self._registry,
            evaluator  = self._evaluator,
            chain      = self._chain,
            validator  = self._validator,
            auditor    = self._auditor,
            statistics = self._stats,
            history    = self._history,
            factory    = self._factory,
        )

        # ── State ───────────────────────────────────────────────────
        self._started_at: float = 0.0

        # ── Listeners ───────────────────────────────────────────────
        self._listeners_lock = threading.Lock()
        self._listeners: List[Callable] = []

    # ==================================================================
    # Lifecycle hooks
    # ==================================================================

    def _on_start(self) -> None:
        self._started_at = time.time()
        _audit.log_lifecycle_event(
            engine_id  = POLICY_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = VERSION,
            actor      = "system",
        )
        _log.info(f"RiskPolicyEngine started (version={VERSION})")

    def _on_stop(self) -> None:
        uptime = round(time.time() - self._started_at, 2)
        _audit.log_lifecycle_event(
            engine_id  = POLICY_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = VERSION,
            actor      = "system",
            uptime_s   = uptime,
        )
        _log.info(f"RiskPolicyEngine stopped (uptime={uptime}s)")

    # ==================================================================
    # Guard
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise RiskPolicyEngineNotRunningError()

    # ==================================================================
    # Primary evaluation entry point
    # ==================================================================

    def evaluate(self, request: RiskPolicyRequest) -> RiskPolicyResponse:
        """
        Evaluate all applicable policies for *request* and return a
        :class:`~.risk_policy_response.RiskPolicyResponse`.

        This is the **primary entry point** for all policy-governed risk decisions.

        Raises
        ------
        RiskPolicyEngineNotRunningError
            When the engine has not been started.
        """
        self._assert_running()

        started_ev = make_evaluation_started(
            evaluation_id = request.evaluation_id,
            request_id    = request.request_id,
            actor         = POLICY_SYSTEM_ID,
        )
        self._dispatch_event(started_ev)

        response = self._manager.run_evaluation(request)

        completed_ev = make_evaluation_completed(
            evaluation_id = request.evaluation_id,
            request_id    = request.request_id,
            final_action  = response.final_action,
            actor         = POLICY_SYSTEM_ID,
            payload       = {
                "policies_evaluated": response.policies_evaluated,
                "elapsed_s":          response.evaluation_elapsed_s,
            },
        )
        self._dispatch_event(completed_ev)
        return response

    # ==================================================================
    # Policy registration interface
    # ==================================================================

    def register_policy(self, policy: RiskPolicy) -> None:
        """Register a policy with the engine's registry."""
        self._assert_running()
        self._registry.register(policy)
        _log.info(
            f"Policy registered: policy_id={policy.policy_id!r} "
            f"name={policy.name!r} type={policy.policy_type.value}"
        )

    def unregister_policy(self, policy_id: str) -> None:
        """Remove a policy from the engine's registry."""
        self._assert_running()
        self._registry.unregister(policy_id)
        _log.info(f"Policy unregistered: policy_id={policy_id!r}")

    def get_policy(self, policy_id: str) -> RiskPolicy:
        """Return the policy with *policy_id*."""
        return self._registry.get(policy_id)

    def list_policies(
        self,
        policy_type: Optional[PolicyType] = None,
    ) -> List[RiskPolicy]:
        """Return all registered policies, optionally filtered by *policy_type*."""
        if policy_type is not None:
            return self._registry.list_by_type(policy_type)
        return self._registry.list_all()

    def list_enabled_policies(
        self,
        policy_type: Optional[PolicyType] = None,
    ) -> List[RiskPolicy]:
        """Return enabled policies, optionally filtered by *policy_type*."""
        if policy_type is not None:
            return self._registry.list_enabled_by_type(policy_type)
        return self._registry.list_enabled()

    # ==================================================================
    # Engine observability
    # ==================================================================

    def health(self) -> Dict[str, Any]:
        """Return a health snapshot dict."""
        state = self.lifecycle_state().value
        return {
            "engine_id":          POLICY_SYSTEM_ID,
            "state":              state,
            "healthy":            state == "running",
            "policies_registered": self._registry.count,
            "policies_enabled":   self._registry.enabled_count,
            "uptime_s":           round(time.time() - self._started_at, 2)
                                   if self._started_at else 0.0,
        }

    def status(self) -> RiskPolicyEngineStatus:
        """Return a structured status snapshot."""
        return RiskPolicyEngineStatus(
            engine_id           = POLICY_SYSTEM_ID,
            state               = self.lifecycle_state().value,
            policies_registered = self._registry.count,
            policies_enabled    = self._registry.enabled_count,
            statistics          = self._stats.snapshot(),
            health              = self.health(),
            started_at          = self._started_at,
        )

    def statistics(self) -> Dict[str, Any]:
        """Return current evaluation statistics."""
        return self._stats.snapshot()

    # ==================================================================
    # Event listeners
    # ==================================================================

    def add_listener(self, fn: Callable) -> None:
        """Register an event listener callback."""
        with self._listeners_lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable) -> None:
        """Remove a previously registered event listener."""
        with self._listeners_lock:
            try:
                self._listeners.remove(fn)
            except ValueError:
                pass

    def _dispatch_event(self, event: Any) -> None:
        """Dispatch *event* to all registered listeners."""
        self._history.record_event(event)
        with self._listeners_lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception as exc:
                _log.info(f"Listener {fn!r} raised: {exc}")
