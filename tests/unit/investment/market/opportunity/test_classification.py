"""tests/unit/investment/market/opportunity/test_classification.py"""
from __future__ import annotations

import pytest

from iios.investment.market.opportunity.classification_engine import ClassificationEngine
from iios.investment.market.opportunity.models import (
    AssetObservation,
    IntelligenceContext,
    OpportunityCategory,
)
from iios.investment.market.opportunity.opportunity_category import (
    BUILT_IN_RULES,
    CategoryRule,
    classify_context,
    matches_rule,
)
from iios.investment.market.opportunity.opportunity_classifier import classify_observation


class TestMatchesRule:
    def test_trend_following_match(self):
        ctx = IntelligenceContext(
            trend_strength=65.0, rs_vs_market=60.0, return_1bar=0.01,
            above_ma20_pct=0.6,
        )
        rule = next(r for r in BUILT_IN_RULES if r.category is OpportunityCategory.TREND_FOLLOWING)
        assert matches_rule(ctx, rule) is True

    def test_trend_following_no_match_low_rs(self):
        ctx = IntelligenceContext(trend_strength=65.0, rs_vs_market=40.0, return_1bar=0.01)
        rule = next(r for r in BUILT_IN_RULES if r.category is OpportunityCategory.TREND_FOLLOWING)
        assert matches_rule(ctx, rule) is False

    def test_momentum_positive_filter(self):
        ctx_up   = IntelligenceContext(trend_strength=60.0, rs_vs_market=65.0, return_1bar=0.02)
        ctx_down = IntelligenceContext(trend_strength=60.0, rs_vs_market=65.0, return_1bar=-0.02)
        rule = next(r for r in BUILT_IN_RULES if r.category is OpportunityCategory.TREND_FOLLOWING)
        assert matches_rule(ctx_up,   rule) is True
        assert matches_rule(ctx_down, rule) is False

    def test_retest_volume_max(self):
        """Retest requires LOW volume (≤1.2x)."""
        rule = next(r for r in BUILT_IN_RULES if r.category is OpportunityCategory.RETEST_CANDIDATE)
        ctx_low_vol  = IntelligenceContext(
            trend_strength=55.0, rs_vs_market=55.0, return_1bar=0.01,
            volume_ratio=1.0,
        )
        ctx_high_vol = IntelligenceContext(
            trend_strength=55.0, rs_vs_market=55.0, return_1bar=0.01,
            volume_ratio=2.0,
        )
        assert matches_rule(ctx_low_vol,  rule) is True
        assert matches_rule(ctx_high_vol, rule) is False

    def test_defensive_candidate_requires_low_vol(self):
        rule = next(r for r in BUILT_IN_RULES if r.category is OpportunityCategory.DEFENSIVE_CANDIDATE)
        ctx = IntelligenceContext(risk_score=70.0, volatility_percentile=0.3, above_ma20_pct=0.6)
        assert matches_rule(ctx, rule) is True
        ctx2 = IntelligenceContext(risk_score=70.0, volatility_percentile=0.9, above_ma20_pct=0.6)
        assert matches_rule(ctx2, rule) is False


class TestClassifyContext:
    def test_strong_trend_is_trend_following(self):
        ctx = IntelligenceContext(
            trend_strength=70.0, rs_vs_market=72.0, return_1bar=0.02,
            above_ma20_pct=0.65, volume_ratio=1.5,
        )
        primary, secondary = classify_context(ctx)
        assert primary is OpportunityCategory.TREND_FOLLOWING

    def test_weak_asset_not_trend_following(self):
        """A very weak asset should not be classified as a trend follower or breakout."""
        ctx = IntelligenceContext(
            trend_strength=20.0, rs_vs_market=20.0, return_1bar=-0.03,
            above_ma20_pct=0.2, volume_ratio=0.5,
        )
        primary, _ = classify_context(ctx)
        assert primary not in {
            OpportunityCategory.TREND_FOLLOWING,
            OpportunityCategory.BREAKOUT_CANDIDATE,
            OpportunityCategory.MOMENTUM_CANDIDATE,
        }

    def test_high_rs_category(self):
        ctx = IntelligenceContext(
            rs_vs_market=75.0, sector_rs_score=70.0, volume_ratio=1.2,
            return_1bar=0.01, trend_strength=55.0,
        )
        primary, _ = classify_context(ctx)
        assert primary is OpportunityCategory.HIGH_RS

    def test_secondary_categories_populated(self):
        ctx = IntelligenceContext(
            trend_strength=70.0, rs_vs_market=78.0, return_1bar=0.02,
            sector_rs_score=72.0, volume_ratio=1.8, above_ma20_pct=0.65,
        )
        _, secondary = classify_context(ctx)
        assert isinstance(secondary, list)

    def test_custom_rule_set(self):
        custom_rule = CategoryRule(
            category=OpportunityCategory.MOMENTUM_CANDIDATE,
            rs_vs_market_min=90.0,
        )
        ctx = IntelligenceContext(rs_vs_market=95.0, return_1bar=0.02)
        primary, _ = classify_context(ctx, [custom_rule])
        assert primary is OpportunityCategory.MOMENTUM_CANDIDATE


class TestClassifyObservation:
    def test_returns_opportunity(self, strong_obs):
        opp = classify_observation(strong_obs)
        assert opp is not None
        assert opp.symbol == "AAPL"
        assert 0 < opp.confidence <= 1.0

    def test_weak_asset_is_observation_only(self, weak_obs):
        opp = classify_observation(weak_obs)
        assert opp is not None   # always returns something
        assert opp.primary_category is OpportunityCategory.OBSERVATION_ONLY

    def test_strong_asset_has_high_priority_score(self, strong_obs):
        opp = classify_observation(strong_obs)
        assert opp is not None
        assert opp.composite_score > 40.0

    def test_category_correct(self, make_obs):
        obs = make_obs(trend=75.0, rs=80.0, vol_ratio=2.0, ret1=0.03)
        opp = classify_observation(obs)
        assert opp is not None
        assert opp.primary_category in {
            OpportunityCategory.TREND_FOLLOWING,
            OpportunityCategory.HIGH_RS,
            OpportunityCategory.BREAKOUT_CANDIDATE,
            OpportunityCategory.MOMENTUM_CANDIDATE,
        }

    def test_sector_stored(self, make_obs):
        obs = make_obs(symbol="JNJ", sector="Health Care")
        opp = classify_observation(obs)
        assert opp is not None
        assert opp.sector == "Health Care"


class TestClassificationEngine:
    def test_classify_batch_all_symbols(self, obs_batch):
        engine = ClassificationEngine()
        result = engine.classify_batch(obs_batch)
        assert len(result) == len(obs_batch)

    def test_pluggable_rules(self, obs_batch):
        custom_rule = CategoryRule(
            category=OpportunityCategory.HIGH_RS,
            rs_vs_market_min=0.0,   # match everything
        )
        engine = ClassificationEngine([custom_rule])
        result = engine.classify_batch(obs_batch)
        for opp in result.values():
            # Every asset matches HIGH_RS because min=0
            assert opp.primary_category is OpportunityCategory.HIGH_RS

    def test_add_rule(self, obs_batch):
        engine = ClassificationEngine()
        initial_len = len(engine.rules)
        engine.add_rule(CategoryRule(
            category=OpportunityCategory.OBSERVATION_ONLY,
        ))
        assert len(engine.rules) == initial_len + 1

    def test_error_resilience(self):
        """Malformed observations should not crash the engine."""
        engine = ClassificationEngine()
        bad_obs = AssetObservation(
            symbol="BAD", sector="", industry="", bar_index=0, timestamp=0.0
        )
        result = engine.classify_batch([bad_obs])
        assert "BAD" in result
