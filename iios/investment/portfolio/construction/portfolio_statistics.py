"""iios/investment/portfolio/construction/portfolio_statistics.py

Composition statistics for a constructed portfolio.
Derived purely from a PortfolioBlueprint — no market data required.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class ConcentrationMetrics:
    """Concentration / diversification metrics for a portfolio."""

    herfindahl_index:      float = 0.0   # HHI of position weights [0, 1]
    effective_n:           float = 0.0   # 1 / HHI — effective number of positions
    top1_weight:           float = 0.0   # Weight of largest holding
    top3_weight:           float = 0.0   # Combined weight of top 3
    top5_weight:           float = 0.0   # Combined weight of top 5
    top10_weight:          float = 0.0   # Combined weight of top 10
    max_sector_weight:     float = 0.0
    max_asset_class_weight:float = 0.0
    gini_coefficient:      float = 0.0   # Weight inequality [0, 1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "herfindahl_index":       round(self.herfindahl_index, 6),
            "effective_n":            round(self.effective_n, 2),
            "top1_weight":            round(self.top1_weight, 4),
            "top3_weight":            round(self.top3_weight, 4),
            "top5_weight":            round(self.top5_weight, 4),
            "top10_weight":           round(self.top10_weight, 4),
            "max_sector_weight":      round(self.max_sector_weight, 4),
            "max_asset_class_weight": round(self.max_asset_class_weight, 4),
            "gini_coefficient":       round(self.gini_coefficient, 4),
        }


@dataclass(frozen=True)
class QualityMetrics:
    """Aggregated quality metrics across all recommendations in the blueprint."""

    avg_conviction:    float = 0.0
    avg_confidence:    float = 0.0
    avg_risk_score:    float = 0.0
    avg_quality_score: float = 0.0   # avg confidence * (1 - risk_score)
    min_conviction:    float = 0.0
    min_confidence:    float = 0.0
    max_risk_score:    float = 0.0
    long_bias:         float = 0.0   # net_exposure (long_weight_sum - short_weight_sum)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_conviction":    round(self.avg_conviction, 4),
            "avg_confidence":    round(self.avg_confidence, 4),
            "avg_risk_score":    round(self.avg_risk_score, 4),
            "avg_quality_score": round(self.avg_quality_score, 4),
            "min_conviction":    round(self.min_conviction, 4),
            "min_confidence":    round(self.min_confidence, 4),
            "max_risk_score":    round(self.max_risk_score, 4),
            "long_bias":         round(self.long_bias, 4),
        }


@dataclass(frozen=True)
class PortfolioCompositionStats:
    """
    Complete composition statistics for one PortfolioBlueprint.

    Computed by compute_statistics() — purely arithmetic, no market data.
    """

    portfolio_id:        str                = ""
    blueprint_id:        str                = ""
    blueprint_version:   int                = 1

    # Holdings counts
    total_holdings:      int                = 0
    long_holdings:       int                = 0
    short_holdings:      int                = 0
    unique_sectors:      int                = 0
    unique_industries:   int                = 0
    unique_asset_classes:int                = 0

    # Weight summary
    long_weight_sum:     float              = 0.0
    short_weight_sum:    float              = 0.0
    cash_weight:         float              = 0.0
    net_exposure:        float              = 0.0
    gross_exposure:      float              = 0.0

    # Breakdowns
    sector_weights:      Dict[str, float]   = field(default_factory=dict)
    industry_weights:    Dict[str, float]   = field(default_factory=dict)
    asset_class_weights: Dict[str, float]   = field(default_factory=dict)
    market_cap_weights:  Dict[str, float]   = field(default_factory=dict)

    # Concentration
    concentration:       ConcentrationMetrics = field(default_factory=ConcentrationMetrics)

    # Recommendation quality
    quality:             QualityMetrics       = field(default_factory=QualityMetrics)

    computed_at:         float               = field(default_factory=__import__("time").time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id":        self.portfolio_id,
            "blueprint_id":        self.blueprint_id,
            "blueprint_version":   self.blueprint_version,
            "total_holdings":      self.total_holdings,
            "long_holdings":       self.long_holdings,
            "short_holdings":      self.short_holdings,
            "unique_sectors":      self.unique_sectors,
            "unique_industries":   self.unique_industries,
            "unique_asset_classes":self.unique_asset_classes,
            "long_weight_sum":     round(self.long_weight_sum, 6),
            "short_weight_sum":    round(self.short_weight_sum, 6),
            "cash_weight":         round(self.cash_weight, 6),
            "net_exposure":        round(self.net_exposure, 6),
            "gross_exposure":      round(self.gross_exposure, 6),
            "sector_weights":      {k: round(v, 4) for k, v in self.sector_weights.items()},
            "industry_weights":    {k: round(v, 4) for k, v in self.industry_weights.items()},
            "asset_class_weights": {k: round(v, 4) for k, v in self.asset_class_weights.items()},
            "market_cap_weights":  {k: round(v, 4) for k, v in self.market_cap_weights.items()},
            "concentration":       self.concentration.to_dict(),
            "quality":             self.quality.to_dict(),
            "computed_at":         self.computed_at,
        }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _gini(weights: List[float]) -> float:
    """Gini coefficient of a list of positive weights."""
    if len(weights) < 2:
        return 0.0
    n = len(weights)
    s = sorted(weights)
    total = sum(s) or 1.0
    cum = sum((2 * i - n - 1) * w for i, w in enumerate(s, 1))
    return abs(cum) / (n * total)


def _herfindahl(weights: List[float]) -> float:
    total = sum(weights) or 1.0
    return sum((w / total) ** 2 for w in weights)


def _top_n_weight(sorted_desc: List[float], n: int) -> float:
    return sum(sorted_desc[:n])


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def compute_statistics(blueprint) -> PortfolioCompositionStats:  # type: ignore[return]
    """
    Compute PortfolioCompositionStats from any PortfolioBlueprint.

    Parameters
    ----------
    blueprint : PortfolioBlueprint
        The fully-built blueprint to analyse.

    Returns
    -------
    PortfolioCompositionStats
    """
    slots = blueprint.slots

    if not slots:
        return PortfolioCompositionStats(
            portfolio_id=blueprint.portfolio_id,
            blueprint_id=blueprint.blueprint_id,
            blueprint_version=blueprint.version,
        )

    long_slots  = [s for s in slots if s.is_long]
    short_slots = [s for s in slots if s.is_short]

    long_weights  = [s.target_weight for s in long_slots]
    short_weights = [abs(s.target_weight) for s in short_slots]
    all_abs_weights = [abs(s.target_weight) for s in slots]

    # Concentration
    sorted_desc = sorted(all_abs_weights, reverse=True)
    hhi  = _herfindahl(all_abs_weights)
    eff_n= 1.0 / hhi if hhi > 0 else 0.0
    gini = _gini(all_abs_weights)

    concentration = ConcentrationMetrics(
        herfindahl_index=hhi,
        effective_n=eff_n,
        top1_weight=_top_n_weight(sorted_desc, 1),
        top3_weight=_top_n_weight(sorted_desc, 3),
        top5_weight=_top_n_weight(sorted_desc, 5),
        top10_weight=_top_n_weight(sorted_desc, 10),
        max_sector_weight=max(blueprint.sector_weights.values(), default=0.0),
        max_asset_class_weight=max(blueprint.asset_class_weights.values(), default=0.0),
        gini_coefficient=gini,
    )

    # Quality
    n = len(slots)
    quality = QualityMetrics(
        avg_conviction=sum(s.conviction for s in slots) / n,
        avg_confidence=sum(s.confidence for s in slots) / n,
        avg_risk_score=sum(s.risk_score for s in slots) / n,
        avg_quality_score=sum(s.confidence * (1 - s.risk_score) for s in slots) / n,
        min_conviction=min(s.conviction for s in slots),
        min_confidence=min(s.confidence for s in slots),
        max_risk_score=max(s.risk_score for s in slots),
        long_bias=blueprint.net_exposure,
    )

    import time as _time
    return PortfolioCompositionStats(
        portfolio_id=blueprint.portfolio_id,
        blueprint_id=blueprint.blueprint_id,
        blueprint_version=blueprint.version,
        total_holdings=len(slots),
        long_holdings=len(long_slots),
        short_holdings=len(short_slots),
        unique_sectors=len(set(s.sector for s in slots)),
        unique_industries=len(set(s.industry for s in slots)),
        unique_asset_classes=len(set(s.asset_class for s in slots)),
        long_weight_sum=blueprint.long_weight_sum,
        short_weight_sum=blueprint.short_weight_sum,
        cash_weight=blueprint.cash_weight,
        net_exposure=blueprint.net_exposure,
        gross_exposure=blueprint.gross_exposure,
        sector_weights=dict(blueprint.sector_weights),
        industry_weights=dict(blueprint.industry_weights),
        asset_class_weights=dict(blueprint.asset_class_weights),
        market_cap_weights=dict(blueprint.market_cap_weights),
        concentration=concentration,
        quality=quality,
        computed_at=_time.time(),
    )
