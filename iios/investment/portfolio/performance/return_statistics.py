"""iios/investment/portfolio/performance/return_statistics.py

Return distribution statistics: volatility, skewness, kurtosis, percentiles.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.performance.performance_types import TRADING_DAYS


@dataclass(frozen=True)
class ReturnDistribution:
    """Statistical distribution of portfolio returns."""

    result_id:         str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str   = ""

    n_observations:    int   = 0
    mean_return:       float = 0.0
    median_return:     float = 0.0
    std_return:        float = 0.0
    annual_vol:        float = 0.0

    min_return:        float = 0.0
    max_return:        float = 0.0
    p5_return:         float = 0.0    # 5th percentile (loss)
    p25_return:        float = 0.0
    p75_return:        float = 0.0
    p95_return:        float = 0.0

    skewness:          float = 0.0    # negative = left-skewed
    excess_kurtosis:   float = 0.0    # positive = fat tails

    positive_periods:  int   = 0
    negative_periods:  int   = 0
    win_rate:          float = 0.0    # fraction of positive periods

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_observations":  self.n_observations,
            "mean_return":     round(self.mean_return, 4),
            "std_return":      round(self.std_return, 4),
            "annual_vol":      round(self.annual_vol, 4),
            "min_return":      round(self.min_return, 4),
            "max_return":      round(self.max_return, 4),
            "skewness":        round(self.skewness, 4),
            "excess_kurtosis": round(self.excess_kurtosis, 4),
            "win_rate":        round(self.win_rate, 4),
        }


def compute_return_statistics(
    returns:      List[float],
    portfolio_id: str   = "",
    annualize:    bool  = True,
    periods_per_year: int = TRADING_DAYS,
) -> ReturnDistribution:
    """Compute full distribution statistics from a list of period returns."""
    n = len(returns)
    if n == 0:
        return ReturnDistribution(portfolio_id=portfolio_id)

    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / n if n > 1 else 0.0
    std  = math.sqrt(variance)
    ann_vol = std * math.sqrt(periods_per_year) if annualize else std

    sorted_r = sorted(returns)
    median   = _percentile(sorted_r, 50)
    p5       = _percentile(sorted_r, 5)
    p25      = _percentile(sorted_r, 25)
    p75      = _percentile(sorted_r, 75)
    p95      = _percentile(sorted_r, 95)

    skew  = _skewness(returns, mean, std)
    kurt  = _excess_kurtosis(returns, mean, std)

    pos = sum(1 for r in returns if r > 0)
    neg = sum(1 for r in returns if r <= 0)
    win = pos / n

    return ReturnDistribution(
        portfolio_id    = portfolio_id,
        n_observations  = n,
        mean_return     = round(mean, 6),
        median_return   = round(median, 6),
        std_return      = round(std, 6),
        annual_vol      = round(ann_vol, 6),
        min_return      = round(sorted_r[0], 6),
        max_return      = round(sorted_r[-1], 6),
        p5_return       = round(p5, 6),
        p25_return      = round(p25, 6),
        p75_return      = round(p75, 6),
        p95_return      = round(p95, 6),
        skewness        = round(skew, 4),
        excess_kurtosis = round(kurt, 4),
        positive_periods= pos,
        negative_periods= neg,
        win_rate        = round(win, 4),
    )


def _percentile(sorted_data: List[float], pct: float) -> float:
    """Linear interpolation percentile on sorted data."""
    n = len(sorted_data)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_data[0]
    pos = (pct / 100.0) * (n - 1)
    lo  = int(pos)
    hi  = lo + 1
    if hi >= n:
        return sorted_data[-1]
    frac = pos - lo
    return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac


def _skewness(returns: List[float], mean: float, std: float) -> float:
    n = len(returns)
    if n < 3 or std < 1e-12:
        return 0.0
    return sum(((r - mean) / std) ** 3 for r in returns) / n


def _excess_kurtosis(returns: List[float], mean: float, std: float) -> float:
    n = len(returns)
    if n < 4 or std < 1e-12:
        return 0.0
    return sum(((r - mean) / std) ** 4 for r in returns) / n - 3.0
