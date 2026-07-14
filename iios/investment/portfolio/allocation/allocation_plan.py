"""iios/investment/portfolio/allocation/allocation_plan.py

Core data models for the Portfolio Allocation Engine.

PositionAllocation  — allocated capital for one holding.
AllocationRequest   — parameters driving a single allocation run.
AllocationPlan      — immutable, version-stamped allocation output.
AllocationResult    — full output of one PortfolioAllocationEngine.allocate() call.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional, Tuple

from iios.investment.portfolio.allocation.allocation_types import (
    ALLOCATION_PLAN_SCHEMA_VERSION,
    ALLOCATION_RESULT_SCHEMA_VERSION,
    AllocationDirection,
    AllocationMethod,
    AllocationRunStatus,
    CapitalDistributionStatus,
)


# ---------------------------------------------------------------------------
# PositionAllocation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PositionAllocation:
    """
    Dollar-amount allocation for a single portfolio holding.

    Derived from blueprint target_weight × total_capital (subject to limits).
    The allocation engine NEVER modifies weights; it converts them to amounts.
    """

    symbol:                str               = ""
    name:                  str               = ""
    direction:             AllocationDirection = AllocationDirection.LONG

    # Weights
    blueprint_weight:      float             = 0.0   # Weight from blueprint
    allocated_weight:      float             = 0.0   # Actual weight after limit enforcement
    weight_delta:          float             = 0.0   # allocated_weight - blueprint_weight

    # Dollar amounts (currency determined by AllocationRequest)
    allocated_capital:     float             = 0.0   # Dollars to deploy in this position
    min_capital:           float             = 0.0   # Hard lower bound
    max_capital:           float             = 0.0   # Hard upper bound

    # Classification (copied from blueprint slot)
    sector:                str               = "unknown"
    industry:              str               = "unknown"
    asset_class:           str               = "equity"
    market_cap_category:   str               = "unknown"

    # Traceability
    blueprint_slot_id:     str               = ""
    recommendation_id:     str               = ""
    source_decision_id:    str               = ""
    rationale:             str               = ""

    # Quality (copied from blueprint slot)
    conviction:            float             = 0.5
    confidence:            float             = 0.5
    risk_score:            float             = 0.5

    # Rank in blueprint
    rank:                  int               = 0

    allocated_at:          float             = field(default_factory=time.time)

    # ------------------------------------------------------------------

    @property
    def is_long(self) -> bool:
        return self.direction == AllocationDirection.LONG

    @property
    def is_short(self) -> bool:
        return self.direction == AllocationDirection.SHORT

    @property
    def abs_capital(self) -> float:
        return abs(self.allocated_capital)

    @property
    def within_limits(self) -> bool:
        return self.min_capital <= self.abs_capital <= self.max_capital

    @property
    def quality_score(self) -> float:
        return self.confidence * (1.0 - self.risk_score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":              self.symbol,
            "name":                self.name,
            "direction":           self.direction.value,
            "blueprint_weight":    round(self.blueprint_weight, 6),
            "allocated_weight":    round(self.allocated_weight, 6),
            "weight_delta":        round(self.weight_delta, 6),
            "allocated_capital":   round(self.allocated_capital, 2),
            "min_capital":         round(self.min_capital, 2),
            "max_capital":         round(self.max_capital, 2),
            "sector":              self.sector,
            "industry":            self.industry,
            "asset_class":         self.asset_class,
            "market_cap_category": self.market_cap_category,
            "blueprint_slot_id":   self.blueprint_slot_id,
            "recommendation_id":   self.recommendation_id,
            "source_decision_id":  self.source_decision_id,
            "conviction":          round(self.conviction, 4),
            "confidence":          round(self.confidence, 4),
            "risk_score":          round(self.risk_score, 4),
            "rank":                self.rank,
            "allocated_at":        self.allocated_at,
        }


# ---------------------------------------------------------------------------
# CashAllocation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CashAllocation:
    """The residual cash position in an AllocationPlan."""

    cash_capital:       float = 0.0      # Dollar amount held as cash
    cash_weight:        float = 0.0      # Fraction of total_capital
    reserve_capital:    float = 0.0      # Required cash reserve
    reserve_weight:     float = 0.0      # Reserve as fraction
    free_cash:          float = 0.0      # cash_capital - reserve_capital
    currency:           str   = "INR"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cash_capital":    round(self.cash_capital, 2),
            "cash_weight":     round(self.cash_weight, 6),
            "reserve_capital": round(self.reserve_capital, 2),
            "reserve_weight":  round(self.reserve_weight, 6),
            "free_cash":       round(self.free_cash, 2),
            "currency":        self.currency,
        }


# ---------------------------------------------------------------------------
# AllocationRequest
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AllocationRequest:
    """
    Parameters controlling a single portfolio allocation run.

    Passed to PortfolioAllocationEngine.allocate().
    """

    request_id:          str               = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:        str               = ""
    blueprint_id:        str               = ""

    # Capital
    total_capital:       float             = 0.0        # Total investable capital (dollars)
    currency:            str               = "INR"
    cash_reserve_pct:    float             = 0.05       # Minimum cash reserve

    # Allocation method
    method:              AllocationMethod  = AllocationMethod.BLUEPRINT_WEIGHT

    # Position limits (fraction of total_capital)
    max_position_weight: float             = 0.15       # 15% per position
    min_position_weight: float             = 0.005      # 0.5% per position

    # Dollar limits
    min_trade_size:      float             = 100.0      # Minimum tradeable dollar amount
    max_position_dollars:float             = 0.0        # 0 = no absolute cap

    # Exposure limits
    max_sector_weight:   float             = 0.40
    max_industry_weight: float             = 0.25
    max_asset_class_weight: float          = 0.80

    # Multi-account / multi-currency
    account_id:          str               = ""
    custodian:           str               = ""
    broker:              str               = ""

    # Universe override (empty = use all blueprint slots)
    symbols_allowed:     FrozenSet[str]    = field(default_factory=frozenset)
    symbols_excluded:    FrozenSet[str]    = field(default_factory=frozenset)

    # Allow short positions
    allow_short:         bool              = False

    # Provenance
    requested_by:        str               = "system"
    requested_at:        float             = field(default_factory=time.time)
    metadata:            Dict[str, Any]    = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":            self.request_id,
            "portfolio_id":          self.portfolio_id,
            "blueprint_id":          self.blueprint_id,
            "total_capital":         self.total_capital,
            "currency":              self.currency,
            "cash_reserve_pct":      self.cash_reserve_pct,
            "method":                self.method.value,
            "max_position_weight":   self.max_position_weight,
            "min_position_weight":   self.min_position_weight,
            "min_trade_size":        self.min_trade_size,
            "max_position_dollars":  self.max_position_dollars,
            "max_sector_weight":     self.max_sector_weight,
            "max_industry_weight":   self.max_industry_weight,
            "max_asset_class_weight":self.max_asset_class_weight,
            "account_id":            self.account_id,
            "custodian":             self.custodian,
            "broker":                self.broker,
            "symbols_allowed":       sorted(self.symbols_allowed),
            "symbols_excluded":      sorted(self.symbols_excluded),
            "allow_short":           self.allow_short,
            "requested_by":          self.requested_by,
            "requested_at":          self.requested_at,
            "metadata":              dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# AllocationPlan
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AllocationPlan:
    """
    Immutable, version-stamped plan mapping each holding to allocated capital.

    Produced by the PositionAllocator and consumed by:
      • AllocationValidator (validates integrity)
      • Downstream execution layer (sizes actual orders)

    Every plan is deterministic: given the same blueprint, same total_capital,
    and same AllocationRequest, the same plan must always be produced.
    """

    plan_id:             str               = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:        str               = ""
    blueprint_id:        str               = ""
    blueprint_version:   int               = 1
    request_id:          str               = ""
    version:             int               = 1
    schema_version:      str               = ALLOCATION_PLAN_SCHEMA_VERSION

    # Method used
    method:              AllocationMethod  = AllocationMethod.BLUEPRINT_WEIGHT
    currency:            str               = "INR"

    # Capital summary
    total_capital:       float             = 0.0
    invested_capital:    float             = 0.0   # sum of long allocations
    short_capital:       float             = 0.0   # sum of abs(short allocations)
    net_invested:        float             = 0.0   # invested - short
    cash_capital:        float             = 0.0   # total_capital - invested_capital
    utilisation_rate:    float             = 0.0   # invested_capital / total_capital

    # Position allocations
    allocations:         Tuple[PositionAllocation, ...] = field(default_factory=tuple)
    cash:                CashAllocation    = field(default_factory=CashAllocation)

    # Exposure summaries
    sector_exposure:     Dict[str, float]  = field(default_factory=dict)   # sector → dollars
    asset_class_exposure:Dict[str, float]  = field(default_factory=dict)
    industry_exposure:   Dict[str, float]  = field(default_factory=dict)

    # Capital distribution status
    distribution_status: CapitalDistributionStatus = CapitalDistributionStatus.UNKNOWN

    # Traceability
    blueprint_request_id:str               = ""

    # Provenance
    created_at:          float             = field(default_factory=time.time)
    created_by:          str               = "PortfolioAllocationEngine"
    allocation_version:  str               = "1.0.0"
    metadata:            Dict[str, Any]    = field(default_factory=dict)

    # ------------------------------------------------------------------

    @property
    def total_positions(self) -> int:
        return len(self.allocations)

    @property
    def long_count(self) -> int:
        return sum(1 for a in self.allocations if a.is_long)

    @property
    def short_count(self) -> int:
        return sum(1 for a in self.allocations if a.is_short)

    @property
    def is_empty(self) -> bool:
        return len(self.allocations) == 0

    @property
    def symbols(self) -> Tuple[str, ...]:
        return tuple(a.symbol for a in self.allocations)

    def get_allocation(self, symbol: str) -> Optional[PositionAllocation]:
        for a in self.allocations:
            if a.symbol == symbol:
                return a
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id":              self.plan_id,
            "portfolio_id":         self.portfolio_id,
            "blueprint_id":         self.blueprint_id,
            "blueprint_version":    self.blueprint_version,
            "request_id":           self.request_id,
            "version":              self.version,
            "schema_version":       self.schema_version,
            "method":               self.method.value,
            "currency":             self.currency,
            "total_capital":        round(self.total_capital, 2),
            "invested_capital":     round(self.invested_capital, 2),
            "short_capital":        round(self.short_capital, 2),
            "net_invested":         round(self.net_invested, 2),
            "cash_capital":         round(self.cash_capital, 2),
            "utilisation_rate":     round(self.utilisation_rate, 4),
            "total_positions":      self.total_positions,
            "long_count":           self.long_count,
            "short_count":          self.short_count,
            "distribution_status":  self.distribution_status.value,
            "sector_exposure":      {k: round(v, 2) for k, v in self.sector_exposure.items()},
            "asset_class_exposure": {k: round(v, 2) for k, v in self.asset_class_exposure.items()},
            "industry_exposure":    {k: round(v, 2) for k, v in self.industry_exposure.items()},
            "cash":                 self.cash.to_dict(),
            "allocations":          [a.to_dict() for a in self.allocations],
            "created_at":           self.created_at,
            "created_by":           self.created_by,
            "metadata":             dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# AllocationResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AllocationResult:
    """Full output of PortfolioAllocationEngine.allocate()."""

    result_id:             str                   = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:            str                   = ""
    portfolio_id:          str                   = ""
    status:                AllocationRunStatus   = AllocationRunStatus.PENDING
    schema_version:        str                   = ALLOCATION_RESULT_SCHEMA_VERSION

    # Plan is present on success, None on failure
    plan:                  Optional[AllocationPlan] = None

    # Run counts
    positions_in:          int                   = 0
    positions_allocated:   int                   = 0

    # Quality / validation summaries
    validation_summary:    Dict[str, Any]        = field(default_factory=dict)
    quality_summary:       Dict[str, Any]        = field(default_factory=dict)
    exposure_summary:      Dict[str, Any]        = field(default_factory=dict)

    warnings:              Tuple[str, ...]       = field(default_factory=tuple)
    errors:                Tuple[str, ...]       = field(default_factory=tuple)

    duration_ms:           float                 = 0.0
    created_at:            float                 = field(default_factory=time.time)
    allocation_version:    str                   = "1.0.0"
    metadata:              Dict[str, Any]        = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status == AllocationRunStatus.COMPLETED

    @property
    def failed(self) -> bool:
        return self.status == AllocationRunStatus.FAILED

    @property
    def has_plan(self) -> bool:
        return self.plan is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":           self.result_id,
            "request_id":          self.request_id,
            "portfolio_id":        self.portfolio_id,
            "status":              self.status.value,
            "schema_version":      self.schema_version,
            "plan":                self.plan.to_dict() if self.plan else None,
            "positions_in":        self.positions_in,
            "positions_allocated": self.positions_allocated,
            "validation_summary":  dict(self.validation_summary),
            "quality_summary":     dict(self.quality_summary),
            "exposure_summary":    dict(self.exposure_summary),
            "warnings":            list(self.warnings),
            "errors":              list(self.errors),
            "duration_ms":         round(self.duration_ms, 2),
            "created_at":          self.created_at,
            "allocation_version":  self.allocation_version,
            "metadata":            dict(self.metadata),
        }
