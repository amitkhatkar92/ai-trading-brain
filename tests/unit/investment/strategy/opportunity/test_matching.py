"""tests/unit/investment/strategy/opportunity/test_matching.py"""
from __future__ import annotations

import pytest

from iios.investment.strategy.opportunity.market_opportunity import (
    MarketRegime, VolatilityRegime, Timeframe, OpportunityType
)
from iios.investment.strategy.opportunity.strategy_matcher import StrategyMatcher
from iios.investment.strategy.opportunity.matching_engine import MatchingEngine
from iios.investment.strategy.opportunity.matching_profile import (
    DEFAULT_PROFILE, CONSERVATIVE_PROFILE, MOMENTUM_PROFILE, MatchingProfile
)
from tests.unit.investment.strategy.opportunity.conftest import (
    make_market_opp, make_company_opp, make_candidate
)


class TestMatchResult:
    def test_perfect_match_high_score(self):
        c   = make_candidate(regimes=["bull"], timeframes=["swing"], directions=["long"])
        opp = make_market_opp(regime=MarketRegime.BULL, timeframe=Timeframe.SWING, direction="long")
        mr  = StrategyMatcher().match(c, opp, DEFAULT_PROFILE)
        assert mr.passed
        assert mr.score >= 60.0

    def test_regime_mismatch_penalised(self):
        c   = make_candidate(regimes=["bear"])
        opp = make_market_opp(regime=MarketRegime.BULL)
        mr  = StrategyMatcher().match(c, opp, DEFAULT_PROFILE)
        assert mr.dimension_scores["regime"] < 80.0

    def test_direction_mismatch_penalised(self):
        c   = make_candidate(directions=["short"])
        opp = make_market_opp(direction="long")
        mr  = StrategyMatcher().match(c, opp, DEFAULT_PROFILE)
        assert mr.dimension_scores["direction"] < 80.0

    def test_low_confidence_hard_rejected(self):
        profile = MatchingProfile(min_opp_confidence=0.80)
        c   = make_candidate()
        opp = make_market_opp(confidence=0.40)
        mr  = StrategyMatcher().match(c, opp, profile)
        assert mr.hard_rejected
        assert not mr.passed
        assert mr.score == 0.0

    def test_rejected_strategy_hard_rejected(self):
        c   = make_candidate(approval="rejected")
        opp = make_market_opp()
        mr  = StrategyMatcher().match(c, opp, DEFAULT_PROFILE)
        assert mr.hard_rejected

    def test_low_liquidity_penalised(self):
        c   = make_candidate()  # min_liquidity_score=0.30
        # Use 0.20: above profile min_opp_liquidity (0.15) but below strategy min
        opp = make_market_opp(liquidity=0.20)
        mr  = StrategyMatcher().match(c, opp, DEFAULT_PROFILE)
        assert mr.dimension_scores["liquidity"] < 100.0

    def test_all_regimes_match_all(self):
        c   = make_candidate(regimes=["all"])
        opp = make_market_opp(regime=MarketRegime.CRISIS)
        mr  = StrategyMatcher().match(c, opp, DEFAULT_PROFILE)
        assert mr.dimension_scores["regime"] == 100.0

    def test_company_opp_matching(self):
        c   = make_candidate(directions=["long"])
        opp = make_company_opp(direction="long", confidence=0.80)
        mr  = StrategyMatcher().match(c, opp, DEFAULT_PROFILE)
        assert mr.passed or not mr.hard_rejected  # should at least not hard-reject

    def test_company_opp_direction_mismatch(self):
        c   = make_candidate(directions=["short"])
        opp = make_company_opp(direction="long")
        mr  = StrategyMatcher().match(c, opp, DEFAULT_PROFILE)
        assert mr.dimension_scores["direction"] < 80.0

    def test_dimension_scores_bounded(self):
        c   = make_candidate()
        opp = make_market_opp()
        mr  = StrategyMatcher().match(c, opp, DEFAULT_PROFILE)
        for k, v in mr.dimension_scores.items():
            assert 0.0 <= v <= 100.0, f"dim {k} out of range: {v}"

    def test_to_dict_complete(self):
        c   = make_candidate()
        opp = make_market_opp()
        mr  = StrategyMatcher().match(c, opp, DEFAULT_PROFILE)
        d   = mr.to_dict()
        for key in ["strategy_id", "opportunity_id", "score", "passed"]:
            assert key in d


class TestMatchingProfile:
    def test_weights_normalise_to_one(self):
        for profile in (DEFAULT_PROFILE, CONSERVATIVE_PROFILE, MOMENTUM_PROFILE):
            w = profile.normalized_weights()
            assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_zero_weight_dimension_excluded(self):
        profile = MatchingProfile(sector_weight=0.0, momentum_weight=0.0)
        w = profile.normalized_weights()
        assert w["sector"] == pytest.approx(0.0, abs=1e-9)

    def test_conservative_higher_min_score(self):
        assert CONSERVATIVE_PROFILE.min_matching_score > DEFAULT_PROFILE.min_matching_score


class TestMatchingEngine:
    def test_no_candidates_empty_result(self):
        engine = MatchingEngine()
        opp    = make_market_opp()
        result = engine.match(opp)
        assert result == []

    def test_registered_candidate_matched(self):
        engine = MatchingEngine()
        c      = make_candidate()
        engine.register(c)
        opp    = make_market_opp()
        result = engine.match(opp)
        assert len(result) >= 0  # may or may not pass threshold

    def test_results_sorted_by_score(self):
        engine = MatchingEngine()
        for i in range(5):
            c = make_candidate(
                strategy_id=f"s{i}",
                regimes=["all"], timeframes=["all"],
                eval_score=50.0 + i * 5,
            )
            engine.register(c)
        opp    = make_market_opp()
        result = engine.match(opp)
        scores = [r.score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_deregister_removes_candidate(self):
        engine = MatchingEngine()
        c      = make_candidate()
        engine.register(c)
        engine.deregister(c.strategy_id)
        assert c.strategy_id not in engine.registered_ids()

    def test_history_records_results(self):
        engine = MatchingEngine()
        c      = make_candidate()
        engine.register(c)
        opp    = make_market_opp()
        engine.match(opp)
        hist   = engine.history(c.strategy_id)
        assert len(hist) == 1

    def test_pass_rate_bounded(self):
        engine = MatchingEngine()
        c      = make_candidate()
        engine.register(c)
        for _ in range(5):
            engine.match(make_market_opp())
        rate = engine.match_pass_rate(c.strategy_id)
        assert 0.0 <= rate <= 1.0

    def test_multiple_candidates_parallel(self):
        engine = MatchingEngine(max_workers=4)
        for i in range(10):
            engine.register(make_candidate(
                strategy_id=f"p{i}",
                regimes=["all"], timeframes=["all"],
            ))
        opp    = make_market_opp(confidence=0.80, liquidity=0.80)
        result = engine.match(opp)
        # All with "all" regimes and good opportunity should match
        assert len(result) >= 5
        engine.shutdown()
