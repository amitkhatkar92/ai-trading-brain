"""iios/execution/orders/order_manager.py

Central OMS coordinator — wires all subsystems together and implements the
full order workflow: create → validate → submit → fill / cancel / modify.

No broker API calls are made here.  Broker adapters will plug into the OMS
through a routing layer implemented separately.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from .order_constants import (
    CANCELLABLE_STATUSES,
    FillStatus,
    MODIFIABLE_STATUSES,
    OMS_SYSTEM_ID,
    OMS_VERSION,
    QueueType,
    OrderStatus,
)
from .order_exceptions import (
    InvalidOrderStatusError,
    OMSNotInitializedError,
    OrderValidationError,
)
from .core.order import Order
from .core.order_execution import OrderExecution
from .core.order_history import OrderHistory
from .core.order_request import OrderRequest
from .core.order_response import OrderResponse
from .core.order_statistics import OrderStatistics
from .lifecycle.lifecycle_engine import LifecycleEngine
from .order_factory import OrderFactory
from .order_registry import OrderRegistry
from .queue.queue_manager import QueueManager
from .tracking.execution_tracker import ExecutionTracker
from .tracking.order_monitor import OrderMonitor
from .tracking.order_tracker import OrderTracker
from .tracking.status_tracker import StatusTracker
from .validation.validation_engine import ValidationEngine

_log = logging.getLogger(__name__)


class OrderManager:
    """Orchestrates the full order lifecycle.

    All public methods are thread-safe.  A single ``threading.RLock``
    serialises mutations to ``_stats``; the individual subsystems carry
    their own locks for finer-grained concurrency.
    """

    def __init__(
        self,
        registry:           OrderRegistry   | None = None,
        history:            OrderHistory    | None = None,
        validation_engine:  ValidationEngine| None = None,
        queue_manager:      QueueManager    | None = None,
        order_tracker:      OrderTracker    | None = None,
        status_tracker:     StatusTracker   | None = None,
        execution_tracker:  ExecutionTracker| None = None,
    ) -> None:
        self._registry          = registry          or OrderRegistry()
        self._history           = history           or OrderHistory()
        self._validation        = validation_engine or ValidationEngine()
        self._queue_mgr         = queue_manager     or QueueManager()
        self._order_tracker     = order_tracker     or OrderTracker()
        self._status_tracker    = status_tracker    or StatusTracker()
        self._execution_tracker = execution_tracker or ExecutionTracker()
        self._factory           = OrderFactory()
        self._lifecycle         = LifecycleEngine(self._history)
        self._monitor           = OrderMonitor(
            self._order_tracker,
            self._status_tracker,
            self._execution_tracker,
            self._queue_mgr,
        )
        self._stats = OrderStatistics()
        self._lock  = threading.RLock()

    # ── Create ────────────────────────────────────────────────────────────────

    def create_order(self, request: OrderRequest) -> Order:
        """Validate *request*, allocate an Order, and advance it to VALIDATED.

        Raises
        ------
        OrderValidationError
            If any mandatory validation rule fails.
        """
        t0 = time.perf_counter()

        # 1. Validate the request
        report = self._validation.validate(request)
        if not report.passed:
            raise OrderValidationError(
                f"Validation failed for {request.ticker!r}",
                errors=report.errors,
            )

        # 2. Build the Order entity
        order = self._factory.create(request)

        # 3. Register (DRAFT state)
        self._registry.register(order)
        self._order_tracker.track(order)
        self._status_tracker.increment(order.status)   # DRAFT

        # 4. DRAFT → CREATED → VALIDATED
        self._lifecycle.create(order)
        self._status_tracker.move(OrderStatus.DRAFT, OrderStatus.CREATED)

        self._lifecycle.validate(order)
        self._status_tracker.move(OrderStatus.CREATED, OrderStatus.VALIDATED)

        # 5. Persist in-place updates
        self._registry.update(order)
        self._order_tracker.update(order)

        # 6. Counters
        with self._lock:
            self._stats.orders_total   += 1
            self._stats.orders_created += 1

        dur_ms = (time.perf_counter() - t0) * 1_000.0
        _log.info(
            "OMS created order=%s ticker=%s qty=%s side=%s %.1f ms",
            order.order_id, order.ticker, order.quantity, order.side.value, dur_ms,
        )
        return order

    # ── Submit ────────────────────────────────────────────────────────────────

    def submit_order(self, order_id: str) -> OrderResponse:
        """Approve, enqueue and submit a VALIDATED (or APPROVED) order."""
        t0    = time.perf_counter()
        order = self._registry.get(order_id)

        if order.status not in {OrderStatus.VALIDATED, OrderStatus.APPROVED}:
            raise InvalidOrderStatusError(
                order_id=order_id,
                from_status=order.status.value,
                to_status=OrderStatus.SUBMITTED.value,
            )

        # VALIDATED → APPROVED
        if order.status == OrderStatus.VALIDATED:
            self._lifecycle.approve(order)
            self._status_tracker.move(OrderStatus.VALIDATED, OrderStatus.APPROVED)

        # APPROVED → QUEUED
        self._lifecycle.enqueue(order)
        self._status_tracker.move(OrderStatus.APPROVED, OrderStatus.QUEUED)
        self._queue_mgr.enqueue(order, QueueType.PRIORITY)

        # QUEUED → SUBMITTED
        self._lifecycle.submit(order)
        self._status_tracker.move(OrderStatus.QUEUED, OrderStatus.SUBMITTED)

        self._registry.update(order)
        self._order_tracker.update(order)

        with self._lock:
            self._stats.orders_submitted += 1

        dur_ms = (time.perf_counter() - t0) * 1_000.0
        _log.info("OMS submitted order=%s %.1f ms", order_id, dur_ms)
        return OrderResponse(
            order_id=order_id,
            request_id=order.request_id,
            status=order.status,
            success=True,
            order=order,
            duration_ms=dur_ms,
        )

    # ── Acknowledge ───────────────────────────────────────────────────────────

    def acknowledge_order(self, order_id: str) -> Order:
        """Advance SUBMITTED → ACKNOWLEDGED (broker confirmation)."""
        order = self._registry.get(order_id)
        self._lifecycle.acknowledge(order)
        self._status_tracker.move(OrderStatus.SUBMITTED, OrderStatus.ACKNOWLEDGED)
        self._registry.update(order)
        self._order_tracker.update(order)
        return order

    # ── Fill ─────────────────────────────────────────────────────────────────

    def fill_order(
        self,
        order_id: str,
        fill_qty: float,
        fill_price: float,
        *,
        commission: float = 0.0,
        slippage: float   = 0.0,
        venue: str        = "",
    ) -> Order:
        """Record a (partial or full) fill event against the order."""
        order = self._registry.get(order_id)

        # Accept fills from SUBMITTED, ACKNOWLEDGED, or PARTIALLY_FILLED
        if order.status not in {
            OrderStatus.SUBMITTED,
            OrderStatus.ACKNOWLEDGED,
            OrderStatus.PARTIALLY_FILLED,
        }:
            raise InvalidOrderStatusError(
                order_id=order_id,
                from_status=order.status.value,
                to_status="filled",
            )

        # Ensure ACKNOWLEDGED first
        if order.status == OrderStatus.SUBMITTED:
            self._lifecycle.acknowledge(order)
            self._status_tracker.move(OrderStatus.SUBMITTED, OrderStatus.ACKNOWLEDGED)

        prev_status = order.status

        # 1. Apply fill to the Order entity (updates remaining_qty, avg_price, etc.)
        order.record_fill(fill_qty, fill_price)

        # 2. Build execution record
        execution = OrderExecution(
            order_id       = order_id,
            fill_quantity   = fill_qty,
            fill_price      = fill_price,
            commission      = commission,
            slippage        = slippage,
            venue           = venue,
        )
        self._history.add_execution(order_id, execution)

        # 3. Track fill metrics
        lat_ms = (time.time() - order.created_at) * 1_000.0
        self._execution_tracker.record(execution, lat_ms)
        self._order_tracker.record_fill(order_id, execution)

        with self._lock:
            self._stats.record_fill_latency(lat_ms)
            self._stats.total_fill_value += execution.fill_value
            self._stats.total_commission  += commission

        # 4. Advance lifecycle
        if order.fill_status == FillStatus.COMPLETE:
            self._lifecycle.advance(order, OrderStatus.FILLED, reason="fully filled")
            self._status_tracker.move(prev_status, OrderStatus.FILLED)
            with self._lock:
                self._stats.orders_filled += 1
        else:
            self._lifecycle.partially_fill(order)
            self._status_tracker.move(prev_status, OrderStatus.PARTIALLY_FILLED)
            with self._lock:
                self._stats.orders_partial += 1

        self._registry.update(order)
        self._order_tracker.update(order)
        return order

    # ── Cancel ────────────────────────────────────────────────────────────────

    def cancel_order(self, order_id: str, *, reason: str = "") -> OrderResponse:
        """Cancel the order if it is in a cancellable state."""
        t0    = time.perf_counter()
        order = self._registry.get(order_id)

        if order.status not in CANCELLABLE_STATUSES:
            raise InvalidOrderStatusError(
                order_id=order_id,
                from_status=order.status.value,
                to_status=OrderStatus.CANCELLED.value,
            )

        prev = order.status
        self._lifecycle.advance(
            order, OrderStatus.CANCELLED, reason=reason or "cancelled"
        )
        self._status_tracker.move(prev, OrderStatus.CANCELLED)

        self._registry.update(order)
        self._order_tracker.update(order)

        with self._lock:
            self._stats.orders_cancelled += 1

        dur_ms = (time.perf_counter() - t0) * 1_000.0
        return OrderResponse(
            order_id=order_id,
            request_id=order.request_id,
            status=order.status,
            success=True,
            order=order,
            duration_ms=dur_ms,
        )

    # ── Reject ────────────────────────────────────────────────────────────────

    def reject_order(self, order_id: str, *, reason: str = "") -> Order:
        """Reject the order (typically called by a broker adapter)."""
        order = self._registry.get(order_id)
        prev  = order.status
        self._lifecycle.advance(
            order, OrderStatus.REJECTED, reason=reason or "rejected by venue"
        )
        self._status_tracker.move(prev, OrderStatus.REJECTED)
        self._registry.update(order)
        self._order_tracker.update(order)
        with self._lock:
            self._stats.orders_rejected += 1
        return order

    # ── Expire ────────────────────────────────────────────────────────────────

    def expire_order(self, order_id: str) -> Order:
        """Mark order as EXPIRED (TIF limit reached)."""
        order = self._registry.get(order_id)
        prev  = order.status
        self._lifecycle.advance(order, OrderStatus.EXPIRED, reason="time in force expired")
        self._status_tracker.move(prev, OrderStatus.EXPIRED)
        self._registry.update(order)
        self._order_tracker.update(order)
        with self._lock:
            self._stats.orders_expired += 1
        return order

    # ── Modify ────────────────────────────────────────────────────────────────

    def modify_order(self, order_id: str, changes: dict[str, Any]) -> Order:
        """Apply field-level changes to an ACKNOWLEDGED or PARTIALLY_FILLED order.

        After modification the order moves to MODIFIED, from where it can be
        re-validated (→ VALIDATED) and re-submitted, or cancelled.
        """
        order = self._registry.get(order_id)

        if order.status not in MODIFIABLE_STATUSES:
            raise InvalidOrderStatusError(
                order_id=order_id,
                from_status=order.status.value,
                to_status=OrderStatus.MODIFIED.value,
            )

        _IMMUTABLE = {"order_id", "request_id", "created_at", "filled_quantity",
                      "avg_fill_price", "fill_status", "remaining_quantity"}
        for k, v in changes.items():
            if k not in _IMMUTABLE and hasattr(order, k):
                setattr(order, k, v)

        prev = order.status
        self._lifecycle.advance(order, OrderStatus.MODIFIED, reason="modified by user")
        self._status_tracker.move(prev, OrderStatus.MODIFIED)

        self._registry.update(order)
        self._order_tracker.update(order)
        return order

    # ── Re-queue after modification ───────────────────────────────────────────

    def requeue_modified_order(self, order_id: str) -> OrderResponse:
        """Advance a MODIFIED order back through VALIDATED → APPROVED → QUEUED → SUBMITTED."""
        order = self._registry.get(order_id)

        if order.status != OrderStatus.MODIFIED:
            raise InvalidOrderStatusError(
                order_id=order_id,
                from_status=order.status.value,
                to_status=OrderStatus.SUBMITTED.value,
            )

        self._lifecycle.validate(order)
        self._status_tracker.move(OrderStatus.MODIFIED, OrderStatus.VALIDATED)

        return self.submit_order(order_id)

    # ── Archive ───────────────────────────────────────────────────────────────

    def archive_order(self, order_id: str) -> Order:
        """Move a terminal (non-ARCHIVED) order to ARCHIVED."""
        order = self._registry.get(order_id)
        prev  = order.status
        self._lifecycle.advance(order, OrderStatus.ARCHIVED, reason="archived")
        self._status_tracker.move(prev, OrderStatus.ARCHIVED)
        self._registry.update(order)
        with self._lock:
            self._stats.orders_archived += 1
        return order

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_order(self, order_id: str) -> Order:
        return self._registry.get(order_id)

    def get_orders_by_portfolio(self, portfolio_id: str) -> list[Order]:
        return self._registry.get_by_portfolio(portfolio_id)

    def get_orders_by_strategy(self, strategy_id: str) -> list[Order]:
        return self._registry.get_by_strategy(strategy_id)

    def get_orders_by_status(self, status: OrderStatus) -> list[Order]:
        return self._registry.get_by_status(status)

    def get_active_orders(self) -> list[Order]:
        return self._registry.get_active()

    def get_fills(self, order_id: str) -> list[OrderExecution]:
        return self._history.get_executions(order_id)

    def get_transitions(self, order_id: str) -> list:
        return self._history.get_transitions(order_id)

    # ── Health / stats ────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        snap = self._stats.to_dict()
        snap["registry"] = self._registry.statistics()
        snap["monitor"]  = self._monitor.snapshot()
        return snap

    def health(self) -> dict[str, Any]:
        return {
            "healthy":        self._monitor.is_healthy(),
            "active_orders":  self._monitor.active_count(),
            "registry_count": self._registry.count(),
        }

    # ── Accessors for composition ─────────────────────────────────────────────

    @property
    def monitor(self) -> OrderMonitor:
        return self._monitor

    @property
    def registry(self) -> OrderRegistry:
        return self._registry

    @property
    def validation(self) -> ValidationEngine:
        return self._validation
