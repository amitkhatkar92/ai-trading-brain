"""tests/unit/investment/market/regime/test_regime_detector.py"""
from __future__ import annotations

import pytest

from iios.investment.market.market_constants import (
    MarketStrength,
    TrendDirection,
    VolatilityLevel,
)
from iios.investment.market.structure.models import StructurePhase, TrendPhase
from iios.investment.market.regime.models import RegimeObservation, RegimeType
from iios.investment.market.regime.regime_detector import RegimeDetector

from tests.unit.investment.market.regime.conftest import (
    make_observation,
    make_structure_snapshot,
    make_market_snapshot,
)


@pytest.fixture
def detector() -> RegimeDetector:
    return RegimeDetector()


class TestObserve:
    def test_observe_without_market_returns_observation(self, detector):
        ss = make_structure_snapshot(TrendDirection.UP, confirmed=True, leg_count=2)
        obs = detector.observe(ss)
        assert isinstance(obs, RegimeObservation)
        assert obs.trend_direction == TrendDirection.UP
        assert obs.trend_confirmed is True
        assert obs.bar_count == 50

    def test_observe_infers_volatility_from_phase(self, detector):
        ss = make_structure_snapshot(phase=StructurePhase.COMPRESSION)
        obs = detector.observe(ss)
        assert obs.volatility == VolatilityLevel.VERY_LOW

    def test_observe_infers_high_vol_for_distribution(self, detector):
        ss = make_structure_snapshot(phase=StructurePhase.DISTRIBUTION)
        obs = detector.observe(ss)
        assert obs.volatility == VolatilityLevel.HIGH

    def test_observe_uses_market_volatility_when_provided(self, detector):
        ss = make_structure_snapshot(phase=StructurePhase.MARKUP)
        ms = make_market_snapshot(volatility=VolatilityLevel.EXTREME)
        obs = detector.observe(ss, ms)
        assert obs.volatility == VolatilityLevel.EXTREME

    def test_observe_uses_market_adr(self, detector):
        ss = make_structure_snapshot()
        ms = make_market_snapshot(advances=20, declines=80)
        obs = detector.observe(ss, ms)
        assert obs.advance_decline_ratio == pytest.approx(20 / 80)

    def test_observe_adr_defaults_to_1_without_market(self, detector):
        ss = make_structure_snapshot()
        obs = detector.observe(ss)
        assert obs.advance_decline_ratio == 1.0

    def test_observe_consolidation_fields(self, detector):
        ss = make_structure_snapshot(
            in_consolidation=True, consolidation_bars=15
        )
        obs = detector.observe(ss)
        assert obs.in_consolidation is True
        assert obs.consolidation_bars == 15

    def test_observe_no_consolidation(self, detector):
        ss = make_structure_snapshot(in_consolidation=False)
        obs = detector.observe(ss)
        assert obs.in_consolidation is False
        assert obs.consolidation_bars == 0

    def test_observe_breakout_bullish(self, detector):
        ss = make_structure_snapshot(has_breakout=True, breakout_bullish=True)
        obs = detector.observe(ss)
        assert obs.has_active_breakout is True
        assert obs.breakout_bullish is True

    def test_observe_breakout_bearish(self, detector):
        ss = make_structure_snapshot(has_breakout=True, breakout_bullish=False)
        obs = detector.observe(ss)
        assert obs.has_active_breakout is True
        assert obs.breakout_bullish is False


class TestDetect:
    def test_detect_bull(self, detector, bull_obs):
        primary, secondary, confidence = detector.detect(bull_obs)
        assert primary == RegimeType.BULL

    def test_detect_bear(self, detector, bear_obs):
        primary, secondary, confidence = detector.detect(bear_obs)
        assert primary == RegimeType.BEAR

    def test_detect_sideways(self, detector, sideways_obs):
        primary, secondary, confidence = detector.detect(sideways_obs)
        assert primary == RegimeType.SIDEWAYS

    def test_detect_crisis(self, detector, crisis_obs):
        primary, secondary, confidence = detector.detect(crisis_obs)
        assert primary == RegimeType.CRISIS

    def test_detect_distribution(self, detector):
        obs = make_observation(
            trend_dir=TrendDirection.UP,
            confirmed=True,
            phase="distribution",
            vol=VolatilityLevel.MODERATE,
        )
        primary, _, _ = detector.detect(obs)
        assert primary == RegimeType.DISTRIBUTION

    def test_detect_accumulation(self, detector):
        obs = make_observation(
            trend_dir=TrendDirection.SIDEWAYS,
            confirmed=False,
            leg_count=1,
            phase="accumulation",
            vol=VolatilityLevel.LOW,
        )
        primary, _, _ = detector.detect(obs)
        assert primary == RegimeType.ACCUMULATION

    def test_returns_tuple_of_correct_types(self, detector, bull_obs):
        result = detector.detect(bull_obs)
        primary, secondary, confidence = result
        assert isinstance(primary, RegimeType)
        assert isinstance(secondary, list)
        assert isinstance(confidence, float)

    def test_confidence_in_range(self, detector, bull_obs):
        _, _, confidence = detector.detect(bull_obs)
        assert 0.0 <= confidence <= 1.0

    def test_volatile_in_secondary_when_high_vol_bull(self, detector):
        obs = make_observation(
            trend_dir=TrendDirection.UP,
            confirmed=True,
            leg_count=2,
            vol=VolatilityLevel.HIGH,
        )
        primary, secondary, _ = detector.detect(obs)
        assert primary == RegimeType.BULL
        assert RegimeType.VOLATILE in secondary

    def test_calm_in_secondary_when_very_low_vol(self, detector):
        obs = make_observation(
            trend_dir=TrendDirection.UP,
            confirmed=True,
            leg_count=2,
            vol=VolatilityLevel.VERY_LOW,
        )
        primary, secondary, _ = detector.detect(obs)
        assert RegimeType.CALM in secondary

    def test_low_quality_reduces_confidence(self, detector):
        high_q = make_observation(quality=90.0, confirmed=True, leg_count=2)
        low_q  = make_observation(quality=20.0, confirmed=True, leg_count=2)
        _, _, conf_high = detector.detect(high_q)
        _, _, conf_low  = detector.detect(low_q)
        assert conf_high > conf_low

    def test_deterministic(self, detector, bull_obs):
        r1 = detector.detect(bull_obs)
        r2 = detector.detect(bull_obs)
        assert r1[0] == r2[0]
        assert r1[2] == r2[2]

    def test_expansion_detected_on_breakout(self, detector):
        obs = make_observation(
            trend_dir=TrendDirection.UP,
            confirmed=False,
            leg_count=1,
            phase="markup",
            has_breakout=True,
        )
        primary, _, _ = detector.detect(obs)
        assert primary == RegimeType.EXPANSION

    def test_ranging_detected_on_long_consolidation(self, detector):
        obs = make_observation(
            trend_dir=TrendDirection.UNDEFINED,
            confirmed=False,
            leg_count=0,
            phase="contraction",
            in_consol=True,
            consol_bars=15,
        )
        primary, _, _ = detector.detect(obs)
        assert primary in (RegimeType.RANGING, RegimeType.CONTRACTION)
