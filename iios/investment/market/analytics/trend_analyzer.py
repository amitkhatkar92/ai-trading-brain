"""iios/investment/market/analytics/trend_analyzer.py
Trend direction and strength from a price series.
Pure computation — no I/O, no side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.market.market_constants import MarketStrength, TrendDirection


@dataclass
class TrendAnalysis:
    direction:   TrendDirection = TrendDirection.UNDEFINED
    strength:    MarketStrength = MarketStrength.NEUTRAL
    score:       float          = 50.0    # 0–100; 50 = neutral, >50 = up, <50 = down
    consistency: float          = 0.0    # 0–1 fraction of bars in dominant direction
    metadata:    dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction":   self.direction.value,
            "strength":    self.strength.value,
            "score":       self.score,
            "consistency": self.consistency,
            "metadata":    self.metadata,
        }


class TrendAnalyzer:
    """
    Computes trend via linear regression on a price series.

    Input : list of prices (oldest → newest), any length ≥ 2.
    Output: TrendAnalysis with direction, strength, score, consistency.
    """

    def analyze(
        self,
        prices: list[float],
        *,
        window: int = 20,
    ) -> TrendAnalysis:
        if not prices or len(prices) < 2:
            return TrendAnalysis()

        series = prices[-window:] if len(prices) > window else list(prices)
        n      = len(series)

        # Linear regression slope
        x_bar = (n - 1) / 2.0
        y_bar = sum(series) / n
        sxy   = sum((i - x_bar) * (y - y_bar) for i, y in enumerate(series))
        sxx   = sum((i - x_bar) ** 2 for i in range(n))

        slope     = sxy / sxx if sxx != 0 else 0.0
        rel_slope = slope / y_bar if y_bar != 0 else 0.0  # normalised % per bar

        # Bar-level consistency
        up_bars   = sum(1 for i in range(1, n) if series[i] > series[i - 1])
        down_bars = sum(1 for i in range(1, n) if series[i] < series[i - 1])
        total     = n - 1
        consistency = max(up_bars, down_bars) / total if total > 0 else 0.0

        # Direction
        if rel_slope > 0.001:
            direction = TrendDirection.UP
            score     = min(100.0, 50.0 + rel_slope * 5000)
        elif rel_slope < -0.001:
            direction = TrendDirection.DOWN
            score     = max(0.0, 50.0 + rel_slope * 5000)
        else:
            direction = TrendDirection.SIDEWAYS
            score     = 50.0

        # Strength bands (relative slope magnitude)
        abs_slope = abs(rel_slope)
        if abs_slope > 0.02:
            strength = MarketStrength.VERY_STRONG
        elif abs_slope > 0.01:
            strength = MarketStrength.STRONG
        elif abs_slope > 0.005:
            strength = MarketStrength.MODERATE
        elif abs_slope > 0.001:
            strength = MarketStrength.WEAK
        else:
            strength = MarketStrength.NEUTRAL

        return TrendAnalysis(
            direction   = direction,
            strength    = strength,
            score       = round(score, 2),
            consistency = round(consistency, 4),
            metadata    = {"rel_slope": rel_slope, "n_bars": n},
        )
