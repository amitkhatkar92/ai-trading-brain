"""tests/unit/investment/market/trend/test_trend_confidence.py
Tests for TrendConfidenceCalculator and TrendScorer.
"""
from __future__ import annotations

import pytest
from iios.investment.market.trend.trend_confidence import TrendConfidenceCalculator
from iios.investment.market.trend.trend_score import TrendScorer
from iios.investment.market.trend.models import (
    TrendStage,
    TrendQualityMetrics,
    TrendMomentumState,
    TrendScore,
    ImpulseQuality,
    CorrectionQuality,
    _default_quality,
    _default_momentum,
)
from tests.unit.investment.market.trend.conftest import make_trend_state


def _quality(overall: float = 70.0) -> TrendQualityMetrics:
    return TrendQualityMetrics(
        smoothness=0.7, reliability=0.7, efficiency=0.7,
        consistency=0.7, stability=0.7, persistence=0.7,
        overall=overall,
    )


def _momentum(is_accelerating: bool = False, is_decelerating: bool = False) -> TrendMomentumState:
    return TrendMomentumState(
        velocity=1.0, acceleration=0.0,
        impulse_quality=ImpulseQuality.MODERATE,
        correction_quality=CorrectionQuality.NORMAL,
        is_accelerating=is_accelerating,
        is_decelerating=is_decelerating,
        momentum_score=65.0,
    )


class TestTrendConfidenceCalculator:
    def setup_method(self):
        self.calc = TrendConfidenceCalculator()

    def test_result_in_range(self):
        trend = make_trend_state(confirmed=True, leg_count=3)
        conf = self.calc.calculate(
            trend, TrendStage.ESTABLISHED, _quality(), _momentum(),
            regime_aligned=True, structure_quality=75.0
        )
        assert 0.05 <= conf <= 0.97

    def test_established_aligned_high_confidence(self):
        trend = make_trend_state(confirmed=True, leg_count=3)
        conf = self.calc.calculate(
            trend, TrendStage.ESTABLISHED, _quality(80.0), _momentum(),
            regime_aligned=True, structure_quality=80.0
        )
        assert conf > 0.70

    def test_reversing_decelerating_low_confidence(self):
        # REVERSING + very low quality + unconfirmed + not aligned + decelerating → low confidence
        trend = make_trend_state(confirmed=False, leg_count=1, phase="reversal")
        conf = self.calc.calculate(
            trend, TrendStage.REVERSING, _quality(10.0), _momentum(is_decelerating=True),
            regime_aligned=False, structure_quality=10.0
        )
        assert conf < 0.40

    def test_continuation_probability_in_range(self):
        q = _quality()
        m = _momentum()
        p = self.calc.continuation_probability(TrendStage.ESTABLISHED, q, m, True)
        assert 0.05 <= p <= 0.92

    def test_failure_probability_in_range(self):
        m = _momentum()
        for stage in TrendStage:
            p = self.calc.failure_probability(stage, m)
            assert 0.02 <= p <= 0.98

    def test_reversal_probability_reversal_phase_high(self):
        p = self.calc.reversal_probability("reversal", TrendStage.REVERSING, 0.70)
        assert p > 0.75

    def test_expected_remaining_legs_established_above_2(self):
        legs = self.calc.expected_remaining_legs(TrendStage.ESTABLISHED, 3, _quality(70.0))
        assert legs > 2.0

    def test_expected_remaining_legs_completed_zero(self):
        legs = self.calc.expected_remaining_legs(TrendStage.COMPLETED, 10, _quality())
        assert legs == 0.0


class TestTrendScorer:
    def setup_method(self):
        self.scorer = TrendScorer()

    def test_returns_trend_score(self):
        result = self.scorer.score(_quality(), _momentum(), TrendStage.ESTABLISHED, True, 0.80)
        assert isinstance(result, TrendScore)

    def test_overall_in_range(self):
        result = self.scorer.score(_quality(), _momentum(), TrendStage.ESTABLISHED, True, 0.80)
        assert 0.0 <= result.overall <= 100.0

    def test_established_aligned_accelerating_high_score(self):
        result = self.scorer.score(
            _quality(80.0), _momentum(is_accelerating=True),
            TrendStage.ESTABLISHED, True, 0.90
        )
        assert result.overall > 65.0

    def test_aligned_regime_alignment_score_high(self):
        result = self.scorer.score(_quality(), _momentum(), TrendStage.ESTABLISHED, True, 0.80)
        assert result.regime_alignment_score >= 80.0

    def test_not_aligned_regime_alignment_score_lower(self):
        result_aligned = self.scorer.score(_quality(), _momentum(), TrendStage.ESTABLISHED, True, 0.80)
        result_not = self.scorer.score(_quality(), _momentum(), TrendStage.ESTABLISHED, False, 0.50)
        assert result_aligned.regime_alignment_score > result_not.regime_alignment_score
