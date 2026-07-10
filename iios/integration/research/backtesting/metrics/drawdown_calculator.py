"""metrics/drawdown_calculator.py — Drawdown series and peak/trough analytics."""
from __future__ import annotations

from typing import Any


def drawdown_series(equity_curve: list[tuple[float, float]]) -> list[float]:
    """
    Compute fractional drawdown at every point.

    Returns list of values ≤ 0.  -0.20 means 20 % below peak.
    """
    if not equity_curve:
        return []
    peak   = equity_curve[0][1]
    result: list[float] = []
    for _, eq in equity_curve:
        peak = max(peak, eq)
        result.append((eq - peak) / peak if peak > 0 else 0.0)
    return result


def max_drawdown(equity_curve: list[tuple[float, float]]) -> float:
    """Return max drawdown as a positive fraction (0.20 == 20 % drawdown)."""
    dds = drawdown_series(equity_curve)
    return abs(min(dds)) if dds else 0.0


def max_drawdown_duration_bars(equity_curve: list[tuple[float, float]]) -> int:
    """Return the longest drawdown period measured in bars."""
    if not equity_curve:
        return 0
    peak          = equity_curve[0][1]
    current_len   = 0
    max_len       = 0
    for _, eq in equity_curve:
        if eq >= peak:
            peak        = eq
            current_len = 0
        else:
            current_len += 1
            max_len      = max(max_len, current_len)
    return max_len


def underwater_curve(equity_curve: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """
    Return the underwater equity curve: (timestamp, drawdown_fraction).

    Useful for plotting.
    """
    if not equity_curve:
        return []
    peak = equity_curve[0][1]
    result: list[tuple[float, float]] = []
    for ts, eq in equity_curve:
        peak = max(peak, eq)
        result.append((ts, (eq - peak) / peak if peak > 0 else 0.0))
    return result


def drawdown_periods(
    equity_curve: list[tuple[float, float]],
    threshold: float = 0.05,
) -> list[dict[str, Any]]:
    """
    Identify drawdown periods exceeding threshold.

    Returns list of dicts with keys: start_ts, end_ts, max_dd_pct, duration_bars.
    threshold – minimum drawdown fraction to report (0.05 == 5 %).
    """
    dds = drawdown_series(equity_curve)
    periods: list[dict[str, Any]] = []
    in_dd        = False
    start_idx    = 0
    running_min  = 0.0

    for i, dd in enumerate(dds):
        if dd < -threshold:
            if not in_dd:
                in_dd    = True
                start_idx = i
                running_min = dd
            else:
                running_min = min(running_min, dd)
        else:
            if in_dd:
                periods.append({
                    "start_ts":    equity_curve[start_idx][0],
                    "end_ts":      equity_curve[i][0],
                    "max_dd_pct":  abs(running_min),
                    "duration_bars": i - start_idx,
                })
                in_dd = False

    if in_dd:
        periods.append({
            "start_ts":    equity_curve[start_idx][0],
            "end_ts":      equity_curve[-1][0],
            "max_dd_pct":  abs(running_min),
            "duration_bars": len(dds) - start_idx,
        })

    return periods
