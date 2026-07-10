"""iios/execution/monitoring/core/execution_record.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.monitoring_constants import (
    ExecutionRecordStatus,
    TERMINAL_EXECUTION_STATUSES,
)


@dataclass
class ExecutionRecord:
    """
    Canonical internal record of a single order execution lifecycle.

    Created when an order enters the execution layer and updated as
    fills, cancellations, or rejections arrive.
    """

    execution_id:    str                  = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:        str                  = ""
    plan_id:         str                  = ""
    broker_id:       str                  = ""
    broker_order_id: str                  = ""
    symbol:          str                  = ""
    side:            str                  = ""   # BUY / SELL
    order_type:      str                  = ""   # MARKET / LIMIT / STOP
    quantity:        float                = 0.0
    price:           float                = 0.0  # requested price
    filled_quantity: float                = 0.0
    avg_fill_price:  float                = 0.0
    fill_count:      int                  = 0
    status:          ExecutionRecordStatus = ExecutionRecordStatus.PENDING
    rejection_reason: str                 = ""
    submitted_at:    float | None         = None
    accepted_at:     float | None         = None
    first_fill_at:   float | None         = None
    last_fill_at:    float | None         = None
    completed_at:    float | None         = None
    created_at:      float                = field(default_factory=time.time)
    updated_at:      float                = field(default_factory=time.time)
    metadata:        dict[str, Any]       = field(default_factory=dict)

    # ── Computed properties ───────────────────────────────────────────────────

    def fill_ratio(self) -> float:
        if self.quantity <= 0:
            return 0.0
        return min(1.0, self.filled_quantity / self.quantity)

    def unfilled_quantity(self) -> float:
        return max(0.0, self.quantity - self.filled_quantity)

    def is_fully_filled(self) -> bool:
        return self.status == ExecutionRecordStatus.FULLY_FILLED

    def is_terminal(self) -> bool:
        return self.status in TERMINAL_EXECUTION_STATUSES

    def notional_value(self) -> float:
        return self.filled_quantity * self.avg_fill_price

    def total_latency_ms(self) -> float | None:
        if self.submitted_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.submitted_at) * 1_000

    # ── Mutation ──────────────────────────────────────────────────────────────

    def apply_fill(self, quantity: float, price: float) -> None:
        """Update record when a fill arrives."""
        now = time.time()
        if self.first_fill_at is None:
            self.first_fill_at = now
        prev_filled = self.filled_quantity
        self.filled_quantity += quantity
        # Update weighted average fill price
        total_qty = prev_filled + quantity
        if total_qty > 0:
            self.avg_fill_price = (
                (prev_filled * self.avg_fill_price + quantity * price) / total_qty
            )
        self.fill_count += 1
        self.last_fill_at = now
        if self.filled_quantity >= self.quantity:
            self.status = ExecutionRecordStatus.FULLY_FILLED
            self.completed_at = now
        else:
            self.status = ExecutionRecordStatus.PARTIALLY_FILLED
        self.updated_at = now

    def transition_to(self, new_status: ExecutionRecordStatus, reason: str = "") -> None:
        now = time.time()
        self.status     = new_status
        self.updated_at = now
        if new_status in TERMINAL_EXECUTION_STATUSES and self.completed_at is None:
            self.completed_at = now
        if new_status == ExecutionRecordStatus.REJECTED:
            self.rejection_reason = reason
        if new_status == ExecutionRecordStatus.SUBMITTED and self.submitted_at is None:
            self.submitted_at = now
        if new_status == ExecutionRecordStatus.ACCEPTED and self.accepted_at is None:
            self.accepted_at = now

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id":    self.execution_id,
            "order_id":        self.order_id,
            "plan_id":         self.plan_id,
            "broker_id":       self.broker_id,
            "broker_order_id": self.broker_order_id,
            "symbol":          self.symbol,
            "side":            self.side,
            "order_type":      self.order_type,
            "quantity":        self.quantity,
            "price":           self.price,
            "filled_quantity": self.filled_quantity,
            "avg_fill_price":  self.avg_fill_price,
            "fill_count":      self.fill_count,
            "fill_ratio":      round(self.fill_ratio(), 4),
            "status":          self.status.value,
            "rejection_reason": self.rejection_reason,
            "submitted_at":    self.submitted_at,
            "accepted_at":     self.accepted_at,
            "first_fill_at":   self.first_fill_at,
            "last_fill_at":    self.last_fill_at,
            "completed_at":    self.completed_at,
            "created_at":      self.created_at,
            "updated_at":      self.updated_at,
            "metadata":        self.metadata,
        }
