"""
market_policy_engine.py — iios.market.policies
================================================
Primary public interface for the Market Policy Framework.

Wraps all subsystems behind the LifecycleAwareMixin and exposes the
canonical ``evaluate()`` entry point.

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import dataclasses
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import POLICY_SYSTEM_ID, VERSION, MarketPolicyType
from .exceptions import MarketPolicyEngineNotRunningError
from .market_policy import MarketPolicy
from .market_policy_audit import MarketPolicyAuditor
from .market_policy_chain import MarketPolicyChain
from .market_policy_evaluator import MarketPolicyEvaluator
from .market_policy_events import (
    make_market_policy_evaluation_completed,
    make_market_policy_evaluation_started,
)
from .market_policy_factory import MarketPolicyFactory
from .market_policy_history import MarketPolicyHistory
from .market_policy_manager import MarketPolicyManager
from .market_policy_registry import MarketPolicyRegistry
from .market_policy_request import MarketPolicyRequest
from .market_policy_response import MarketPolicyResponse
from .market_policy_statistics import MarketPolicyStatistics
from .market_policy_validator import MarketPolicyValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=POLICY_SYSTEM_ID)


# ---------------------------------------------------------------------------
# Engine status value object
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class MarketPolicyEngineStatus:
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

class MarketPolicyEngine(LifecycleAwareMixin):
    """
    Institutional Market Policy Engine — primary public interface.

    Wires together all Market Policy subsystems and provides the single
    entry point ``evaluate()`` for policy-governed market intelligence decisions.

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
        registry:   Optional[MarketPolicyRegistry]   = None,
        evaluator:  Optional[MarketPolicyEvaluator]  = None,
        chain:      Optional[MarketPolicyChain]       = None,
        validator:  Optional[MarketPolicyValidator]   = None,
        auditor:    Optional[MarketPolicyAuditor]     = None,
        statistics: Optional[MarketPolicyStatistics]  = None,
        history:    Optional[MarketPolicyHistory]     = None,
        factory:    Optional[MarketPolicyFactory]     = None,
        manager:    Optional[MarketPolicyManager]     = None,
    ) -> None:
        super().__init__()

        # ── Subsystems ──────────────────────────────────────────────
        self._registry  = registry   or MarketPolicyRegistry()
        self._evaluator = evaluator  or MarketPolicyEvaluator()
        self._chain     = chain      or MarketPolicyChain(self._evaluator)
        self._validator = validator  or MarketPolicyValidator()
        self._auditor   = auditor    or MarketPolicyAuditor()
        self._stats     = statistics or MarketPolicyStatistics()
        self._history   = history    or MarketPolicyHistory()
        self._factory   = factory    or MarketPolicyFactory()

        self._manager = manager or MarketPolicyManager(
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
        _log.info(f"MarketPolicyEngine started (version={VERSION})")

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
        _log.info(f"MarketPolicyEngine stopped (uptime={uptime}s)")

    # ==================================================================
    # Guard
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise MarketPolicyEngineNotRunningError()

    # ==================================================================
    # Primary evaluation entry point
    # ==================================================================

    def evaluate(self, request: MarketPolicyRequest) -> MarketPolicyResponse:
        """
        Evaluate all applicable market policies for *request* and return a
        :class:`~.market_policy_response.MarketPolicyResponse`.

        This is the **primary entry point** for all policy-governed market
        intelligence decisions.

        Raises
        ------
        MarketPolicyEngineNotRunningError
            When the engine has not been started.
        """
        self._assert_running()

        started_ev = make_market_policy_evaluation_started(
            evaluation_id      = request.evaluation_id,
            request_id         = request.request_id,
            market_analysis_id = request.market_analysis_id,
            exchange           = request.exchange,
            actor              = POLICY_SYSTEM_ID,
        )
        self._dispatch_event(started_ev)
        self._history.record_event(started_ev)

        response = self._manager.run_evaluation(request)

        completed_ev = make_market_policy_evaluation_completed(
            evaluation_id      = request.evaluation_id,
            request_id         = request.request_id,
            final_action       = response.final_action,
            market_analysis_id = request.market_analysis_id,
            exchange           = request.exchange,
            actor              = POLICY_SYSTEM_ID,
            payload            = {
                "policies_evaluated":   response.policies_evaluated,
                "evaluation_elapsed_s": response.evaluation_elapsed_s,
                "is_success":           response.is_success,
            },
        )
        self._dispatch_event(completed_ev)
        self._history.record_event(completed_ev)

        return response

    # ==================================================================
    # Policy registration
    # ==================================================================

    def register_policy(self, policy: MarketPolicy) -> None:
        """Register a market policy with the registry."""
        self._assert_running()
        self._registry.register(policy)

    def unregister_policy(self, policy_id: str) -> None:
        """Unregister a market policy by ID."""
        self._assert_running()
        self._registry.unregister(policy_id)

    def get_policy(self, policy_id: str) -> MarketPolicy:
        """Return the policy with *policy_id*."""
        self._assert_running()
        return self._registry.get(policy_id)

    def list_policies(
        self, policy_type: Optional[MarketPolicyType] = None
    ) -> List[MarketPolicy]:
        """Return all enabled policies, optionally filtered by *policy_type*."""
        self._assert_running()
        if policy_type is not None:
            return self._registry.list_enabled_by_type(policy_type)
        return self._registry.list_enabled()

    # ==================================================================
    # Validation
    # ==================================================================

    def validate_policy(self, policy: MarketPolicy):
        """Validate a policy configuration."""
        return self._validator.validate_policy(policy)

    def validate_request(self, request: MarketPolicyRequest):
        """Validate an evaluation request."""
        return self._validator.validate_request(request)

    # ==================================================================
    # Introspection
    # ==================================================================

    def statistics(self) -> Dict[str, Any]:
        """Return a snapshot of evaluation statistics."""
        return self._stats.snapshot()

    def history(self) -> Dict[str, Any]:
        """Return history counts."""
        return self._history.counts()

    def status(self) -> MarketPolicyEngineStatus:
        """Return an engine status snapshot."""
        stats = self._stats.snapshot()
        health = self._health()
        return MarketPolicyEngineStatus(
            engine_id           = POLICY_SYSTEM_ID,
            state               = self.lifecycle_state().value,
            policies_registered = self._registry.count,
            policies_enabled    = self._registry.enabled_count,
            statistics          = stats,
            health              = health,
            started_at          = self._started_at,
        )

    def _health(self) -> Dict[str, Any]:
        """Return a simple health dict."""
        return {
            "registry":   {"policies": self._registry.count},
            "statistics": self._stats.snapshot(),
            "checked_at": time.time(),
        }

    # ==================================================================
    # Event listeners
    # ==================================================================

    def add_listener(self, fn: Callable) -> None:
        """Register an event listener."""
        with self._listeners_lock:
            if not any(l == fn for l in self._listeners):
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable) -> None:
        """Unregister an event listener."""
        with self._listeners_lock:
            self._listeners = [l for l in self._listeners if l != fn]

    def _dispatch_event(self, event: Any) -> None:
        """Fan out *event* to all registered listeners; swallow per-listener errors."""
        with self._listeners_lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:  # noqa: BLE001
                pass
