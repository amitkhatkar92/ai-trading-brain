"""iios/investment/market/analytics/volatility_analyzer.py
Realized volatility from a return series.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from iios.investment.market.market_constants import (
    ANNUAL_TRADING_DAYS,
    MIN_HISTORY_FOR_VOLATILITY,
    VolatilityLevel,
)


@dataclass
class VolatilityAnalysis:
    level:        VolatilityLevel = VolatilityLevel.MODERATE
    realized_vol: float           = 0.0   # annualized, e.g. 0.20 = 20%
    daily_vol:    float           = 0.0
    score:        float           = 50.0  # 0–100
    metadata:     dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level":        self.level.value,
            "realized_vol": self.realized_vol,
            "daily_vol":    self.daily_vol,
            "score":        self.score,
            "metadata":     self.metadata,
        }


class VolatilityAnalyzer:
    """
    Annualized realized volatility via standard deviation of log returns.

    Input : list of period returns (e.g. [0.01, -0.005, …]) oldest first.
    Output: VolatilityAnalysis.
    """

    def analyze(
        self,
        returns:       list[float],
        *,
        window:        int   = 20,
        annual_factor: float = ANNUAL_TRADING_DAYS,
    ) -> VolatilityAnalysis:
        if len(returns) < MIN_HISTORY_FOR_VOLATILITY:
            return VolatilityAnalysis()

        series = returns[-window:] if len(returns) > window else list(returns)
        n      = len(series)

        mean      = sum(series) / n
        var       = sum((r - mean) ** 2 for r in series) / (n - 1) if n > 1 else 0.0
        daily_vol = math.sqrt(var)
        ann_vol   = daily_vol * math.sqrt(annual_factor)

        # Score: 0–100 where ann_vol ≥ 1.0 (100%) maps to 100
        score = min(100.0, ann_vol * 100)

        if ann_vol >= 0.60:
            level = VolatilityLevel.EXTREME
        elif ann_vol >= 0.30:
            level = VolatilityLevel.HIGH
        elif ann_vol >= 0.15:
            level = VolatilityLevel.MODERATE
        elif ann_vol >= 0.08:
            level = VolatilityLevel.LOW
        else:
            level = VolatilityLevel.VERY_LOW

        return VolatilityAnalysis(
            level        = level,
            realized_vol = round(ann_vol, 6),
            daily_vol    = round(daily_vol, 6),
            score        = round(score, 2),
            metadata     = {"n_bars": n, "mean_return": round(mean, 6)},
        )
