"""iios/execution/core/execution_result.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.execution_constants import ExecutionStatus, ExecutionType


@dataclass
class ExecutionResult:
    """
    Immutable outcome record produced at the end of an execution workflow.

    Populated by the FinalizeStep.  In paper/simulation modes, fill_price
    equals the request's target_price (or a synthetic mid-price).
    """

    # ── Identifiers ────────────────────────────────────────────────────────────
    result_id:    str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = ""
    request_id:   str = ""
    plan_id:      str = ""

    # ── Outcome ────────────────────────────────────────────────────────────────
    status:         ExecutionStatus = ExecutionStatus.COMPLETED
    execution_type: ExecutionType   = ExecutionType.UNKNOWN

    # ── Instrument ─────────────────────────────────────────────────────────────
    ticker:   str = ""
    exchange: str = ""

    # ── Fill details ───────────────────────────────────────────────────────────
    quantity_requested: float = 0.0
    quantity_executed:  float = 0.0
    avg_fill_price:     float = 0.0
    total_value:        float = 0.0
    commission:         float = 0.0
    slippage:           float = 0.0
    pnl_realized:       float = 0.0

    # ── Timing ─────────────────────────────────────────────────────────────────
    execution_time_ms: float = 0.0
    started_at:        float = field(default_factory=time.time)
    completed_at:      float = field(default_factory=time.time)

    # ── Broker reference (populated by Broker Adapter — future phase) ──────────
    broker_id: str       = ""
    order_id:  str       = ""
    fill_ids:  list[str] = field(default_factory=list)

    # ── Error handling ─────────────────────────────────────────────────────────
    error_message: str = ""
    error_code:    str = ""

    # ── Extra ──────────────────────────────────────────────────────────────────
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Derived properties ─────────────────────────────────────────────────────

    @property
    def is_successful(self) -> bool:
        return self.status == ExecutionStatus.COMPLETED

    @property
    def fill_ratio(self) -> float:
        if self.quantity_requested <= 0.0:
            return 0.0
        return min(1.0, self.quantity_executed / self.quantity_requested)

    @property
    def is_partial(self) -> bool:
        return 0.0 < self.fill_ratio < 1.0

    @property
    def net_value(self) -> float:
        return self.total_value - self.commission

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":          self.result_id,
            "execution_id":       self.execution_id,
            "request_id":         self.request_id,
            "plan_id":            self.plan_id,
            "status":             self.status.value,
            "execution_type":     self.execution_type.value,
            "ticker":             self.ticker,
            "exchange":           self.exchange,
            "quantity_requested": self.quantity_requested,
            "quantity_executed":  self.quantity_executed,
            "avg_fill_price":     self.avg_fill_price,
            "total_value":        self.total_value,
            "commission":         self.commission,
            "slippage":           self.slippage,
            "pnl_realized":       self.pnl_realized,
            "execution_time_ms":  self.execution_time_ms,
            "started_at":         self.started_at,
            "completed_at":       self.completed_at,
            "broker_id":          self.broker_id,
            "order_id":           self.order_id,
            "fill_ids":           list(self.fill_ids),
            "error_message":      self.error_message,
            "error_code":         self.error_code,
            "metadata":           dict(self.metadata),
        }
