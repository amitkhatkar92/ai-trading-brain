"""metrics/risk_metrics.py — Sharpe, Sortino, Calmar, Volatility, Beta, VaR."""
from __future__ import annotations

import math
import statistics
from typing import Optional

from iios.integration.research.backtesting.backtest_constants import TRADING_DAYS_PER_YEAR


# ── Core risk metrics ─────────────────────────────────────────────────────────

def volatility(daily_returns: list[float]) -> float:
    """Annualised volatility (std of daily returns × √252)."""
    if len(daily_returns) < 2:
        return 0.0
    return statistics.stdev(daily_returns) * math.sqrt(TRADING_DAYS_PER_YEAR)


def sharpe_ratio(
    daily_returns: list[float],
    risk_free_rate: float = 0.06,
) -> float:
    """
    Annualised Sharpe ratio.

    sharpe = (annualised_excess_return) / annualised_volatility
    """
    if len(daily_returns) < 2:
        return 0.0
    daily_rf  = risk_free_rate / TRADING_DAYS_PER_YEAR
    excess    = [r - daily_rf for r in daily_returns]
    mean_exc  = statistics.mean(excess)
    stdev_exc = statistics.stdev(excess)
    if stdev_exc == 0.0:
        return 0.0
    return mean_exc / stdev_exc * math.sqrt(TRADING_DAYS_PER_YEAR)


def sortino_ratio(
    daily_returns: list[float],
    risk_free_rate: float = 0.06,
) -> float:
    """
    Annualised Sortino ratio.

    Uses only downside deviation (negative excess returns).
    """
    if len(daily_returns) < 2:
        return 0.0
    daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
    excess   = [r - daily_rf for r in daily_returns]
    neg      = [r for r in excess if r < 0.0]
    if not neg:
        return float("inf")
    downside_stdev = statistics.stdev(neg) if len(neg) > 1 else abs(neg[0])
    if downside_stdev == 0.0:
        return 0.0
    return statistics.mean(excess) / downside_stdev * math.sqrt(TRADING_DAYS_PER_YEAR)


def calmar_ratio(annualised_return: float, max_dd: float) -> float:
    """Calmar = annualised_return / max_drawdown."""
    if max_dd == 0.0:
        return float("inf") if annualised_return > 0 else 0.0
    return annualised_return / max_dd


def omega_ratio(
    daily_returns: list[float],
    threshold: float = 0.0,
) -> float:
    """
    Omega ratio: sum(gains above threshold) / abs(sum(losses below threshold)).
    """
    gains  = sum(max(r - threshold, 0.0) for r in daily_returns)
    losses = sum(max(threshold - r, 0.0) for r in daily_returns)
    if losses == 0.0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def value_at_risk(
    daily_returns: list[float],
    confidence:    float = 0.95,
) -> float:
    """
    Historical VaR at given confidence level (positive number = loss).

    confidence = 0.95 returns the 5th-percentile return.
    """
    if not daily_returns:
        return 0.0
    sorted_r = sorted(daily_returns)
    idx = max(0, int((1.0 - confidence) * len(sorted_r)) - 1)
    return abs(sorted_r[idx])


def compute_beta(
    strategy_returns:  list[float],
    benchmark_returns: list[float],
) -> float:
    """
    OLS beta of strategy vs benchmark.

    Returns 0.0 if data series lengths differ or variance is zero.
    """
    n = min(len(strategy_returns), len(benchmark_returns))
    if n < 2:
        return 0.0
    s  = strategy_returns[:n]
    b  = benchmark_returns[:n]
    cov    = statistics.covariance(s, b)
    var_b  = statistics.variance(b)
    return cov / var_b if var_b != 0 else 0.0


def information_ratio(
    strategy_returns:  list[float],
    benchmark_returns: list[float],
) -> float:
    """
    Information ratio = mean(active_return) / tracking_error.
    """
    n = min(len(strategy_returns), len(benchmark_returns))
    if n < 2:
        return 0.0
    active = [s - b for s, b in zip(strategy_returns[:n], benchmark_returns[:n])]
    te     = statistics.stdev(active) if len(active) > 1 else 0.0
    if te == 0.0:
        return 0.0
    return statistics.mean(active) / te * math.sqrt(TRADING_DAYS_PER_YEAR)
