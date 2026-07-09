"""iios/investment/portfolio/core/asset_allocation.py"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.portfolio_constants import AllocationStatus, AssetClass


@dataclass
class AssetAllocation:
    """Target vs actual weight for a single asset class."""

    allocation_id:  str             = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:   str             = ""
    asset_class:    AssetClass      = AssetClass.UNKNOWN
    target_weight:  float           = 0.0    # desired fraction of NAV
    actual_weight:  float           = 0.0    # current fraction of NAV
    deviation:      float           = 0.0    # actual − target
    market_value:   float           = 0.0
    position_count: int             = 0
    status:         AllocationStatus = AllocationStatus.UNKNOWN
    metadata:       dict[str, Any]  = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.deviation = self.actual_weight - self.target_weight
        self._refresh_status()

    def update(self, actual_weight: float, market_value: float = 0.0) -> None:
        self.actual_weight = actual_weight
        self.market_value  = market_value
        self.deviation     = actual_weight - self.target_weight
        self._refresh_status()

    def _refresh_status(self) -> None:
        if self.actual_weight <= 0 and self.target_weight <= 0:
            self.status = AllocationStatus.WITHIN_LIMITS
        elif self.deviation > 0.05:
            self.status = AllocationStatus.OVERALLOCATED
        elif self.deviation < -0.05:
            self.status = AllocationStatus.UNDERALLOCATED
        else:
            self.status = AllocationStatus.WITHIN_LIMITS

    def to_dict(self) -> dict[str, Any]:
        return {
            "allocation_id":  self.allocation_id,
            "portfolio_id":   self.portfolio_id,
            "asset_class":    self.asset_class.value,
            "target_weight":  self.target_weight,
            "actual_weight":  self.actual_weight,
            "deviation":      self.deviation,
            "market_value":   self.market_value,
            "position_count": self.position_count,
            "status":         self.status.value,
            "metadata":       self.metadata,
        }
