"""iios/investment/strategy/performance/performance_record.py
Single trade / signal execution result consumed by the evaluation pipeline.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.strategy.strategy_constants import MarketRegime


@dataclass
class PerformanceRecord:
    """
    Records the outcome of one trade or signal produced by a strategy.

    PnL values are expressed as fractions (e.g. 0.05 = 5 %).
    Durations are in days.
    """

    record_id:    str         = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id:  str         = ""

    # Trade outcome
    pnl:          float       = 0.0     # fractional P&L (negative = loss)
    is_win:       bool        = False
    entry_price:  float       = 0.0
    exit_price:   float       = 0.0
    duration_days: float      = 0.0

    # Context at the time of the trade
    market_regime: MarketRegime = MarketRegime.UNKNOWN
    symbol:        str          = ""
    asset_class:   str          = ""

    timestamp:     float        = field(default_factory=time.time)
    metadata:      dict[str, Any] = field(default_factory=dict)

    @property
    def is_loss(self) -> bool:
        return not self.is_win

    @property
    def return_pct(self) -> float:
        return self.pnl * 100.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":     self.record_id,
            "strategy_id":   self.strategy_id,
            "pnl":           self.pnl,
            "is_win":        self.is_win,
            "return_pct":    self.return_pct,
            "entry_price":   self.entry_price,
            "exit_price":    self.exit_price,
            "duration_days": self.duration_days,
            "market_regime": self.market_regime.value,
            "symbol":        self.symbol,
            "timestamp":     self.timestamp,
            "metadata":      self.metadata,
        }
