"""iios/investment/strategy/portfolio/portfolio_score.py
PortfolioScore — overall institutional-grade scoring of a strategy portfolio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.portfolio.strategy_portfolio import StrategyPortfolio
from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.portfolio_quality import PortfolioQuality
from iios.investment.strategy.portfolio.portfolio_confidence import PortfolioConfidence
from iios.investment.strategy.portfolio.portfolio_health import PortfolioHealth, HealthStatus
from iios.investment.strategy.portfolio.diversification_engine import DiversificationEngine, DiversificationReport
from iios.investment.strategy.portfolio.construction_constraints import (
    ConstructionConstraints, DEFAULT_CONSTRAINTS
)
from iios.investment.strategy.portfolio.portfolio_statistics import weighted_average


@dataclass(frozen=True)
class PortfolioScore:
    """
    Institutional-grade composite score for a strategy portfolio.

    Dimensions:
        Diversification   30%
        Allocation Quality 25%
        Stability          25%   (proxy: 100 - max_drift * 1000 clamped at 100)
        Robustness         20%   (weighted avg of strategy robustness_scores, 0-100)

    Grade mapping: A(≥80), B(≥65), C(≥50), D(≥35), F(<35)
    """
    portfolio_id:          str

    # Dimension scores (0–100)
    diversification_score: float
    allocation_quality:    float
    stability_score:       float
    robustness_score:      float

    # Weights
    overall_score:         float   # weighted composite

    # Metadata
    strategy_count:        int
    health_status:         str
    grade:                 str
    scored_at:             datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    _WEIGHTS = {
        "diversification":  0.30,
        "allocation":       0.25,
        "stability":        0.25,
        "robustness":       0.20,
    }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id":          self.portfolio_id,
            "overall_score":         round(self.overall_score, 2),
            "grade":                 self.grade,
            "health_status":         self.health_status,
            "strategy_count":        self.strategy_count,
            "dimensions": {
                "diversification":   round(self.diversification_score, 2),
                "allocation_quality": round(self.allocation_quality, 2),
                "stability":         round(self.stability_score, 2),
                "robustness":        round(self.robustness_score, 2),
            },
            "scored_at": self.scored_at.isoformat(),
        }


def _grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    if score >= 35:
        return "D"
    return "F"


class PortfolioScoreCalculator:
    """
    Computes PortfolioScore from a portfolio and its associated strategies.
    All upstream intelligence (evaluation, diversification) is consumed, not generated.
    """

    def __init__(self) -> None:
        self._div_engine = DiversificationEngine()

    def score(
        self,
        portfolio:         StrategyPortfolio,
        strategies:        List[PortfolioStrategy],
        strategy_conf_map: Optional[Dict[str, float]] = None,
        constraints:       ConstructionConstraints = DEFAULT_CONSTRAINTS,
    ) -> PortfolioScore:
        active = portfolio.active_allocations()
        pid    = portfolio.portfolio_id

        if not active:
            return PortfolioScore(
                portfolio_id=pid, diversification_score=0.0, allocation_quality=0.0,
                stability_score=0.0, robustness_score=0.0, overall_score=0.0,
                strategy_count=0, health_status="unknown", grade="F",
            )

        conf_map = strategy_conf_map or {s.strategy_id: s.confidence_score for s in strategies}

        # Diversification
        div_report = self._div_engine.analyse(portfolio, strategies)
        div_score  = div_report.diversification_score

        # Allocation quality
        quality   = PortfolioQuality.compute(portfolio)
        alloc_q   = quality.allocation_quality

        # Stability (inverse of drift)
        max_drift = portfolio.max_drift
        stability = max(0.0, min(100.0, (1.0 - max_drift * 10.0) * 100.0))

        # Robustness: weighted average of strategy robustness_scores
        strat_map = {s.strategy_id: s for s in strategies}
        weights   = []
        rob_vals  = []
        for alloc in active:
            s = strat_map.get(alloc.strategy_id)
            if s:
                weights.append(alloc.weight)
                rob_vals.append(s.robustness_score * 100.0)
        robustness = weighted_average(rob_vals, weights) if rob_vals else 0.0

        # Health
        health = PortfolioHealth.assess(portfolio, conf_map, constraints)

        # Composite
        w = PortfolioScore._WEIGHTS
        overall = (
            w["diversification"]  * div_score
            + w["allocation"]     * alloc_q
            + w["stability"]      * stability
            + w["robustness"]     * robustness
        )
        overall = min(100.0, max(0.0, overall))

        return PortfolioScore(
            portfolio_id=pid,
            diversification_score=div_score,
            allocation_quality=alloc_q,
            stability_score=stability,
            robustness_score=robustness,
            overall_score=overall,
            strategy_count=portfolio.active_count,
            health_status=health.health_status.value,
            grade=_grade(overall),
        )
