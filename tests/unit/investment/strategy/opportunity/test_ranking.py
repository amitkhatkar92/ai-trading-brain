"""tests/unit/investment/strategy/opportunity/test_ranking.py"""
from __future__ import annotations

import pytest

from iios.investment.strategy.opportunity.ranking_engine import RankingEngine
from iios.investment.strategy.opportunity.ranking_history import RankingHistory
from iios.investment.strategy.opportunity.ranking_score import RankingScore
from iios.investment.strategy.opportunity.strategy_ranking import StrategyRanking, RankedOpportunity
from iios.investment.strategy.opportunity.strategy_matcher import MatchResult
from iios.investment.strategy.opportunity.strategy_suitability import SuitabilityEngine
from tests.unit.investment.strategy.opportunity.conftest import (
    make_market_opp, make_candidate
)


def _match_result(strategy_id, opp_id, score=70.0, passed=True):
    return MatchResult(
        strategy_id=strategy_id,
        opportunity_id=opp_id,
        score=score,
        passed=passed,
        dimension_scores={"regime": 80.0, "direction": 90.0},
    )


def _suitability(strategy_id, opp_id, score=65.0):
    from iios.investment.strategy.opportunity.constraint_engine import ConstraintResult
    from iios.investment.strategy.opportunity.compatibility_engine import CompatibilityScores
    from iios.investment.strategy.opportunity.strategy_suitability import SuitabilityResult
    return SuitabilityResult(
        strategy_id=strategy_id,
        opportunity_id=opp_id,
        suitable=True,
        score=score,
        constraints=ConstraintResult(passed=True),
        compatibility=CompatibilityScores(
            risk_compatibility=70.0,
            execution_readiness=75.0,
            overall=score,
        ),
    )


class TestRankingEngine:
    def test_score_bounded(self):
        engine = RankingEngine()
        c  = make_candidate(eval_score=75.0, sharpe=1.2, max_dd=0.12)
        mr = _match_result(c.strategy_id, "opp-1")
        sr = _suitability(c.strategy_id, "opp-1")
        rs = engine.score(c, mr, sr)
        assert 0.0 <= rs.overall_score <= 100.0

    def test_higher_eval_score_higher_rank(self):
        engine = RankingEngine()
        opp_id = "opp-1"
        c_good = make_candidate("s-good", eval_score=90.0, sharpe=2.0)
        c_bad  = make_candidate("s-bad",  eval_score=40.0, sharpe=0.5, max_dd=0.35)

        rs_good = engine.score(c_good, _match_result("s-good", opp_id, 80.0), _suitability("s-good", opp_id, 80.0))
        rs_bad  = engine.score(c_bad,  _match_result("s-bad",  opp_id, 50.0), _suitability("s-bad",  opp_id, 45.0))

        assert rs_good.overall_score > rs_bad.overall_score

    def test_rank_assigns_ordinal(self):
        engine = RankingEngine()
        scores = [
            RankingScore("s1", "o1", 70.0, 60.0, 65.0, 0.7, 0.6, 0.5, 66.0),
            RankingScore("s2", "o1", 85.0, 75.0, 80.0, 0.8, 0.7, 0.6, 78.0),
            RankingScore("s3", "o1", 50.0, 45.0, 48.0, 0.5, 0.4, 0.3, 48.0),
        ]
        ranked = engine.rank(scores)
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2
        assert ranked[2].rank == 3

    def test_rank_ordered_descending(self):
        engine = RankingEngine()
        scores = [
            RankingScore("s1", "o1", 70.0, 60.0, 65.0, 0.7, 0.6, 0.5, 66.0),
            RankingScore("s2", "o1", 85.0, 75.0, 80.0, 0.8, 0.7, 0.6, 78.0),
        ]
        ranked = engine.rank(scores)
        assert ranked[0].overall_score >= ranked[1].overall_score

    def test_empty_rank_returns_empty(self):
        assert RankingEngine().rank([]) == []

    def test_historical_score_influences_result(self):
        engine = RankingEngine()
        c  = make_candidate()
        mr = _match_result(c.strategy_id, "opp-1")
        sr = _suitability(c.strategy_id, "opp-1")
        rs_high = engine.score(c, mr, sr, historical_pass_rate=0.90)
        rs_low  = engine.score(c, mr, sr, historical_pass_rate=0.10)
        assert rs_high.overall_score > rs_low.overall_score


class TestRankingHistory:
    def test_record_and_latest(self):
        hist = RankingHistory()
        rs   = RankingScore("s1", "o1", 70.0, 60.0, 65.0, 0.7, 0.6, 0.5, 66.0, rank=1)
        hist.record(rs)
        assert hist.latest("s1").overall_score == pytest.approx(66.0)

    def test_history_capped(self):
        hist = RankingHistory(max_per_strategy=3)
        for i in range(6):
            rs = RankingScore(f"s1", f"o{i}", 70.0, 60.0, 65.0, 0.7, 0.6, 0.5, 66.0)
            hist.record(rs)
        assert len(hist.history("s1")) <= 3

    def test_avg_score_reasonable(self):
        hist = RankingHistory()
        for score in [60.0, 70.0, 80.0]:
            rs = RankingScore("s1", "o1", score, score, score, 0.7, 0.6, 0.5, score)
            hist.record(rs)
        avg = hist.avg_score("s1")
        assert avg == pytest.approx(70.0)

    def test_unknown_strategy_returns_none(self):
        hist = RankingHistory()
        assert hist.latest("nonexistent") is None

    def test_purge_removes_strategy(self):
        hist = RankingHistory()
        rs   = RankingScore("s1", "o1", 70.0, 60.0, 65.0, 0.7, 0.6, 0.5, 66.0)
        hist.record(rs)
        hist.purge("s1")
        assert hist.latest("s1") is None
