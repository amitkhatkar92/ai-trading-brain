"""iios/investment/portfolio/allocation/allocation_constraints.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.portfolio_constants import (
    DEFAULT_MAX_ASSET_CLASS_PCT,
    DEFAULT_MAX_SECTOR_PCT,
    DEFAULT_MAX_SINGLE_WEIGHT,
    DEFAULT_MIN_CASH_PCT,
    AssetClass,
)


@dataclass
class AllocationConstraints:
    """
    Target allocation weights and hard limits for a portfolio.

    ``target_allocations``: asset_class.value → target fraction of NAV.
    """

    min_cash_pct:         float             = DEFAULT_MIN_CASH_PCT
    max_single_position:  float             = DEFAULT_MAX_SINGLE_WEIGHT
    max_sector_pct:       float             = DEFAULT_MAX_SECTOR_PCT
    max_asset_class_pct:  float             = DEFAULT_MAX_ASSET_CLASS_PCT
    rebalance_threshold:  float             = 0.05   # 5% deviation triggers rebalance flag
    target_allocations:   dict[str, float]  = field(default_factory=dict)

    def get_target(self, asset_class: AssetClass) -> float:
        return self.target_allocations.get(asset_class.value, 0.0)

    def set_target(self, asset_class: AssetClass, weight: float) -> None:
        self.target_allocations[asset_class.value] = max(0.0, min(1.0, weight))

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_cash_pct":        self.min_cash_pct,
            "max_single_position": self.max_single_position,
            "max_sector_pct":      self.max_sector_pct,
            "max_asset_class_pct": self.max_asset_class_pct,
            "rebalance_threshold": self.rebalance_threshold,
            "target_allocations":  self.target_allocations,
        }
