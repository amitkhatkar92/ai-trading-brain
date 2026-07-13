"""tests/unit/investment/strategy/portfolio/test_scoring.py
Tests for PortfolioQuality, PortfolioConfidence, PortfolioHealth,
and PortfolioScore.
"""
from __future__ import annotations

import pytest
from typing import List

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioType, PortfolioState
)
from iios.investment.strategy.portfolio.strategy_allocation import StrategyAllocation
from iios.investment.strategy.portfolio.portfolio_quality import PortfolioQuality
from iios.investment.strategy.portfolio.portfolio_confidence import PortfolioConfidence
from iios.investment.strategy.portfolio.portfolio_health import PortfolioHealth, HealthStatus
from iios.investment.strategy.portfolio.portfolio_score import (
    PortfolioScore, PortfolioScoreCalculator
)
from iios.investment.strategy.portfolio.construction_constraints import DEFAULT_CONSTRAINTS
from tests.unit.investment.strategy.portfolio.conftest import make_strategy


def _build_portfolio(strategies: List[PortfolioStrategy]) -> StrategyPortfolio:
    p = StrategyPortfolio("p1", "Test", PortfolioType.EQUAL_WEIGHT, state=PortfolioState.ACTIVE)
    n = len(strategies)
    for s in strategies:
        p.add_strategy(StrategyAllocation(s.strategy_id, s.strategy_name, 1.0 / n, 1.0 / n,
                                          evaluation_score=s.evaluation_score))
    return p


# ── PortfolioQuality ──────────────────────────────────────────────────────────

class TestPortfolioQuality:
    def test_empty_portfolio_zero(self):
        p = StrategyPortfolio("p1", "T", PortfolioType.EQUAL_WEIGHT)
        q = PortfolioQuality.compute(p)
        assert q.allocation_quality == 0.0

    def test_equal_weight_high_efficiency(self, five_strategies):
        p = _build_portfolio(five_strategies)
        q = PortfolioQuality.compute(p)
        # Equal weights should give near-max weight efficiency
        assert q.weight_efficiency > 70.0

    def test_coverage_full_above_min(self, five_strategies):
        p = _build_portfolio(five_strategies)
        q = PortfolioQuality.compute(p)
        # All weights = 0.20 ≥ 0.02 → coverage = 100
        assert abs(q.coverage_score - 100.0) < 1e-6

    def test_quality_in_range(self, five_strategies):
        p = _build_portfolio(five_strategies)
        q = PortfolioQuality.compute(p)
        assert 0.0 <= q.allocation_quality <= 100.0

    def test_to_dict_has_keys(self, five_strategies):
        p = _build_portfolio(five_strategies)
        d = PortfolioQuality.compute(p).to_dict()
        for key in ["portfolio_id", "allocation_quality", "gini"]:
            assert key in d


# ── PortfolioConfidence ───────────────────────────────────────────────────────

class TestPortfolioConfidence:
    def test_empty_portfolio(self):
        p = StrategyPortfolio("p1", "T", PortfolioType.EQUAL_WEIGHT)
        c = PortfolioConfidence.compute(p, {})
        assert c.weighted_confidence == 0.0

    def test_high_confidence_grade(self, five_strategies):
        p = _build_portfolio(five_strategies)
        conf_map = {s.strategy_id: 85.0 for s in five_strategies}
        c = PortfolioConfidence.compute(p, conf_map)
        assert c.grade == "HIGH"

    def test_low_confidence_grade(self, five_strategies):
        p = _build_portfolio(five_strategies)
        conf_map = {s.strategy_id: 25.0 for s in five_strategies}
        c = PortfolioConfidence.compute(p, conf_map)
        assert c.grade == "LOW"

    def test_low_confidence_count(self, five_strategies):
        p = _build_portfolio(five_strategies)
        conf_map = {s.strategy_id: 20.0 for s in five_strategies}
        c = PortfolioConfidence.compute(p, conf_map)
        assert c.low_confidence_count == len(five_strategies)

    def test_to_dict_has_grade(self, five_strategies):
        p = _build_portfolio(five_strategies)
        conf_map = {s.strategy_id: 75.0 for s in five_strategies}
        d = PortfolioConfidence.compute(p, conf_map).to_dict()
        assert "grade" in d


# ── PortfolioHealth ───────────────────────────────────────────────────────────

class TestPortfolioHealth:
    def test_healthy_portfolio(self, five_strategies):
        p = _build_portfolio(five_strategies)
        conf_map = {s.strategy_id: 80.0 for s in five_strategies}
        health = PortfolioHealth.assess(p, conf_map, DEFAULT_CONSTRAINTS)
        assert health.health_score >= 0.0

    def test_critical_portfolio_no_strategies(self):
        p = StrategyPortfolio("p1", "T", PortfolioType.EQUAL_WEIGHT, state=PortfolioState.ACTIVE)
        health = PortfolioHealth.assess(p, {}, DEFAULT_CONSTRAINTS)
        # Should have critical issues due to no strategies
        assert len(health.issues) > 0
        assert health.health_status in (HealthStatus.CRITICAL, HealthStatus.DEGRADED)

    def test_weight_drift_issue_detected(self, five_strategies):
        p = _build_portfolio(five_strategies)
        # Force heavy drift on one allocation
        alloc = list(p.allocations.values())[0]
        alloc.weight       = 0.70
        alloc.target_weight = 0.20
        conf_map = {s.strategy_id: 75.0 for s in five_strategies}
        health = PortfolioHealth.assess(p, conf_map, DEFAULT_CONSTRAINTS)
        assert any("drift" in issue.lower() for issue in health.issues)

    def test_recommendations_non_empty_when_issues(self, five_strategies):
        p = _build_portfolio(five_strategies)
        alloc = list(p.allocations.values())[0]
        alloc.weight = 0.70
        conf_map = {s.strategy_id: 75.0 for s in five_strategies}
        health = PortfolioHealth.assess(p, conf_map, DEFAULT_CONSTRAINTS)
        if health.issues:
            assert len(health.recommendations) > 0

    def test_to_dict_keys(self, five_strategies):
        p = _build_portfolio(five_strategies)
        conf_map = {s.strategy_id: 70.0 for s in five_strategies}
        d = PortfolioHealth.assess(p, conf_map).to_dict()
        for key in ["health_score", "health_status", "issues", "recommendations"]:
            assert key in d


# ── PortfolioScoreCalculator ──────────────────────────────────────────────────

class TestPortfolioScoreCalculator:
    def test_score_in_range(self, five_strategies):
        p = _build_portfolio(five_strategies)
        calc = PortfolioScoreCalculator()
        score = calc.score(p, five_strategies)
        assert 0.0 <= score.overall_score <= 100.0

    def test_grade_assigned(self, five_strategies):
        p = _build_portfolio(five_strategies)
        calc = PortfolioScoreCalculator()
        score = calc.score(p, five_strategies)
        assert score.grade in ("A", "B", "C", "D", "F")

    def test_empty_portfolio_gets_F(self):
        p = StrategyPortfolio("p1", "T", PortfolioType.EQUAL_WEIGHT)
        calc = PortfolioScoreCalculator()
        score = calc.score(p, [])
        assert score.grade == "F"
        assert score.overall_score == 0.0

    def test_to_dict_has_all_dimensions(self, five_strategies):
        p = _build_portfolio(five_strategies)
        calc = PortfolioScoreCalculator()
        score = calc.score(p, five_strategies)
        d = score.to_dict()
        assert "dimensions" in d
        dims = d["dimensions"]
        for key in ["diversification", "allocation_quality", "stability", "robustness"]:
            assert key in dims

    def test_diverse_portfolio_scores_higher(self, five_strategies):
        # Diverse portfolio (five_strategies has varied tags/sectors)
        p_diverse = _build_portfolio(five_strategies)
        calc = PortfolioScoreCalculator()
        score_diverse = calc.score(p_diverse, five_strategies)

        # Concentrated portfolio (same tag)
        same_strats = [make_strategy(f"s{i}", tags=["momentum"], sectors=["tech"],
                                     regimes=["trending"], timeframes=["daily"])
                       for i in range(3)]
        p_conc = _build_portfolio(same_strats)
        score_conc = calc.score(p_conc, same_strats)

        # Diverse should score higher on diversification dimension
        assert score_diverse.diversification_score > score_conc.diversification_score
