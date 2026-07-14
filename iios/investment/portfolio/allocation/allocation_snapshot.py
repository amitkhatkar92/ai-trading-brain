"""iios/investment/portfolio/allocation/allocation_snapshot.py

Point-in-time view of a portfolio's capital allocation state.
Created after each successful allocation run for audit and replay.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from iios.investment.portfolio.allocation.allocation_types import (
    AllocationMethod,
    CapitalDistributionStatus,
)


@dataclass(frozen=True)
class AllocationHolding:
    """A single holding in an AllocationSnapshot."""

    symbol:            str   = ""
    direction:         str   = "long"
    allocated_capital: float = 0.0
    allocated_weight:  float = 0.0
    sector:            str   = "unknown"
    asset_class:       str   = "equity"
    recommendation_id: str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":            self.symbol,
            "direction":         self.direction,
            "allocated_capital": round(self.allocated_capital, 2),
            "allocated_weight":  round(self.allocated_weight, 6),
            "sector":            self.sector,
            "asset_class":       self.asset_class,
            "recommendation_id": self.recommendation_id,
        }


@dataclass(frozen=True)
class AllocationSnapshot:
    """
    Immutable point-in-time record of an allocation run output.
    Stored in AllocationHistory for audit, replay, and comparison.
    """

    snapshot_id:         str                      = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:        str                      = ""
    plan_id:             str                      = ""
    blueprint_id:        str                      = ""
    plan_version:        int                      = 1
    result_id:           str                      = ""

    # Capital summary
    total_capital:       float                    = 0.0
    invested_capital:    float                    = 0.0
    cash_capital:        float                    = 0.0
    utilisation_rate:    float                    = 0.0
    currency:            str                      = "INR"

    # Holdings
    holdings:            Tuple[AllocationHolding, ...] = field(default_factory=tuple)

    # Exposures
    sector_weights:      Dict[str, float]         = field(default_factory=dict)
    asset_class_weights: Dict[str, float]         = field(default_factory=dict)

    # Status
    distribution_status: CapitalDistributionStatus = CapitalDistributionStatus.UNKNOWN
    method:              AllocationMethod          = AllocationMethod.BLUEPRINT_WEIGHT
    quality_score:       float                    = 0.0
    is_valid:            bool                     = False
    is_ready:            bool                     = False

    snapshotted_at:      float                    = field(default_factory=time.time)
    metadata:            Dict[str, Any]           = field(default_factory=dict)

    @property
    def total_holdings(self) -> int:
        return len(self.holdings)

    @property
    def symbols(self) -> Tuple[str, ...]:
        return tuple(h.symbol for h in self.holdings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":       self.snapshot_id,
            "portfolio_id":      self.portfolio_id,
            "plan_id":           self.plan_id,
            "blueprint_id":      self.blueprint_id,
            "plan_version":      self.plan_version,
            "total_capital":     round(self.total_capital, 2),
            "invested_capital":  round(self.invested_capital, 2),
            "cash_capital":      round(self.cash_capital, 2),
            "utilisation_rate":  round(self.utilisation_rate, 4),
            "currency":          self.currency,
            "total_holdings":    self.total_holdings,
            "distribution_status": self.distribution_status.value,
            "method":            self.method.value,
            "quality_score":     round(self.quality_score, 4),
            "is_valid":          self.is_valid,
            "is_ready":          self.is_ready,
            "sector_weights":    {k: round(v, 4) for k, v in self.sector_weights.items()},
            "asset_class_weights":{k: round(v, 4) for k, v in self.asset_class_weights.items()},
            "holdings":          [h.to_dict() for h in self.holdings],
            "snapshotted_at":    self.snapshotted_at,
            "metadata":          dict(self.metadata),
        }
