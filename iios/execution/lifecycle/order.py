"""iios/execution/lifecycle/order.py
==================================================
Order — the core order entity for the IIOS Order Lifecycle.

An Order is the single source of truth for an individual
instruction to buy or sell an instrument.  It encapsulates:

  • Identity and linkage  (order_id, context)
  • Instrument spec       (instrument, exchange, side, order_type)
  • Quantities / prices   (quantity, filled_quantity, limit_price, …)
  • Lifecycle state       (current state, immutable history)
  • Live statistics
  • Extensible metadata

Thread Safety
-------------
Order owns a threading.RLock.  All state mutations are
applied through the internal _apply_transition() and
_apply_fill() methods, which are only called by OrderRegistry
while holding the registry-level lock.  External callers
treat Order as read-only.
"""
from __future__ import annotations

import threading
import time
from decimal import Decimal
from typing import Any, Optional

from .constants import OrderSide, OrderType, TimeInForce
from .order_context import OrderContext
from .order_history import OrderHistory
from .order_metadata import OrderMetadata
from .order_state import ACTIVE_STATES, TERMINAL_STATES, OrderState
from .order_statistics import OrderStatistics
from .order_transition import OrderTransition


class Order:
    """
    Institutional order entity.

    Construction is done via OrderFactory.  All state mutations
    are routed through OrderRegistry — do not call _apply_*
    methods directly from outside this package.
    """

    __slots__ = (
        "order_id", "context",
        "instrument", "exchange", "side", "order_type", "time_in_force",
        "quantity", "limit_price", "stop_price",
        "state", "filled_quantity", "average_price",
        "child_order_ids", "created_at", "updated_at",
        "history", "metadata", "statistics",
        "_lock",
    )

    def __init__(
        self,
        order_id:      str,
        context:       OrderContext,
        instrument:    str,
        exchange:      str,
        side:          OrderSide,
        order_type:    OrderType,
        quantity:      Decimal,
        limit_price:   Optional[Decimal]   = None,
        stop_price:    Optional[Decimal]   = None,
        time_in_force: TimeInForce         = TimeInForce.DAY,
        metadata:      Optional[OrderMetadata] = None,
    ) -> None:
        now = time.time()

        # Identity
        self.order_id: str          = order_id
        self.context:  OrderContext = context

        # Instrument spec (immutable after creation)
        self.instrument:    str         = instrument
        self.exchange:      str         = exchange
        self.side:          OrderSide   = side
        self.order_type:    OrderType   = order_type
        self.time_in_force: TimeInForce = time_in_force
        self.quantity:      Decimal     = quantity
        self.limit_price:   Optional[Decimal] = limit_price
        self.stop_price:    Optional[Decimal] = stop_price

        # Mutable execution state
        self.state:           OrderState       = OrderState.CREATED
        self.filled_quantity: Decimal          = Decimal("0")
        self.average_price:   Optional[Decimal] = None
        self.child_order_ids: list[str]        = []

        # Timestamps
        self.created_at: float = now
        self.updated_at: float = now

        # Supporting subsystems
        self.history:    OrderHistory    = OrderHistory(order_id)
        self.metadata:   OrderMetadata   = (
            metadata if metadata is not None
            else OrderMetadata(source="order_factory")
        )
        self.statistics: OrderStatistics = OrderStatistics(
            order_id=order_id, created_at=now
        )

        # Thread safety (RLock — reentrant for same-thread calls)
        self._lock: threading.RLock = threading.RLock()

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def remaining_quantity(self) -> Decimal:
        """Quantity not yet filled."""
        return self.quantity - self.filled_quantity

    @property
    def fill_pct(self) -> float:
        """Fill percentage (0.0–100.0)."""
        if self.quantity == 0:
            return 0.0
        return float(self.filled_quantity / self.quantity * 100)

    @property
    def is_terminal(self) -> bool:
        """True iff the order is in a terminal state."""
        return self.state in TERMINAL_STATES

    @property
    def is_active(self) -> bool:
        """True iff the order is in a live-market active state."""
        return self.state in ACTIVE_STATES

    @property
    def parent_order_id(self) -> Optional[str]:
        """Parent order ID for child orders; None for top-level orders."""
        return self.context.parent_order_id

    # ── Internal mutations (OrderRegistry only) ───────────────────────────────

    def _apply_transition(self, transition: OrderTransition) -> None:
        """Apply a validated state transition.  Called ONLY by OrderRegistry."""
        with self._lock:
            self.state      = transition.to_state
            self.updated_at = transition.occurred_at
            self.history.record(transition)
            self.metadata.bump_version(transition.occurred_at)
            self.statistics.on_transition(transition)

    def _apply_fill(
        self,
        fill_qty:    Decimal,
        fill_price:  Decimal,
        occurred_at: float,
    ) -> None:
        """Apply a fill.  Called ONLY by OrderRegistry after validating."""
        with self._lock:
            prev_filled = self.filled_quantity
            new_filled  = prev_filled + fill_qty

            # Running weighted average price
            if self.average_price is None:
                self.average_price = fill_price
            else:
                self.average_price = (
                    (self.average_price * prev_filled + fill_price * fill_qty)
                    / new_filled
                )

            self.filled_quantity = new_filled
            self.updated_at      = occurred_at

            self.statistics.on_fill(
                fill_qty    = fill_qty,
                total_qty   = self.quantity,
                filled_qty  = new_filled,
                occurred_at = occurred_at,
            )

    def _add_child(self, child_order_id: str) -> None:
        """Register a child order.  Called ONLY by OrderRegistry."""
        with self._lock:
            if child_order_id not in self.child_order_ids:
                self.child_order_ids.append(child_order_id)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "order_id":           self.order_id,
                "context":            self.context.to_dict(),
                "instrument":         self.instrument,
                "exchange":           self.exchange,
                "side":               self.side.value,
                "order_type":         self.order_type.value,
                "time_in_force":      self.time_in_force.value,
                "quantity":           str(self.quantity),
                "filled_quantity":    str(self.filled_quantity),
                "remaining_quantity": str(self.remaining_quantity),
                "average_price":      str(self.average_price) if self.average_price else None,
                "limit_price":        str(self.limit_price)   if self.limit_price   else None,
                "stop_price":         str(self.stop_price)    if self.stop_price    else None,
                "state":              self.state.value,
                "fill_pct":           round(self.fill_pct, 4),
                "is_terminal":        self.is_terminal,
                "is_active":          self.is_active,
                "child_order_ids":    list(self.child_order_ids),
                "parent_order_id":    self.parent_order_id,
                "created_at":         self.created_at,
                "updated_at":         self.updated_at,
                "metadata":           self.metadata.to_dict(),
                "statistics":         self.statistics.to_dict(),
            }

    def __repr__(self) -> str:
        return (
            f"Order(id={self.order_id!r}, state={self.state.value}, "
            f"instrument={self.instrument!r}, side={self.side.value}, "
            f"qty={self.quantity}, filled={self.filled_quantity})"
        )
