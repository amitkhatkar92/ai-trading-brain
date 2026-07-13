"""iios/investment/strategy/evaluation/drawdown_analysis.py
Drawdown metrics: max DD, avg DD, DD duration, Ulcer Index.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.strategy.evaluation.equity_curve import EquityCurve
from iios.investment.strategy.evaluation.performance_statistics import (
    safe_mean, percentile
)


@dataclass(frozen=True)
class DrawdownMetrics:
    max_drawdown: float         = 0.0   # fraction, e.g. 0.20 = 20 %
    avg_drawdown: float         = 0.0   # mean of all intra-drawdown points
    max_drawdown_duration: int  = 0     # periods from peak to trough
    avg_drawdown_duration: float = 0.0  # avg periods per drawdown episode
    recovery_periods: int       = 0     # periods from trough to new peak
    ulcer_index: float          = 0.0   # sqrt(mean(dd_pct^2)); lower = better
    drawdown_count: int         = 0     # number of distinct drawdown episodes
    max_drawdown_currency: float = 0.0  # in the same units as equity values

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_drawdown":           self.max_drawdown,
            "avg_drawdown":           self.avg_drawdown,
            "max_drawdown_duration":  self.max_drawdown_duration,
            "avg_drawdown_duration":  self.avg_drawdown_duration,
            "recovery_periods":       self.recovery_periods,
            "ulcer_index":            self.ulcer_index,
            "drawdown_count":         self.drawdown_count,
            "max_drawdown_currency":  self.max_drawdown_currency,
        }


class DrawdownAnalyzer:
    """Computes all drawdown-related metrics from an EquityCurve."""

    def analyze(self, curve: EquityCurve) -> DrawdownMetrics:
        if curve.is_empty():
            return DrawdownMetrics()

        vals = curve.values
        n = len(vals)

        # Build drawdown series
        peak = vals[0]
        peak_idx = 0
        dd_series: List[float] = []
        dd_currency: List[float] = []
        peaks: List[float] = []
        for v in vals:
            peak = max(peak, v)
            peaks.append(peak)
            dd = (peak - v) / peak if peak > 0.0 else 0.0
            dd_series.append(dd)
            dd_currency.append(peak - v)

        max_dd = max(dd_series)
        max_dd_currency = max(dd_currency)
        avg_dd = safe_mean([d for d in dd_series if d > 0.0])

        # Ulcer Index
        ulcer = math.sqrt(safe_mean([d ** 2 for d in dd_series]))

        # Count distinct drawdown episodes and durations
        episodes, current_len = [], 0
        in_dd = False
        recovery_sum = 0
        recovery_count = 0
        for i, d in enumerate(dd_series):
            if d > 0.0:
                current_len += 1
                in_dd = True
            else:
                if in_dd:
                    episodes.append(current_len)
                    in_dd = False
                    current_len = 0
        if in_dd:
            episodes.append(current_len)

        # Max DD duration (longest episode length)
        max_dd_duration = max(episodes) if episodes else 0

        # Recovery: find the max DD trough and measure to next new peak
        if max_dd > 0.0:
            trough_idx = dd_series.index(max_dd)
            for j in range(trough_idx, n):
                if dd_series[j] == 0.0:
                    recovery_periods = j - trough_idx
                    break
            else:
                recovery_periods = n - trough_idx
        else:
            recovery_periods = 0

        return DrawdownMetrics(
            max_drawdown=max_dd,
            avg_drawdown=avg_dd,
            max_drawdown_duration=max_dd_duration,
            avg_drawdown_duration=safe_mean(episodes) if episodes else 0.0,
            recovery_periods=recovery_periods,
            ulcer_index=ulcer,
            drawdown_count=len(episodes),
            max_drawdown_currency=max_dd_currency,
        )
