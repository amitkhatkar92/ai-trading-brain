"""tests/unit/investment/market/trend/test_trend_momentum.py
Tests for TrendMomentumAnalyzer, TrendVelocityCalculator,
TrendAccelerationAnalyzer, TrendDecelerationDetector.
"""
from __future__ import annotations

import pytest
from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.trend.trend_momentum import TrendMomentumAnalyzer
from iios.investment.market.trend.trend_velocity import TrendVelocityCalculator
from iios.investment.market.trend.trend_acceleration import TrendAccelerationAnalyzer
from iios.investment.market.trend.trend_deceleration import TrendDecelerationDetector
from iios.investment.market.trend.models import (
    TrendMomentumState,
    TrendLegMetrics,
    ImpulseQuality,
    CorrectionQuality,
)
from tests.unit.investment.market.trend.conftest import make_legs


def _make_impulse_leg(velocity: float, displacement: float = None) -> TrendLegMetrics:
    d = displacement if displacement is not None else velocity * 5
    return TrendLegMetrics(
        leg_number=1, is_impulse=True,
        direction=TrendDirection.UP,
        displacement=d, bars=5,
        velocity=velocity, retracement_pct=0.35,
        impulse_quality=ImpulseQuality.MODERATE,
        correction_quality=CorrectionQuality.NORMAL,
    )


class TestTrendMomentumAnalyzer:
    def setup_method(self):
        self.analyzer = TrendMomentumAnalyzer()

    def test_analyze_returns_momentum_state(self):
        legs = make_legs(4)
        result = self.analyzer.analyze(legs, TrendDirection.UP, "impulse", 0.35)
        assert isinstance(result, TrendMomentumState)

    def test_momentum_score_in_range(self):
        legs = make_legs(4)
        state = self.analyzer.analyze(legs, TrendDirection.UP, "impulse", 0.30)
        assert 0.0 <= state.momentum_score <= 100.0

    def test_accelerating_and_decelerating_not_both_true_for_strong_accel(self):
        """A strongly accelerating trend cannot also be decelerating."""
        legs = [
            _make_impulse_leg(velocity=1.0),
            TrendLegMetrics(
                leg_number=2, is_impulse=False,
                direction=TrendDirection.UP,
                displacement=3.0, bars=3,
                velocity=1.0, retracement_pct=0.30,
                impulse_quality=ImpulseQuality.MODERATE,
                correction_quality=CorrectionQuality.SHALLOW,
            ),
            _make_impulse_leg(velocity=3.0),  # much faster = strongly accelerating
        ]
        state = self.analyzer.analyze(legs, TrendDirection.UP, "acceleration", 0.20)
        if state.is_accelerating and state.is_decelerating:
            # Both can't be logically true for large positive acceleration
            pytest.fail("is_accelerating and is_decelerating are both True")

    def test_velocity_positive_for_uptrend(self):
        legs = make_legs(4)
        state = self.analyzer.analyze(legs, TrendDirection.UP, "impulse", 0.30)
        assert state.velocity >= 0.0

    def test_acceleration_detected_correctly(self):
        """Leg 2 velocity > leg 1 velocity → should be accelerating."""
        legs = [
            _make_impulse_leg(velocity=1.0, displacement=5.0),
            TrendLegMetrics(
                leg_number=2, is_impulse=False,
                direction=TrendDirection.UP,
                displacement=2.0, bars=5,
                velocity=0.4, retracement_pct=0.35,
                impulse_quality=ImpulseQuality.MODERATE,
                correction_quality=CorrectionQuality.NORMAL,
            ),
            _make_impulse_leg(velocity=2.0, displacement=10.0),
        ]
        state = self.analyzer.analyze(legs, TrendDirection.UP, "impulse", 0.30)
        assert state.is_accelerating

    def test_deceleration_detected_correctly(self):
        """Exhaustion phase + deep correction → deceleration."""
        legs = [
            _make_impulse_leg(velocity=2.0, displacement=10.0),
            TrendLegMetrics(
                leg_number=2, is_impulse=False,
                direction=TrendDirection.UP,
                displacement=7.0, bars=5,
                velocity=1.4, retracement_pct=0.70,
                impulse_quality=ImpulseQuality.WEAK,
                correction_quality=CorrectionQuality.DEEP,
            ),
            _make_impulse_leg(velocity=0.5, displacement=2.5),
        ]
        state = self.analyzer.analyze(legs, TrendDirection.UP, "exhaustion", 0.72)
        assert state.is_decelerating


class TestTrendVelocityCalculator:
    def setup_method(self):
        self.calc = TrendVelocityCalculator()

    def test_returns_zero_for_empty_legs(self):
        assert self.calc.calculate_current([], TrendDirection.UP) == 0.0

    def test_positive_velocity_for_uptrend(self):
        legs = [_make_impulse_leg(velocity=1.5)]
        v = self.calc.calculate_current(legs, TrendDirection.UP)
        assert v > 0

    def test_negative_velocity_for_downtrend(self):
        leg = TrendLegMetrics(
            leg_number=1, is_impulse=True,
            direction=TrendDirection.DOWN,
            displacement=5.0, bars=5,
            velocity=1.0, retracement_pct=0.35,
            impulse_quality=ImpulseQuality.MODERATE,
            correction_quality=CorrectionQuality.NORMAL,
        )
        v = self.calc.calculate_current([leg], TrendDirection.DOWN)
        assert v < 0

    def test_avg_velocity_unsigned(self):
        legs = [_make_impulse_leg(velocity=float(i + 1)) for i in range(4)]
        avg = self.calc.calculate_avg(legs, n=3)
        assert avg > 0


class TestTrendAccelerationAnalyzer:
    def setup_method(self):
        self.analyzer = TrendAccelerationAnalyzer()

    def test_fewer_than_2_impulse_legs_returns_no_accel(self):
        accel, is_accel, is_decel = self.analyzer.analyze([_make_impulse_leg(1.0)])
        assert accel == 0.0
        assert not is_accel
        assert not is_decel

    def test_acceleration_detected(self):
        legs = [
            _make_impulse_leg(velocity=1.0),
            _make_impulse_leg(velocity=2.0),
        ]
        accel, is_accel, _ = self.analyzer.analyze(legs)
        assert accel > 0
        assert is_accel

    def test_deceleration_detected(self):
        legs = [
            _make_impulse_leg(velocity=2.0),
            _make_impulse_leg(velocity=0.5),
        ]
        accel, _, is_decel = self.analyzer.analyze(legs)
        assert accel < 0
        assert is_decel


class TestTrendDecelerationDetector:
    def setup_method(self):
        self.detector = TrendDecelerationDetector()

    def test_healthy_legs_not_decelerating(self):
        legs = [_make_impulse_leg(velocity=float(i + 1)) for i in range(3)]
        is_decel, conf = self.detector.detect(legs, "impulse", 0.30)
        assert not is_decel
        assert conf < 0.40

    def test_exhaustion_deep_correction_is_decelerating(self):
        legs = [
            _make_impulse_leg(velocity=2.0),
            TrendLegMetrics(
                leg_number=2, is_impulse=False,
                direction=TrendDirection.UP,
                displacement=7.0, bars=5,
                velocity=1.4, retracement_pct=0.72,
                impulse_quality=ImpulseQuality.WEAK,
                correction_quality=CorrectionQuality.DEEP,
            ),
            TrendLegMetrics(
                leg_number=3, is_impulse=True,
                direction=TrendDirection.UP,
                displacement=3.0, bars=8,
                velocity=0.375, retracement_pct=0.0,
                impulse_quality=ImpulseQuality.WEAK,
                correction_quality=CorrectionQuality.DEEP,
            ),
        ]
        is_decel, conf = self.detector.detect(legs, "exhaustion", 0.72)
        assert is_decel
        assert conf >= 0.40
