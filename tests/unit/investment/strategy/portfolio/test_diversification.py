"""tests/unit/investment/strategy/portfolio/test_diversification.py
Tests for CorrelationMatrix, OverlapAnalysis, RedundancyDetector,
and DiversificationEngine.
"""
from __future__ import annotations

import pytest
from typing import List

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.strategy_correlation import (
    CorrelationMatrix, StrategyCorrelation
)
from iios.investment.strategy.portfolio.overlap_analysis import OverlapAnalysis
from iios.investment.strategy.portfolio.redundancy_detector import (
    RedundancyDetector, RedundancyReport
)
from iios.investment.strategy.portfolio.diversification_engine import (
    DiversificationEngine, DiversificationReport
)
from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioType
)
from iios.investment.strategy.portfolio.strategy_allocation import StrategyAllocation
from tests.unit.investment.strategy.portfolio.conftest import make_strategy


def build_portfolio_with_strategies(strategies: List[PortfolioStrategy]) -> StrategyPortfolio:
    p = StrategyPortfolio("p1", "T", PortfolioType.EQUAL_WEIGHT)
    n = len(strategies)
    for s in strategies:
        p.add_strategy(StrategyAllocation(s.strategy_id, s.strategy_name, 1.0 / n, 1.0 / n))
    return p


# ── CorrelationMatrix ─────────────────────────────────────────────────────────

class TestCorrelationMatrix:
    def test_self_similarity_is_not_in_matrix(self, five_strategies):
        m = CorrelationMatrix(five_strategies)
        # get() for different ids
        corr = m.get(five_strategies[0].strategy_id, five_strategies[1].strategy_id)
        assert corr is not None

    def test_similarity_between_identical_profiles(self):
        s1 = make_strategy("s1", tags=["momentum"], sectors=["tech"],
                            regimes=["trending"], timeframes=["daily"])
        s2 = make_strategy("s2", tags=["momentum"], sectors=["tech"],
                            regimes=["trending"], timeframes=["daily"])
        m = CorrelationMatrix([s1, s2])
        corr = m.get("s1", "s2")
        assert corr is not None
        assert corr.similarity > 0.95

    def test_similarity_between_orthogonal_profiles(self):
        s1 = make_strategy("s1", tags=["momentum"], sectors=["tech"],
                            regimes=["trending"], timeframes=["daily"])
        s2 = make_strategy("s2", tags=["arbitrage"], sectors=["energy"],
                            regimes=["bear"], timeframes=["weekly"])
        m = CorrelationMatrix([s1, s2])
        corr = m.get("s1", "s2")
        assert corr is not None
        assert corr.similarity < 0.15

    def test_average_correlation_range(self, five_strategies):
        m = CorrelationMatrix(five_strategies)
        avg = m.average_correlation()
        assert 0.0 <= avg <= 1.0

    def test_all_pairs_unique(self, five_strategies):
        m = CorrelationMatrix(five_strategies)
        pairs = m.all_pairs()
        pair_keys = [(c.strategy_id_a, c.strategy_id_b) for c in pairs]
        assert len(pair_keys) == len(set(pair_keys))

    def test_matrix_as_dict_diagonal(self, five_strategies):
        m = CorrelationMatrix(five_strategies)
        mat = m.matrix_as_dict()
        for s in five_strategies:
            assert mat[s.strategy_id][s.strategy_id] == 1.0

    def test_get_returns_none_for_unknown(self, five_strategies):
        m = CorrelationMatrix(five_strategies)
        assert m.get("unknown-a", "unknown-b") is None

    def test_symmetric(self, five_strategies):
        m = CorrelationMatrix(five_strategies)
        a = five_strategies[0].strategy_id
        b = five_strategies[1].strategy_id
        assert m.get(a, b).similarity == m.get(b, a).similarity


# ── OverlapAnalysis ───────────────────────────────────────────────────────────

class TestOverlapAnalysis:
    def test_empty_strategies(self):
        oa = OverlapAnalysis()
        report = oa.analyse([])
        assert report.total_strategies == 0

    def test_shared_tags_detected(self):
        s1 = make_strategy("s1", tags=["momentum", "trend"])
        s2 = make_strategy("s2", tags=["momentum", "reversal"])
        oa = OverlapAnalysis()
        report = oa.analyse([s1, s2])
        assert "momentum" in report.shared_tags

    def test_sector_spread_single(self):
        strategies = [make_strategy(f"s{i}", sectors=["tech"]) for i in range(4)]
        oa = OverlapAnalysis()
        report = oa.analyse(strategies)
        assert report.dominant_sector == "tech"

    def test_tag_concentration_zero_when_no_overlap(self):
        s1 = make_strategy("s1", tags=["momentum"])
        s2 = make_strategy("s2", tags=["reversal"])
        oa = OverlapAnalysis()
        report = oa.analyse([s1, s2])
        assert report.tag_concentration == 0.0

    def test_to_dict_has_all_keys(self, five_strategies):
        oa = OverlapAnalysis()
        d = oa.analyse(five_strategies).to_dict()
        for k in ["total_strategies", "unique_tags", "shared_tags", "dominant_sector"]:
            assert k in d


# ── RedundancyDetector ────────────────────────────────────────────────────────

class TestRedundancyDetector:
    def test_detects_identical_strategies(self):
        s1 = make_strategy("s1", tags=["a", "b"], sectors=["tech"],
                            regimes=["trending"], timeframes=["daily"])
        s2 = make_strategy("s2", tags=["a", "b"], sectors=["tech"],
                            regimes=["trending"], timeframes=["daily"])
        m = CorrelationMatrix([s1, s2])
        rd = RedundancyDetector(threshold=0.70)
        report = rd.detect(m, {"s1": 70.0, "s2": 65.0})
        assert report.has_redundancy

    def test_no_redundancy_for_orthogonal(self):
        s1 = make_strategy("s1", tags=["momentum"])
        s2 = make_strategy("s2", tags=["arbitrage"], sectors=["energy"],
                            regimes=["bear"], timeframes=["weekly"])
        m = CorrelationMatrix([s1, s2])
        rd = RedundancyDetector(threshold=0.70)
        report = rd.detect(m, {"s1": 70.0, "s2": 65.0})
        assert not report.has_redundancy

    def test_report_to_dict(self, five_strategies):
        m = CorrelationMatrix(five_strategies)
        rd = RedundancyDetector()
        eval_scores = {s.strategy_id: s.evaluation_score for s in five_strategies}
        report = rd.detect(m, eval_scores)
        d = report.to_dict()
        assert "redundant_count" in d
        assert "threshold" in d


# ── DiversificationEngine ─────────────────────────────────────────────────────

class TestDiversificationEngine:
    def test_diverse_portfolio_high_score(self, five_strategies):
        p = build_portfolio_with_strategies(five_strategies)
        eng = DiversificationEngine()
        report = eng.analyse(p, five_strategies)
        assert report.diversification_score > 30.0   # more than minimal

    def test_concentrated_portfolio_lower_score(self):
        # Same tags across all strategies
        strategies = [
            make_strategy(f"s{i}", tags=["momentum"], sectors=["tech"],
                          regimes=["trending"], timeframes=["daily"])
            for i in range(4)
        ]
        p = build_portfolio_with_strategies(strategies)
        eng = DiversificationEngine()
        report = eng.analyse(p, strategies)
        # Highly similar strategies → lower diversification
        assert report.average_correlation > 0.80

    def test_empty_portfolio_zero_score(self):
        p = StrategyPortfolio("p1", "T", PortfolioType.EQUAL_WEIGHT)
        eng = DiversificationEngine()
        report = eng.analyse(p, [])
        assert report.diversification_score == 0.0

    def test_score_range(self, five_strategies):
        p = build_portfolio_with_strategies(five_strategies)
        eng = DiversificationEngine()
        report = eng.analyse(p, five_strategies)
        assert 0.0 <= report.diversification_score <= 100.0

    def test_report_grade(self, five_strategies):
        p = build_portfolio_with_strategies(five_strategies)
        eng = DiversificationEngine()
        report = eng.analyse(p, five_strategies)
        assert report.grade in ("A", "B", "C", "D", "F")

    def test_to_dict_keys(self, five_strategies):
        p = build_portfolio_with_strategies(five_strategies)
        eng = DiversificationEngine()
        report = eng.analyse(p, five_strategies)
        d = report.to_dict()
        for key in ["portfolio_id", "diversification_score", "average_correlation", "grade"]:
            assert key in d
