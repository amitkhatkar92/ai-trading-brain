"""iios/execution/planning/analytics/slippage_estimator.py"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.planning_constants import DEFAULT_SLIPPAGE_RATE


@dataclass
class SlippageEstimatorConfig:
    base_slippage_rate: float = DEFAULT_SLIPPAGE_RATE  # 5 bps baseline
    adv_sensitivity:    float = 1.5    # exponent on participation rate
    min_slippage_rate:  float = 0.0001 # 1 bp floor
    max_slippage_rate:  float = 0.05   # 5% cap
    metadata:           dict  = field(default_factory=dict)


class SlippageEstimator:
    """Estimates expected slippage as a fraction of order value.

    Formula:
        participation_rate = order_quantity / average_daily_volume
        slippage_factor    = base_rate * (1 + participation_rate ^ sensitivity)
        slippage_value     = order_value * slippage_factor

    When no volume data is available, returns base slippage.
    """

    def __init__(self, config: SlippageEstimatorConfig | None = None) -> None:
        self._cfg = config or SlippageEstimatorConfig()

    def estimate_slippage_rate(
        self,
        order_quantity:       float,
        average_daily_volume: float = 0.0,
    ) -> float:
        """Returns slippage as a fraction (0–1)."""
        base = self._cfg.base_slippage_rate
        if average_daily_volume > 0 and order_quantity > 0:
            participation_rate = order_quantity / average_daily_volume
            multiplier         = 1.0 + math.pow(participation_rate, self._cfg.adv_sensitivity)
            slippage           = base * multiplier
        else:
            slippage = base
        return max(
            self._cfg.min_slippage_rate,
            min(slippage, self._cfg.max_slippage_rate),
        )

    def estimate(
        self,
        order_value:          float,
        order_quantity:       float = 0.0,
        average_daily_volume: float = 0.0,
    ) -> float:
        """Returns estimated slippage in currency units."""
        rate = self.estimate_slippage_rate(order_quantity, average_daily_volume)
        return order_value * rate

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_slippage_rate": self._cfg.base_slippage_rate,
            "adv_sensitivity":    self._cfg.adv_sensitivity,
            "min_slippage_rate":  self._cfg.min_slippage_rate,
            "max_slippage_rate":  self._cfg.max_slippage_rate,
        }
