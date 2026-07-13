"""iios/investment/strategy/evaluation/performance_statistics.py
Pure statistical helpers — no I/O, no state, safe to use from any thread.
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple


# ── basic stats ──────────────────────────────────────────────────────────────

def safe_mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def safe_std(xs: List[float], ddof: int = 1) -> float:
    n = len(xs)
    if n <= ddof:
        return 0.0
    m = safe_mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (n - ddof)
    return math.sqrt(var)


def safe_variance(xs: List[float], ddof: int = 1) -> float:
    n = len(xs)
    if n <= ddof:
        return 0.0
    m = safe_mean(xs)
    return sum((x - m) ** 2 for x in xs) / (n - ddof)


def safe_median(xs: List[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def percentile(xs: List[float], p: float) -> float:
    """Linear interpolation percentile, p in [0, 100]."""
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    if n == 1:
        return s[0]
    idx = p / 100.0 * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    frac = idx - lo
    return s[lo] + frac * (s[hi] - s[lo])


def covariance(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    if n != len(ys) or n < 2:
        return 0.0
    mx, my = safe_mean(xs), safe_mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)


def correlation(xs: List[float], ys: List[float]) -> float:
    sx, sy = safe_std(xs), safe_std(ys)
    if sx == 0.0 or sy == 0.0:
        return 0.0
    return covariance(xs, ys) / (sx * sy)


# ── return-based metrics ─────────────────────────────────────────────────────

def annualized_return(total_return: float, years: float) -> float:
    if years <= 0.0 or total_return <= -1.0:
        return 0.0
    return (1.0 + total_return) ** (1.0 / years) - 1.0


def sharpe_ratio(
    returns: List[float],
    rf_per_period: float,
    periods_per_year: int = 252,
) -> float:
    """Annualised Sharpe ratio from period returns."""
    excess = [r - rf_per_period for r in returns]
    std = safe_std(excess)
    if std == 0.0:
        return 0.0
    return safe_mean(excess) / std * math.sqrt(periods_per_year)


def sortino_ratio(
    returns: List[float],
    rf_per_period: float,
    periods_per_year: int = 252,
) -> float:
    """Annualised Sortino ratio using downside deviation below rf."""
    excess = [r - rf_per_period for r in returns]
    m = safe_mean(excess)
    downside = [min(e, 0.0) ** 2 for e in excess]
    dd = math.sqrt(safe_mean(downside)) if downside else 0.0
    if dd == 0.0:
        return 0.0
    return m / dd * math.sqrt(periods_per_year)


def calmar_ratio(ann_return: float, max_drawdown: float) -> float:
    if max_drawdown == 0.0:
        return math.inf if ann_return > 0 else 0.0
    return ann_return / abs(max_drawdown)


def information_ratio(
    strategy_returns: List[float],
    benchmark_returns: List[float],
    periods_per_year: int = 252,
) -> float:
    if len(strategy_returns) != len(benchmark_returns):
        return 0.0
    active = [s - b for s, b in zip(strategy_returns, benchmark_returns)]
    te = safe_std(active) * math.sqrt(periods_per_year)
    if te == 0.0:
        return 0.0
    return safe_mean(active) * periods_per_year / te


def beta(
    strategy_returns: List[float],
    benchmark_returns: List[float],
) -> float:
    bv = safe_variance(benchmark_returns)
    if bv == 0.0:
        return 1.0
    return covariance(strategy_returns, benchmark_returns) / bv


def alpha(
    ann_strategy: float,
    ann_benchmark: float,
    beta_val: float,
    rf_rate: float,
) -> float:
    return ann_strategy - (rf_rate + beta_val * (ann_benchmark - rf_rate))


def treynor_ratio(
    ann_return: float,
    beta_val: float,
    rf_rate: float,
) -> float:
    if beta_val == 0.0:
        return 0.0
    return (ann_return - rf_rate) / beta_val


def profit_factor(pnls: List[float]) -> float:
    gross_profit = sum(p for p in pnls if p > 0.0)
    gross_loss = abs(sum(p for p in pnls if p < 0.0))
    if gross_loss == 0.0:
        return math.inf if gross_profit > 0.0 else 1.0
    return gross_profit / gross_loss


def expectancy(win_rate: float, avg_winner: float, avg_loser: float) -> float:
    """Expected value per trade in currency units."""
    return win_rate * avg_winner - (1.0 - win_rate) * abs(avg_loser)


def recovery_factor(total_pnl: float, max_drawdown_value: float) -> float:
    if max_drawdown_value == 0.0:
        return math.inf if total_pnl > 0.0 else 0.0
    return total_pnl / abs(max_drawdown_value)


# ── normalisation helpers ────────────────────────────────────────────────────

def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def scale_metric(
    value: float,
    low: float,
    high: float,
    invert: bool = False,
) -> float:
    """Map value from [low, high] to [0, 100], clamp outside range."""
    if high == low:
        return 50.0
    raw = (value - low) / (high - low) * 100.0
    raw = clamp(raw, 0.0, 100.0)
    return 100.0 - raw if invert else raw
