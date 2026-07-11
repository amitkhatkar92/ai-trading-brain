"""iios/investment/market/breadth/new_high_low_metric.py
New 52-week highs vs new 52-week lows breadth metric.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from iios.investment.market.breadth.models import BreadthMetricValue

if TYPE_CHECKING:
    from iios.investment.market.breadth.models import SecurityObservation


class NewHighLowMetric:
    """New-high / new-low ratio as a market-breadth signal."""

    @property
    def name(self) -> str:
        return "new_high_low"

    @property
    def required_observations(self) -> int:
        return 1

    def compute(
        self, observations: "List[SecurityObservation]"
    ) -> Optional[BreadthMetricValue]:
        n = len(observations)
        if n < self.required_observations:
            return None

        new_highs = sum(1 for o in observations if o.is_new_52w_high)
        new_lows  = sum(1 for o in observations if o.is_new_52w_low)
        ratio     = new_highs / max(new_lows, 1)

        # Normalise: ratio=1 → 0.5
        normalized = ratio / (1.0 + ratio)
        signal = "bullish" if new_highs > new_lows else (
            "bearish" if new_lows > new_highs else "neutral"
        )

        return BreadthMetricValue(
            metric_name=self.name,
            value=round(ratio, 4),
            normalized_value=round(normalized, 4),
            confidence=min(1.0, (new_highs + new_lows) / max(n * 0.10, 1)),
            signal=signal,
        )
