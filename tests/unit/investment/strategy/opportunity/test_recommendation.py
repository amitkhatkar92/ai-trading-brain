"""tests/unit/investment/strategy/opportunity/test_recommendation.py"""
from __future__ import annotations

import pytest

from iios.investment.strategy.opportunity.evidence_collector import EvidenceCollector
from iios.investment.strategy.opportunity.reason_generator import ReasonGenerator
from iios.investment.strategy.opportunity.recommendation_engine import RecommendationEngine
from iios.investment.strategy.opportunity.ranking_score import RankingScore
from iios.investment.strategy.opportunity.strategy_matcher import MatchResult
from iios.investment.strategy.opportunity.constraint_engine import ConstraintResult
from iios.investment.strategy.opportunity.compatibility_engine import CompatibilityScores
from iios.investment.strategy.opportunity.strategy_suitability import SuitabilityResult
from tests.unit.investment.strategy.opportunity.conftest import (
    make_market_opp, make_company_opp, make_candidate
)


def _make_suit(sid, oid, score=70.0, suitable=True):
    return SuitabilityResult(
        strategy_id=sid,
        opportunity_id=oid,
        suitable=suitable,
        score=score,
        constraints=ConstraintResult(passed=True),
        compatibility=CompatibilityScores(
            risk_compatibility=70.0,
            execution_readiness=80.0,
            overall=score,
        ),
    )


def _make_match(sid, oid, score=72.0):
    return MatchResult(
        strategy_id=sid,
        opportunity_id=oid,
        score=score,
        passed=True,
        dimension_scores={"regime": 90.0, "direction": 85.0, "liquidity": 75.0},
    )


def _make_ranking(sid, oid, overall=68.0, rank=1):
    return RankingScore(
        strategy_id=sid,
        opportunity_id=oid,
        strategy_score=75.0,
        opportunity_score=70.0,
        risk_score=65.0,
        robustness_score=0.72 * 100,
        confidence_score=68.0,
        historical_score=55.0,
        overall_score=overall,
        rank=rank,
    )


class TestEvidenceCollector:
    def test_positive_evidence_for_good_strategy(self):
        c   = make_candidate(sharpe=1.8, win_rate=0.60, robustness=0.80, approval="approved")
        opp = make_market_opp(confidence=0.85, liquidity=0.80, strength=0.75)
        mr  = _make_match(c.strategy_id, opp.opportunity_id)
        sr  = _make_suit(c.strategy_id, opp.opportunity_id)
        rs  = _make_ranking(c.strategy_id, opp.opportunity_id)
        bundle = EvidenceCollector().collect(c, opp, mr, sr, rs)
        assert len(bundle.supporting) > 0

    def test_negative_evidence_for_poor_strategy(self):
        c   = make_candidate(sharpe=0.3, win_rate=0.35, robustness=0.25, approval="conditional")
        opp = make_market_opp(confidence=0.30, liquidity=0.25)
        mr  = _make_match(c.strategy_id, opp.opportunity_id, score=35.0)
        mr2 = MatchResult(
            strategy_id=c.strategy_id, opportunity_id=opp.opportunity_id,
            score=35.0, passed=False,
            dimension_scores={"regime": 20.0, "direction": 15.0, "liquidity": 10.0},
        )
        sr  = _make_suit(c.strategy_id, opp.opportunity_id, score=35.0)
        rs  = _make_ranking(c.strategy_id, opp.opportunity_id)
        bundle = EvidenceCollector().collect(c, opp, mr2, sr, rs)
        assert len(bundle.contradicting) > 0

    def test_net_confidence_bounded(self):
        c   = make_candidate()
        opp = make_market_opp()
        mr  = _make_match(c.strategy_id, opp.opportunity_id)
        sr  = _make_suit(c.strategy_id, opp.opportunity_id)
        rs  = _make_ranking(c.strategy_id, opp.opportunity_id)
        bundle = EvidenceCollector().collect(c, opp, mr, sr, rs)
        assert 0.0 <= bundle.net_confidence <= 1.0

    def test_company_opp_evidence(self):
        c   = make_candidate(approval="approved")
        opp = make_company_opp(fundamental=0.85, confidence=0.80)
        mr  = _make_match(c.strategy_id, opp.opportunity_id)
        sr  = _make_suit(c.strategy_id, opp.opportunity_id)
        rs  = _make_ranking(c.strategy_id, opp.opportunity_id)
        bundle = EvidenceCollector().collect(c, opp, mr, sr, rs)
        assert bundle is not None

    def test_to_dict_complete(self):
        c   = make_candidate()
        opp = make_market_opp()
        mr  = _make_match(c.strategy_id, opp.opportunity_id)
        sr  = _make_suit(c.strategy_id, opp.opportunity_id)
        rs  = _make_ranking(c.strategy_id, opp.opportunity_id)
        bundle = EvidenceCollector().collect(c, opp, mr, sr, rs)
        d = bundle.to_dict()
        assert "supporting" in d
        assert "net_confidence" in d


class TestReasonGenerator:
    def _bundle(self):
        from iios.investment.strategy.opportunity.evidence_collector import Evidence, EvidenceBundle
        return EvidenceBundle(
            strategy_id="s1",
            opportunity_id="o1",
            supporting=[
                Evidence("Strong Sharpe", "eval", 0.85, "positive"),
                Evidence("High liquidity", "mkt", 0.80, "positive"),
            ],
            contradicting=[
                Evidence("Low win rate", "eval", 0.75, "negative"),
            ],
            neutral=[
                Evidence("Conditional approval", "approval", 0.60, "neutral"),
            ],
        )

    def test_why_selected_not_empty(self):
        gen    = ReasonGenerator()
        bundle = self._bundle()
        reasons = gen.why_selected(bundle)
        assert len(reasons) >= 1

    def test_why_caution_not_empty(self):
        gen    = ReasonGenerator()
        bundle = self._bundle()
        cautions = gen.why_caution(bundle)
        assert len(cautions) >= 1

    def test_confidence_explanation_matches_level(self):
        gen    = ReasonGenerator()
        bundle = self._bundle()
        exp    = gen.confidence_explanation(bundle)
        assert isinstance(exp, str)
        assert len(exp) > 10

    def test_headline_contains_strategy_name(self):
        gen      = ReasonGenerator()
        headline = gen.generate_headline("MyStrategy", "trend_following", 1)
        assert "MyStrategy" in headline
        assert "1st" in headline


class TestRecommendationEngine:
    def test_generate_returns_summary(self):
        c   = make_candidate()
        opp = make_market_opp()
        mr  = _make_match(c.strategy_id, opp.opportunity_id)
        sr  = _make_suit(c.strategy_id, opp.opportunity_id)
        rs  = _make_ranking(c.strategy_id, opp.opportunity_id, rank=1)
        rec = RecommendationEngine().generate(c, opp, mr, sr, rs, overall_score=72.0)
        assert rec.strategy_id == c.strategy_id
        assert rec.rank == 1
        assert rec.overall_score == pytest.approx(72.0)

    def test_recommendation_has_explanation(self):
        c   = make_candidate()
        opp = make_market_opp()
        mr  = _make_match(c.strategy_id, opp.opportunity_id)
        sr  = _make_suit(c.strategy_id, opp.opportunity_id)
        rs  = _make_ranking(c.strategy_id, opp.opportunity_id)
        rec = RecommendationEngine().generate(c, opp, mr, sr, rs, overall_score=70.0)
        assert rec.headline != ""
        assert len(rec.why_selected) >= 0
        assert rec.confidence_explanation != ""

    def test_recommendation_risks_not_empty(self):
        c   = make_candidate(max_dd=0.25, robustness=0.35, approval="conditional")
        opp = make_market_opp()
        mr  = _make_match(c.strategy_id, opp.opportunity_id)
        sr  = _make_suit(c.strategy_id, opp.opportunity_id)
        rs  = _make_ranking(c.strategy_id, opp.opportunity_id)
        rec = RecommendationEngine().generate(c, opp, mr, sr, rs, overall_score=52.0)
        assert len(rec.expected_risks) > 0

    def test_to_dict_complete(self):
        c   = make_candidate()
        opp = make_market_opp()
        mr  = _make_match(c.strategy_id, opp.opportunity_id)
        sr  = _make_suit(c.strategy_id, opp.opportunity_id)
        rs  = _make_ranking(c.strategy_id, opp.opportunity_id)
        rec = RecommendationEngine().generate(c, opp, mr, sr, rs, overall_score=70.0)
        d   = rec.to_dict()
        for key in [
            "recommendation_id", "strategy_id", "opportunity_id",
            "overall_score", "rank", "headline", "why_selected",
            "caution_factors", "expected_risks",
        ]:
            assert key in d
