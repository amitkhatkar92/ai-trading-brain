"""tests/unit/investment/market/regime/test_transition_detector.py"""
from __future__ import annotations

import pytest

from iios.investment.market.market_constants import TrendDirection, VolatilityLevel
from iios.investment.market.regime.models import (
    RegimeObservation,
    RegimeType,
    TransitionEvent,
    TransitionType,
)
from iios.investment.market.regime.transition_detector import TransitionDetector

from tests.unit.investment.market.regime.conftest import make_observation


@pytest.fixture
def detector() -> TransitionDetector:
    return TransitionDetector()


class TestReturnNoneWhenNoPrev:
    def test_returns_none_when_prev_is_none(self, detector):
        obs = make_observation()
        result = detector.detect(obs, None, RegimeType.BULL, 10)
        assert result is None


class TestEmergingTrend:
    def test_detects_emerging_trend_bullish(self, detector):
        prev = make_observation(in_consol=True, consol_bars=15, has_breakout=False)
        curr = make_observation(in_consol=False, has_breakout=True, breakout_bullish=True)
        result = detector.detect(curr, prev, RegimeType.RANGING, 20)
        assert result is not None
        assert result.transition_type == TransitionType.EMERGING_TREND
        assert result.to_regime == RegimeType.BULL

    def test_detects_emerging_trend_bearish(self, detector):
        prev = make_observation(in_consol=True, consol_bars=15, has_breakout=False)
        curr = make_observation(in_consol=False, has_breakout=True, breakout_bullish=False)
        result = detector.detect(curr, prev, RegimeType.RANGING, 20)
        assert result is not None
        assert result.transition_type == TransitionType.EMERGING_TREND
        assert result.to_regime == RegimeType.BEAR

    def test_no_emerging_trend_without_breakout(self, detector):
        prev = make_observation(in_consol=True)
        curr = make_observation(in_consol=False, has_breakout=False)
        result = detector.detect(curr, prev, RegimeType.RANGING, 5)
        # Should not detect EMERGING_TREND
        if result:
            assert result.transition_type != TransitionType.EMERGING_TREND


class TestTrendFailure:
    def test_detects_bull_failure_to_distribution(self, detector):
        prev = make_observation(trend_dir=TrendDirection.UP, trend_phase="impulse")
        curr = make_observation(
            trend_dir=TrendDirection.UP,
            trend_phase="exhaustion",
            phase="distribution",
        )
        result = detector.detect(curr, prev, RegimeType.BULL, 25)
        assert result is not None
        assert result.transition_type == TransitionType.TREND_FAILURE
        assert result.to_regime == RegimeType.DISTRIBUTION

    def test_detects_bear_failure_to_accumulation(self, detector):
        prev = make_observation(trend_dir=TrendDirection.DOWN, trend_phase="impulse")
        curr = make_observation(
            trend_dir=TrendDirection.DOWN,
            trend_phase="correction",
            phase="accumulation",
        )
        result = detector.detect(curr, prev, RegimeType.BEAR, 25)
        assert result is not None
        assert result.transition_type == TransitionType.TREND_FAILURE
        assert result.to_regime == RegimeType.ACCUMULATION


class TestReversal:
    def test_detects_reversal_from_bull(self, detector):
        prev = make_observation(trend_phase="impulse")
        curr = make_observation(trend_phase="reversal")
        result = detector.detect(curr, prev, RegimeType.BULL, 15)
        assert result is not None
        assert result.transition_type == TransitionType.REVERSAL
        assert result.to_regime == RegimeType.BEAR

    def test_detects_reversal_from_bear(self, detector):
        prev = make_observation(trend_phase="impulse")
        curr = make_observation(trend_phase="reversal")
        result = detector.detect(curr, prev, RegimeType.BEAR, 15)
        assert result is not None
        assert result.transition_type == TransitionType.REVERSAL
        assert result.to_regime == RegimeType.BULL


class TestVolatilityExpansion:
    def test_detects_vol_expansion(self, detector):
        prev = make_observation(vol=VolatilityLevel.LOW)   # severity 1
        curr = make_observation(vol=VolatilityLevel.EXTREME)  # severity 4
        result = detector.detect(curr, prev, RegimeType.BULL, 5)
        assert result is not None
        assert result.transition_type == TransitionType.VOLATILITY_EXPANSION
        assert result.to_regime == RegimeType.VOLATILE

    def test_no_vol_expansion_for_small_jump(self, detector):
        prev = make_observation(vol=VolatilityLevel.LOW)     # 1
        curr = make_observation(vol=VolatilityLevel.MODERATE)  # 2 (jump=1)
        result = detector.detect(curr, prev, RegimeType.BULL, 5)
        if result:
            assert result.transition_type != TransitionType.VOLATILITY_EXPANSION


class TestVolatilityCompression:
    def test_detects_vol_compression(self, detector):
        prev = make_observation(vol=VolatilityLevel.EXTREME)  # 4
        curr = make_observation(vol=VolatilityLevel.LOW)       # 1
        result = detector.detect(curr, prev, RegimeType.VOLATILE, 5)
        assert result is not None
        assert result.transition_type == TransitionType.VOLATILITY_COMPRESSION
        assert result.to_regime == RegimeType.CALM


class TestRegimePersistence:
    def test_detects_persistence_after_50_bars(self, detector):
        obs = make_observation(
            trend_dir=TrendDirection.UP,
            vol=VolatilityLevel.MODERATE,
            in_consol=False,
        )
        prev = make_observation(
            trend_dir=TrendDirection.UP,
            vol=VolatilityLevel.MODERATE,
            in_consol=False,
        )
        result = detector.detect(obs, prev, RegimeType.BULL, 55)
        assert result is not None
        assert result.transition_type == TransitionType.REGIME_PERSISTENCE
        assert result.to_regime == RegimeType.BULL
        assert result.confirmed is True

    def test_no_persistence_before_50_bars(self, detector):
        obs = make_observation(trend_dir=TrendDirection.UP)
        prev = make_observation(trend_dir=TrendDirection.UP)
        result = detector.detect(obs, prev, RegimeType.BULL, 30)
        if result:
            assert result.transition_type != TransitionType.REGIME_PERSISTENCE


class TestStableConditions:
    def test_returns_none_for_stable_bull(self, detector):
        obs  = make_observation(trend_dir=TrendDirection.UP, vol=VolatilityLevel.MODERATE, trend_phase="impulse")
        prev = make_observation(trend_dir=TrendDirection.UP, vol=VolatilityLevel.MODERATE, trend_phase="impulse")
        result = detector.detect(obs, prev, RegimeType.BULL, 10)
        assert result is None


class TestTransitionEventFields:
    def test_event_fields_populated(self, detector):
        prev = make_observation(in_consol=True, consol_bars=15)
        curr = make_observation(in_consol=False, has_breakout=True, breakout_bullish=True)
        result = detector.detect(curr, prev, RegimeType.RANGING, 20)
        assert result is not None
        assert result.transition_type is not None
        assert isinstance(result.from_regime, RegimeType)
        assert isinstance(result.to_regime, RegimeType)
        assert isinstance(result.probability, float)
        assert isinstance(result.confidence, float)
        assert isinstance(result.trigger, str)
