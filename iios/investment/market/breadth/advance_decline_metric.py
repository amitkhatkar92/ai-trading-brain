"""iios/investment/market/breadth/advance_decline_metric.py
Advance/Decline ratio and net-change breadth metric.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from iios.investment.market.breadth.models import BreadthMetricValue

if TYPE_CHECKING:
    from iios.investment.market.breadth.models import SecurityObservation


class AdvanceDeclineMetric:
    """Computes A/D ratio and net-change signal."""

    @property
    def name(self) -> str:
        return "advance_decline"

    @property
    def required_observations(self) -> int:
        return 2

    def compute(
        self, observations: "List[SecurityObservation]"
    ) -> Optional[BreadthMetricValue]:
        n = len(observations)
        if n < self.required_observations:
            return None

        advancing = sum(1 for o in observations if o.is_advancing)
        declining = sum(1 for o in observations if o.is_declining)

        ad_ratio = advancing / max(declining, 1)
        # Normalise to 0-1: ratio=1 → 0.5, ratio=2 → 0.67, ratio=0.5 → 0.33
        normalized = ad_ratio / (1.0 + ad_ratio)
        signal = "bullish" if ad_ratio > 1.0 else ("bearish" if ad_ratio < 1.0 else "neutral")

        return BreadthMetricValue(
            metric_name=self.name,
            value=round(ad_ratio, 4),
            normalized_value=round(normalized, 4),
            confidence=min(1.0, n / 50),
            signal=signal,
        )
