"""iios/execution/positions/lifecycle/position.py
==================================================
Position — the core domain object for the IIOS Position Lifecycle.

Tracks all lifecycle state, quantities, prices, and PnL for a single
trading position.  Exposes a controlled ``transition_to()`` method that
enforces the state machine and appends immutable history records.

This class is NOT a LifecycleAwareMixin; it is a pure domain object.
Thread-safety is provided via an internal RLock.

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

import threading
import time
import uuid
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from .constants import (
    ACTOR_LIFECYCLE,
    ACTIVE_STATES,
    CLOSED_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    PositionDirection,
    PositionProduct,
    PositionState,
    VERSION,
)
from .exceptions import InvalidTransitionError
from .position_event import (
    PositionEvent,
    make_position_archived,
    make_position_closed,
    make_position_created,
    make_position_opened,
    make_position_partially_closed,
    make_position_recovered,
    make_position_updated,
)
from .position_history import PositionHistory
from .position_metadata import PositionMetadata
from .position_state import PositionStateRecord
from .position_transition import PositionTransition, make_transition


# ── Event type → factory mapping ──────────────────────────────────────────────

_STATE_EVENT_FACTORY: Dict[PositionState, Callable[..., PositionEvent]] = {
    PositionState.OPEN:             make_position_opened,
    PositionState.PARTIALLY_CLOSED: make_position_partially_closed,
    PositionState.CLOSED:           make_position_closed,
    PositionState.RECOVERED:        make_position_recovered,
    PositionState.ARCHIVED:         make_position_archived,
}


class Position:
    """
    Core domain object representing a single institutional trading position.

    Responsibilities
    ----------------
    * Hold all position identity and financial fields.
    * Enforce the state machine via ``transition_to()``.
    * Maintain an immutable, ordered transition and state history.
    * Emit domain events on lifecycle milestones.

    Non-responsibilities
    --------------------
    * No broker communication.
    * No execution routing.
    * No portfolio optimisation.
    * No risk calculations.
    """

    __slots__ = (
        # identity
        "_position_id", "_portfolio_id", "_strategy_id",
        "_decision_id", "_workflow_id", "_execution_id",
        "_correlation_id",
        # instrument
        "_instrument", "_exchange", "_product", "_direction",
        # quantities
        "_quantity", "_open_quantity", "_closed_quantity",
        # prices
        "_average_entry_price", "_average_exit_price",
        # pnl
        "_realized_pnl", "_unrealized_pnl",
        # state
        "_state",
        # timestamps
        "_created_at", "_updated_at",
        # internals
        "_history", "_metadata", "_lock",
        "_event_listeners",
    )

    def __init__(
        self,
        position_id:  str,
        portfolio_id: str,
        strategy_id:  str,
        decision_id:  str,
        workflow_id:  str,
        execution_id: str,
        instrument:   str,
        exchange:     str,
        product:      PositionProduct,
        direction:    PositionDirection,
        quantity:     Decimal,
        *,
        correlation_id:    str = "",
        open_quantity:     Optional[Decimal] = None,
        closed_quantity:   Optional[Decimal] = None,
        avg_entry_price:   Optional[Decimal] = None,
        avg_exit_price:    Optional[Decimal] = None,
        realized_pnl:      Optional[Decimal] = None,
        unrealized_pnl:    Optional[Decimal] = None,
        max_history:       int = 500,
    ) -> None:
        now = time.time()

        self._position_id   = position_id
        self._portfolio_id  = portfolio_id
        self._strategy_id   = strategy_id
        self._decision_id   = decision_id
        self._workflow_id   = workflow_id
        self._execution_id  = execution_id
        self._correlation_id = correlation_id

        self._instrument = instrument
        self._exchange   = exchange
        self._product    = product
        self._direction  = direction

        self._quantity        = quantity
        self._open_quantity   = open_quantity   if open_quantity   is not None else Decimal(0)
        self._closed_quantity = closed_quantity if closed_quantity is not None else Decimal(0)

        self._average_entry_price = avg_entry_price  if avg_entry_price  is not None else Decimal(0)
        self._average_exit_price  = avg_exit_price   if avg_exit_price   is not None else Decimal(0)

        self._realized_pnl   = realized_pnl   if realized_pnl   is not None else Decimal(0)
        self._unrealized_pnl = unrealized_pnl if unrealized_pnl is not None else Decimal(0)

        self._state      = PositionState.CREATED
        self._created_at = now
        self._updated_at = now

        self._history          = PositionHistory(max_history)
        self._metadata         = PositionMetadata()
        self._lock             = threading.RLock()
        self._event_listeners: List[Callable[[PositionEvent], None]] = []

        # Seed initial state record
        self._history.append_state(PositionStateRecord(state=PositionState.CREATED, entered_at=now))

    # ── Identity ──────────────────────────────────────────────────────────────

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
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def correlation_id(self) -> str:
        return self._correlation_id

    # ── Instrument ────────────────────────────────────────────────────────────

    @property
    def instrument(self) -> str:
        return self._instrument

    @property
    def exchange(self) -> str:
        return self._exchange

    @property
    def product(self) -> PositionProduct:
        return self._product

    @property
    def direction(self) -> PositionDirection:
        return self._direction

    # ── Quantities ────────────────────────────────────────────────────────────

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def open_quantity(self) -> Decimal:
        with self._lock:
            return self._open_quantity

    @property
    def closed_quantity(self) -> Decimal:
        with self._lock:
            return self._closed_quantity

    @property
    def fill_ratio(self) -> float:
        """Fraction of total quantity that is open (0.0 – 1.0)."""
        if self._quantity == Decimal(0):
            return 0.0
        with self._lock:
            return float(self._open_quantity / self._quantity)

    # ── Prices ────────────────────────────────────────────────────────────────

    @property
    def average_entry_price(self) -> Decimal:
        with self._lock:
            return self._average_entry_price

    @property
    def average_exit_price(self) -> Decimal:
        with self._lock:
            return self._average_exit_price

    # ── PnL ───────────────────────────────────────────────────────────────────

    @property
    def realized_pnl(self) -> Decimal:
        with self._lock:
            return self._realized_pnl

    @property
    def unrealized_pnl(self) -> Decimal:
        with self._lock:
            return self._unrealized_pnl

    @property
    def total_pnl(self) -> Decimal:
        with self._lock:
            return self._realized_pnl + self._unrealized_pnl

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def state(self) -> PositionState:
        with self._lock:
            return self._state

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._state in ACTIVE_STATES

    @property
    def is_closed(self) -> bool:
        with self._lock:
            return self._state in CLOSED_STATES

    @property
    def is_archived(self) -> bool:
        with self._lock:
            return self._state in TERMINAL_STATES

    @property
    def is_suspended(self) -> bool:
        with self._lock:
            from .constants import SUSPENDED_STATES
            return self._state in SUSPENDED_STATES

    # ── Timestamps ────────────────────────────────────────────────────────────

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        with self._lock:
            return self._updated_at

    # ── State machine ─────────────────────────────────────────────────────────

    def transition_to(
        self,
        new_state: PositionState,
        *,
        actor:    str = ACTOR_LIFECYCLE,
        reason:   str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PositionTransition:
        """
        Transition the position to *new_state*.

        Raises ``InvalidTransitionError`` if the transition is not allowed.
        Returns the ``PositionTransition`` record on success.
        """
        with self._lock:
            current = self._state
            allowed = VALID_TRANSITIONS.get(current, frozenset())

            if new_state not in allowed:
                raise InvalidTransitionError(self._position_id, current, new_state)

            now = time.time()

            # Close out the current state record
            self._history.update_last_state_exit(now)

            # Build the transition record
            transition = make_transition(
                self._position_id, current, new_state,
                actor=actor, reason=reason, metadata=metadata,
            )
            self._history.append_transition(transition)

            # Open the new state record
            self._history.append_state(PositionStateRecord(state=new_state, entered_at=now))

            # Commit
            self._state      = new_state
            self._updated_at = now

            # Emit domain event (outside lock held, but we hold RLock so re-entrant is safe)
            self._emit_state_event(new_state, actor)

            return transition

    # ── Field updates ─────────────────────────────────────────────────────────

    def update_quantities(
        self,
        open_quantity:   Decimal,
        closed_quantity: Decimal,
    ) -> None:
        """Update open and closed quantity fields."""
        with self._lock:
            self._open_quantity   = open_quantity
            self._closed_quantity = closed_quantity
            self._updated_at      = time.time()

    def update_prices(
        self,
        avg_entry: Optional[Decimal] = None,
        avg_exit:  Optional[Decimal] = None,
    ) -> None:
        """Update average entry / exit price fields."""
        with self._lock:
            if avg_entry is not None:
                self._average_entry_price = avg_entry
            if avg_exit is not None:
                self._average_exit_price = avg_exit
            self._updated_at = time.time()

    def update_pnl(
        self,
        realized:   Optional[Decimal] = None,
        unrealized: Optional[Decimal] = None,
    ) -> None:
        """Update realized and/or unrealized PnL fields."""
        with self._lock:
            if realized is not None:
                self._realized_pnl = realized
            if unrealized is not None:
                self._unrealized_pnl = unrealized
            self._updated_at = time.time()

    # ── Event subscription ────────────────────────────────────────────────────

    def add_event_listener(self, listener: Callable[[PositionEvent], None]) -> None:
        """Register a callback invoked on every lifecycle event."""
        with self._lock:
            self._event_listeners.append(listener)

    def remove_event_listener(self, listener: Callable[[PositionEvent], None]) -> None:
        with self._lock:
            try:
                self._event_listeners.remove(listener)
            except ValueError:
                pass

    def _emit_state_event(self, new_state: PositionState, actor: str) -> None:
        factory = _STATE_EVENT_FACTORY.get(new_state)
        if factory is None:
            # Generic update event for intermediate states (OPENING, CLOSING, etc.)
            factory = make_position_updated
        if factory is make_position_updated:
            event = factory(
                self._position_id,
                state=new_state,
                portfolio_id=self._portfolio_id,
                strategy_id=self._strategy_id,
                actor=actor,
            )
        else:
            event = factory(
                self._position_id,
                portfolio_id=self._portfolio_id,
                strategy_id=self._strategy_id,
                actor=actor,
            )
        for listener in list(self._event_listeners):
            try:
                listener(event)
            except Exception:  # noqa: BLE001
                pass

    # ── History ───────────────────────────────────────────────────────────────

    @property
    def history(self) -> PositionHistory:
        return self._history

    @property
    def metadata(self) -> PositionMetadata:
        return self._metadata

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "position_id":          self._position_id,
                "portfolio_id":         self._portfolio_id,
                "strategy_id":          self._strategy_id,
                "decision_id":          self._decision_id,
                "workflow_id":          self._workflow_id,
                "execution_id":         self._execution_id,
                "correlation_id":       self._correlation_id,
                "instrument":           self._instrument,
                "exchange":             self._exchange,
                "product":              self._product.value,
                "direction":            self._direction.value,
                "quantity":             str(self._quantity),
                "open_quantity":        str(self._open_quantity),
                "closed_quantity":      str(self._closed_quantity),
                "average_entry_price":  str(self._average_entry_price),
                "average_exit_price":   str(self._average_exit_price),
                "realized_pnl":         str(self._realized_pnl),
                "unrealized_pnl":       str(self._unrealized_pnl),
                "total_pnl":            str(self._realized_pnl + self._unrealized_pnl),
                "state":                self._state.value,
                "created_at":           self._created_at,
                "updated_at":           self._updated_at,
                "metadata":             self._metadata.to_dict(),
                "version":              VERSION,
            }

    def snapshot(self) -> Dict[str, Any]:
        """Return an immutable point-in-time snapshot (alias for to_dict)."""
        return self.to_dict()

    def __repr__(self) -> str:
        return (
            f"Position(id={self._position_id!r}, "
            f"instrument={self._instrument!r}, "
            f"direction={self._direction.value}, "
            f"qty={self._quantity}, "
            f"state={self._state.value})"
        )
