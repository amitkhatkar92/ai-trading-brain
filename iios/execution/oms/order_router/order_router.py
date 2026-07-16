"""iios/execution/oms/order_router/order_router.py
==================================================
OrderRouter — IIOS v1.0 primary facade for order routing.

Receives a RoutingRequest, evaluates candidates against
the selected policy, ranks them and returns a RoutingDecision.

NEVER submits orders. NEVER communicates with brokers.
NEVER performs execution. Returns routing decisions only.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

import time
import threading
from typing import Any, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from iios.execution.oms.order_router.constants import (
    ROUTER_SYSTEM_ID,
    VERSION,
    RoutingPolicyType,
    RoutingStatus,
)
from iios.execution.oms.order_router.exceptions import (
    NoCandidatesError,
    RoutingExpiredError,
    RoutingPolicyError,
    RoutingRejectedError,
    RoutingValidationError,
    RouterNotRunning,
)
from iios.execution.oms.order_router.routing_candidate import RoutingCandidate
from iios.execution.oms.order_router.routing_context import BrokerCapabilities, RoutingContext
from iios.execution.oms.order_router.routing_decision import RoutingDecision
from iios.execution.oms.order_router.routing_events import (
    make_candidate_evaluated,
    make_route_selected,
    make_routing_completed,
    make_routing_rejected,
    make_routing_started,
    RoutingEvent,
)
from iios.execution.oms.order_router.routing_factory import RoutingFactory
from iios.execution.oms.order_router.routing_history import RoutingHistory
from iios.execution.oms.order_router.routing_policy import get_policy
from iios.execution.oms.order_router.routing_registry import RoutingRegistry
from iios.execution.oms.order_router.routing_request import RoutingRequest
from iios.execution.oms.order_router.routing_result import RoutingResult
from iios.execution.oms.order_router.routing_statistics import RoutingStatistics
from iios.execution.oms.order_router.routing_strategy import RoutingStrategy
from iios.execution.oms.order_router.routing_validation import RoutingValidator


class OrderRouter(LifecycleAwareMixin):
    """
    Institutional Order Router.

    Responsibilities
    ----------------
    1. Receive a RoutingRequest.
    2. Validate request completeness.
    3. Resolve broker candidates from registry (or request).
    4. Evaluate candidates using the selected RoutingPolicy.
    5. Rank candidates with RoutingStrategy.
    6. Emit routing events.
    7. Return RoutingDecision (immutable) — ONLY the destination.

    No execution. No broker communication. No side-effects beyond
    updating RoutingHistory and RoutingStatistics.
    """

    def __init__(
        self,
        registry:    Optional[RoutingRegistry] = None,
        max_history: int = 5_000,
    ) -> None:
        super().__init__()
        self._registry   = registry or RoutingRegistry()
        self._factory    = RoutingFactory()
        self._validator  = RoutingValidator()
        self._strategy   = RoutingStrategy()
        self._history    = RoutingHistory(max_size=max_history)
        self._stats      = RoutingStatistics()
        self._events:    list[RoutingEvent] = []
        self._event_lock = threading.Lock()
        self._log        = get_logger(__name__, engine_id=ROUTER_SYSTEM_ID)
        self._audit      = get_audit_logger(__name__, engine_id=ROUTER_SYSTEM_ID)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        if not self._registry.lifecycle_state() == EngineState.RUNNING:
            self._registry.start()
        self._audit.log_lifecycle_event(
            ROUTER_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        self._log.info("OrderRouter started.")

    def _on_stop(self) -> None:
        self._audit.log_lifecycle_event(
            ROUTER_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        self._log.info("OrderRouter stopped.")

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RouterNotRunning("OrderRouter is not running — call start() first")

    # ── Primary API ───────────────────────────────────────────────────────────

    def route(self, request: RoutingRequest) -> RoutingDecision:
        """
        Primary entry-point. Route the request and return an immutable RoutingDecision.

        Raises
        ------
        RouterNotRunning       if the router has not been started
        RoutingValidationError if the request fails validation
        RoutingExpiredError    if the request TTL has elapsed
        """
        self._assert_running()
        start_ts = time.perf_counter()

        # Validate ────────────────────────────────────────────────────────────
        self._validator.validate(request)
        if request.is_expired:
            self._stats.record_expiry()
            raise RoutingExpiredError(request.order_id)

        self._stats.record_request()
        context = request.build_context()

        self._emit(make_routing_started(
            request.order_id, request.request_id, request.policy_type.value
        ))

        # Resolve candidates ──────────────────────────────────────────────────
        candidates = self._build_candidates(request)

        # Apply policy ────────────────────────────────────────────────────────
        policy = get_policy(request.policy_type)
        try:
            policy.apply(candidates, context)
        except Exception as exc:
            raise RoutingPolicyError(
                f"Policy '{request.policy_type.value}' evaluation error: {exc}",
                context={"order_id": request.order_id},
            ) from exc

        # Emit candidate events ───────────────────────────────────────────────
        for cand in candidates:
            self._emit(make_candidate_evaluated(
                request.order_id,
                request.request_id,
                cand.broker_id,
                cand.score,
                cand.is_eligible,
                cand.discard_reason,
            ))

        elapsed_ms = (time.perf_counter() - start_ts) * 1_000

        # Select best candidate ───────────────────────────────────────────────
        try:
            best = self._strategy.select(candidates, context)
        except NoCandidatesError as exc:
            decision = self._factory.make_rejected_decision(
                order_id         = request.order_id,
                reason           = "no_eligible_candidates",
                policy_applied   = request.policy_type.value,
                candidates_total = len(candidates),
                routing_time_ms  = elapsed_ms,
                request_id       = request.request_id,
            )
            self._emit(make_routing_rejected(
                request.order_id, request.request_id, "no_eligible_candidates"
            ))
            self._emit(make_routing_completed(
                request.order_id, request.request_id, False, elapsed_ms, len(candidates)
            ))
            self._stats.record_rejection(elapsed_ms)
            result = self._factory.make_result(
                decision    = decision,
                request_id  = request.request_id,
                order_id    = request.order_id,
                policy_type = request.policy_type.value,
                elapsed_ms  = elapsed_ms,
                candidates  = candidates,
            )
            self._history.append(result)
            return decision

        # Success ─────────────────────────────────────────────────────────────
        decision = self._factory.make_success_decision(
            order_id         = request.order_id,
            broker_id        = best.broker_id,
            exchange         = best.exchange or request.exchange,
            policy_applied   = request.policy_type.value,
            score            = best.score,
            candidates_total = len(candidates),
            routing_time_ms  = elapsed_ms,
            request_id       = request.request_id,
        )

        self._emit(make_route_selected(
            request.order_id, request.request_id,
            decision.decision_id, best.broker_id,
            decision.selected_exchange, best.score,
        ))
        self._emit(make_routing_completed(
            request.order_id, request.request_id, True, elapsed_ms, len(candidates)
        ))

        self._stats.record_success(
            elapsed_ms,
            policy=request.policy_type.value,
            broker_id=best.broker_id,
        )

        result = self._factory.make_result(
            decision    = decision,
            request_id  = request.request_id,
            order_id    = request.order_id,
            policy_type = request.policy_type.value,
            elapsed_ms  = elapsed_ms,
            candidates  = candidates,
        )
        self._history.append(result)

        self._log.info(
            "Order routed.",
            order_id=request.order_id,
            broker_id=best.broker_id,
            exchange=decision.selected_exchange,
            score=round(best.score, 4),
            elapsed_ms=round(elapsed_ms, 2),
        )
        return decision

    # ── Registry pass-through ─────────────────────────────────────────────────

    def register_broker(self, capabilities: BrokerCapabilities) -> None:
        self._assert_running()
        self._registry.register(capabilities)

    def unregister_broker(self, broker_id: str) -> bool:
        self._assert_running()
        return self._registry.unregister(broker_id)

    def get_broker(self, broker_id: str) -> Optional[BrokerCapabilities]:
        self._assert_running()
        return self._registry.get(broker_id)

    def list_brokers(self) -> list[BrokerCapabilities]:
        self._assert_running()
        return self._registry.all()

    # ── History / Stats ───────────────────────────────────────────────────────

    def history(self) -> RoutingHistory:
        return self._history

    def statistics(self) -> RoutingStatistics:
        return self._stats

    def events(self) -> list[RoutingEvent]:
        with self._event_lock:
            return list(self._events)

    def clear_events(self) -> None:
        with self._event_lock:
            self._events.clear()

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        return {
            "system_id":   ROUTER_SYSTEM_ID,
            "version":     VERSION,
            "state":       self.lifecycle_state().value,
            "statistics":  self._stats.to_dict(),
            "history":     self._history.to_dict(),
            "registry":    self._registry.to_dict(),
        }

    # ── Internal ─────────────────────────────────────────────────────────────

    def _build_candidates(self, request: RoutingRequest) -> list[RoutingCandidate]:
        """
        Assemble the list of RoutingCandidate objects to evaluate.

        If the request supplies explicit broker_capabilities, use those.
        Otherwise look up all registered brokers (or the requested subset).
        """
        if request.broker_capabilities:
            sources = request.broker_capabilities
        elif request.candidate_broker_ids:
            sources = [
                self._registry.get(bid)
                for bid in request.candidate_broker_ids
                if self._registry.get(bid) is not None
            ]
        else:
            sources = self._registry.all()

        candidates: list[RoutingCandidate] = []
        for cap in sources:
            if cap is None:
                continue
            c = RoutingCandidate(
                broker_id    = cap.broker_id,
                exchange     = request.exchange,
                capabilities = cap,
            )
            candidates.append(c)
        return candidates

    def _emit(self, event: RoutingEvent) -> None:
        with self._event_lock:
            self._events.append(event)
