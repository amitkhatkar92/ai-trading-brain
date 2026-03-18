"""
Performance Evaluation Framework — Drawdown Analyzer
=====================================================
Analyses equity curve drawdown characteristics:

Metrics produced:
  • max_drawdown_pct     — largest peak-to-trough decline
  • current_drawdown_pct — current unrealised drawdown
  • avg_drawdown_pct     — average of all drawdowns > 0.5%
  • max_drawdown_duration_days — longest time spent below previous high
  • avg_recovery_days    — average trading days to recover from a drawdown
  • calmar_ratio         — annualised return / max drawdown
  • pain_index           — average depth of all underwater periods
  • ulcer_index          — RMS of drawdown series (penalises deep + long DDs)
"""

from __future__ import annotations
import math
import statistics
from dataclasses import dataclass, field
from typing import Optional

from utils import get_logger

log = get_logger(__name__)


@dataclass
class DrawdownReport:
    max_drawdown_pct:           float = 0.0
    current_drawdown_pct:       float = 0.0
    avg_drawdown_pct:           float = 0.0
    max_drawdown_duration_days: int   = 0
    avg_recovery_days:          float = 0.0
    calmar_ratio:               float = 0.0
    pain_index:                 float = 0.0
    ulcer_index:                float = 0.0
    underwater_pct:             float = 0.0   # % of time in drawdown

    def summary(self) -> str:
        return (
            f"MaxDD={self.max_drawdown_pct:.1f}% | "
            f"CurrDD={self.current_drawdown_pct:.1f}% | "
            f"MaxDuration={self.max_drawdown_duration_days}d | "
            f"Calmar={self.calmar_ratio:.2f} | "
            f"UlcerIdx={self.ulcer_index:.3f}"
        )


class DrawdownAnalyzer:
    """Analyses an equity curve for drawdown characteristics."""

    def __init__(self) -> None:
        log.info("[DrawdownAnalyzer] Initialised.")

    def analyse(self, equity_curve: list[float],
                annualised_return_pct: float = 0.0) -> DrawdownReport:
        """
        Parameters
        ----------
        equity_curve : list[float]
            Ordered sequence of portfolio values (one per trading day/cycle).
        annualised_return_pct : float
            For Calmar ratio calculation.
        """
        if len(equity_curve) < 2:
            return DrawdownReport()

        # Build drawdown series (as positive %)
        peak        = equity_curve[0]
        dd_series:  list[float] = []
        durations:  list[int]   = []
        recoveries: list[int]   = []
        in_dd       = False
        dd_start    = 0
        current_dur = 0

        for i, val in enumerate(equity_curve):
            if val > peak:
                peak = val
                if in_dd:
                    recoveries.append(i - dd_start)
                    in_dd = False
            dd = (peak - val) / peak * 100 if peak > 0 else 0.0
            dd_series.append(dd)
            if dd > 0.5:
                if not in_dd:
                    in_dd    = True
                    dd_start = i
                current_dur = i - dd_start + 1
                durations.append(current_dur)

        max_dd       = max(dd_series) if dd_series else 0.0
        current_dd   = dd_series[-1]  if dd_series else 0.0
        sig_dds      = [d for d in dd_series if d > 0.5]
        avg_dd       = statistics.mean(sig_dds) if sig_dds else 0.0
        max_dur      = max(durations) if durations else 0
        avg_rec      = statistics.mean(recoveries) if recoveries else 0.0
        pain_idx     = statistics.mean(dd_series)  if dd_series else 0.0
        ulcer_idx    = math.sqrt(statistics.mean([d**2 for d in dd_series])) \
                       if dd_series else 0.0
        underwater_p = sum(1 for d in dd_series if d > 0) / len(dd_series) * 100 \
                       if dd_series else 0.0
        calmar       = annualised_return_pct / max_dd if max_dd > 0 else 0.0

        return DrawdownReport(
            max_drawdown_pct           = round(max_dd, 2),
            current_drawdown_pct       = round(current_dd, 2),
            avg_drawdown_pct           = round(avg_dd, 2),
            max_drawdown_duration_days = max_dur,
            avg_recovery_days          = round(avg_rec, 1),
            calmar_ratio               = round(calmar, 3),
            pain_index                 = round(pain_idx, 4),
            ulcer_index                = round(ulcer_idx, 4),
            underwater_pct             = round(underwater_p, 1),
        )
