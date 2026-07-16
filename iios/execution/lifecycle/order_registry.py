"""iios/execution/lifecycle/order_registry.py
==================================================
OrderRegistry — thread-safe, lifecycle-aware store for
all Order objects managed by the IIOS Order Lifecycle.

Responsibilities
----------------
• Register new orders (enforce capacity and uniqueness).
• Apply state transitions (validate → record → emit event).
• Apply fill events (validate → update order → trigger transition).
• Secondary indexes: portfolio_id, strategy_id.
• Query: active orders, by portfolio, by strategy, by state.
• Statistics: registry-level counters.

Framework adoption (IIOS v1.0)
-------------------------------
Lifecycle : LifecycleAwareMixin  (_on_start / _on_stop)
Logging   : get_logger / get_audit_logger
Errors    : get_error_manager / ErrorContext / report_failure
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin, EngineState
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.errors.error_context import ErrorContext

from .constants import (
    REGISTRY_SYSTEM_ID, VERSION,
    DEFAULT_MAX_ORDERS, ACTOR_SYSTEM, ACTOR_EXCHANGE,
)
from .exceptions import (
    DuplicateOrderError, InvalidFillError, InvalidTransitionError,
    OrderNotFoundError, OrderTerminalError, OrderValidationError,
    RegistryCapacityError, RegistryNotRunningError,
)
from .order import Order
from .order_event import OrderEvent, OrderEventType, event_type_for_state, make_event
from .order_state import (
    FILL_STATES, OrderState, can_transition, is_terminal,
)
from .order_transition import OrderTransition, make_transition
from .order_validation import OrderValidator

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID,
                          component="OrderRegistry")


@dataclass
class RegistryStatistics:
    """Point-in-time registry counters."""
    total_registered:  int
    total_transitions: int
    total_fills:       int
    active_count:      int
    by_state:          Dict[str, int]
    capacity:          int
    utilisation_pct:   float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_registered":  self.total_registered,
            "total_transitions": self.total_transitions,
            "total_fills":       self.total_fills,
            "active_count":      self.active_count,
            "by_state":          self.by_state,
            "capacity":          self.capacity,
            "utilisation_pct":   round(self.utilisation_pct, 2),
        }


class OrderRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry of Order objects.

    All mutating operations (register, apply_transition, apply_fill)
    hold the registry lock for the duration of the operation.
    Read operations snapshot the relevant data structures and
    release the lock before returning.

    Parameters
    ----------
    max_orders : int
        Maximum number of orders the registry will accept.
    """

    SYSTEM_ID = REGISTRY_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_orders: int = DEFAULT_MAX_ORDERS) -> None:
        super().__init__()
        self._max_orders: int  = max(1, max_orders)
        self._validator         = OrderValidator()

        # Primary store
        self._orders: Dict[str, Order] = {}
        # Secondary indexes
        self._by_portfolio: Dict[str, List[str]] = defaultdict(list)
        self._by_strategy:  Dict[str, List[str]] = defaultdict(list)
        self._by_state:     Dict[str, List[str]] = defaultdict(list)

        # Registry-level metrics
        self._total_registered:  int = 0
        self._total_transitions: int = 0
        self._total_fills:       int = 0

        # Event listeners (called after each successful transition/fill)
        self._listeners: List[Callable[[OrderEvent], None]] = []

        # Registry-level lock (RLock for reentrant access within the same thread)
        self._lock: threading.RLock = threading.RLock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("OrderRegistry started.", max_orders=self._max_orders)
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, "stopped", "started", VERSION)

    def _on_stop(self) -> None:
        with self._lock:
            count = len(self._orders)
        _log.info("OrderRegistry stopped.", active_orders=count)
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, "started", "stopped", VERSION)

    @property
    def is_running(self) -> bool:
        """True when the registry is in the RUNNING lifecycle state."""
        return self.lifecycle_state() == EngineState.RUNNING

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, order: Order) -> None:
        """
        Register a new order.

        Raises
        ------
        RegistryNotRunningError
            If the registry has not been started.
        RegistryCapacityError
            If max_orders would be exceeded.
        DuplicateOrderError
            If order.order_id already exists in the registry.
        OrderValidationError
            If the order fails structural validation.
        """
        self._assert_running()
        ctx = ErrorContext(
            engine_id = self.SYSTEM_ID,
            operation = "register",
            stage     = "order_registry",
        )
        try:
            result = self._validator.validate_new(order)
            if not result:
                raise OrderValidationError(
                    f"Order {order.order_id!r} failed validation: "
                    + "; ".join(result.errors),
                    code    = "EL-003",
                    context = {"order_id": order.order_id, "errors": list(result.errors)},
                )

            with self._lock:
                if len(self._orders) >= self._max_orders:
                    raise RegistryCapacityError(
                        f"Registry capacity ({self._max_orders}) reached.",
                        code = "EL-005",
                    )
                if order.order_id in self._orders:
                    raise DuplicateOrderError(
                        f"Order {order.order_id!r} is already registered.",
                        code = "EL-004",
                    )
                self._orders[order.order_id] = order
                self._by_portfolio[order.context.portfolio_id].append(order.order_id)
                self._by_strategy[order.context.strategy_id].append(order.order_id)
                self._by_state[order.state.value].append(order.order_id)
                self._total_registered += 1

            _log.info(
                "Order registered.",
                order_id     = order.order_id,
                instrument   = order.instrument,
                portfolio_id = order.context.portfolio_id,
                strategy_id  = order.context.strategy_id,
            )
        except (OrderValidationError, RegistryCapacityError,
                DuplicateOrderError, RegistryNotRunningError):
            raise
        except Exception as exc:
            _get_err_mgr().report_failure(self.SYSTEM_ID, exc, ctx)
            _log.exception("Unexpected error in register.", exc=exc,
                           order_id=order.order_id)
            raise

    # ── State transition ───────────────────────────────────────────────────────

    def apply_transition(
        self,
        order_id:   str,
        to_state:   OrderState,
        *,
        reason:     str,
        actor:      str  = ACTOR_SYSTEM,
        metadata:   Optional[Dict[str, Any]] = None,
        occurred_at: Optional[float] = None,
    ) -> tuple[Order, OrderTransition, OrderEvent]:
        """
        Apply a validated state transition to the specified order.

        Returns
        -------
        (order, transition, event)

        Raises
        ------
        OrderNotFoundError, InvalidTransitionError, OrderTerminalError
        """
        self._assert_running()
        ctx = ErrorContext(
            engine_id = self.SYSTEM_ID,
            operation = "apply_transition",
            stage     = "order_registry",
        )
        try:
            with self._lock:
                order = self._get_or_raise(order_id)

                if is_terminal(order.state):
                    raise OrderTerminalError(
                        f"Order {order_id!r} is in terminal state "
                        f"{order.state.value!r}.",
                        code = "EL-006",
                        context = {"order_id": order_id,
                                   "state": order.state.value},
                    )

                result = self._validator.validate_transition(order, to_state)
                if not result:
                    raise InvalidTransitionError(
                        from_state = order.state.value,
                        to_state   = to_state.value,
                        order_id   = order_id,
                    )

                now = occurred_at if occurred_at is not None else time.time()
                transition = make_transition(
                    order_id    = order_id,
                    from_state  = order.state,
                    to_state    = to_state,
                    reason      = reason,
                    actor       = actor,
                    metadata    = metadata,
                    occurred_at = now,
                )

                # Update secondary state index
                old_state_val = order.state.value
                self._by_state[old_state_val] = [
                    oid for oid in self._by_state.get(old_state_val, [])
                    if oid != order_id
                ]
                self._by_state[to_state.value].append(order_id)

                order._apply_transition(transition)
                self._total_transitions += 1

                event = make_event(
                    order_id    = order_id,
                    event_type  = event_type_for_state(to_state),
                    transition  = transition,
                    occurred_at = now,
                )

            # Dispatch outside the lock to avoid deadlock in listeners
            self._dispatch(event)
            _log.info(
                "Transition applied.",
                order_id   = order_id,
                from_state = transition.from_state.value,
                to_state   = to_state.value,
                actor      = actor,
            )
            return order, transition, event

        except (OrderNotFoundError, InvalidTransitionError,
                OrderTerminalError, RegistryNotRunningError):
            raise
        except Exception as exc:
            _get_err_mgr().report_failure(self.SYSTEM_ID, exc, ctx)
            _log.exception("Unexpected error in apply_transition.", exc=exc,
                           order_id=order_id)
            raise

    # ── Fill ──────────────────────────────────────────────────────────────────

    def apply_fill(
        self,
        order_id:   str,
        fill_qty:   Decimal,
        fill_price: Decimal,
        *,
        actor:       str   = ACTOR_EXCHANGE,
        occurred_at: Optional[float] = None,
    ) -> tuple[Order, OrderTransition, OrderEvent]:
        """
        Apply a fill to *order_id* and automatically advance its state.

        Determines the correct target state:
          • remaining_quantity → 0  ⟹  FILLED
          • remaining_quantity > 0  ⟹  PARTIALLY_FILLED

        Returns
        -------
        (order, transition, event)

        Raises
        ------
        OrderNotFoundError, InvalidFillError
        """
        self._assert_running()
        ctx = ErrorContext(
            engine_id = self.SYSTEM_ID,
            operation = "apply_fill",
            stage     = "order_registry",
        )
        try:
            with self._lock:
                order = self._get_or_raise(order_id)
                result = self._validator.validate_fill(order, fill_qty, fill_price)
                if not result:
                    raise InvalidFillError(
                        f"Fill validation failed for {order_id!r}: "
                        + "; ".join(result.errors),
                        code    = "EL-007",
                        context = {"order_id": order_id,
                                   "errors":   list(result.errors)},
                    )

                now = occurred_at if occurred_at is not None else time.time()
                order._apply_fill(fill_qty, fill_price, now)
                self._total_fills += 1

                # Determine target state
                is_complete = order.remaining_quantity <= 0
                to_state    = OrderState.FILLED if is_complete else OrderState.PARTIALLY_FILLED

                # Record state transition (may be PARTIALLY_FILLED → PARTIALLY_FILLED)
                transition = make_transition(
                    order_id    = order_id,
                    from_state  = order.state,
                    to_state    = to_state,
                    reason      = (
                        "order fully filled"
                        if is_complete
                        else f"partial fill: {fill_qty} @ {fill_price}"
                    ),
                    actor       = actor,
                    metadata    = {
                        "fill_qty":   str(fill_qty),
                        "fill_price": str(fill_price),
                        "is_complete": is_complete,
                    },
                    occurred_at = now,
                )

                old_state_val = order.state.value
                self._by_state[old_state_val] = [
                    oid for oid in self._by_state.get(old_state_val, [])
                    if oid != order_id
                ]
                self._by_state[to_state.value].append(order_id)

                order._apply_transition(transition)
                self._total_transitions += 1

                event_type = (
                    OrderEventType.ORDER_FILLED
                    if is_complete
                    else OrderEventType.ORDER_PARTIALLY_FILLED
                )
                event = make_event(
                    order_id    = order_id,
                    event_type  = event_type,
                    transition  = transition,
                    payload     = {
                        "fill_qty":    str(fill_qty),
                        "fill_price":  str(fill_price),
                        "fill_pct":    round(order.fill_pct, 4),
                        "is_complete": is_complete,
                    },
                    occurred_at = now,
                )

            self._dispatch(event)
            _log.info(
                "Fill applied.",
                order_id   = order_id,
                fill_qty   = str(fill_qty),
                fill_price = str(fill_price),
                fill_pct   = round(order.fill_pct, 4),
                complete   = is_complete,
            )
            return order, transition, event

        except (OrderNotFoundError, InvalidFillError, RegistryNotRunningError):
            raise
        except Exception as exc:
            _get_err_mgr().report_failure(self.SYSTEM_ID, exc, ctx)
            _log.exception("Unexpected error in apply_fill.", exc=exc,
                           order_id=order_id)
            raise

    # ── Queries ───────────────────────────────────────────────────────────────

    def get(self, order_id: str) -> Order:
        """Return the Order for *order_id* or raise OrderNotFoundError."""
        self._assert_running()
        with self._lock:
            return self._get_or_raise(order_id)

    def contains(self, order_id: str) -> bool:
        """Return True iff *order_id* is registered."""
        with self._lock:
            return order_id in self._orders

    def get_by_portfolio(self, portfolio_id: str) -> List[Order]:
        """Return all orders for *portfolio_id*."""
        with self._lock:
            ids = list(self._by_portfolio.get(portfolio_id, []))
        return [self._orders[oid] for oid in ids if oid in self._orders]

    def get_by_strategy(self, strategy_id: str) -> List[Order]:
        """Return all orders for *strategy_id*."""
        with self._lock:
            ids = list(self._by_strategy.get(strategy_id, []))
        return [self._orders[oid] for oid in ids if oid in self._orders]

    def get_by_state(self, state: OrderState) -> List[Order]:
        """Return all orders currently in *state*."""
        with self._lock:
            ids = list(self._by_state.get(state.value, []))
        return [self._orders[oid] for oid in ids if oid in self._orders]

    def get_active(self) -> List[Order]:
        """Return all orders in an ACTIVE state."""
        from .order_state import ACTIVE_STATES
        with self._lock:
            return [
                o for o in self._orders.values()
                if o.state in ACTIVE_STATES
            ]

    def count(self) -> int:
        """Current number of registered orders."""
        with self._lock:
            return len(self._orders)

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_listener(self, listener: Callable[[OrderEvent], None]) -> None:
        """Register a callback invoked after every state change / fill."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[OrderEvent], None]) -> None:
        """Unregister a callback."""
        with self._lock:
            self._listeners = [l for l in self._listeners if l != listener]

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> RegistryStatistics:
        """Return a point-in-time registry statistics snapshot."""
        with self._lock:
            by_state = {
                k: len(v)
                for k, v in self._by_state.items()
                if v
            }
            active  = sum(
                1 for o in self._orders.values() if o.is_active
            )
            total   = len(self._orders)
            util    = (total / self._max_orders * 100) if self._max_orders else 0.0
        return RegistryStatistics(
            total_registered  = self._total_registered,
            total_transitions = self._total_transitions,
            total_fills       = self._total_fills,
            active_count      = active,
            by_state          = by_state,
            capacity          = self._max_orders,
            utilisation_pct   = util,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_or_raise(self, order_id: str) -> Order:
        """Return order or raise OrderNotFoundError.  Must hold self._lock."""
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(
                f"Order {order_id!r} not found in registry.",
                code    = "EL-002",
                context = {"order_id": order_id},
            )
        return order

    def _dispatch(self, event: OrderEvent) -> None:
        """Call all registered listeners.  Called outside the registry lock."""
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                _log.warning(
                    "OrderRegistry listener raised an exception; ignoring.",
                    exc=exc,
                )

    def _assert_running(self) -> None:
        """Raise RegistryNotRunningError if the registry is not RUNNING."""
        if not self.is_running:
            raise RegistryNotRunningError(
                "OrderRegistry is not running.  Call start() first.",
                code = "EL-008",
            )
