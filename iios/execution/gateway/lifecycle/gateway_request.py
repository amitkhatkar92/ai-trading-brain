"""iios/execution/gateway/lifecycle/gateway_request.py
==================================================
GatewayRequest — the core domain object for the IIOS
Execution Gateway Lifecycle.

Tracks all lifecycle state for a single gateway request.
Exposes a controlled ``transition_to()`` method that enforces the state
machine and appends immutable history records.

This class is NOT a LifecycleAwareMixin; it is a pure domain object.
Thread-safety is provided via an internal RLock.

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .constants import (
    ACTIVE_STATES,
    ACTOR_LIFECYCLE,
    ENDED_STATES,
    FAILURE_STATES,
    OUTCOME_STATES,
    SUCCESS_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    GatewayState,
    VERSION,
)
from .exceptions import InvalidGatewayTransitionError
from .gateway_context import GatewayContext
from .gateway_events import (
    GatewayEvent,
    make_gateway_archived,
    make_gateway_cancelled,
    make_gateway_completed,
    make_gateway_dispatched,
    make_gateway_failed,
    make_gateway_queued,
    make_gateway_received,
    make_gateway_validated,
)
from .gateway_history import GatewayHistory
from .gateway_metadata import GatewayMetadata
from .gateway_state import GatewayStateRecord
from .gateway_transition import GatewayTransition, make_gateway_transition


# ── State → event factory mapping ─────────────────────────────────────────────

_STATE_EVENT_FACTORY: Dict[GatewayState, Callable[..., GatewayEvent]] = {
    GatewayState.RECEIVED:   make_gateway_received,
    GatewayState.READY:      make_gateway_validated,
    GatewayState.QUEUED:     make_gateway_queued,
    GatewayState.DISPATCHED: make_gateway_dispatched,
    GatewayState.COMPLETED:  make_gateway_completed,
    GatewayState.FAILED:     make_gateway_failed,
    GatewayState.CANCELLED:  make_gateway_cancelled,
    GatewayState.ARCHIVED:   make_gateway_archived,
}


class GatewayRequest:
    """
    Core domain object representing a single institutional execution gateway request.

    Responsibilities
    ----------------
    * Hold all gateway identity and lifecycle fields.
    * Enforce the state machine via ``transition_to()``.
    * Maintain an immutable, ordered transition and state history.
    * Emit domain events on lifecycle milestones.

    Non-responsibilities
    --------------------
    * No routing logic.
    * No broker communication.
    * No order execution.
    * No risk calculations.
    """

    __slots__ = (
        # identity
        "_gateway_id", "_execution_id", "_workflow_id", "_order_id",
        "_position_id", "_portfolio_id", "_strategy_id", "_decision_id",
        "_correlation_id",
        # versioning
        "_version",
        # state
        "_state",
        # timestamps
        "_created_at", "_updated_at", "_completion_time",
        # internals
        "_history", "_metadata", "_context",
        "_lock", "_event_listeners",
    )

    def __init__(
        self,
        gateway_id:     str,
        execution_id:   str,
        workflow_id:    str,
        order_id:       str,
        position_id:    str,
        portfolio_id:   str,
        strategy_id:    str,
        decision_id:    str,
        *,
        correlation_id: str                       = "",
        max_history:    int                       = 500,
        context:        Optional[GatewayContext]  = None,
    ) -> None:
        now = time.time()

        self._gateway_id     = gateway_id
        self._execution_id   = execution_id
        self._workflow_id    = workflow_id
        self._order_id       = order_id
        self._position_id    = position_id
        self._portfolio_id   = portfolio_id
        self._strategy_id    = strategy_id
        self._decision_id    = decision_id
        self._correlation_id = correlation_id

        self._version         = VERSION
        self._state           = GatewayState.CREATED
        self._created_at      = now
        self._updated_at      = now
        self._completion_time: Optional[float] = None

        self._history         = GatewayHistory(max_size=max_history)
        self._metadata        = GatewayMetadata()
        self._context         = context
        self._lock            = threading.RLock()
        self._event_listeners: List[Callable[[GatewayEvent], None]] = []

        # Seed history with the initial CREATED state record
        self._history.append_state(GatewayStateRecord(
            state=GatewayState.CREATED,
            entered_at=now,
        ))

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def gateway_id(self) -> str:
        return self._gateway_id

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def position_id(self) -> str:
        return self._position_id

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def decision_id(self) -> str:
        return self._decision_id

    @property
    def correlation_id(self) -> str:
        return self._correlation_id

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def state(self) -> GatewayState:
        with self._lock:
            return self._state

    @property
    def version(self) -> str:
        return self._version

    # ── Timestamps ────────────────────────────────────────────────────────────

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        with self._lock:
            return self._updated_at

    @property
    def completion_time(self) -> Optional[float]:
        with self._lock:
            return self._completion_time

    # ── Derived flags ─────────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self.state in ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    @property
    def is_ended(self) -> bool:
        return self.state in ENDED_STATES

    @property
    def is_completed(self) -> bool:
        return self.state in SUCCESS_STATES

    @property
    def is_failed(self) -> bool:
        return self.state == GatewayState.FAILED

    @property
    def is_cancelled(self) -> bool:
        return self.state == GatewayState.CANCELLED

    @property
    def is_archived(self) -> bool:
        return self.state in TERMINAL_STATES

    @property
    def lifecycle_elapsed_ms(self) -> float:
        """Milliseconds since this request was created."""
        with self._lock:
            end = self._completion_time or time.time()
        return (end - self._created_at) * 1_000.0

    # ── Internals ─────────────────────────────────────────────────────────────

    @property
    def history(self) -> GatewayHistory:
        return self._history

    @property
    def metadata(self) -> GatewayMetadata:
        return self._metadata

    @property
    def context(self) -> Optional[GatewayContext]:
        return self._context

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def transition_to(
        self,
        new_state: GatewayState,
        *,
        actor:    str                     = ACTOR_LIFECYCLE,
        reason:   str                     = "",
        metadata: Dict[str, Any] | None   = None,
    ) -> GatewayTransition:
        """
        Transition this request to *new_state*.

        Enforces the strict state machine defined in ``VALID_TRANSITIONS``.
        Appends immutable records to both the transition and state histories.
        Fires registered event listeners.

        Parameters
        ----------
        new_state : GatewayState
            Target state.
        actor : str
            Identity of the component triggering the transition.
        reason : str
            Human-readable reason for the transition.
        metadata : dict, optional
            Arbitrary extra data attached to this specific transition.

        Returns
        -------
        GatewayTransition
            The recorded transition.

        Raises
        ------
        InvalidGatewayTransitionError
            If the transition is not permitted by the state machine.
        """
        with self._lock:
            current = self._state
            allowed = VALID_TRANSITIONS.get(current, frozenset())

            if new_state not in allowed:
                raise InvalidGatewayTransitionError(
                    self._gateway_id, current, new_state
                )

            now = time.time()

            # Stamp exit on previous state record
            self._history.update_last_state_exit(now)

            # Build & record transition
            transition = make_gateway_transition(
                self._gateway_id, current, new_state,
                actor=actor, reason=reason, metadata=metadata,
            )
            self._history.append_transition(transition)

            # Record new state occupancy
            self._history.append_state(GatewayStateRecord(
                state=new_state, entered_at=now
            ))

            # Update object state
            self._state      = new_state
            self._updated_at = now

            # Stamp completion time on terminal/outcome states
            if new_state in ENDED_STATES:
                self._completion_time = now

        # Emit domain event outside the lock
        event_factory = _STATE_EVENT_FACTORY.get(new_state)
        if event_factory:
            event = event_factory(
                self._gateway_id,
                execution_id=self._execution_id,
                portfolio_id=self._portfolio_id,
                strategy_id=self._strategy_id,
                actor=actor,
                metadata=metadata,
            )
            self._fire_event(event)

        return transition

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_event_listener(self, listener: Callable[[GatewayEvent], None]) -> None:
        """Register a callable that will be invoked on every lifecycle event."""
        with self._lock:
            self._event_listeners.append(listener)

    def remove_event_listener(self, listener: Callable[[GatewayEvent], None]) -> None:
        """Deregister a previously registered event listener."""
        with self._lock:
            try:
                self._event_listeners.remove(listener)
            except ValueError:
                pass

    def _fire_event(self, event: GatewayEvent) -> None:
        """Invoke all registered listeners with *event*."""
        with self._lock:
            listeners = list(self._event_listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                pass  # never let a listener crash the lifecycle

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Return a point-in-time dictionary representation."""
        with self._lock:
            state       = self._state
            updated_at  = self._updated_at
            compl_time  = self._completion_time

        return {
            "gateway_id":       self._gateway_id,
            "execution_id":     self._execution_id,
            "workflow_id":      self._workflow_id,
            "order_id":         self._order_id,
            "position_id":      self._position_id,
            "portfolio_id":     self._portfolio_id,
            "strategy_id":      self._strategy_id,
            "decision_id":      self._decision_id,
            "correlation_id":   self._correlation_id,
            "state":            state.value,
            "version":          self._version,
            "created_at":       self._created_at,
            "updated_at":       updated_at,
            "completion_time":  compl_time,
            "is_active":        state in ACTIVE_STATES,
            "is_terminal":      state in TERMINAL_STATES,
            "is_completed":     state in SUCCESS_STATES,
            "lifecycle_elapsed_ms": self.lifecycle_elapsed_ms,
            "transition_count": self._history.transition_count,
            "metadata":         self._metadata.to_dict(),
        }

    def __repr__(self) -> str:
        return (
            f"GatewayRequest(gateway_id={self._gateway_id!r}, "
            f"state={self._state.value}, "
            f"execution_id={self._execution_id!r})"
        )
