"""tests/unit/investment/market/trend/test_trend_quality.py
Tests for TrendQualityAnalyzer, TrendStrengthCalculator,
TrendStabilityCalculator, TrendPersistenceCalculator.
"""
from __future__ import annotations

import pytest
from iios.investment.market.trend.trend_quality import TrendQualityAnalyzer
from iios.investment.market.trend.trend_strength import TrendStrengthCalculator
from iios.investment.market.trend.trend_stability import TrendStabilityCalculator
from iios.investment.market.trend.trend_persistence import TrendPersistenceCalculator
from iios.investment.market.trend.models import (
    TrendStage,
    TrendQualityMetrics,
    TrendLegMetrics,
    ImpulseQuality,
    CorrectionQuality,
    _default_quality,
)
from iios.investment.market.market_constants import TrendDirection, MarketStrength
from tests.unit.investment.market.trend.conftest import (
    make_legs,
    make_trend_state,
)


class TestTrendQualityAnalyzer:
    def setup_method(self):
        self.analyzer = TrendQualityAnalyzer()

    def test_returns_trend_quality_metrics(self):
        legs = make_legs(4)
        result = self.analyzer.analyze(legs, 72.0, 0.35)
        assert isinstance(result, TrendQualityMetrics)

    def test_all_fields_in_valid_range(self):
        legs = make_legs(4)
        q = self.analyzer.analyze(legs, 72.0, 0.35)
        for attr in ("smoothness", "reliability", "efficiency", "consistency", "stability", "persistence"):
            val = getattr(q, attr)
            assert 0.0 <= val <= 1.0, f"{attr}={val} out of range"
        assert 0.0 <= q.overall <= 100.0

    def test_grade_property_correct(self):
        q = TrendQualityMetrics(0.9, 0.9, 0.9, 0.9, 0.9, 0.9, overall=85.0)
        assert q.grade == "A"
        q2 = TrendQualityMetrics(0.3, 0.3, 0.3, 0.3, 0.3, 0.3, overall=25.0)
        assert q2.grade == "F"

    def test_empty_legs_graceful_fallback(self):
        q = self.analyzer.analyze([], 50.0, 0.4)
        assert isinstance(q, TrendQualityMetrics)
        assert 0.0 <= q.overall <= 100.0

    def test_perfect_legs_high_quality(self):
        # Consistent impulse legs with shallow corrections → high quality
        legs = []
        for i in range(6):
            legs.append(TrendLegMetrics(
                leg_number=i + 1,
                is_impulse=(i % 2 == 0),
                direction=TrendDirection.UP,
                displacement=10.0,
                bars=5,
                velocity=2.0,
                retracement_pct=0.30,
                impulse_quality=ImpulseQuality.STRONG,
                correction_quality=CorrectionQuality.SHALLOW,
            ))
        q = self.analyzer.analyze(legs, 90.0, 0.25, regime_stability=0.85)
        assert q.overall >= 60.0

    def test_failed_corrections_lower_quality(self):
        legs = []
        for i in range(4):
            legs.append(TrendLegMetrics(
                leg_number=i + 1,
                is_impulse=(i % 2 == 0),
                direction=TrendDirection.UP,
                displacement=10.0 if i % 2 == 0 else 12.0,  # corrections > impulse
                bars=5,
                velocity=2.0,
                retracement_pct=1.2,
                impulse_quality=ImpulseQuality.WEAK,
                correction_quality=CorrectionQuality.FAILED,
            ))
        q_bad = self.analyzer.analyze(legs, 30.0, 0.90, regime_stability=0.2)
        q_good = self.analyzer.analyze(make_legs(4), 85.0, 0.30, regime_stability=0.8)
        assert q_good.overall > q_bad.overall


class TestTrendStrengthCalculator:
    def setup_method(self):
        self.calc = TrendStrengthCalculator()

    def test_very_strong_strength_returns_high_score(self):
        trend = make_trend_state(strength="very_strong", confirmed=True, leg_count=5)
        legs = make_legs(4)
        score = self.calc.calculate(trend, legs)
        assert score >= 95.0

    def test_score_in_range(self):
        for strength in ("very_strong", "strong", "moderate", "weak", "very_weak", "neutral"):
            trend = make_trend_state(strength=strength)
            score = self.calc.calculate(trend, make_legs(2))
            assert 0.0 <= score <= 100.0

    def test_confirmed_adds_bonus(self):
        trend_confirmed = make_trend_state(confirmed=True, strength="moderate")
        trend_not = make_trend_state(confirmed=False, strength="moderate")
        legs = make_legs(2)
        assert self.calc.calculate(trend_confirmed, legs) > self.calc.calculate(trend_not, legs)


class TestTrendStabilityCalculator:
    def setup_method(self):
        self.calc = TrendStabilityCalculator()

    def test_deep_correction_lowers_stability(self):
        legs_shallow = make_legs(4)
        s_shallow = self.calc.calculate(legs_shallow, correction_depth=0.20, quality_score=70.0)
        s_deep = self.calc.calculate(legs_shallow, correction_depth=0.90, quality_score=70.0)
        assert s_shallow > s_deep

    def test_result_in_valid_range(self):
        legs = make_legs(4)
        s = self.calc.calculate(legs, 0.5, 60.0)
        assert 0.1 <= s <= 0.95

    def test_failed_corrections_reduce_stability(self):
        legs_normal = make_legs(4)
        legs_failed = [
            TrendLegMetrics(
                leg_number=i + 1, is_impulse=(i % 2 == 0),
                direction=TrendDirection.UP, displacement=5.0,
                bars=5, velocity=1.0, retracement_pct=1.2,
                impulse_quality=ImpulseQuality.WEAK,
                correction_quality=CorrectionQuality.FAILED,
            )
            for i in range(4)
        ]
        s_normal = self.calc.calculate(legs_normal, 0.3, 70.0)
        s_failed = self.calc.calculate(legs_failed, 0.3, 70.0)
        assert s_normal > s_failed


class TestTrendPersistenceCalculator:
    def setup_method(self):
        self.calc = TrendPersistenceCalculator()

    def test_failing_stage_near_base_probability(self):
        q = _default_quality()
        p = self.calc.calculate(TrendStage.FAILING, q, False, False, False)
        # Base is 0.25, with no regime alignment (-0.08) → ~0.17, clamped to 0.05+
        assert p <= 0.30
        assert p >= 0.05

    def test_established_aligned_higher_than_reversing(self):
        q = _default_quality()
        p_est = self.calc.calculate(TrendStage.ESTABLISHED, q, True, False, False)
        p_rev = self.calc.calculate(TrendStage.REVERSING, q, False, False, False)
        assert p_est > p_rev

    def test_result_in_valid_range(self):
        q = _default_quality()
        for stage in TrendStage:
            p = self.calc.calculate(stage, q, True, False, False)
            assert 0.05 <= p <= 0.95
