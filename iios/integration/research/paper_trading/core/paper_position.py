"""core/paper_position.py — PaperPosition model."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import (
    PaperPositionSide,
)


@dataclass
class PaperPosition:
    """
    An open position in one symbol for a paper account.

    ``realized_pnl`` accumulates across partial reductions.
    ``unrealized_pnl`` is mark-to-market of the remaining open quantity.
    """

    position_id:    str
    account_id:     str
    session_id:     str
    symbol:         str
    side:           PaperPositionSide
    quantity:       float          # remaining open quantity
    avg_cost:       float          # weighted average entry price
    current_price:  float          # last mark-to-market price
    realized_pnl:   float          = 0.0
    commission:     float          = 0.0  # total commission paid so far
    opened_at:      float          = field(default_factory=time.time)
    updated_at:     float          = field(default_factory=time.time)
    metadata:       dict[str, Any] = field(default_factory=dict)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def open(
        cls,
        account_id:  str,
        session_id:  str,
        symbol:      str,
        side:        PaperPositionSide,
        quantity:    float,
        price:       float,
        commission:  float = 0.0,
        *,
        position_id: Optional[str] = None,
    ) -> "PaperPosition":
        now = time.time()
        return cls(
            position_id   = position_id or f"pos_{uuid.uuid4().hex[:12]}",
            account_id    = account_id,
            session_id    = session_id,
            symbol        = symbol,
            side          = side,
            quantity      = quantity,
            avg_cost      = price,
            current_price = price,
            realized_pnl  = 0.0,
            commission    = commission,
            opened_at     = now,
            updated_at    = now,
        )

    # ── Mark-to-market ────────────────────────────────────────────────────────

    @property
    def unrealized_pnl(self) -> float:
        mult = 1.0 if self.side == PaperPositionSide.LONG else -1.0
        return mult * (self.current_price - self.avg_cost) * self.quantity

    @property
    def market_value(self) -> float:
        return self.current_price * self.quantity

    @property
    def cost_basis(self) -> float:
        return self.avg_cost * self.quantity

    @property
    def exposure(self) -> float:
        """Absolute exposure: market_value."""
        return self.market_value

    def update_price(self, price: float, timestamp: float) -> None:
        self.current_price = price
        self.updated_at    = timestamp

    # ── Position adjustments ──────────────────────────────────────────────────

    def add_to_position(
        self,
        quantity:   float,
        price:      float,
        commission: float = 0.0,
    ) -> None:
        """Add to the open position; recalculate weighted average cost."""
        total_cost     = self.avg_cost * self.quantity + price * quantity
        self.quantity  += quantity
        self.avg_cost   = total_cost / self.quantity
        self.commission += commission
        self.updated_at = time.time()

    def reduce_position(
        self,
        quantity:   float,
        price:      float,
        commission: float = 0.0,
    ) -> float:
        """
        Reduce (or close) the position by *quantity* at *price*.

        Returns the realized PnL for this reduction.
        Caller is responsible for ensuring quantity <= self.quantity.
        """
        mult        = 1.0 if self.side == PaperPositionSide.LONG else -1.0
        realized    = mult * (price - self.avg_cost) * quantity - commission
        self.realized_pnl  += realized
        self.quantity       -= quantity
        self.commission     += commission
        self.current_price   = price
        self.updated_at      = time.time()
        return realized

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_long(self) -> bool:
        return self.side == PaperPositionSide.LONG

    def is_short(self) -> bool:
        return self.side == PaperPositionSide.SHORT

    def is_closed(self) -> bool:
        return self.quantity <= 0.0

    def return_pct(self) -> float:
        if self.avg_cost == 0.0:
            return 0.0
        mult = 1.0 if self.side == PaperPositionSide.LONG else -1.0
        return mult * (self.current_price - self.avg_cost) / self.avg_cost

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_id":   self.position_id,
            "account_id":    self.account_id,
            "session_id":    self.session_id,
            "symbol":        self.symbol,
            "side":          self.side.value,
            "quantity":      self.quantity,
            "avg_cost":      self.avg_cost,
            "current_price": self.current_price,
            "market_value":  self.market_value,
            "cost_basis":    self.cost_basis,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl":  self.realized_pnl,
            "commission":    self.commission,
            "return_pct":    self.return_pct(),
            "opened_at":     self.opened_at,
            "updated_at":    self.updated_at,
            "metadata":      self.metadata,
        }
