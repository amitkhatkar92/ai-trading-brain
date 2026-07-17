"""iios/execution/gateway/routing/routing_manager.py
==================================================
RoutingManager — lifecycle-aware orchestrator for the full
routing workflow.

Ownership
---------
  RoutingRegistry      — policies + candidates
  RoutingSelector      — policy + strategy selection
  RoutingValidator     — input/output validation
  RoutingStatistics    — cumulative metrics
  RoutingHistory       — bounded decision + event log

Routing workflow (route())
--------------------------
  1. Assert running
  2. Validate request
  3. Collect candidates from registry
  4. Fire ROUTING_STARTED event
  5. Resolve policy (explicit ID or default)
  6. Fire POLICY_APPLIED if policy found
  7. Run RoutingSelector.select() → (candidate, rejections)
  8. Fire per-broker BROKER_REJECTED events
  9. If no selection and policy.supports_failover → failover attempt
 10. Build RoutingDecision (routed or failed)
 11. Fire BROKER_SELECTED / ROUTING_FAILED + ROUTING_COMPLETED
 12. Record statistics + history
 13. Return decision

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    ROUTING_MANAGER_SYSTEM_ID,
    RoutingOutcome,
    RoutingStrategyType,
    VERSION,
)
from .exceptions import RoutingEngineNotRunningError
from .routing_candidate import RoutingCandidate
from .routing_events import (
    RoutingEvent,
    make_broker_rejected_event,
    make_broker_selected_event,
    make_failover_activated_event,
    make_policy_applied_event,
    make_routing_completed_event,
    make_routing_failed_event,
    make_routing_started_event,
)
from .routing_history import RoutingHistory
from .routing_policy import RoutingPolicyBase
from .routing_registry import RoutingRegistry
from .routing_request import RoutingRequest
from .routing_response import RoutingDecision, make_failed_decision, make_routed_decision
from .routing_selector import RoutingSelector
from .routing_statistics import RoutingStatistics
from .routing_validation import RoutingValidator

_log   = get_logger(__name__, engine_id=ROUTING_MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=ROUTING_MANAGER_SYSTEM_ID)


class RoutingManager(LifecycleAwareMixin):
    """
    Lifecycle-aware orchestrator that executes the full routing workflow.

    All route() calls are serialised behind an internal lock to keep
    statistics consistent.  Registry mutations (register_* / blacklist_*)
    acquire their own lock inside RoutingRegistry.
    """

    SYSTEM_ID = ROUTING_MANAGER_SYSTEM_ID

    def __init__(
        self,
        max_policies:   int = DEFAULT_MAX_POLICIES,
        max_candidates: int = DEFAULT_MAX_CANDIDATES,
        max_history:    int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._registry  = RoutingRegistry(
            max_policies=max_policies,
            max_candidates=max_candidates,
        )
        self._selector  = RoutingSelector()
        self._validator = RoutingValidator()
        self._stats     = RoutingStatistics()
        self._history   = RoutingHistory(max_decisions=max_history, max_events=max_history)
        self._listeners: List[Callable[[RoutingEvent], None]] = []
        self._lock      = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        _audit.log_lifecycle_event(
            ROUTING_MANAGER_SYSTEM_ID,
            EngineState.STOPPED,
            EngineState.RUNNING,
            VERSION,
        )
        _log.info("RoutingManager started.", version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            ROUTING_MANAGER_SYSTEM_ID,
            EngineState.RUNNING,
            EngineState.STOPPED,
            VERSION,
        )
        self._registry.stop()
        _log.info("RoutingManager stopped.", version=VERSION)

    # ── Core routing workflow ─────────────────────────────────────────────────

    def route(self, request: RoutingRequest) -> RoutingDecision:
        """
        Execute the full 13-step routing workflow.

        Raises RoutingEngineNotRunningError if the manager is not RUNNING.
        """
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RoutingEngineNotRunningError()

        t_start = time.perf_counter()

        # Step 1 — Validate request
        all_candidates       = self._registry.all_candidates()
        available_candidates = self._registry.available_candidates()

        validation = self._validator.validate_request(request, all_candidates)
        if not validation.is_valid:
            routing_ms = (time.perf_counter() - t_start) * 1_000.0
            decision   = make_failed_decision(
                request_id=request.request_id,
                routing_id=request.routing_id,
                outcome=RoutingOutcome.VALIDATION_FAILED,
                candidates_available=len(available_candidates),
                rejection_reasons=validation.errors,
                routing_time_ms=routing_ms,
            )
            with self._lock:
                self._stats.record_routing(
                    is_success=False,
                    routing_time_ms=routing_ms,
                )
                self._history.append_decision(decision)
            return decision

        # Step 4 — ROUTING_STARTED
        self._fire_event(make_routing_started_event(request.routing_id))

        # Step 5 — Resolve policy
        policy: Optional[RoutingPolicyBase] = self._registry.get_policy_optional(
            request.policy_id
        )
        if policy is None:
            policy = self._registry.default_policy()

        # Step 6 — POLICY_APPLIED
        if policy is not None:
            self._fire_event(
                make_policy_applied_event(request.routing_id, policy.policy_id)
            )

        # Step 7 — Select (policy filter + strategy)
        selected, rejection_reasons = self._selector.select(
            available_candidates=available_candidates,
            context=request.context,
            policy=policy,
            strategy=request.strategy,
        )

        # Step 8 — BROKER_REJECTED events
        if policy is not None and rejection_reasons:
            for bid in (
                {c.broker_id for c in available_candidates}
                - ({selected.broker_id} if selected else set())
            ):
                self._fire_event(
                    make_broker_rejected_event(
                        request.routing_id,
                        bid,
                        policy_id=policy.policy_id,
                    )
                )

        # Step 9 — Failover attempt
        failover_used = False
        if selected is None and policy is not None and policy.supports_failover:
            selected = self._selector.select_fallback(
                available_candidates, request.context
            )
            failover_used = selected is not None
            if failover_used:
                self._fire_event(
                    make_failover_activated_event(
                        request.routing_id,
                        selected.broker_id,
                        policy_id=policy.policy_id,
                    )
                )

        routing_ms = (time.perf_counter() - t_start) * 1_000.0

        # Step 10/11 — Build decision + fire events
        if selected is not None:
            outcome = RoutingOutcome.FAILOVER_ROUTED if failover_used else RoutingOutcome.ROUTED
            decision = make_routed_decision(
                request_id=request.request_id,
                routing_id=request.routing_id,
                selected_broker_id=selected.broker_id,
                selected_broker_name=selected.broker_name,
                policy_id=policy.policy_id if policy else None,
                strategy=request.strategy,
                failover_used=failover_used,
                candidates_evaluated=len(available_candidates),
                candidates_available=len(available_candidates),
                routing_time_ms=routing_ms,
            )
            self._fire_event(
                make_broker_selected_event(
                    request.routing_id,
                    selected.broker_id,
                    policy_id=policy.policy_id if policy else None,
                )
            )
        else:
            if not available_candidates:
                outcome = RoutingOutcome.NO_CANDIDATES
            elif rejection_reasons:
                outcome = RoutingOutcome.POLICY_REJECTED
            else:
                outcome = RoutingOutcome.FAILED

            decision = make_failed_decision(
                request_id=request.request_id,
                routing_id=request.routing_id,
                outcome=outcome,
                policy_id=policy.policy_id if policy else None,
                strategy=request.strategy,
                candidates_evaluated=len(available_candidates),
                candidates_available=len(available_candidates),
                rejection_reasons=tuple(rejection_reasons),
                routing_time_ms=routing_ms,
            )
            self._fire_event(
                make_routing_failed_event(
                    request.routing_id,
                    policy_id=policy.policy_id if policy else None,
                )
            )

        self._fire_event(
            make_routing_completed_event(
                request.routing_id,
                broker_id=selected.broker_id if selected else None,
            )
        )

        # Step 12 — Record statistics + history
        with self._lock:
            self._stats.record_routing(
                is_success=decision.is_routed,
                routing_time_ms=routing_ms,
                policy_id=policy.policy_id if policy else None,
            )
            if failover_used:
                self._stats.record_failover()
            if selected is not None:
                self._stats.record_broker_utilization(selected.broker_id)
            self._history.append_decision(decision)

        _log.debug(
            "Routing completed.",
            routing_id=request.routing_id,
            broker_id=decision.selected_broker_id,
            outcome=decision.outcome.value,
            routing_time_ms=round(routing_ms, 1),
        )
        return decision

    # ── Policy management ─────────────────────────────────────────────────────

    def register_policy(self, policy: RoutingPolicyBase) -> None:
        self._registry.register_policy(policy)

    def remove_policy(self, policy_id: str) -> None:
        self._registry.remove_policy(policy_id)

    def set_default_policy(self, policy_id: str) -> None:
        self._registry.set_default_policy(policy_id)

    def default_policy(self) -> Optional[RoutingPolicyBase]:
        return self._registry.default_policy()

    # ── Candidate management ──────────────────────────────────────────────────

    def register_candidate(self, candidate: RoutingCandidate) -> None:
        self._registry.register_candidate(candidate)

    def remove_candidate(self, broker_id: str) -> None:
        self._registry.remove_candidate(broker_id)

    def update_candidate_health(self, broker_id: str, health_score: float) -> None:
        candidate = self._registry.get_candidate(broker_id)
        candidate.update_health(health_score)

    def update_candidate_status(
        self,
        broker_id:        str,
        is_connected:     bool,
        is_authenticated: bool,
    ) -> None:
        candidate = self._registry.get_candidate(broker_id)
        candidate.update_status(is_connected, is_authenticated)

    def blacklist_broker(self, broker_id: str) -> None:
        self._registry.blacklist_broker(broker_id)

    def unblacklist_broker(self, broker_id: str) -> None:
        self._registry.unblacklist_broker(broker_id)

    # ── Event listener management ─────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[RoutingEvent], None]
    ) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_event_listener(
        self, listener: Callable[[RoutingEvent], None]
    ) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def _fire_event(self, event: RoutingEvent) -> None:
        with self._lock:
            listeners = list(self._listeners)
        self._history.append_event(event)
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                _log.exception("Event listener raised.", event_type=event.event_type.value)

    # ── Observability ─────────────────────────────────────────────────────────

    def statistics(self) -> RoutingStatistics:
        with self._lock:
            return self._stats.copy()

    def history(self) -> RoutingHistory:
        return self._history

    def snapshot(self) -> Dict[str, Any]:
        return {
            "system_id":         ROUTING_MANAGER_SYSTEM_ID,
            "version":           VERSION,
            "lifecycle_state":   self.lifecycle_state().name,
            "policy_count":      self._registry.policy_count,
            "candidate_count":   self._registry.candidate_count,
            "decision_count":    self._history.decision_count,
            "event_count":       self._history.event_count,
            "statistics":        self._stats.to_dict(),
        }
