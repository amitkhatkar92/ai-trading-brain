"""core/paper_order.py — PaperOrder model."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import (
    OrderSide,
    PaperOrderStatus,
    PaperOrderType,
    TimeInForce,
)


@dataclass
class PaperOrder:
    """
    Represents a single order in the paper trading session.

    ``filled_quantity`` accumulates across partial fills.
    An order is terminal when its status is FILLED, CANCELLED, REJECTED, or EXPIRED.
    """

    order_id:         str
    account_id:       str
    session_id:       str
    symbol:           str
    side:             OrderSide
    order_type:       PaperOrderType
    quantity:         float
    limit_price:      Optional[float]
    stop_price:       Optional[float]
    tif:              TimeInForce       = TimeInForce.DAY
    status:           PaperOrderStatus  = PaperOrderStatus.PENDING
    filled_quantity:  float             = 0.0
    avg_fill_price:   float             = 0.0
    commission:       float             = 0.0
    slippage:         float             = 0.0
    submitted_at:     float             = field(default_factory=time.time)
    updated_at:       float             = field(default_factory=time.time)
    filled_at:        Optional[float]   = None
    expires_at:       Optional[float]   = None
    reject_reason:    Optional[str]     = None
    metadata:         dict[str, Any]    = field(default_factory=dict)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        account_id:   str,
        session_id:   str,
        symbol:       str,
        side:         OrderSide,
        order_type:   PaperOrderType,
        quantity:     float,
        *,
        limit_price:  Optional[float]  = None,
        stop_price:   Optional[float]  = None,
        tif:          TimeInForce       = TimeInForce.DAY,
        expires_at:   Optional[float]  = None,
        order_id:     Optional[str]    = None,
        metadata:     Optional[dict]   = None,
    ) -> "PaperOrder":
        now = time.time()
        return cls(
            order_id       = order_id or f"ord_{uuid.uuid4().hex[:12]}",
            account_id     = account_id,
            session_id     = session_id,
            symbol         = symbol,
            side           = side,
            order_type     = order_type,
            quantity       = quantity,
            limit_price    = limit_price,
            stop_price     = stop_price,
            tif            = tif,
            status         = PaperOrderStatus.PENDING,
            filled_quantity = 0.0,
            avg_fill_price  = 0.0,
            commission      = 0.0,
            slippage        = 0.0,
            submitted_at    = now,
            updated_at      = now,
            filled_at       = None,
            expires_at      = expires_at,
            reject_reason   = None,
            metadata        = metadata or {},
        )

    # ── State helpers ─────────────────────────────────────────────────────────

    def touch(self) -> None:
        self.updated_at = time.time()

    def is_terminal(self) -> bool:
        return self.status in (
            PaperOrderStatus.FILLED,
            PaperOrderStatus.CANCELLED,
            PaperOrderStatus.REJECTED,
            PaperOrderStatus.EXPIRED,
        )

    def is_buy(self) -> bool:
        return self.side == OrderSide.BUY

    def is_sell(self) -> bool:
        return self.side == OrderSide.SELL

    def is_filled(self) -> bool:
        return self.status == PaperOrderStatus.FILLED

    # ── Fill helpers ──────────────────────────────────────────────────────────

    def remaining_quantity(self) -> float:
        return max(0.0, self.quantity - self.filled_quantity)

    def fill_fraction(self) -> float:
        if self.quantity <= 0.0:
            return 0.0
        return self.filled_quantity / self.quantity

    def apply_fill(
        self,
        quantity:    float,
        fill_price:  float,
        commission:  float,
        slippage:    float,
        timestamp:   float,
    ) -> None:
        """Record a (partial) fill against this order."""
        prev_total        = self.avg_fill_price * self.filled_quantity
        self.filled_quantity += quantity
        if self.filled_quantity > 0.0:
            self.avg_fill_price = (prev_total + fill_price * quantity) / self.filled_quantity
        self.commission  += commission
        self.slippage    += slippage
        self.updated_at   = timestamp
        if self.filled_quantity >= self.quantity:
            self.status    = PaperOrderStatus.FILLED
            self.filled_at = timestamp
        else:
            self.status = PaperOrderStatus.PARTIALLY_FILLED

    # ── Cost calculation ──────────────────────────────────────────────────────

    def total_cost(self) -> float:
        """Notional cost = avg_fill_price * filled_quantity + commission + slippage."""
        return self.avg_fill_price * self.filled_quantity + self.commission + self.slippage

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id":        self.order_id,
            "account_id":      self.account_id,
            "session_id":      self.session_id,
            "symbol":          self.symbol,
            "side":            self.side.value,
            "order_type":      self.order_type.value,
            "quantity":        self.quantity,
            "limit_price":     self.limit_price,
            "stop_price":      self.stop_price,
            "tif":             self.tif.value,
            "status":          self.status.value,
            "filled_quantity": self.filled_quantity,
            "avg_fill_price":  self.avg_fill_price,
            "commission":      self.commission,
            "slippage":        self.slippage,
            "submitted_at":    self.submitted_at,
            "updated_at":      self.updated_at,
            "filled_at":       self.filled_at,
            "expires_at":      self.expires_at,
            "reject_reason":   self.reject_reason,
            "metadata":        self.metadata,
        }
