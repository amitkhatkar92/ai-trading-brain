"""iios/execution/gateway/lifecycle/gateway_lifecycle.py
==================================================
GatewayLifecycle — LifecycleAwareMixin coordinator for the
Execution Gateway Lifecycle subsystem.

This is the primary public API for all gateway lifecycle operations.
It owns the registry and factory and provides transition methods for
each valid lifecycle stage.

DOES NOT perform routing, broker communication, order execution,
or risk calculations.

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_LIFECYCLE,
    ACTIVE_STATES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    GatewayState,
)
from .exceptions import (
    GatewayLifecycleNotRunningError,
    GatewayRequestNotFoundError,
    GatewayValidationError,
)
from .gateway_context import GatewayContext
from .gateway_events import GatewayEvent
from .gateway_factory import GatewayFactory
from .gateway_registry import GatewayRegistry
from .gateway_request import GatewayRequest
from .gateway_statistics import GatewayStatistics
from .gateway_transition import GatewayTransition
from .gateway_validation import GatewayValidator, ValidationResult

_log   = get_logger(__name__, engine_id=LIFECYCLE_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=LIFECYCLE_SYSTEM_ID)


class GatewayLifecycle(LifecycleAwareMixin):
    """
    Coordinator for the Execution Gateway Lifecycle subsystem.

    Responsibilities
    ----------------
    * Create gateway requests via factory.
    * Enforce state-machine transitions on registered requests.
    * Track lifecycle statistics.
    * Publish lifecycle events to registered global listeners.
    * Provide filtered query access to the registry.

    Non-responsibilities
    --------------------
    * No routing logic.
    * No broker communication.
    * No order execution.
    * No risk calculations.

    Usage
    -----
    lc = GatewayLifecycle()
    lc.start()

    request = lc.create(execution_id="E1", order_id="O1",
                        portfolio_id="PORT-1", strategy_id="STRAT-1")
    lc.receive(request.gateway_id)
    lc.start_validation(request.gateway_id)
    lc.mark_ready(request.gateway_id)
    lc.queue(request.gateway_id)
    lc.start_routing(request.gateway_id)
    lc.dispatch(request.gateway_id)
    lc.complete(request.gateway_id)
    lc.archive(request.gateway_id)

    lc.stop()
    """

    SYSTEM_ID = LIFECYCLE_SYSTEM_ID
    VERSION   = VERSION

    def __init__(
        self,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        max_history:  int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._max_history  = max(1, max_history)
        self._registry     = GatewayRegistry(max_requests=max_requests)
        self._factory      = GatewayFactory()
        self._validator    = GatewayValidator()
        self._stats        = GatewayStatistics()
        self._lock         = threading.RLock()
        self._event_listeners: List[Callable[[GatewayEvent], None]] = []

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise GatewayLifecycleNotRunningError()

    def _on_start(self) -> None:
        self._registry.start()
        _audit.log_lifecycle_event(
            LIFECYCLE_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("GatewayLifecycle started.", version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            LIFECYCLE_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info(
            "GatewayLifecycle stopped.",
            requests_received=self._stats.requests_received,
            requests_completed=self._stats.requests_completed,
        )
        self._registry.stop()

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    # ── Create ────────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        gateway_id:     Optional[str]            = None,
        execution_id:   str                      = "",
        workflow_id:    str                      = "",
        order_id:       str                      = "",
        position_id:    str                      = "",
        portfolio_id:   str                      = "",
        strategy_id:    str                      = "",
        decision_id:    str                      = "",
        correlation_id: str                      = "",
        context:        Optional[GatewayContext] = None,
    ) -> GatewayRequest:
        """
        Create a new ``GatewayRequest`` in CREATED state and register it.

        Raises
        ------
        GatewayLifecycleNotRunningError
            If the lifecycle has not been started.
        GatewayRegistryCapacityError
            If the registry is at capacity.
        """
        self._assert_running()

        request, event = self._factory.create_with_event(
            gateway_id=gateway_id,
            execution_id=execution_id,
            workflow_id=workflow_id,
            order_id=order_id,
            position_id=position_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            decision_id=decision_id,
            correlation_id=correlation_id,
            max_history=self._max_history,
            context=context,
        )

        # Wire global listeners into the request
        with self._lock:
            for listener in self._event_listeners:
                request.add_event_listener(listener)

        self._registry.register(request)
        self._fire_global_event(event)

        _log.debug(
            "GatewayRequest created.",
            gateway_id=request.gateway_id,
            execution_id=execution_id,
        )
        return request

    def create_from_context(
        self,
        ctx: GatewayContext,
        *,
        gateway_id: Optional[str] = None,
    ) -> GatewayRequest:
        """
        Create a ``GatewayRequest`` from a ``GatewayContext``.
        Convenience wrapper around ``create()``.
        """
        return self.create(
            gateway_id=gateway_id,
            execution_id=ctx.execution_id,
            workflow_id=ctx.workflow_id,
            order_id=ctx.order_id,
            position_id=ctx.position_id,
            portfolio_id=ctx.portfolio_id,
            strategy_id=ctx.strategy_id,
            decision_id=ctx.decision_id,
            correlation_id=ctx.correlation_id,
            context=ctx,
        )

    # ── Lifecycle transitions ─────────────────────────────────────────────────

    def receive(
        self,
        gateway_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "Request received by gateway",
    ) -> GatewayRequest:
        """
        Transition CREATED → RECEIVED.

        Records that the gateway has accepted the request.
        """
        self._assert_running()
        request = self._get_request(gateway_id)
        request.transition_to(GatewayState.RECEIVED, actor=actor, reason=reason)
        with self._lock:
            self._stats.record_received()
            self._stats.record_transition()
        _log.debug("Gateway request received.", gateway_id=gateway_id)
        return request

    def start_validation(
        self,
        gateway_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "Starting request validation",
    ) -> GatewayRequest:
        """
        Transition RECEIVED → VALIDATING.

        Marks that validation of the request has begun.
        """
        self._assert_running()
        request = self._get_request(gateway_id)
        request.transition_to(GatewayState.VALIDATING, actor=actor, reason=reason)
        with self._lock:
            self._stats.record_transition()
        _log.debug("Gateway request validation started.", gateway_id=gateway_id)
        return request

    def mark_ready(
        self,
        gateway_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "Request validated and ready for dispatch",
    ) -> GatewayRequest:
        """
        Transition VALIDATING → READY.

        Marks that the request passed validation.
        """
        self._assert_running()
        request = self._get_request(gateway_id)
        request.transition_to(GatewayState.READY, actor=actor, reason=reason)
        with self._lock:
            self._stats.record_transition()
        _log.debug("Gateway request marked ready.", gateway_id=gateway_id)
        return request

    def queue(
        self,
        gateway_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "Request enqueued for routing",
    ) -> GatewayRequest:
        """
        Transition READY → QUEUED.

        Marks that the request has been placed in the dispatch queue.
        """
        self._assert_running()
        request = self._get_request(gateway_id)
        request.transition_to(GatewayState.QUEUED, actor=actor, reason=reason)
        with self._lock:
            self._stats.record_transition()
        _log.debug("Gateway request queued.", gateway_id=gateway_id)
        return request

    def start_routing(
        self,
        gateway_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "Routing request to broker",
    ) -> GatewayRequest:
        """
        Transition QUEUED → ROUTING.

        Marks that active routing to a broker is in progress.
        """
        self._assert_running()
        request = self._get_request(gateway_id)
        request.transition_to(GatewayState.ROUTING, actor=actor, reason=reason)
        with self._lock:
            self._stats.record_transition()
        _log.debug("Gateway request routing started.", gateway_id=gateway_id)
        return request

    def dispatch(
        self,
        gateway_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "Request dispatched to broker",
    ) -> GatewayRequest:
        """
        Transition ROUTING → DISPATCHED.

        Marks that the request has been handed to the broker layer.
        """
        self._assert_running()
        request = self._get_request(gateway_id)
        request.transition_to(GatewayState.DISPATCHED, actor=actor, reason=reason)
        with self._lock:
            self._stats.record_transition()
        _log.debug("Gateway request dispatched.", gateway_id=gateway_id)
        return request

    def complete(
        self,
        gateway_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "Request completed successfully",
    ) -> GatewayRequest:
        """
        Transition DISPATCHED → COMPLETED.

        Marks that the gateway lifecycle has completed successfully.
        """
        self._assert_running()
        request = self._get_request(gateway_id)
        request.transition_to(GatewayState.COMPLETED, actor=actor, reason=reason)
        lifecycle_ms = request.lifecycle_elapsed_ms
        with self._lock:
            self._stats.record_completed(lifecycle_ms)
            self._stats.record_transition()
        _log.info(
            "Gateway request completed.",
            gateway_id=gateway_id,
            lifecycle_ms=round(lifecycle_ms, 2),
        )
        return request

    def fail(
        self,
        gateway_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "Request failed",
    ) -> GatewayRequest:
        """
        Transition any active state → FAILED.

        Records a lifecycle failure.  The reason should describe
        what caused the failure.
        """
        self._assert_running()
        request = self._get_request(gateway_id)
        request.transition_to(GatewayState.FAILED, actor=actor, reason=reason)
        lifecycle_ms = request.lifecycle_elapsed_ms
        with self._lock:
            self._stats.record_failed(lifecycle_ms)
            self._stats.record_transition()
        _log.warning(
            "Gateway request failed.",
            gateway_id=gateway_id,
            reason=reason,
            lifecycle_ms=round(lifecycle_ms, 2),
        )
        return request

    def cancel(
        self,
        gateway_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "Request cancelled",
    ) -> GatewayRequest:
        """
        Transition any active state → CANCELLED.

        Records a lifecycle cancellation.
        """
        self._assert_running()
        request = self._get_request(gateway_id)
        request.transition_to(GatewayState.CANCELLED, actor=actor, reason=reason)
        lifecycle_ms = request.lifecycle_elapsed_ms
        with self._lock:
            self._stats.record_cancelled(lifecycle_ms)
            self._stats.record_transition()
        _log.info(
            "Gateway request cancelled.",
            gateway_id=gateway_id,
            reason=reason,
        )
        return request

    def archive(
        self,
        gateway_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "Request archived",
    ) -> GatewayRequest:
        """
        Transition COMPLETED / FAILED / CANCELLED → ARCHIVED.

        Terminal state — no further transitions are possible.
        """
        self._assert_running()
        request = self._get_request(gateway_id)
        request.transition_to(GatewayState.ARCHIVED, actor=actor, reason=reason)
        with self._lock:
            self._stats.record_archived()
            self._stats.record_transition()
        _log.debug("Gateway request archived.", gateway_id=gateway_id)
        return request

    # ── Validation ────────────────────────────────────────────────────────────

    def validate_request(self, gateway_id: str) -> ValidationResult:
        """Validate the lifecycle consistency of a registered request."""
        request = self._get_request(gateway_id)
        return self._validator.validate_request(request)

    def validate_history(self, gateway_id: str) -> ValidationResult:
        """Validate the transition history integrity of a registered request."""
        request = self._get_request(gateway_id)
        return self._validator.validate_history(request)

    def validate_transition(
        self,
        gateway_id: str,
        target_state: GatewayState,
    ) -> ValidationResult:
        """Check whether *target_state* is reachable from the request's current state."""
        request = self._get_request(gateway_id)
        return self._validator.validate_transition(request, target_state)

    # ── Query ─────────────────────────────────────────────────────────────────

    def get(self, gateway_id: str) -> GatewayRequest:
        """Retrieve a request by gateway_id."""
        return self._registry.get(gateway_id)

    def all(self) -> List[GatewayRequest]:
        """All registered requests."""
        return self._registry.all()

    def active(self) -> List[GatewayRequest]:
        """Requests in an active (non-ended) state."""
        return self._registry.active()

    def completed(self) -> List[GatewayRequest]:
        """Requests in COMPLETED state."""
        return self._registry.completed()

    def failed(self) -> List[GatewayRequest]:
        """Requests in FAILED state."""
        return self._registry.failed()

    def cancelled(self) -> List[GatewayRequest]:
        """Requests in CANCELLED state."""
        return self._registry.cancelled()

    def archived(self) -> List[GatewayRequest]:
        """Requests in ARCHIVED state."""
        return self._registry.archived()

    def by_execution_id(self, execution_id: str) -> List[GatewayRequest]:
        """All requests for *execution_id*."""
        return self._registry.by_execution_id(execution_id)

    def by_portfolio_id(self, portfolio_id: str) -> List[GatewayRequest]:
        """All requests for *portfolio_id*."""
        return self._registry.by_portfolio_id(portfolio_id)

    def by_strategy_id(self, strategy_id: str) -> List[GatewayRequest]:
        """All requests for *strategy_id*."""
        return self._registry.by_strategy_id(strategy_id)

    def by_state(self, state: GatewayState) -> List[GatewayRequest]:
        """All requests in *state*."""
        return self._registry.by_state(state)

    # ── Statistics & observability ────────────────────────────────────────────

    def statistics(self) -> GatewayStatistics:
        """Return a copy of current lifecycle statistics."""
        with self._lock:
            return self._stats.copy()

    def request_count(self) -> int:
        """Total number of registered requests."""
        return self._registry.count

    # ── Global event listeners ────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[GatewayEvent], None]
    ) -> None:
        """
        Register a global listener that receives all lifecycle events from
        every request managed by this lifecycle instance.

        Listeners are wired into future requests at creation time.
        Existing requests are not affected.
        """
        with self._lock:
            self._event_listeners.append(listener)

    def remove_event_listener(
        self, listener: Callable[[GatewayEvent], None]
    ) -> None:
        """Remove a previously registered global event listener."""
        with self._lock:
            try:
                self._event_listeners.remove(listener)
            except ValueError:
                pass

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_request(self, gateway_id: str) -> GatewayRequest:
        """Retrieve a request from the registry; raise if not found."""
        return self._registry.get(gateway_id)

    def _fire_global_event(self, event: GatewayEvent) -> None:
        """Deliver *event* to all registered global listeners."""
        with self._lock:
            listeners = list(self._event_listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                pass
