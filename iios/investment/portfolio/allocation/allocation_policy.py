"""iios/investment/portfolio/allocation/allocation_policy.py

Allocation policy objects — govern HOW capital is distributed.
Policies are pure data; they do not perform allocation themselves.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional

from iios.investment.portfolio.allocation.allocation_types import (
    AllocationMethod,
    DEFAULT_CASH_RESERVE_PCT,
    DEFAULT_MAX_POSITION_WEIGHT,
    DEFAULT_MIN_POSITION_WEIGHT,
)


@dataclass(frozen=True)
class CashPolicy:
    """Policy governing cash allocation and reserve management."""

    policy_name:          str   = "default_cash"
    min_cash_reserve_pct: float = DEFAULT_CASH_RESERVE_PCT   # Minimum cash as fraction
    max_cash_pct:         float = 0.30                        # Maximum cash holding
    sweep_threshold_pct:  float = 0.02   # Cash excess above this triggers a sweep note

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":          self.policy_name,
            "min_cash_reserve_pct": self.min_cash_reserve_pct,
            "max_cash_pct":         self.max_cash_pct,
            "sweep_threshold_pct":  self.sweep_threshold_pct,
        }


@dataclass(frozen=True)
class PositionSizingPolicy:
    """Policy governing individual position sizes."""

    policy_name:         str   = "default_sizing"
    max_position_weight: float = DEFAULT_MAX_POSITION_WEIGHT
    min_position_weight: float = DEFAULT_MIN_POSITION_WEIGHT
    min_trade_size:      float = 100.0    # Minimum dollar amount per position
    max_position_dollars:float = 0.0      # 0 = no absolute cap
    round_to_lot:        bool  = False    # Round positions to lot size
    lot_size:            int   = 1        # Shares per lot

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":          self.policy_name,
            "max_position_weight":  self.max_position_weight,
            "min_position_weight":  self.min_position_weight,
            "min_trade_size":       self.min_trade_size,
            "max_position_dollars": self.max_position_dollars,
            "round_to_lot":         self.round_to_lot,
            "lot_size":             self.lot_size,
        }


@dataclass(frozen=True)
class ExposurePolicy:
    """Policy governing sector, industry, and asset-class exposure."""

    policy_name:          str   = "default_exposure"
    max_sector_weight:    float = 0.40
    max_industry_weight:  float = 0.25
    max_asset_class_weight:float= 0.80
    max_single_name_weight:float= DEFAULT_MAX_POSITION_WEIGHT
    excluded_sectors:     FrozenSet[str] = field(default_factory=frozenset)
    excluded_industries:  FrozenSet[str] = field(default_factory=frozenset)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":            self.policy_name,
            "max_sector_weight":      self.max_sector_weight,
            "max_industry_weight":    self.max_industry_weight,
            "max_asset_class_weight": self.max_asset_class_weight,
            "max_single_name_weight": self.max_single_name_weight,
            "excluded_sectors":       sorted(self.excluded_sectors),
            "excluded_industries":    sorted(self.excluded_industries),
        }


@dataclass(frozen=True)
class AllocationPolicy:
    """
    Master policy object passed to AllocationEngine.
    Combines cash, position-sizing, and exposure policies.
    """

    policy_id:    str                 = field(default_factory=lambda: str(uuid.uuid4()))
    policy_name:  str                 = "default"
    method:       AllocationMethod    = AllocationMethod.BLUEPRINT_WEIGHT
    currency:     str                 = "INR"

    cash:         CashPolicy          = field(default_factory=CashPolicy)
    sizing:       PositionSizingPolicy= field(default_factory=PositionSizingPolicy)
    exposure:     ExposurePolicy      = field(default_factory=ExposurePolicy)

    allow_short:  bool                = False
    description:  str                 = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":    self.policy_id,
            "policy_name":  self.policy_name,
            "method":       self.method.value,
            "currency":     self.currency,
            "cash":         self.cash.to_dict(),
            "sizing":       self.sizing.to_dict(),
            "exposure":     self.exposure.to_dict(),
            "allow_short":  self.allow_short,
            "description":  self.description,
        }


# ---------------------------------------------------------------------------
# Built-in policies
# ---------------------------------------------------------------------------

CONSERVATIVE_POLICY = AllocationPolicy(
    policy_name = "conservative",
    method      = AllocationMethod.BLUEPRINT_WEIGHT,
    cash        = CashPolicy(min_cash_reserve_pct=0.10, max_cash_pct=0.30),
    sizing      = PositionSizingPolicy(max_position_weight=0.10, min_position_weight=0.005),
    exposure    = ExposurePolicy(max_sector_weight=0.30, max_asset_class_weight=0.60),
    description = "Conservative: high cash reserve, tight position limits",
)

BALANCED_POLICY = AllocationPolicy(
    policy_name = "balanced",
    method      = AllocationMethod.BLUEPRINT_WEIGHT,
    cash        = CashPolicy(min_cash_reserve_pct=0.05, max_cash_pct=0.20),
    sizing      = PositionSizingPolicy(max_position_weight=0.15, min_position_weight=0.005),
    exposure    = ExposurePolicy(max_sector_weight=0.40, max_asset_class_weight=0.80),
    description = "Balanced: moderate cash reserve and position limits",
)

AGGRESSIVE_POLICY = AllocationPolicy(
    policy_name = "aggressive",
    method      = AllocationMethod.BLUEPRINT_WEIGHT,
    cash        = CashPolicy(min_cash_reserve_pct=0.02, max_cash_pct=0.10),
    sizing      = PositionSizingPolicy(max_position_weight=0.25, min_position_weight=0.005),
    exposure    = ExposurePolicy(max_sector_weight=0.50, max_asset_class_weight=0.90),
    description = "Aggressive: low cash reserve, higher concentration allowed",
)
