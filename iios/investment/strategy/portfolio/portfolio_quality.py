"""iios/investment/strategy/portfolio/portfolio_quality.py
PortfolioQuality — allocation quality metrics for a portfolio.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.strategy.portfolio.strategy_portfolio import StrategyPortfolio
from iios.investment.strategy.portfolio.portfolio_statistics import (
    herfindahl_index, safe_div, gini_coefficient, weighted_average
)


@dataclass(frozen=True)
class PortfolioQuality:
    """
    Allocation quality assessment of a portfolio.
    All scores in [0, 100]; higher = better quality.
    """
    portfolio_id:       str

    # Coverage: how many strategies are contributing meaningful weight (weight > min)
    coverage_score:     float   # proportion of strategies above trivial weight

    # Weight efficiency: how evenly weight is distributed (anti-concentration)
    weight_efficiency:  float   # 1 - concentration

    # Strategy synergy: average evaluation_score of active strategies
    strategy_synergy:   float   # 0–100

    # Gini coefficient of weights (lower = more equal)
    gini:               float   # 0–1 (informational)

    # Overall allocation quality
    allocation_quality: float   # composite of above, 0–100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id":      self.portfolio_id,
            "coverage_score":    round(self.coverage_score, 2),
            "weight_efficiency": round(self.weight_efficiency, 2),
            "strategy_synergy":  round(self.strategy_synergy, 2),
            "gini":              round(self.gini, 4),
            "allocation_quality": round(self.allocation_quality, 2),
        }

    @classmethod
    def compute(cls, portfolio: StrategyPortfolio) -> "PortfolioQuality":
        active = portfolio.active_allocations()
        n = len(active)
        pid = portfolio.portfolio_id

        if n == 0:
            return cls(pid, 0.0, 0.0, 0.0, 1.0, 0.0)

        weights = [a.weight for a in active]
        scores  = [a.evaluation_score for a in active]

        # Coverage: fraction of strategies with weight ≥ 0.02
        meaningful = sum(1 for w in weights if w >= 0.02)
        coverage = meaningful / n * 100.0

        # Weight efficiency: inverse of HHI concentration, scaled to 100
        hhi  = herfindahl_index(weights)
        min_hhi = 1.0 / n
        conc = safe_div(hhi - min_hhi, 1.0 - min_hhi, 0.0)
        weight_efficiency = (1.0 - conc) * 100.0

        # Strategy synergy: weighted average evaluation score
        synergy = weighted_average(scores, weights)

        # Gini
        gini = gini_coefficient(weights)

        # Composite quality
        quality = (
            0.30 * coverage
            + 0.40 * weight_efficiency
            + 0.30 * synergy
        )

        return cls(
            portfolio_id=pid,
            coverage_score=coverage,
            weight_efficiency=weight_efficiency,
            strategy_synergy=synergy,
            gini=gini,
            allocation_quality=min(100.0, max(0.0, quality)),
        )
