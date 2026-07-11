"""iios/investment/market/breadth/above_ma_metric.py
Percent-of-securities-above-moving-average breadth metric.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from iios.investment.market.breadth.models import BreadthMetricValue

if TYPE_CHECKING:
    from iios.investment.market.breadth.models import SecurityObservation


class AboveMa20Metric:
    """Fraction of securities above their 20-period moving average."""

    @property
    def name(self) -> str:
        return "above_ma20"

    @property
    def required_observations(self) -> int:
        return 1

    def compute(
        self, observations: "List[SecurityObservation]"
    ) -> Optional[BreadthMetricValue]:
        n = len(observations)
        if n < self.required_observations:
            return None
        rate = sum(1 for o in observations if o.is_above_ma20) / n
        signal = "bullish" if rate > 0.60 else ("bearish" if rate < 0.40 else "neutral")
        return BreadthMetricValue(
            metric_name=self.name,
            value=round(rate, 4),
            normalized_value=round(rate, 4),
            confidence=min(1.0, n / 30),
            signal=signal,
        )


class AboveMa50Metric:
    """Fraction of securities above their 50-period moving average."""

    @property
    def name(self) -> str:
        return "above_ma50"

    @property
    def required_observations(self) -> int:
        return 1

    def compute(
        self, observations: "List[SecurityObservation]"
    ) -> Optional[BreadthMetricValue]:
        n = len(observations)
        if n < self.required_observations:
            return None
        rate = sum(1 for o in observations if o.is_above_ma50) / n
        signal = "bullish" if rate > 0.60 else ("bearish" if rate < 0.40 else "neutral")
        return BreadthMetricValue(
            metric_name=self.name,
            value=round(rate, 4),
            normalized_value=round(rate, 4),
            confidence=min(1.0, n / 30),
            signal=signal,
        )
