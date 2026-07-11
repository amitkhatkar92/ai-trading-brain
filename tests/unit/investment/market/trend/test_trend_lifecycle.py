"""tests/unit/investment/market/trend/test_trend_lifecycle.py
Tests for TrendLifecycleDetector and TrendTransitionDetector.
"""
from __future__ import annotations

import pytest
from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.trend.trend_lifecycle import TrendLifecycleDetector
from iios.investment.market.trend.trend_transition import TrendTransitionDetector
from iios.investment.market.trend.models import (
    TrendStage,
    TrendEventType,
    TrendTransitionType,
    TrendMomentumState,
    ImpulseQuality,
    CorrectionQuality,
    _default_momentum,
)
from tests.unit.investment.market.trend.conftest import make_trend_state, make_legs


def _default_momentum_state(**kwargs) -> TrendMomentumState:
    m = _default_momentum()
    for k, v in kwargs.items():
        object.__setattr__(m, k, v)
    # TrendMomentumState is a plain dataclass, not frozen
    d = m.__dict__.copy()
    d.update(kwargs)
    return TrendMomentumState(**d)


class TestTrendLifecycleDetector:
    def setup_method(self):
        self.detector = TrendLifecycleDetector()

    def _momentum(self, **kw) -> TrendMomentumState:
        base = TrendMomentumState(
            velocity=1.0, acceleration=0.0,
            impulse_quality=kw.get("impulse_quality", ImpulseQuality.MODERATE),
            correction_quality=kw.get("correction_quality", CorrectionQuality.NORMAL),
            is_accelerating=kw.get("is_accelerating", False),
            is_decelerating=kw.get("is_decelerating", False),
            momentum_score=kw.get("momentum_score", 55.0),
        )
        return base

    def test_reversing_stage_when_reversal_phase(self):
        trend = make_trend_state(phase="reversal", confirmed=True, leg_count=3)
        legs = make_legs(4)
        mom = self._momentum()
        stage, conf = self.detector.detect(trend, legs, mom)
        assert stage == TrendStage.REVERSING
        assert 0 < conf <= 1.0

    def test_established_for_confirmed_4_legs(self):
        trend = make_trend_state(confirmed=True, leg_count=4, phase="impulse")
        legs = make_legs(4)
        mom = self._momentum()
        stage, conf = self.detector.detect(trend, legs, mom)
        assert stage == TrendStage.ESTABLISHED

    def test_mature_for_confirmed_6_legs(self):
        trend = make_trend_state(confirmed=True, leg_count=6, phase="continuation")
        legs = make_legs(6)
        mom = self._momentum()
        stage, conf = self.detector.detect(trend, legs, mom)
        assert stage == TrendStage.MATURE

    def test_emerging_for_unconfirmed_trend(self):
        trend = make_trend_state(confirmed=False, leg_count=0)
        legs = []
        mom = self._momentum()
        stage, conf = self.detector.detect(trend, legs, mom)
        assert stage == TrendStage.EMERGING

    def test_exhausting_decelerating_deep_correction(self):
        trend = make_trend_state(confirmed=True, leg_count=5, correction_depth=0.65)
        legs = make_legs(5)
        mom = self._momentum(is_decelerating=True)
        stage, conf = self.detector.detect(trend, legs, mom)
        assert stage == TrendStage.EXHAUSTING

    def test_failing_exhaustion_weak_impulse(self):
        from iios.investment.market.trend.models import TrendLegMetrics
        trend = make_trend_state(confirmed=True, leg_count=4, phase="exhaustion")
        legs = make_legs(4)
        # Replace last impulse with WEAK
        for i, l in enumerate(legs):
            if l.is_impulse:
                legs[i] = TrendLegMetrics(
                    leg_number=l.leg_number, is_impulse=True,
                    direction=TrendDirection.UP,
                    displacement=l.displacement, bars=l.bars,
                    velocity=l.velocity, retracement_pct=l.retracement_pct,
                    impulse_quality=ImpulseQuality.WEAK,
                    correction_quality=l.correction_quality,
                )
        mom = self._momentum(impulse_quality=ImpulseQuality.WEAK)
        stage, conf = self.detector.detect(trend, legs, mom)
        assert stage in (TrendStage.FAILING, TrendStage.EXHAUSTING)

    def test_stage_confidence_in_range(self):
        trend = make_trend_state(confirmed=True, leg_count=3)
        _, conf = self.detector.detect(trend, make_legs(3), self._momentum())
        assert 0 < conf <= 1.0

    def test_detect_event_emerging_to_developing(self):
        trend = make_trend_state()
        event = self.detector.detect_event(TrendStage.EMERGING, TrendStage.DEVELOPING, trend)
        assert event == TrendEventType.TREND_START

    def test_detect_event_exhausting_to_failing(self):
        trend = make_trend_state()
        event = self.detector.detect_event(TrendStage.EXHAUSTING, TrendStage.FAILING, trend)
        assert event == TrendEventType.TREND_WEAKENING

    def test_detect_event_no_change_returns_none(self):
        trend = make_trend_state()
        event = self.detector.detect_event(TrendStage.ESTABLISHED, TrendStage.ESTABLISHED, trend)
        assert event is None


class TestTrendTransitionDetector:
    def setup_method(self):
        self.detector = TrendTransitionDetector()

    def test_returns_none_when_stage_and_direction_unchanged(self):
        rec = self.detector.detect(
            prev_stage=TrendStage.ESTABLISHED,
            new_stage=TrendStage.ESTABLISHED,
            prev_direction=TrendDirection.UP,
            new_direction=TrendDirection.UP,
            confidence=0.80,
            bar_index=10,
            symbol="TEST",
            timeframe="1d",
        )
        assert rec is None

    def test_returns_stage_advance_for_forward_progress(self):
        rec = self.detector.detect(
            prev_stage=TrendStage.DEVELOPING,
            new_stage=TrendStage.ESTABLISHED,
            prev_direction=TrendDirection.UP,
            new_direction=TrendDirection.UP,
            confidence=0.80,
            bar_index=20,
            symbol="TEST",
            timeframe="1d",
        )
        assert rec is not None
        assert rec.transition_type == TrendTransitionType.STAGE_ADVANCE

    def test_returns_reversal_for_direction_change(self):
        rec = self.detector.detect(
            prev_stage=TrendStage.ESTABLISHED,
            new_stage=TrendStage.REVERSING,
            prev_direction=TrendDirection.UP,
            new_direction=TrendDirection.DOWN,
            confidence=0.70,
            bar_index=30,
            symbol="TEST",
            timeframe="1d",
        )
        assert rec is not None
        assert rec.transition_type == TrendTransitionType.REVERSAL

    def test_returns_stage_decline_for_backward_progress(self):
        rec = self.detector.detect(
            prev_stage=TrendStage.EXHAUSTING,
            new_stage=TrendStage.ESTABLISHED,
            prev_direction=TrendDirection.UP,
            new_direction=TrendDirection.UP,
            confidence=0.70,
            bar_index=40,
            symbol="TEST",
            timeframe="1d",
        )
        assert rec is not None
        assert rec.transition_type == TrendTransitionType.STAGE_DECLINE
