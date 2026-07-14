"""iios/investment/portfolio/allocation/allocation_metrics.py

Detailed aggregate metrics derived from a completed AllocationPlan.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from iios.investment.portfolio.allocation.allocation_plan import AllocationPlan


@dataclass(frozen=True)
class AllocationMetrics:
    """
    Aggregate metrics for a completed AllocationPlan.
    All amounts in the plan's currency; weights as fractions.
    """

    metrics_id:             str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:           str   = ""
    plan_id:                str   = ""

    # Capital breakdown
    total_capital:          float = 0.0
    invested_capital:       float = 0.0
    short_capital:          float = 0.0
    cash_capital:           float = 0.0
    capital_utilisation_pct:float = 0.0
    long_pct:               float = 0.0
    short_pct:              float = 0.0
    cash_pct:               float = 0.0
    net_exposure_pct:       float = 0.0
    gross_exposure_pct:     float = 0.0

    # Position statistics
    long_count:             int   = 0
    short_count:            int   = 0
    total_count:            int   = 0
    avg_position_dollars:   float = 0.0
    median_position_dollars:float = 0.0
    max_position_dollars:   float = 0.0
    min_position_dollars:   float = 0.0
    std_position_dollars:   float = 0.0

    # Concentration (Herfindahl-Hirschman Index, computed on absolute weights)
    hhi:                    float = 0.0   # 0 = perfectly diversified, 1 = fully concentrated
    effective_n:            float = 0.0   # 1/HHI effective number of positions

    # Diversity
    sector_count:           int   = 0
    industry_count:         int   = 0
    asset_class_count:      int   = 0

    # Quality (average across positions)
    avg_conviction:         float = 0.0
    avg_confidence:         float = 0.0
    avg_risk_score:         float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics_id":              self.metrics_id,
            "portfolio_id":            self.portfolio_id,
            "plan_id":                 self.plan_id,
            "total_capital":           round(self.total_capital, 2),
            "invested_capital":        round(self.invested_capital, 2),
            "short_capital":           round(self.short_capital, 2),
            "cash_capital":            round(self.cash_capital, 2),
            "capital_utilisation_pct": round(self.capital_utilisation_pct, 4),
            "long_pct":                round(self.long_pct, 4),
            "short_pct":               round(self.short_pct, 4),
            "cash_pct":                round(self.cash_pct, 4),
            "net_exposure_pct":        round(self.net_exposure_pct, 4),
            "gross_exposure_pct":      round(self.gross_exposure_pct, 4),
            "long_count":              self.long_count,
            "short_count":             self.short_count,
            "total_count":             self.total_count,
            "avg_position_dollars":    round(self.avg_position_dollars, 2),
            "median_position_dollars": round(self.median_position_dollars, 2),
            "max_position_dollars":    round(self.max_position_dollars, 2),
            "min_position_dollars":    round(self.min_position_dollars, 2),
            "std_position_dollars":    round(self.std_position_dollars, 2),
            "hhi":                     round(self.hhi, 6),
            "effective_n":             round(self.effective_n, 2),
            "sector_count":            self.sector_count,
            "industry_count":          self.industry_count,
            "asset_class_count":       self.asset_class_count,
            "avg_conviction":          round(self.avg_conviction, 4),
            "avg_confidence":          round(self.avg_confidence, 4),
            "avg_risk_score":          round(self.avg_risk_score, 4),
        }


def compute_allocation_metrics(plan: AllocationPlan) -> AllocationMetrics:
    """Compute AllocationMetrics from a finished AllocationPlan."""
    import math
    import statistics

    allocs  = list(plan.allocations)
    n       = len(allocs)
    total   = plan.total_capital

    longs   = [a for a in allocs if a.is_long]
    shorts  = [a for a in allocs if a.is_short]

    invested  = sum(a.abs_capital for a in longs)
    short_cap = sum(a.abs_capital for a in shorts)
    cash_cap  = plan.cash_capital
    utilisation = invested / total if total > 0 else 0.0
    long_pct    = invested / total if total > 0 else 0.0
    short_pct   = short_cap / total if total > 0 else 0.0
    cash_pct    = cash_cap / total if total > 0 else 0.0

    if n > 0:
        amounts = [a.abs_capital for a in allocs]
        avg_pos = sum(amounts) / n
        med_pos = statistics.median(amounts)
        max_pos = max(amounts)
        min_pos = min(amounts)
        std_pos = statistics.stdev(amounts) if n > 1 else 0.0

        # HHI on weight fractions
        weights = [a.abs_capital / total for a in allocs if total > 0]
        hhi     = sum(w * w for w in weights)
        eff_n   = 1.0 / hhi if hhi > 0 else 0.0

        sectors     = {a.sector for a in allocs}
        industries  = {a.industry for a in allocs}
        asset_cls   = {a.asset_class for a in allocs}

        avg_conviction = sum(a.conviction for a in allocs) / n
        avg_confidence = sum(a.confidence for a in allocs) / n
        avg_risk       = sum(a.risk_score for a in allocs) / n
    else:
        avg_pos = med_pos = max_pos = min_pos = std_pos = 0.0
        hhi = 0.0; eff_n = 0.0
        sectors = industries = asset_cls = set()
        avg_conviction = avg_confidence = avg_risk = 0.0

    return AllocationMetrics(
        portfolio_id            = plan.portfolio_id,
        plan_id                 = plan.plan_id,
        total_capital           = total,
        invested_capital        = invested,
        short_capital           = short_cap,
        cash_capital            = cash_cap,
        capital_utilisation_pct = utilisation,
        long_pct                = long_pct,
        short_pct               = short_pct,
        cash_pct                = cash_pct,
        net_exposure_pct        = long_pct - short_pct,
        gross_exposure_pct      = long_pct + short_pct,
        long_count              = len(longs),
        short_count             = len(shorts),
        total_count             = n,
        avg_position_dollars    = avg_pos,
        median_position_dollars = med_pos,
        max_position_dollars    = max_pos,
        min_position_dollars    = min_pos,
        std_position_dollars    = std_pos,
        hhi                     = hhi,
        effective_n             = eff_n,
        sector_count            = len(sectors),
        industry_count          = len(industries),
        asset_class_count       = len(asset_cls),
        avg_conviction          = avg_conviction,
        avg_confidence          = avg_confidence,
        avg_risk_score          = avg_risk,
    )
