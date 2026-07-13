"""iios/investment/strategy/evaluation/trade.py
Immutable Trade record for evaluation input.  Not linked to execution layer.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class Trade:
    """A completed trade submitted for evaluation."""

    strategy_id: str
    symbol: str
    side: str                    # "LONG" | "SHORT"
    entry_price: float
    exit_price: float
    quantity: float              # number of shares / contracts
    entry_time: datetime
    exit_time: datetime
    gross_pnl: float             # before commission
    commission: float            # total round-trip commission
    net_pnl: float               # gross_pnl - commission
    pnl_pct: float               # net_pnl / capital_deployed
    trade_id: str                = field(default_factory=lambda: str(uuid.uuid4()))
    entry_slippage: float        = 0.0   # price units away from decision price
    exit_slippage: float         = 0.0
    metadata: Dict[str, Any]     = field(default_factory=dict)

    # ── derived ─────────────────────────────────────────────────────────────

    @property
    def holding_seconds(self) -> float:
        delta = self.exit_time - self.entry_time
        return delta.total_seconds()

    @property
    def holding_days(self) -> float:
        return self.holding_seconds / 86_400.0

    @property
    def is_winner(self) -> bool:
        return self.net_pnl > 0.0

    @property
    def is_loser(self) -> bool:
        return self.net_pnl < 0.0

    @property
    def is_breakeven(self) -> bool:
        return self.net_pnl == 0.0

    @property
    def total_slippage_pts(self) -> float:
        return abs(self.entry_slippage) + abs(self.exit_slippage)

    @property
    def slippage_pct(self) -> float:
        """Total slippage as fraction of entry notional."""
        notional = self.entry_price * self.quantity
        return self.total_slippage_pts * self.quantity / notional if notional else 0.0

    @property
    def return_on_risk(self) -> float:
        """net_pnl / abs(entry_price * quantity)."""
        cost = abs(self.entry_price * self.quantity)
        return self.net_pnl / cost if cost else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id":       self.trade_id,
            "strategy_id":    self.strategy_id,
            "symbol":         self.symbol,
            "side":           self.side,
            "entry_price":    self.entry_price,
            "exit_price":     self.exit_price,
            "quantity":       self.quantity,
            "entry_time":     self.entry_time.isoformat(),
            "exit_time":      self.exit_time.isoformat(),
            "holding_days":   round(self.holding_days, 4),
            "gross_pnl":      self.gross_pnl,
            "commission":     self.commission,
            "net_pnl":        self.net_pnl,
            "pnl_pct":        self.pnl_pct,
            "entry_slippage": self.entry_slippage,
            "exit_slippage":  self.exit_slippage,
        }
