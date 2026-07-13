"""iios/investment/strategy/evaluation/walk_forward_analysis.py
Walk-forward (out-of-sample) stability analysis over the trade list.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from iios.investment.strategy.evaluation.trade import Trade
from iios.investment.strategy.evaluation.equity_curve import EquityCurve, EquityPoint
from iios.investment.strategy.evaluation.performance_statistics import (
    safe_mean, safe_std, sharpe_ratio, annualized_return, percentile
)

_MIN_TRADES_PER_WINDOW = 3


@dataclass(frozen=True)
class WalkForwardWindow:
    window_index:    int
    n_is_trades:     int
    n_oos_trades:    int
    is_sharpe:       float   # in-sample
    oos_sharpe:      float   # out-of-sample
    is_return:       float
    oos_return:      float
    oos_win_rate:    float
    degradation:     float   # is_sharpe - oos_sharpe


@dataclass(frozen=True)
class WalkForwardReport:
    n_windows:          int   = 0
    avg_oos_sharpe:     float = 0.0
    avg_oos_return:     float = 0.0
    avg_degradation:    float = 0.0   # mean(is_sharpe - oos_sharpe)
    stability_score:    float = 0.0   # 0–1; higher = more stable OOS
    oos_sharpe_std:     float = 0.0   # std of OOS Sharpe across windows
    pct_windows_positive: float = 0.0  # fraction with positive OOS return
    windows: List[WalkForwardWindow] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_windows":            self.n_windows,
            "avg_oos_sharpe":       self.avg_oos_sharpe,
            "avg_oos_return":       self.avg_oos_return,
            "avg_degradation":      self.avg_degradation,
            "stability_score":      self.stability_score,
            "oos_sharpe_std":       self.oos_sharpe_std,
            "pct_windows_positive": self.pct_windows_positive,
        }


class WalkForwardAnalyzer:

    def __init__(self, n_folds: int = 4) -> None:
        self._n_folds = max(2, n_folds)

    def analyze(
        self,
        trades: List[Trade],
        equity_curve: EquityCurve,
        rf_per_period: float = 0.0,
        periods_per_year: int = 252,
    ) -> WalkForwardReport:
        if len(trades) < self._n_folds * _MIN_TRADES_PER_WINDOW:
            return WalkForwardReport()

        sorted_trades = sorted(trades, key=lambda t: t.entry_time)
        n = len(sorted_trades)
        # Build equal-sized IS and OOS windows over the trade list
        fold_size = n // (self._n_folds + 1)
        if fold_size < _MIN_TRADES_PER_WINDOW:
            return WalkForwardReport()

        windows: List[WalkForwardWindow] = []

        for i in range(self._n_folds):
            is_end = fold_size * (i + 1)
            oos_start = is_end
            oos_end = min(oos_start + fold_size, n)

            is_trades = sorted_trades[:is_end]
            oos_trades = sorted_trades[oos_start:oos_end]

            if (
                len(is_trades) < _MIN_TRADES_PER_WINDOW
                or len(oos_trades) < _MIN_TRADES_PER_WINDOW
            ):
                continue

            is_sr = self._trade_sharpe(is_trades, rf_per_period, periods_per_year)
            oos_sr = self._trade_sharpe(oos_trades, rf_per_period, periods_per_year)
            is_ret = sum(t.pnl_pct for t in is_trades) / len(is_trades)
            oos_ret = sum(t.pnl_pct for t in oos_trades) / len(oos_trades)
            oos_wr = sum(1 for t in oos_trades if t.is_winner) / len(oos_trades)

            windows.append(WalkForwardWindow(
                window_index=i,
                n_is_trades=len(is_trades),
                n_oos_trades=len(oos_trades),
                is_sharpe=is_sr,
                oos_sharpe=oos_sr,
                is_return=is_ret,
                oos_return=oos_ret,
                oos_win_rate=oos_wr,
                degradation=is_sr - oos_sr,
            ))

        if not windows:
            return WalkForwardReport()

        oos_sharpes = [w.oos_sharpe for w in windows]
        oos_returns = [w.oos_return for w in windows]
        degradations = [w.degradation for w in windows]

        avg_oos_sr = safe_mean(oos_sharpes)
        avg_oos_ret = safe_mean(oos_returns)
        avg_deg = safe_mean(degradations)
        oos_sr_std = safe_std(oos_sharpes)

        # Stability score: fraction positive OOS Sharpes, penalised by degradation
        pos_windows = sum(1 for s in oos_sharpes if s > 0.0)
        pct_positive = pos_windows / len(windows)
        # Normalise average degradation penalty
        deg_penalty = min(1.0, max(0.0, avg_deg / 2.0))  # scale: 0 deg → 0 penalty
        stability = max(0.0, pct_positive - 0.5 * deg_penalty)

        return WalkForwardReport(
            n_windows=len(windows),
            avg_oos_sharpe=avg_oos_sr,
            avg_oos_return=avg_oos_ret,
            avg_degradation=avg_deg,
            stability_score=stability,
            oos_sharpe_std=oos_sr_std,
            pct_windows_positive=pct_positive,
            windows=windows,
        )

    @staticmethod
    def _trade_sharpe(
        trades: List[Trade], rf_per_period: float, periods_per_year: int
    ) -> float:
        returns = [t.pnl_pct for t in trades]
        return sharpe_ratio(returns, rf_per_period, periods_per_year)
