"""portfolio/performance_tracker.py — Running performance metrics for a paper trading session."""
from __future__ import annotations

from typing import Any

from iios.integration.research.paper_trading.core.paper_trade import PaperTrade


class PerformanceTracker:
    """
    Tracks equity and completed trades to provide live performance metrics.

    Designed to be updated once per bar.
    """

    def __init__(self) -> None:
        self._equity_curve: list[tuple[float, float]] = []   # (timestamp, equity)
        self._trade_log:    list[PaperTrade]           = []
        self._peak_equity:  float                      = 0.0
        self._initial_equity: float                    = 0.0
        self._initialized:  bool                       = False

    # ── Update methods ────────────────────────────────────────────────────────

    def update(self, equity: float, timestamp: float) -> None:
        """Record the current equity value at *timestamp*."""
        if not self._initialized:
            self._initial_equity = equity
            self._peak_equity    = equity
            self._initialized    = True
        self._equity_curve.append((timestamp, equity))
        if equity > self._peak_equity:
            self._peak_equity = equity

    def record_trade(self, trade: PaperTrade) -> None:
        self._trade_log.append(trade)

    # ── Derived metrics ───────────────────────────────────────────────────────

    def current_drawdown(self) -> float:
        """Current drawdown from peak as a fraction."""
        if self._peak_equity <= 0.0:
            return 0.0
        current = self._equity_curve[-1][1] if self._equity_curve else self._initial_equity
        return max(0.0, (self._peak_equity - current) / self._peak_equity)

    def peak_equity(self) -> float:
        return self._peak_equity

    def total_return(self) -> float:
        if self._initial_equity <= 0.0 or not self._equity_curve:
            return 0.0
        return (self._equity_curve[-1][1] - self._initial_equity) / self._initial_equity

    def win_rate(self) -> float:
        if not self._trade_log:
            return 0.0
        winners = sum(1 for t in self._trade_log if t.is_winner())
        return winners / len(self._trade_log)

    def equity_curve(self) -> list[tuple[float, float]]:
        return list(self._equity_curve)

    def trade_log(self) -> list[PaperTrade]:
        return list(self._trade_log)

    def trade_count(self) -> int:
        return len(self._trade_log)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "bar_count":       len(self._equity_curve),
            "trade_count":     len(self._trade_log),
            "total_return":    self.total_return(),
            "current_drawdown": self.current_drawdown(),
            "peak_equity":     self._peak_equity,
            "win_rate":        self.win_rate(),
        }
