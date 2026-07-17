"""iios/execution/gateway/routing/routing_engine.py
==================================================
RoutingEngine — primary public API for the IIOS Routing Framework.

The engine owns a RoutingManager and exposes a clean, high-level
interface to the execution pipeline.

Usage
-----
    engine = RoutingEngine()
    engine.start()

    engine.register_candidate(candidate)
    engine.register_policy(policy)
    engine.set_default_policy(policy_id)

    decision = engine.route(context)
    assert decision.is_routed

    engine.stop()

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    ROUTING_ENGINE_SYSTEM_ID,
    ROUTING_SYSTEM_ID,
    RoutingStrategyType,
    VERSION,
)
from .exceptions import RoutingEngineNotRunningError
from .routing_candidate import RoutingCandidate
from .routing_context import RoutingContext
from .routing_events import RoutingEvent
from .routing_history import RoutingHistory
from .routing_manager import RoutingManager
from .routing_policy import RoutingPolicyBase
from .routing_request import make_routing_request
from .routing_response import RoutingDecision
from .routing_statistics import RoutingStatistics

_log   = get_logger(__name__, engine_id=ROUTING_ENGINE_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=ROUTING_ENGINE_SYSTEM_ID)


class RoutingEngine(LifecycleAwareMixin):
    """
    Primary public API for the IIOS Routing Framework.

    Owns exactly one RoutingManager and delegates all operations to it.
    """

    SYSTEM_ID = ROUTING_SYSTEM_ID
    VERSION   = VERSION

    def __init__(
        self,
        max_policies:     int = DEFAULT_MAX_POLICIES,
        max_candidates:   int = DEFAULT_MAX_CANDIDATES,
        max_history:      int = DEFAULT_MAX_HISTORY,
        default_strategy: RoutingStrategyType = RoutingStrategyType.PRIORITY_SELECTION,
    ) -> None:
        super().__init__()
        self._default_strategy = default_strategy
        self._manager = RoutingManager(
            max_policies=max_policies,
            max_candidates=max_candidates,
            max_history=max_history,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._manager.start()
        _audit.log_lifecycle_event(
            ROUTING_SYSTEM_ID,
            EngineState.STOPPED,
            EngineState.RUNNING,
            VERSION,
        )
        _log.info("RoutingEngine started.", strategy=self._default_strategy.value, version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            ROUTING_SYSTEM_ID,
            EngineState.RUNNING,
            EngineState.STOPPED,
            VERSION,
        )
        self._manager.stop()
        _log.info("RoutingEngine stopped.", version=VERSION)

    # ── Core API ──────────────────────────────────────────────────────────────

    def route(
        self,
        context:   RoutingContext,
        *,
        policy_id: Optional[str] = None,
        strategy:  Optional[RoutingStrategyType] = None,
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """
        Route an execution request and return a RoutingDecision.

        Parameters
        ----------
        context:
            Execution context carrying instrument, quantity, and routing hints.
        policy_id:
            Explicit policy to use; None → use the default policy.
        strategy:
            Selection strategy; None → use the engine's default_strategy.
        metadata:
            Arbitrary key-value pairs attached to the RoutingRequest.

        Returns
        -------
        RoutingDecision — always returned, never raises for routing failures.

        Raises
        ------
        RoutingEngineNotRunningError — if the engine is not RUNNING.
        """
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RoutingEngineNotRunningError()

        request = make_routing_request(
            context=context,
            policy_id=policy_id,
            strategy=strategy or self._default_strategy,
            metadata=metadata,
        )
        return self._manager.route(request)

    # ── Policy management ─────────────────────────────────────────────────────

    def register_policy(self, policy: RoutingPolicyBase) -> None:
        """Register a routing policy.  Engine must be RUNNING."""
        self._manager.register_policy(policy)

    def remove_policy(self, policy_id: str) -> None:
        """Remove a routing policy.  Engine must be RUNNING."""
        self._manager.remove_policy(policy_id)

    def set_default_policy(self, policy_id: str) -> None:
        """Designate the default policy.  Engine must be RUNNING."""
        self._manager.set_default_policy(policy_id)

    # ── Candidate management ──────────────────────────────────────────────────

    def register_candidate(self, candidate: RoutingCandidate) -> None:
        """Register a broker routing candidate.  Engine must be RUNNING."""
        self._manager.register_candidate(candidate)

    def remove_candidate(self, broker_id: str) -> None:
        """Remove a routing candidate.  Engine must be RUNNING."""
        self._manager.remove_candidate(broker_id)

    def update_candidate_health(self, broker_id: str, health_score: float) -> None:
        """Update a candidate's health score (0.0–1.0)."""
        self._manager.update_candidate_health(broker_id, health_score)

    def update_candidate_status(
        self,
        broker_id:        str,
        is_connected:     bool,
        is_authenticated: bool,
    ) -> None:
        """Update a candidate's connection / authentication state."""
        self._manager.update_candidate_status(broker_id, is_connected, is_authenticated)

    # ── Blacklist ─────────────────────────────────────────────────────────────

    def blacklist_broker(self, broker_id: str) -> None:
        """Exclude a broker from routing.  Engine must be RUNNING."""
        self._manager.blacklist_broker(broker_id)

    def unblacklist_broker(self, broker_id: str) -> None:
        """Re-admit a previously blacklisted broker.  Engine must be RUNNING."""
        self._manager.unblacklist_broker(broker_id)

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_event_listener(self, listener: Callable[[RoutingEvent], None]) -> None:
        self._manager.add_event_listener(listener)

    def remove_event_listener(self, listener: Callable[[RoutingEvent], None]) -> None:
        self._manager.remove_event_listener(listener)

    # ── Observability ─────────────────────────────────────────────────────────

    def statistics(self) -> RoutingStatistics:
        return self._manager.statistics()

    def history(self) -> RoutingHistory:
        return self._manager.history()

    def snapshot(self) -> Dict[str, Any]:
        snap = self._manager.snapshot()
        snap["engine_system_id"]    = ROUTING_ENGINE_SYSTEM_ID
        snap["default_strategy"]    = self._default_strategy.value
        return snap

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def candidate_count(self) -> int:
        return self._manager._registry.candidate_count

    @property
    def policy_count(self) -> int:
        return self._manager._registry.policy_count

    @property
    def default_strategy(self) -> RoutingStrategyType:
        return self._default_strategy

    @property
    def engine_state(self) -> str:
        return self.lifecycle_state().name
