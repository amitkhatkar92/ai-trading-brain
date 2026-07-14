"""iios/investment/portfolio/construction/portfolio_snapshot.py

Point-in-time view of a constructed portfolio's composition.
Distinct from the core PortfolioSnapshot which tracks operational state.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from iios.investment.portfolio.construction.construction_types import (
    AssetClass,
    ConstructionDirection,
    MarketCapCategory,
)


@dataclass(frozen=True)
class HoldingRecord:
    """A single holding in a PortfolioConstructionSnapshot."""

    symbol:              str                 = ""
    name:                str                 = ""
    direction:           ConstructionDirection = ConstructionDirection.LONG
    target_weight:       float               = 0.0
    sector:              str                 = "unknown"
    asset_class:         AssetClass          = AssetClass.EQUITY
    market_cap_category: MarketCapCategory   = MarketCapCategory.UNKNOWN
    recommendation_id:   str                 = ""
    conviction:          float               = 0.5
    confidence:          float               = 0.5
    risk_score:          float               = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":              self.symbol,
            "name":                self.name,
            "direction":           self.direction.value,
            "target_weight":       round(self.target_weight, 6),
            "sector":              self.sector,
            "asset_class":         self.asset_class.value,
            "market_cap_category": self.market_cap_category.value,
            "recommendation_id":   self.recommendation_id,
            "conviction":          round(self.conviction, 4),
            "confidence":          round(self.confidence, 4),
            "risk_score":          round(self.risk_score, 4),
        }


@dataclass(frozen=True)
class PortfolioConstructionSnapshot:
    """
    Immutable point-in-time view of a portfolio's constructed composition.

    Created after each successful construction run and stored in
    PortfolioConstructionHistory for audit and replay purposes.
    """

    snapshot_id:          str                      = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str                      = ""
    blueprint_id:         str                      = ""
    blueprint_version:    int                      = 1
    result_id:            str                      = ""

    holdings:             Tuple[HoldingRecord, ...]= field(default_factory=tuple)

    # Summary weights
    cash_weight:          float                    = 0.0
    long_count:           int                      = 0
    short_count:          int                      = 0
    long_weight_sum:      float                    = 0.0
    short_weight_sum:     float                    = 0.0
    net_exposure:         float                    = 0.0
    gross_exposure:       float                    = 0.0

    # Composition breakdowns
    sector_weights:       Dict[str, float]         = field(default_factory=dict)
    asset_class_weights:  Dict[str, float]         = field(default_factory=dict)

    # Quality summary
    quality_score:        float                    = 0.0
    is_valid:             bool                     = False
    is_ready:             bool                     = False

    snapshotted_at:       float                    = field(default_factory=time.time)
    metadata:             Dict[str, Any]           = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def total_holdings(self) -> int:
        return len(self.holdings)

    @property
    def symbols(self) -> Tuple[str, ...]:
        return tuple(h.symbol for h in self.holdings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":        self.snapshot_id,
            "portfolio_id":       self.portfolio_id,
            "blueprint_id":       self.blueprint_id,
            "blueprint_version":  self.blueprint_version,
            "result_id":          self.result_id,
            "holdings":           [h.to_dict() for h in self.holdings],
            "cash_weight":        round(self.cash_weight, 6),
            "long_count":         self.long_count,
            "short_count":        self.short_count,
            "long_weight_sum":    round(self.long_weight_sum, 6),
            "short_weight_sum":   round(self.short_weight_sum, 6),
            "net_exposure":       round(self.net_exposure, 6),
            "gross_exposure":     round(self.gross_exposure, 6),
            "sector_weights":     {k: round(v, 6) for k, v in self.sector_weights.items()},
            "asset_class_weights":{k: round(v, 6) for k, v in self.asset_class_weights.items()},
            "quality_score":      round(self.quality_score, 4),
            "is_valid":           self.is_valid,
            "is_ready":           self.is_ready,
            "snapshotted_at":     self.snapshotted_at,
            "metadata":           dict(self.metadata),
        }


def snapshot_from_blueprint(
    blueprint,  # PortfolioBlueprint — no circular import via type annotation
    *,
    result_id: str = "",
    quality_score: float = 0.0,
    is_valid: bool = False,
    is_ready: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> PortfolioConstructionSnapshot:
    """Build a PortfolioConstructionSnapshot from a PortfolioBlueprint."""
    holdings = tuple(
        HoldingRecord(
            symbol=s.symbol,
            name=s.name,
            direction=s.direction,
            target_weight=s.target_weight,
            sector=s.sector,
            asset_class=s.asset_class,
            market_cap_category=s.market_cap_category,
            recommendation_id=s.recommendation_id,
            conviction=s.conviction,
            confidence=s.confidence,
            risk_score=s.risk_score,
        )
        for s in blueprint.slots
    )
    return PortfolioConstructionSnapshot(
        portfolio_id=blueprint.portfolio_id,
        blueprint_id=blueprint.blueprint_id,
        blueprint_version=blueprint.version,
        result_id=result_id,
        holdings=holdings,
        cash_weight=blueprint.cash_weight,
        long_count=blueprint.long_count,
        short_count=blueprint.short_count,
        long_weight_sum=blueprint.long_weight_sum,
        short_weight_sum=blueprint.short_weight_sum,
        net_exposure=blueprint.net_exposure,
        gross_exposure=blueprint.gross_exposure,
        sector_weights=dict(blueprint.sector_weights),
        asset_class_weights=dict(blueprint.asset_class_weights),
        quality_score=quality_score,
        is_valid=is_valid,
        is_ready=is_ready,
        metadata=metadata or {},
    )
