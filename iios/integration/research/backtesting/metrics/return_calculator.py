"""metrics/return_calculator.py — Return series and summary return metrics."""
from __future__ import annotations

import math
from typing import Any

from iios.integration.research.backtesting.backtest_constants import TRADING_DAYS_PER_YEAR


def calculate_bar_returns(equity_curve: list[tuple[float, float]]) -> list[float]:
    """
    Compute bar-over-bar fractional returns from an equity curve.

    equity_curve – list of (timestamp, equity) sorted by timestamp.
    Returns list of length len(equity_curve) - 1.
    """
    if len(equity_curve) < 2:
        return []
    returns: list[float] = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1][1]
        curr = equity_curve[i][1]
        returns.append((curr - prev) / prev if prev > 0 else 0.0)
    return returns


def total_return(initial: float, final: float) -> float:
    """Fractional total return. (1.0 == 100 % return)"""
    if initial <= 0:
        return 0.0
    return (final - initial) / initial


def annualized_return(total_ret: float, trading_days: int) -> float:
    """
    Compound annualised return.

    total_ret    – fractional total return (e.g. 0.25 for 25 %)
    trading_days – number of simulated trading days
    """
    if trading_days <= 0:
        return 0.0
    return (1.0 + total_ret) ** (TRADING_DAYS_PER_YEAR / trading_days) - 1.0


def cumulative_returns(equity_curve: list[tuple[float, float]]) -> list[float]:
    """Return cumulative return at each point (fraction from start)."""
    if not equity_curve:
        return []
    initial = equity_curve[0][1]
    if initial <= 0:
        return [0.0] * len(equity_curve)
    return [(eq / initial) - 1.0 for _, eq in equity_curve]


def monthly_returns(
    equity_curve: list[tuple[float, float]],
) -> dict[str, float]:
    """
    Group equity curve into calendar-month buckets.

    Returns dict of "YYYY-MM" → monthly fractional return.
    Requires timestamps to be unix epoch seconds.
    """
    from datetime import datetime, timezone

    if len(equity_curve) < 2:
        return {}

    monthly: dict[str, list[float]] = {}
    for ts, eq in equity_curve:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        key = f"{dt.year:04d}-{dt.month:02d}"
        monthly.setdefault(key, []).append(eq)

    result: dict[str, float] = {}
    for key in sorted(monthly.keys()):
        vals = monthly[key]
        if len(vals) >= 2:
            result[key] = total_return(vals[0], vals[-1])
    return result


def annual_returns(
    equity_curve: list[tuple[float, float]],
) -> dict[str, float]:
    """Return dict of "YYYY" → annual fractional return."""
    from datetime import datetime, timezone

    if len(equity_curve) < 2:
        return {}

    annual: dict[str, list[float]] = {}
    for ts, eq in equity_curve:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        key = str(dt.year)
        annual.setdefault(key, []).append(eq)

    result: dict[str, float] = {}
    for key in sorted(annual.keys()):
        vals = annual[key]
        if len(vals) >= 2:
            result[key] = total_return(vals[0], vals[-1])
    return result
