"""iios/execution/monitoring/tracking/fill_tracker.py"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.monitoring_constants import FillType


@dataclass
class FillRecord:
    """One broker fill event for a single order."""

    order_id:       str      = ""
    execution_id:   str      = ""
    broker_id:      str      = ""
    broker_fill_id: str      = ""
    symbol:         str      = ""
    side:           str      = ""
    quantity:       float    = 0.0
    price:          float    = 0.0
    fill_type:      FillType = FillType.PARTIAL
    fee:            float    = 0.0
    fill_id:        str      = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:      float    = field(default_factory=time.time)
    metadata:       dict[str, Any] = field(default_factory=dict)

    def value(self) -> float:
        return self.quantity * self.price

    def to_dict(self) -> dict[str, Any]:
        return {
            "fill_id":       self.fill_id,
            "order_id":      self.order_id,
            "execution_id":  self.execution_id,
            "broker_id":     self.broker_id,
            "broker_fill_id": self.broker_fill_id,
            "symbol":        self.symbol,
            "side":          self.side,
            "quantity":      self.quantity,
            "price":         self.price,
            "fill_type":     self.fill_type.value,
            "fee":           self.fee,
            "value":         self.value(),
            "timestamp":     self.timestamp,
            "metadata":      self.metadata,
        }


class FillTracker:
    """
    Tracks all fills received per order and execution.
    Thread-safe.
    """

    def __init__(self) -> None:
        self._fills_by_order:     dict[str, list[FillRecord]] = {}
        self._fills_by_execution: dict[str, list[FillRecord]] = {}
        self._all_fills:          dict[str, FillRecord]        = {}
        self._total_fill_count    = 0
        self._lock                = threading.RLock()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record_fill(self, fill: FillRecord) -> None:
        with self._lock:
            self._all_fills[fill.fill_id] = fill
            self._fills_by_order.setdefault(fill.order_id, []).append(fill)
            if fill.execution_id:
                self._fills_by_execution.setdefault(fill.execution_id, []).append(fill)
            self._total_fill_count += 1

    # ── Queries ───────────────────────────────────────────────────────────────

    def fills_for_order(self, order_id: str) -> list[FillRecord]:
        with self._lock:
            return list(self._fills_by_order.get(order_id, []))

    def fills_for_execution(self, execution_id: str) -> list[FillRecord]:
        with self._lock:
            return list(self._fills_by_execution.get(execution_id, []))

    def get_fill(self, fill_id: str) -> FillRecord | None:
        with self._lock:
            return self._all_fills.get(fill_id)

    def total_filled_quantity(self, order_id: str) -> float:
        return sum(f.quantity for f in self.fills_for_order(order_id))

    def total_notional(self, order_id: str) -> float:
        return sum(f.value() for f in self.fills_for_order(order_id))

    def avg_fill_price(self, order_id: str) -> float:
        fills = self.fills_for_order(order_id)
        total_qty = sum(f.quantity for f in fills)
        if total_qty == 0:
            return 0.0
        return sum(f.value() for f in fills) / total_qty

    def all_fills(self) -> list[FillRecord]:
        with self._lock:
            return list(self._all_fills.values())

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_fills":       self._total_fill_count,
                "orders_with_fills": len(self._fills_by_order),
            }
