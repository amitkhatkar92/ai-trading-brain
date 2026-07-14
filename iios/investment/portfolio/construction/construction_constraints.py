"""iios/investment/portfolio/construction/construction_constraints.py

Constraint definitions for the Portfolio Construction Engine.
Constraints are pure data objects describing institutional limits.
The ConstraintEngine evaluates them against a PortfolioBlueprint.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional

from iios.investment.portfolio.construction.construction_types import (
    AssetClass,
    ConstraintSeverity,
    ConstraintType,
    MarketCapCategory,
)


@dataclass(frozen=True)
class ConstraintDefinition:
    """
    Base immutable definition of a single portfolio constraint.

    Subclasses add type-specific parameters.  All constraint instances
    are registered with the ConstraintRegistry and evaluated by
    ConstraintValidator implementations.
    """

    constraint_id:   str               = field(default_factory=lambda: str(uuid.uuid4()))
    name:            str               = ""
    constraint_type: ConstraintType    = ConstraintType.CUSTOM
    severity:        ConstraintSeverity= ConstraintSeverity.HARD
    description:     str               = ""
    enabled:         bool              = True
    tags:            FrozenSet[str]    = field(default_factory=frozenset)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_id":   self.constraint_id,
            "name":            self.name,
            "constraint_type": self.constraint_type.value,
            "severity":        self.severity.value,
            "description":     self.description,
            "enabled":         self.enabled,
            "tags":            sorted(self.tags),
        }


@dataclass(frozen=True)
class MaxHoldingsConstraint(ConstraintDefinition):
    """Portfolio may not exceed max_holdings long + short positions."""

    constraint_type: ConstraintType = ConstraintType.MAX_HOLDINGS
    max_holdings:    int            = 30

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["max_holdings"] = self.max_holdings
        return d


@dataclass(frozen=True)
class MinHoldingsConstraint(ConstraintDefinition):
    """Portfolio must contain at least min_holdings positions."""

    constraint_type: ConstraintType = ConstraintType.MIN_HOLDINGS
    min_holdings:    int            = 5

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["min_holdings"] = self.min_holdings
        return d


@dataclass(frozen=True)
class MaxSingleWeightConstraint(ConstraintDefinition):
    """No single position may exceed max_weight of portfolio value."""

    constraint_type: ConstraintType = ConstraintType.MAX_WEIGHT
    max_weight:      float          = 0.10

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["max_weight"] = self.max_weight
        return d


@dataclass(frozen=True)
class MinSingleWeightConstraint(ConstraintDefinition):
    """No single position may be smaller than min_weight of portfolio value."""

    constraint_type: ConstraintType = ConstraintType.MIN_WEIGHT
    min_weight:      float          = 0.005

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["min_weight"] = self.min_weight
        return d


@dataclass(frozen=True)
class SectorLimitConstraint(ConstraintDefinition):
    """Combined weight of all holdings in a single sector ≤ max_weight."""

    constraint_type: ConstraintType    = ConstraintType.SECTOR_LIMIT
    sector:          str               = ""            # empty = applies to ALL sectors
    max_weight:      float             = 0.30
    excluded_sectors:FrozenSet[str]    = field(default_factory=frozenset)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["sector"]           = self.sector
        d["max_weight"]       = self.max_weight
        d["excluded_sectors"] = sorted(self.excluded_sectors)
        return d


@dataclass(frozen=True)
class IndustryLimitConstraint(ConstraintDefinition):
    """Combined weight of all holdings in a single industry ≤ max_weight."""

    constraint_type: ConstraintType = ConstraintType.INDUSTRY_LIMIT
    industry:        str            = ""
    max_weight:      float          = 0.20

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["industry"]   = self.industry
        d["max_weight"] = self.max_weight
        return d


@dataclass(frozen=True)
class AssetClassLimitConstraint(ConstraintDefinition):
    """Combined weight in a single asset class ≤ max_weight."""

    constraint_type: ConstraintType = ConstraintType.ASSET_CLASS_LIMIT
    asset_class:     AssetClass     = AssetClass.EQUITY
    max_weight:      float          = 0.70

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["asset_class"] = self.asset_class.value
        d["max_weight"]  = self.max_weight
        return d


@dataclass(frozen=True)
class CashReserveConstraint(ConstraintDefinition):
    """Portfolio must maintain at least min_cash_pct in cash / cash equivalents."""

    constraint_type: ConstraintType = ConstraintType.CASH_RESERVE
    min_cash_pct:    float          = 0.02   # 2% minimum cash
    max_cash_pct:    float          = 0.50   # 50% maximum idle cash

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["min_cash_pct"] = self.min_cash_pct
        d["max_cash_pct"] = self.max_cash_pct
        return d


@dataclass(frozen=True)
class MarketCapConstraint(ConstraintDefinition):
    """Only holdings in the specified market cap categories are allowed."""

    constraint_type:       ConstraintType              = ConstraintType.MARKET_CAP
    allowed_market_caps:   FrozenSet[MarketCapCategory]= field(default_factory=frozenset)
    excluded_market_caps:  FrozenSet[MarketCapCategory]= field(default_factory=frozenset)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["allowed_market_caps"]  = sorted(v.value for v in self.allowed_market_caps)
        d["excluded_market_caps"] = sorted(v.value for v in self.excluded_market_caps)
        return d


@dataclass(frozen=True)
class ESGConstraint(ConstraintDefinition):
    """ESG eligibility: symbols in excluded_symbols are prohibited."""

    constraint_type:   ConstraintType = ConstraintType.ESG
    excluded_symbols:  FrozenSet[str] = field(default_factory=frozenset)
    min_esg_score:     float          = 0.0   # 0 = unconstrained
    description:       str            = "ESG institutional mandate"

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["excluded_symbols"] = sorted(self.excluded_symbols)
        d["min_esg_score"]    = self.min_esg_score
        return d


@dataclass(frozen=True)
class LeverageConstraint(ConstraintDefinition):
    """
    Gross exposure (long + |short|) must not exceed max_gross_exposure.
    Net exposure |long - |short|| must not exceed max_net_exposure.
    """

    constraint_type:     ConstraintType = ConstraintType.LEVERAGE
    max_gross_exposure:  float          = 1.0   # 1.0 = no leverage
    max_net_exposure:    float          = 1.0

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["max_gross_exposure"] = self.max_gross_exposure
        d["max_net_exposure"]   = self.max_net_exposure
        return d


@dataclass(frozen=True)
class CustomConstraint(ConstraintDefinition):
    """
    Free-form institutional constraint.  The parameters dict is passed to
    the registered ConstraintChecker at evaluation time.
    """

    constraint_type: ConstraintType    = ConstraintType.CUSTOM
    parameters:      Dict[str, Any]    = field(default_factory=dict)
    checker_class:   str               = ""   # dotted import path

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["parameters"]    = dict(self.parameters)
        d["checker_class"] = self.checker_class
        return d
