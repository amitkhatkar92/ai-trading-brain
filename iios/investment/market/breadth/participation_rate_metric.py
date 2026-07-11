"""iios/investment/market/breadth/participation_rate_metric.py
Market participation rate breadth metric.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from iios.investment.market.breadth.models import BreadthMetricValue

if TYPE_CHECKING:
    from iios.investment.market.breadth.models import SecurityObservation


class ParticipationRateMetric:
    """Fraction of securities advancing (0-1)."""

    @property
    def name(self) -> str:
        return "participation_rate"

    @property
    def required_observations(self) -> int:
        return 1

    def compute(
        self, observations: "List[SecurityObservation]"
    ) -> Optional[BreadthMetricValue]:
        n = len(observations)
        if n < self.required_observations:
            return None

        advancing = sum(1 for o in observations if o.is_advancing)
        rate = advancing / n
        signal = "bullish" if rate > 0.55 else ("bearish" if rate < 0.45 else "neutral")

        return BreadthMetricValue(
            metric_name=self.name,
            value=round(rate, 4),
            normalized_value=round(rate, 4),  # already 0-1
            confidence=min(1.0, n / 30),
            signal=signal,
        )
