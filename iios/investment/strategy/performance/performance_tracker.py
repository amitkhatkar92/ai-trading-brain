"""iios/investment/strategy/performance/performance_tracker.py
Thread-safe per-strategy performance record store with incremental stats.
"""
from __future__ import annotations

import math
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from iios.investment.strategy.strategy_constants import DEFAULT_HISTORY_SIZE
from iios.investment.strategy.performance.performance_record import PerformanceRecord


@dataclass
class StrategyStatistics:
    """Computed aggregate statistics from a set of PerformanceRecord objects."""

    strategy_id:      str   = ""
    total_trades:     int   = 0
    winning_trades:   int   = 0
    losing_trades:    int   = 0
    win_rate:         float = 0.0    # fraction [0, 1]
    avg_return:       float = 0.0    # fractional mean PnL
    avg_win:          float = 0.0    # mean PnL of winning trades
    avg_loss:         float = 0.0    # mean PnL of losing trades (negative)
    profit_factor:    float = 0.0    # |total_wins| / |total_losses|
    max_drawdown:     float = 0.0    # max peak-to-trough as fraction
    sharpe_ratio:     float = 0.0    # annualised (252 trading days)
    sortino_ratio:    float = 0.0
    best_trade:       float = 0.0
    worst_trade:      float = 0.0
    avg_holding_days: float = 0.0
    total_pnl:        float = 0.0
    metadata:         dict[str, Any] = field(default_factory=dict)

    @property
    def has_enough_data(self) -> bool:
        from iios.investment.strategy.strategy_constants import MIN_TRADES_FOR_EVAL
        return self.total_trades >= MIN_TRADES_FOR_EVAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id":      self.strategy_id,
            "total_trades":     self.total_trades,
            "winning_trades":   self.winning_trades,
            "losing_trades":    self.losing_trades,
            "win_rate":         round(self.win_rate, 6),
            "avg_return":       round(self.avg_return, 6),
            "avg_win":          round(self.avg_win, 6),
            "avg_loss":         round(self.avg_loss, 6),
            "profit_factor":    round(self.profit_factor, 4),
            "max_drawdown":     round(self.max_drawdown, 6),
            "sharpe_ratio":     round(self.sharpe_ratio, 4),
            "sortino_ratio":    round(self.sortino_ratio, 4),
            "best_trade":       round(self.best_trade, 6),
            "worst_trade":      round(self.worst_trade, 6),
            "avg_holding_days": round(self.avg_holding_days, 2),
            "total_pnl":        round(self.total_pnl, 6),
            "has_enough_data":  self.has_enough_data,
            "metadata":         self.metadata,
        }


def _compute_statistics(
    strategy_id: str,
    records: list[PerformanceRecord],
) -> StrategyStatistics:
    """Pure function — derives StrategyStatistics from a list of records."""
    n = len(records)
    if n == 0:
        return StrategyStatistics(strategy_id=strategy_id)

    pnls      = [r.pnl for r in records]
    wins      = [r for r in records if r.is_win]
    losses    = [r for r in records if r.is_loss]
    durations = [r.duration_days for r in records]

    total_pnl = sum(pnls)
    avg_ret   = total_pnl / n

    avg_win  = sum(r.pnl for r in wins)  / len(wins)  if wins   else 0.0
    avg_loss = sum(r.pnl for r in losses) / len(losses) if losses else 0.0

    total_win_pnl  = sum(r.pnl for r in wins)
    total_loss_pnl = abs(sum(r.pnl for r in losses))
    profit_factor  = total_win_pnl / total_loss_pnl if total_loss_pnl > 0 else (
        float("inf") if total_win_pnl > 0 else 0.0
    )

    # Max drawdown via equity curve
    equity = 0.0
    peak   = 0.0
    max_dd = 0.0
    for pnl in pnls:
        equity += pnl
        if equity > peak:
            peak = equity
        dd = (peak - equity) / (1 + peak) if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    # Sharpe (annualised, assume 252 trading days)
    if n >= 2:
        mean   = avg_ret
        var    = sum((p - mean) ** 2 for p in pnls) / (n - 1)
        std    = math.sqrt(var) if var > 0 else 0.0
        sharpe = (mean / std) * math.sqrt(252) if std > 0 else 0.0
    else:
        sharpe = 0.0

    # Sortino — downside deviation
    down_pnls = [p for p in pnls if p < 0]
    if down_pnls and n >= 2:
        down_var = sum(p ** 2 for p in down_pnls) / (n - 1)
        down_std = math.sqrt(down_var)
        sortino  = (avg_ret / down_std) * math.sqrt(252) if down_std > 0 else 0.0
    else:
        sortino = 0.0

    return StrategyStatistics(
        strategy_id      = strategy_id,
        total_trades     = n,
        winning_trades   = len(wins),
        losing_trades    = len(losses),
        win_rate         = len(wins) / n,
        avg_return       = avg_ret,
        avg_win          = avg_win,
        avg_loss         = avg_loss,
        profit_factor    = min(profit_factor, 999.0),
        max_drawdown     = max_dd,
        sharpe_ratio     = round(sharpe, 4),
        sortino_ratio    = round(sortino, 4),
        best_trade       = max(pnls),
        worst_trade      = min(pnls),
        avg_holding_days = sum(durations) / n if durations else 0.0,
        total_pnl        = total_pnl,
    )


class PerformanceTracker:
    """
    Thread-safe store for PerformanceRecord objects per strategy.

    Maintains a bounded ring buffer per strategy (default 10 000 records).
    Cached statistics are invalidated on every new record.
    """

    def __init__(self, max_per_strategy: int = DEFAULT_HISTORY_SIZE) -> None:
        self._lock             = threading.RLock()
        self._max              = max_per_strategy
        self._store:  dict[str, deque[PerformanceRecord]] = {}
        self._stats:  dict[str, StrategyStatistics]       = {}   # cache
        self._dirty:  set[str]                             = set()

    def add_record(self, strategy_id: str, record: PerformanceRecord) -> None:
        with self._lock:
            buf = self._store.setdefault(strategy_id, deque(maxlen=self._max))
            buf.append(record)
            self._dirty.add(strategy_id)

    def get_records(self, strategy_id: str) -> list[PerformanceRecord]:
        with self._lock:
            return list(self._store.get(strategy_id, []))

    def get_stats(self, strategy_id: str) -> StrategyStatistics:
        with self._lock:
            if strategy_id not in self._stats or strategy_id in self._dirty:
                records = list(self._store.get(strategy_id, []))
                self._stats[strategy_id] = _compute_statistics(strategy_id, records)
                self._dirty.discard(strategy_id)
            return self._stats[strategy_id]

    def record_count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._store.get(strategy_id, []))

    def all_strategies(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "tracked_strategies": len(self._store),
                "total_records":      sum(len(b) for b in self._store.values()),
                "max_per_strategy":   self._max,
            }
