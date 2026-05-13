"""
Portfolio & Position Models
Tracks the current state of all open positions and overall portfolio health.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Position:
    """A single live position in the portfolio."""
    symbol: str
    quantity: int                       # Positive = long, Negative = short
    avg_entry_price: float
    ltp: float = 0.0                    # Last traded price (updated live)
    stop_loss: float = 0.0
    target_price: float = 0.0
    strategy_name: str = ""
    entry_time: datetime = field(default_factory=datetime.now)
    segment: str = "equity"            # equity | futures | options
    has_live_ltp: bool = False          # True once a real market price has been fetched
    ltp_timestamp: Optional[datetime] = None  # Wall-clock time of last LTP update
    ltp_tick_count: int = 0             # Consecutive fresh ticks; resets to 0 when stale
    restore_time: Optional[datetime] = None          # Wall-clock time of last journal restore
    confidence_achieved_at: Optional[datetime] = None  # First time tick_count reached threshold

    @property
    def unrealised_pnl(self) -> float:
        return (self.ltp - self.avg_entry_price) * self.quantity

    @property
    def unrealised_pnl_pct(self) -> float:
        if self.avg_entry_price == 0:
            return 0.0
        return (self.ltp - self.avg_entry_price) / self.avg_entry_price

    @property
    def r_multiple(self) -> float:
        """How many R multiples (risk units) are we up/down?"""
        risk = abs(self.avg_entry_price - self.stop_loss)
        return self.unrealised_pnl / (risk * abs(self.quantity)) if risk else 0.0

    def summary(self) -> str:
        return (
            f"[Position] {self.symbol} Qty:{self.quantity} "
            f"Entry:{self.avg_entry_price:.2f} LTP:{self.ltp:.2f} "
            f"PnL:{self.unrealised_pnl:+.0f} ({self.unrealised_pnl_pct:+.1%}) "
            f"R:{self.r_multiple:.2f}"
        )


@dataclass
class Portfolio:
    """Aggregate view of all positions and portfolio metrics."""
    capital: float
    positions: Dict[str, Position] = field(default_factory=dict)
    realised_pnl: float = 0.0
    peak_capital: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.peak_capital == 0:
            self.peak_capital = self.capital

    @property
    def total_unrealised_pnl(self) -> float:
        return sum(p.unrealised_pnl for p in self.positions.values())

    @property
    def _confirmed_unrealised_pnl(self) -> float:
        """Unrealised P&L from positions with a confirmed live LTP only.

        Used for drawdown_pct to avoid false halts caused by startup-prefetch
        prices (e.g. raw NIFTY spot stored on an options premium position, or
        SIM ~1000 stored for an equity that failed the yfinance batch).
        Positions without has_live_ltp=True contribute 0 until the monitoring
        cycle provides a real market price.
        """
        return sum(p.unrealised_pnl for p in self.positions.values() if p.has_live_ltp)

    @property
    def net_value(self) -> float:
        return self.capital + self.total_unrealised_pnl + self.realised_pnl

    @property
    def drawdown_pct(self) -> float:
        if self.peak_capital == 0:
            return 0.0
        confirmed_net = self.capital + self._confirmed_unrealised_pnl + self.realised_pnl
        return max(0.0, (self.peak_capital - confirmed_net) / self.peak_capital)

    @property
    def num_positions(self) -> int:
        return len(self.positions)

    def sector_exposure(self) -> Dict[str, float]:
        """Returns capital allocated per strategy as a fraction of net_value."""
        exposure: Dict[str, float] = {}
        for pos in self.positions.values():
            key = pos.strategy_name or "unknown"
            exposure[key] = exposure.get(key, 0) + abs(pos.ltp * pos.quantity)
        return {k: v / self.net_value for k, v in exposure.items()}

    def summary(self) -> str:
        return (
            f"[Portfolio] Capital: ₹{self.capital:,.0f} | "
            f"Net Value: ₹{self.net_value:,.0f} | "
            f"Unrealised: {self.total_unrealised_pnl:+,.0f} | "
            f"Drawdown: {self.drawdown_pct:.1%} | "
            f"Open Positions: {self.num_positions}"
        )
