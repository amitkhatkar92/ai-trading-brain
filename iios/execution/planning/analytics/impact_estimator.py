"""iios/execution/planning/analytics/impact_estimator.py
Market-impact estimation — broker-independent linear model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.planning_constants import DEFAULT_IMPACT_RATE


@dataclass
class ImpactEstimatorConfig:
    impact_rate:         float = DEFAULT_IMPACT_RATE   # fraction of order_value
    participation_rate:  float = 0.10                  # assumed fraction of market volume
    metadata:            dict  = field(default_factory=dict)


class ImpactEstimator:
    """
    Estimates market impact using a simple linear model.

    impact = order_value × impact_rate × sqrt(participation_rate / 0.10)

    The square-root scaling approximates the well-known square-root market
    impact law: impact ∝ sqrt(order_size / avg_daily_volume).
    """

    def __init__(self, config: ImpactEstimatorConfig | None = None) -> None:
        self._cfg = config or ImpactEstimatorConfig()

    def estimate(
        self,
        order_value:        float,
        participation_rate: float | None = None,
    ) -> float:
        """Return estimated market-impact cost in currency units."""
        if order_value <= 0:
            return 0.0
        p = participation_rate if participation_rate is not None else self._cfg.participation_rate
        p = max(1e-6, p)
        import math
        scaling = math.sqrt(p / 0.10)
        return order_value * self._cfg.impact_rate * scaling

    def impact_bps(
        self,
        order_value:        float,
        participation_rate: float | None = None,
    ) -> float:
        """Return impact in basis points."""
        if order_value <= 0:
            return 0.0
        impact = self.estimate(order_value, participation_rate)
        return (impact / order_value) * 10_000

    def to_dict(self) -> dict[str, Any]:
        return {
            "impact_rate":        self._cfg.impact_rate,
            "participation_rate": self._cfg.participation_rate,
        }
