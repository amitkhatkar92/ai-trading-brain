"""iios/execution/core/execution_request.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.execution_constants import (
    ExecutionMode,
    ExecutionPriority,
    ExecutionType,
    TimeInForce,
)


@dataclass
class ExecutionRequest:
    """Input submitted to the Execution Engine from the Decision Layer."""

    # ── Identifiers ────────────────────────────────────────────────────────────
    request_id:   str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id:  str = ""
    strategy_id:  str = ""
    portfolio_id: str = ""
    company_id:   str = ""

    # ── Instrument ─────────────────────────────────────────────────────────────
    ticker:         str = ""
    exchange:       str = ""
    instrument_type: str = "equity"  # equity, futures, options, bond, crypto …

    # ── Order parameters ───────────────────────────────────────────────────────
    execution_type: ExecutionType     = ExecutionType.UNKNOWN
    execution_mode: ExecutionMode     = ExecutionMode.PAPER
    priority:       ExecutionPriority = ExecutionPriority.NORMAL
    time_in_force:  TimeInForce       = TimeInForce.DAY

    quantity:     float       = 0.0
    target_price: float | None = None   # None → market price in paper mode
    price_limit:  float | None = None
    stop_loss:    float | None = None
    take_profit:  float | None = None

    # ── Timestamps ─────────────────────────────────────────────────────────────
    requested_at: float       = field(default_factory=time.time)
    expires_at:   float | None = None

    # ── Extra ──────────────────────────────────────────────────────────────────
    notes:       str             = ""
    constraints: dict[str, Any] = field(default_factory=dict)
    metadata:    dict[str, Any] = field(default_factory=dict)

    # ── Derived helpers ────────────────────────────────────────────────────────

    @property
    def is_buy(self) -> bool:
        return self.execution_type in (ExecutionType.BUY, ExecutionType.COVER)

    @property
    def is_sell(self) -> bool:
        return self.execution_type in (ExecutionType.SELL, ExecutionType.SHORT)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def estimated_value(self) -> float:
        price = self.target_price or self.price_limit or 0.0
        return self.quantity * price

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":       self.request_id,
            "decision_id":      self.decision_id,
            "strategy_id":      self.strategy_id,
            "portfolio_id":     self.portfolio_id,
            "company_id":       self.company_id,
            "ticker":           self.ticker,
            "exchange":         self.exchange,
            "instrument_type":  self.instrument_type,
            "execution_type":   self.execution_type.value,
            "execution_mode":   self.execution_mode.value,
            "priority":         self.priority.value,
            "time_in_force":    self.time_in_force.value,
            "quantity":         self.quantity,
            "target_price":     self.target_price,
            "price_limit":      self.price_limit,
            "stop_loss":        self.stop_loss,
            "take_profit":      self.take_profit,
            "requested_at":     self.requested_at,
            "expires_at":       self.expires_at,
            "notes":            self.notes,
            "constraints":      dict(self.constraints),
            "metadata":         dict(self.metadata),
        }
