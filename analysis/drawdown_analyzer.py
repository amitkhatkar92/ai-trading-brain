"""
analysis/drawdown_analyzer.py
====================================
OPTIONS_RISK_AUDIT_001 — Equity curve and drawdown analytics.

No IO. No database. Pure functions over a time-ordered list of R-multiples.

Reconstructs a cumulative equity curve (starting at 0R) from a
date-sorted list of trade outcomes, then computes:

    max_drawdown_r     : peak-to-trough in R-multiples
    max_drawdown_pct   : as % of peak equity (capital erosion metric)
    recovery_days      : calendar days from trough to new equity high
    worst_week_r       : worst single ISO week sum of R
    worst_month_r      : worst single calendar month sum of R
    best_week_r        : best single week (completes the picture)
    best_month_r       : best single month
    calmar_ratio       : annualised return / |max_drawdown_r| (higher = better)
    ulcer_index        : RMS of all drawdown depths (pain index)
    consecutive_loss_r : total R lost in the worst consecutive loss streak

All metrics use R-multiples, not notional ₹ amounts, so they are
instrument-independent and comparable across strategies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import groupby
from typing import List, Optional, Tuple


@dataclass
class DrawdownResult:
    strategy:             str
    regime:               str
    n:                    int
    final_equity_r:       float      # total R accumulated over sample
    max_drawdown_r:       float      # peak-to-trough (negative, e.g. −8.4)
    max_drawdown_pct:     float      # as % of peak equity at that point
    recovery_trades:      int        # trades to recover from worst drawdown
    worst_week_r:         float      # worst ISO week P&L (negative)
    best_week_r:          float      # best ISO week P&L
    worst_month_r:        float      # worst calendar month P&L
    best_month_r:         float      # best calendar month P&L
    calmar_ratio:         float      # annualised_return / |max_dd|
    ulcer_index:          float      # RMS of drawdown depths
    consecutive_loss_r:   float      # R lost in worst loss streak (negative)
    worst_single_trade_r: float      # single worst trade R


def _equity_curve(pnl_series: List[float]) -> List[float]:
    """Cumulative sum of R series starting from 0."""
    curve  = []
    cumsum = 0.0
    for r in pnl_series:
        cumsum += r
        curve.append(cumsum)
    return curve


def _max_drawdown(curve: List[float]) -> Tuple[float, float, int]:
    """
    Returns (max_drawdown_r, max_drawdown_pct, recovery_trades).

    max_drawdown_r   : largest peak-to-trough drop in R
    max_drawdown_pct : drop as % of peak equity at that point
    recovery_trades  : number of trades from trough back to previous peak
    """
    if not curve:
        return 0.0, 0.0, 0

    peak         = curve[0]
    peak_idx     = 0
    max_dd       = 0.0
    max_dd_pct   = 0.0
    trough_idx   = 0

    for i, val in enumerate(curve):
        if val > peak:
            peak     = val
            peak_idx = i
        dd = val - peak
        if dd < max_dd:
            max_dd     = dd
            trough_idx = i
            # % of peak (use peak+100 to avoid div by 0; normalise around 100R base)
            max_dd_pct = (dd / (abs(peak) + 1e-9)) * 100 if peak != 0 else 0.0

    # Recovery: how many trades from trough until we exceeded the previous peak
    recovery = 0
    if trough_idx < len(curve) - 1:
        trough_val = curve[trough_idx]
        for j in range(trough_idx + 1, len(curve)):
            if curve[j] >= peak:
                recovery = j - trough_idx
                break
        if recovery == 0 and trough_idx < len(curve) - 1:
            recovery = len(curve) - 1 - trough_idx   # still in drawdown

    return round(max_dd, 3), round(max_dd_pct, 2), recovery


def _ulcer_index(curve: List[float]) -> float:
    """
    RMS of all drawdown depths relative to running peak.
    Higher = more painful volatility profile.
    """
    if not curve:
        return 0.0
    peak   = curve[0]
    sq_sum = 0.0
    for val in curve:
        if val > peak:
            peak = val
        dd    = val - peak
        sq_sum += dd ** 2
    return round(math.sqrt(sq_sum / len(curve)), 3)


def _group_by_period(
    records:    List[dict],
    period_key: str,    # "week" or "month"
) -> dict:
    """
    Sum pnl_r by week (YYYY-WNN) or month (YYYY-MM).
    Returns dict of period_label → total_r.
    """
    period_sums: dict = {}
    for r in records:
        date = str(r["date"])[:10]   # "YYYY-MM-DD"
        if len(date) < 7:
            continue
        if period_key == "month":
            key = date[:7]           # "YYYY-MM"
        else:
            # ISO week: crude but consistent — use year + week-of-year
            from datetime import datetime
            try:
                d    = datetime.strptime(date, "%Y-%m-%d")
                iso  = d.isocalendar()
                key  = f"{iso[0]}-W{iso[1]:02d}"
            except ValueError:
                continue
        period_sums[key] = period_sums.get(key, 0.0) + r["pnl_r"]
    return period_sums


def _worst_loss_streak_r(pnl_series: List[float]) -> float:
    """Total R lost during the single worst consecutive losing streak."""
    worst  = 0.0
    streak = 0.0
    for r in pnl_series:
        if r < 0:
            streak += r
            worst   = min(worst, streak)
        else:
            streak  = 0.0
    return round(worst, 3)


def compute_drawdown(
    strategy:   str,
    records:    List[dict],   # dicts with: date, pnl_r, win_loss
    regime:     str = "ALL",
) -> DrawdownResult:
    """
    Compute full drawdown and temporal risk metrics for one strategy.

    Args:
        strategy : name
        records  : list of dicts sorted by date (ascending),
                   each with keys: date (str YYYY-MM-DD), pnl_r (float)
        regime   : regime label for display
    """
    if not records:
        return DrawdownResult(
            strategy=strategy, regime=regime, n=0,
            final_equity_r=0, max_drawdown_r=0, max_drawdown_pct=0,
            recovery_trades=0, worst_week_r=0, best_week_r=0,
            worst_month_r=0, best_month_r=0, calmar_ratio=0,
            ulcer_index=0, consecutive_loss_r=0, worst_single_trade_r=0,
        )

    pnl_series = [r["pnl_r"] for r in sorted(records, key=lambda x: x["date"])]
    n          = len(pnl_series)
    curve      = _equity_curve(pnl_series)

    final_eq               = round(curve[-1], 3) if curve else 0.0
    max_dd_r, max_dd_pct, recov = _max_drawdown(curve)
    ui                     = _ulcer_index(curve)
    streak_r               = _worst_loss_streak_r(pnl_series)
    worst_single           = round(min(pnl_series), 3) if pnl_series else 0.0

    # Weekly / monthly grouping
    by_week  = _group_by_period(records, "week")
    by_month = _group_by_period(records, "month")

    worst_week  = round(min(by_week.values()),  3) if by_week  else 0.0
    best_week   = round(max(by_week.values()),  3) if by_week  else 0.0
    worst_month = round(min(by_month.values()), 3) if by_month else 0.0
    best_month  = round(max(by_month.values()), 3) if by_month else 0.0

    # Calmar: annualised return / |max_drawdown|
    # Assume ~52 trades/year → scale mean trade R to annual
    mean_r      = final_eq / n if n else 0.0
    annual_r    = mean_r * 52
    calmar      = round(annual_r / abs(max_dd_r), 3) if max_dd_r != 0 else 0.0

    return DrawdownResult(
        strategy             = strategy,
        regime               = regime,
        n                    = n,
        final_equity_r       = final_eq,
        max_drawdown_r       = max_dd_r,
        max_drawdown_pct     = max_dd_pct,
        recovery_trades      = recov,
        worst_week_r         = worst_week,
        best_week_r          = best_week,
        worst_month_r        = worst_month,
        best_month_r         = best_month,
        calmar_ratio         = calmar,
        ulcer_index          = ui,
        consecutive_loss_r   = streak_r,
        worst_single_trade_r = worst_single,
    )


def compute_all_drawdowns(
    all_records: List[dict],    # dicts with: strategy, regime, date, pnl_r
) -> dict:
    """
    Compute DrawdownResult for every strategy (overall + per-regime).

    Returns dict[strategy] = {"ALL": DrawdownResult, "HIGH_VOL": ..., ...}
    """
    by_strategy: dict = {}
    for r in all_records:
        s = r["strategy"]
        by_strategy.setdefault(s, []).append(r)

    result = {}
    for strat, recs in by_strategy.items():
        result[strat] = {}
        # Overall
        result[strat]["ALL"] = compute_drawdown(strat, recs, "ALL")
        # Per regime
        regimes = list({r["regime"] for r in recs})
        for regime in regimes:
            subset = [r for r in recs if r["regime"] == regime]
            result[strat][regime] = compute_drawdown(strat, subset, regime)
    return result
