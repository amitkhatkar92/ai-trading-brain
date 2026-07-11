"""tests/unit/investment/market/opportunity/test_ranking.py"""
from __future__ import annotations

import pytest

from iios.investment.market.opportunity.models import (
    IntelligenceContext,
    Opportunity,
    OpportunityCategory,
    RankingScore,
)
from iios.investment.market.opportunity.ranking_engine import RankingEngine
from iios.investment.market.opportunity.ranking_history import RankingHistory
from iios.investment.market.opportunity.ranking_score import score_opportunity
from iios.investment.market.opportunity.ranking_statistics import (
    avg_score_by_category,
    rank_stability,
    top_stable_opportunities,
)


def _make_opp(symbol: str, cat: OpportunityCategory = OpportunityCategory.TREND_FOLLOWING) -> Opportunity:
    return Opportunity.new(symbol, "IT", "Software", cat, 1)


def _make_ctx(trend: float = 65.0, rs: float = 70.0, vol: float = 1.5) -> IntelligenceContext:
    return IntelligenceContext(
        trend_strength=trend, rs_vs_market=rs, volume_ratio=vol,
        sector_rs_score=65.0, sector_momentum=60.0, risk_score=65.0,
        return_20bar=0.05, liquidity_score=70.0, fundamental_score=60.0,
        breadth_score=65.0, volatility_percentile=0.3,
    )


class TestScoreOpportunity:
    def test_returns_ranking_score(self):
        opp = _make_opp("AAPL")
        ctx = _make_ctx()
        rs  = score_opportunity(opp, ctx)
        assert isinstance(rs, RankingScore)
        assert rs.symbol == "AAPL"

    def test_composite_in_range(self):
        for trend in (20.0, 50.0, 80.0):
            for rs_v in (20.0, 50.0, 80.0):
                opp = _make_opp("X")
                ctx = _make_ctx(trend=trend, rs=rs_v)
                rs  = score_opportunity(opp, ctx)
                assert 0.0 <= rs.composite_score <= 100.0

    def test_strong_beats_weak(self):
        strong_opp = _make_opp("STRONG")
        weak_opp   = _make_opp("WEAK", OpportunityCategory.OBSERVATION_ONLY)
        strong_ctx = _make_ctx(trend=85.0, rs=90.0, vol=2.0)
        weak_ctx   = _make_ctx(trend=20.0, rs=15.0, vol=0.5)
        rs_strong = score_opportunity(strong_opp, strong_ctx)
        rs_weak   = score_opportunity(weak_opp,   weak_ctx)
        assert rs_strong.composite_score > rs_weak.composite_score

    def test_category_weight_affects_score(self):
        """HIGH_RS category has 1.10 weight → higher score than OBSERVATION_ONLY."""
        high_rs = _make_opp("A", OpportunityCategory.HIGH_RS)
        obs     = _make_opp("B", OpportunityCategory.OBSERVATION_ONLY)
        ctx     = _make_ctx(trend=70.0, rs=75.0)
        rs1 = score_opportunity(high_rs, ctx)
        rs2 = score_opportunity(obs,     ctx)
        assert rs1.composite_score > rs2.composite_score


class TestRankingEngine:
    def test_update_assigns_ranks(self, obs_batch):
        from iios.investment.market.opportunity.classification_engine import ClassificationEngine
        engine   = RankingEngine()
        cls_eng  = ClassificationEngine()
        opps     = list(cls_eng.classify_batch(obs_batch).values())
        ranked   = engine.update(opps, obs_batch)
        ranks    = [o.rank for o in ranked]
        assert ranks == sorted(ranks)
        assert min(ranks) == 1

    def test_rank_1_has_highest_score(self, obs_batch):
        from iios.investment.market.opportunity.classification_engine import ClassificationEngine
        engine  = RankingEngine()
        cls_eng = ClassificationEngine()
        opps    = list(cls_eng.classify_batch(obs_batch).values())
        ranked  = engine.update(opps, obs_batch)
        if len(ranked) >= 2:
            assert ranked[0].composite_score >= ranked[1].composite_score

    def test_top_n(self, obs_batch):
        from iios.investment.market.opportunity.classification_engine import ClassificationEngine
        engine  = RankingEngine()
        cls_eng = ClassificationEngine()
        opps    = list(cls_eng.classify_batch(obs_batch).values())
        engine.update(opps, obs_batch)
        top3    = engine.top_n(3)
        assert len(top3) <= 3

    def test_get_score(self, obs_batch):
        from iios.investment.market.opportunity.classification_engine import ClassificationEngine
        engine  = RankingEngine()
        cls_eng = ClassificationEngine()
        opps    = list(cls_eng.classify_batch(obs_batch).values())
        ranked  = engine.update(opps, obs_batch)
        if ranked:
            rs = engine.get_score(ranked[0].opportunity_id)
            assert rs is not None


class TestRankingHistory:
    def test_append_and_latest(self):
        hist = RankingHistory()
        opp  = _make_opp("X")
        rs   = RankingScore(opp.opportunity_id, "X", 80.0, 70.0, 75.0, 65.0, 72.0, 70.0, 68.0, 1)
        hist.append({opp.opportunity_id: rs})
        assert len(hist) == 1
        assert hist.latest() is not None

    def test_symbol_series(self):
        hist = RankingHistory()
        opp  = _make_opp("X")
        for score in [60.0, 65.0, 70.0]:
            rs = RankingScore(opp.opportunity_id, "X", score, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1)
            hist.append({opp.opportunity_id: rs})
        series = hist.symbol_series(opp.opportunity_id, 3)
        assert series == [60.0, 65.0, 70.0]


class TestRankingStatistics:
    def test_avg_score_by_category(self):
        opps = [
            _make_opp("A", OpportunityCategory.TREND_FOLLOWING),
            _make_opp("B", OpportunityCategory.TREND_FOLLOWING),
            _make_opp("C", OpportunityCategory.HIGH_RS),
        ]
        opps[0].composite_score = 80.0
        opps[1].composite_score = 60.0
        opps[2].composite_score = 90.0
        avgs = avg_score_by_category(opps)
        assert avgs["trend_following"] == pytest.approx(70.0)
        assert avgs["high_relative_strength"] == pytest.approx(90.0)

    def test_rank_stability_constant(self):
        hist = RankingHistory()
        opp  = _make_opp("X")
        for _ in range(5):
            rs = RankingScore(opp.opportunity_id, "X", 70.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1)
            hist.append({opp.opportunity_id: rs})
        stab = rank_stability(hist, opp.opportunity_id)
        assert stab == pytest.approx(1.0, abs=0.01)

    def test_rank_stability_volatile(self):
        hist = RankingHistory()
        opp  = _make_opp("X")
        for score in [50.0, 90.0, 50.0, 90.0, 50.0]:
            rs = RankingScore(opp.opportunity_id, "X", score, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1)
            hist.append({opp.opportunity_id: rs})
        stab = rank_stability(hist, opp.opportunity_id)
        assert stab < 1.0
