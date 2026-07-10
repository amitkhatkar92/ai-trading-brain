"""core/paper_trade.py — PaperTrade model (completed round-trip)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import (
    OrderSide,
    PaperPositionSide,
)


@dataclass
class PaperTrade:
    """
    A completed round-trip trade.

    ``side`` is the *position* side (LONG / SHORT).
    ``entry_price`` / ``exit_price`` define the round-trip.
    ``net_pnl`` is the trade's contribution to account equity.
    ``duration_sec`` is the wall-clock holding period in seconds.
    """

    trade_id:     str
    order_id:     str
    account_id:   str
    session_id:   str
    symbol:       str
    side:         PaperPositionSide
    quantity:     float
    entry_price:  float
    exit_price:   float
    commission:   float
    slippage:     float
    gross_pnl:    float
    net_pnl:      float
    return_pct:   float
    entry_time:   float
    exit_time:    float
    duration_sec: float
    metadata:     dict[str, Any] = field(default_factory=dict)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        order_id:    str,
        account_id:  str,
        session_id:  str,
        symbol:      str,
        side:        PaperPositionSide,
        quantity:    float,
        entry_price: float,
        exit_price:  float,
        commission:  float,
        slippage:    float,
        entry_time:  float,
        exit_time:   float,
        *,
        trade_id:    Optional[str] = None,
        metadata:    Optional[dict] = None,
    ) -> "PaperTrade":
        mult     = 1.0 if side == PaperPositionSide.LONG else -1.0
        gross    = mult * (exit_price - entry_price) * quantity
        net      = gross - commission - slippage
        ret_pct  = (gross / (entry_price * quantity)) if entry_price > 0.0 else 0.0
        return cls(
            trade_id     = trade_id or f"trd_{uuid.uuid4().hex[:12]}",
            order_id     = order_id,
            account_id   = account_id,
            session_id   = session_id,
            symbol       = symbol,
            side         = side,
            quantity     = quantity,
            entry_price  = entry_price,
            exit_price   = exit_price,
            commission   = commission,
            slippage     = slippage,
            gross_pnl    = gross,
            net_pnl      = net,
            return_pct   = ret_pct,
            entry_time   = entry_time,
            exit_time    = exit_time,
            duration_sec = exit_time - entry_time,
            metadata     = metadata or {},
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_winner(self) -> bool:
        return self.net_pnl > 0.0

    def is_loser(self) -> bool:
        return self.net_pnl < 0.0

    def is_flat(self) -> bool:
        return self.net_pnl == 0.0

    # ── Serialization (compatible with backtesting trade_statistics) ──────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "trade_id":    self.trade_id,
            "order_id":    self.order_id,
            "account_id":  self.account_id,
            "session_id":  self.session_id,
            "symbol":      self.symbol,
            "side":        self.side.value,
            "quantity":    self.quantity,
            "entry_price": self.entry_price,
            "exit_price":  self.exit_price,
            "commission":  self.commission,
            "slippage":    self.slippage,
            "gross_pnl":   self.gross_pnl,
            "net_pnl":     self.net_pnl,
            "return_pct":  self.return_pct,
            "entry_time":  self.entry_time,
            "exit_time":   self.exit_time,
            "duration_sec": self.duration_sec,
            "metadata":    self.metadata,
        }
