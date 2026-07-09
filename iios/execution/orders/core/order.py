"""iios/execution/orders/core/order.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..order_constants import (
    DEFAULT_MAX_HISTORY,
    DEFAULT_RETRY_LIMIT,
    TERMINAL_STATUSES,
    VALID_TRANSITIONS,
    FillStatus,
    OrderAssetClass,
    OrderMode,
    OrderPriority,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from ..order_exceptions import InvalidOrderStatusError, OrderFillError, OrderTerminalError, OverfillError


@dataclass
class Order:
    """Core order entity — the single source of truth for an order inside IIOS."""

    # ── Identity ──────────────────────────────────────────────────────────────
    order_id:        str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:      str = ""
    execution_id:    str = ""
    decision_id:     str = ""
    portfolio_id:    str = ""
    strategy_id:     str = ""
    account_id:      str = ""

    # ── Asset ─────────────────────────────────────────────────────────────────
    asset_id:        str             = ""
    ticker:          str             = ""
    exchange:        str             = ""
    asset_class:     OrderAssetClass = OrderAssetClass.UNKNOWN

    # ── Order spec ────────────────────────────────────────────────────────────
    order_type:      OrderType     = OrderType.MARKET
    side:            OrderSide     = OrderSide.BUY
    quantity:        float         = 0.0
    price:           float | None  = None    # None → MARKET
    stop_price:      float | None  = None
    limit_price:     float | None  = None
    trail_amount:    float | None  = None    # for TRAILING_STOP
    time_in_force:   TimeInForce   = TimeInForce.DAY

    # ── Control ───────────────────────────────────────────────────────────────
    status:          OrderStatus   = OrderStatus.DRAFT
    priority:        OrderPriority = OrderPriority.NORMAL
    mode:            OrderMode     = OrderMode.PAPER

    # ── Fill tracking ─────────────────────────────────────────────────────────
    filled_quantity:    float      = 0.0
    avg_fill_price:     float      = 0.0
    remaining_quantity: float      = field(init=False)
    fill_status:        FillStatus = FillStatus.UNFILLED

    # ── Risk constraints ──────────────────────────────────────────────────────
    max_slippage_pct:      float = 0.01
    max_market_impact_pct: float = 0.005

    # ── Timestamps (epoch-float) ──────────────────────────────────────────────
    created_at:    float         = field(default_factory=time.time)
    updated_at:    float         = field(default_factory=time.time)
    submitted_at:  float | None  = None
    filled_at:     float | None  = None
    expires_at:    float | None  = None

    # ── Retry ─────────────────────────────────────────────────────────────────
    retry_count:   int  = 0
    max_retries:   int  = DEFAULT_RETRY_LIMIT

    # ── Parent / child relationships (split/merge) ────────────────────────────
    parent_order_id:   str        = ""
    child_order_ids:   list[str]  = field(default_factory=list)

    # ── Free-form tags and metadata ───────────────────────────────────────────
    tags:     list[str]      = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.remaining_quantity = self.quantity

    # ── Status machine ────────────────────────────────────────────────────────

    def can_transition_to(self, new_status: OrderStatus) -> bool:
        return new_status in VALID_TRANSITIONS.get(self.status, frozenset())

    def transition_to(self, new_status: OrderStatus, *, reason: str = "") -> None:
        # Allow terminal → ARCHIVED (archiving any closed order is valid).
        if self.status in TERMINAL_STATUSES and new_status != OrderStatus.ARCHIVED:
            raise OrderTerminalError(
                order_id=self.order_id,
                status=self.status.value,
            )
        if not self.can_transition_to(new_status):
            raise InvalidOrderStatusError(
                order_id=self.order_id,
                from_status=self.status.value,
                to_status=new_status.value,
            )
        self.status = new_status
        self.updated_at = time.time()

        if new_status == OrderStatus.SUBMITTED:
            self.submitted_at = self.updated_at
        elif new_status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
            if new_status == OrderStatus.FILLED:
                self.filled_at = self.updated_at

    # ── Fill recording ────────────────────────────────────────────────────────

    def record_fill(self, fill_qty: float, fill_price: float) -> None:
        """Update running average price and remaining quantity."""
        if fill_qty <= 0:
            raise OrderFillError(order_id=self.order_id, fill_qty=fill_qty)
        if fill_qty > self.remaining_quantity + 1e-9:
            raise OverfillError(
                order_id=self.order_id,
                requested=fill_qty,
                remaining=self.remaining_quantity,
            )
        # Running average
        total_filled = self.filled_quantity + fill_qty
        if total_filled > 0:
            self.avg_fill_price = (
                (self.avg_fill_price * self.filled_quantity + fill_price * fill_qty) / total_filled
            )
        self.filled_quantity    = total_filled
        self.remaining_quantity = max(0.0, self.quantity - self.filled_quantity)
        self.fill_status = (
            FillStatus.COMPLETE if self.remaining_quantity <= 1e-9 else FillStatus.PARTIAL
        )
        self.updated_at = time.time()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def is_active(self) -> bool:
        return not self.is_terminal()

    def fill_pct(self) -> float:
        return (self.filled_quantity / self.quantity * 100.0) if self.quantity else 0.0

    def notional_value(self) -> float:
        p = self.price or self.avg_fill_price or 0.0
        return self.quantity * p

    def filled_value(self) -> float:
        return self.filled_quantity * self.avg_fill_price

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id":            self.order_id,
            "request_id":          self.request_id,
            "execution_id":        self.execution_id,
            "decision_id":         self.decision_id,
            "portfolio_id":        self.portfolio_id,
            "strategy_id":         self.strategy_id,
            "account_id":          self.account_id,
            "asset_id":            self.asset_id,
            "ticker":              self.ticker,
            "exchange":            self.exchange,
            "asset_class":         self.asset_class.value,
            "order_type":          self.order_type.value,
            "side":                self.side.value,
            "quantity":            self.quantity,
            "price":               self.price,
            "stop_price":          self.stop_price,
            "limit_price":         self.limit_price,
            "trail_amount":        self.trail_amount,
            "time_in_force":       self.time_in_force.value,
            "status":              self.status.value,
            "priority":            self.priority.value,
            "mode":                self.mode.value,
            "filled_quantity":     self.filled_quantity,
            "avg_fill_price":      self.avg_fill_price,
            "remaining_quantity":  self.remaining_quantity,
            "fill_status":         self.fill_status.value,
            "fill_pct":            self.fill_pct(),
            "max_slippage_pct":    self.max_slippage_pct,
            "created_at":          self.created_at,
            "updated_at":          self.updated_at,
            "submitted_at":        self.submitted_at,
            "filled_at":           self.filled_at,
            "expires_at":          self.expires_at,
            "retry_count":         self.retry_count,
            "max_retries":         self.max_retries,
            "parent_order_id":     self.parent_order_id,
            "child_order_ids":     list(self.child_order_ids),
            "tags":                list(self.tags),
            "metadata":            dict(self.metadata),
        }


# Avoid circular import from order_exceptions
from ..order_exceptions import OrderFillError  # noqa: E402 — must come after class body
