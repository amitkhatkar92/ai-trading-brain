"""execution/trade.py — Completed round-trip trade record."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.research.backtesting.backtest_constants import PositionSide


@dataclass
class Trade:
    """
    Represents a completed (closed) position.

    Created by Portfolio when a closing Fill is applied.
    All PnL figures are net of commission.
    """
    symbol:       str          = ""
    side:         PositionSide = PositionSide.LONG

    entry_price:  float        = 0.0
    exit_price:   float        = 0.0
    quantity:     float        = 0.0

    gross_pnl:    float        = 0.0   # before commission
    commission:   float        = 0.0
    net_pnl:      float        = 0.0   # after commission
    return_pct:   float        = 0.0   # net_pnl / (entry_price * quantity)

    entry_time:   float        = 0.0   # unix timestamp
    exit_time:    float        = 0.0
    duration_sec: float        = 0.0

    trade_id:     str          = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:     dict[str, Any] = field(default_factory=dict)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_winner(self) -> bool:
        return self.net_pnl > 0

    def is_loser(self) -> bool:
        return self.net_pnl < 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "trade_id":     self.trade_id,
            "symbol":       self.symbol,
            "side":         self.side.value,
            "entry_price":  self.entry_price,
            "exit_price":   self.exit_price,
            "quantity":     self.quantity,
            "gross_pnl":    self.gross_pnl,
            "commission":   self.commission,
            "net_pnl":      self.net_pnl,
            "return_pct":   self.return_pct,
            "entry_time":   self.entry_time,
            "exit_time":    self.exit_time,
            "duration_sec": self.duration_sec,
        }
