"""iios/investment/portfolio/performance/performance_attribution.py

Portfolio-level attribution orchestrator (BHB model).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.performance.benchmark_comparison import BenchmarkComparison
from iios.investment.portfolio.performance.factor_attribution import (
    FactorAttribution, compute_factor_attribution,
)
from iios.investment.portfolio.performance.performance_types import (
    AttributionMethod, PerformancePosition,
)
from iios.investment.portfolio.performance.sector_attribution import (
    SectorAttribution, compute_sector_attribution,
)
from iios.investment.portfolio.performance.security_attribution import (
    SecurityAttribution, compute_security_attribution,
)
from iios.investment.portfolio.performance.strategy_attribution import (
    StrategyAttribution, compute_strategy_attribution,
)


@dataclass(frozen=True)
class AttributionResult:
    """Full attribution decomposition for a portfolio."""

    result_id:    str = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str = ""
    method:       AttributionMethod = AttributionMethod.BRINSON

    # BHB top-level
    allocation_effect:    float = 0.0
    selection_effect:     float = 0.0
    interaction_effect:   float = 0.0
    total_active_return:  float = 0.0

    # Sub-level results
    sector_attribution:   Optional[SectorAttribution]   = None
    security_attribution: Optional[SecurityAttribution] = None
    factor_attribution:   Optional[FactorAttribution]   = None
    strategy_attribution: Optional[StrategyAttribution] = None

    # Benchmark reference
    benchmark_id:     str   = ""
    benchmark_return: float = 0.0
    portfolio_return: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "method":              self.method.value,
            "allocation_effect":   round(self.allocation_effect, 4),
            "selection_effect":    round(self.selection_effect, 4),
            "interaction_effect":  round(self.interaction_effect, 4),
            "total_active_return": round(self.total_active_return, 4),
            "benchmark_id":        self.benchmark_id,
        }
        if self.sector_attribution:
            d["sector"] = self.sector_attribution.to_dict()
        if self.security_attribution:
            d["security"] = self.security_attribution.to_dict()
        if self.factor_attribution:
            d["factor"] = self.factor_attribution.to_dict()
        if self.strategy_attribution:
            d["strategy"] = self.strategy_attribution.to_dict()
        return d


class PortfolioAttributionEngine:
    """Orchestrates all attribution analyses."""

    def analyze(
        self,
        positions:         List[PerformancePosition],
        benchmark_comparison: Optional[BenchmarkComparison] = None,
        portfolio_id:      str = "",
        benchmark_sector_weights: Optional[Dict[str, float]] = None,
        benchmark_sector_returns: Optional[Dict[str, float]] = None,
        method:            AttributionMethod = AttributionMethod.BRINSON,
    ) -> AttributionResult:

        bmk_ret  = benchmark_comparison.benchmark_return if benchmark_comparison else 0.0
        port_ret = benchmark_comparison.portfolio_return  if benchmark_comparison else 0.0
        bmk_id   = benchmark_comparison.benchmark_id     if benchmark_comparison else ""

        sector = compute_sector_attribution(
            positions,
            benchmark_return          = bmk_ret,
            portfolio_id              = portfolio_id,
            benchmark_sector_weights  = benchmark_sector_weights,
            benchmark_sector_returns  = benchmark_sector_returns,
        )
        security = compute_security_attribution(positions, portfolio_id)
        factor   = compute_factor_attribution(positions, portfolio_id)
        strategy = compute_strategy_attribution(positions, portfolio_id)

        return AttributionResult(
            portfolio_id         = portfolio_id,
            method               = method,
            allocation_effect    = sector.total_allocation,
            selection_effect     = sector.total_selection,
            interaction_effect   = sector.total_interaction,
            total_active_return  = sector.total_active,
            sector_attribution   = sector,
            security_attribution = security,
            factor_attribution   = factor,
            strategy_attribution = strategy,
            benchmark_id         = bmk_id,
            benchmark_return     = round(bmk_ret, 6),
            portfolio_return     = round(port_ret, 6),
        )
