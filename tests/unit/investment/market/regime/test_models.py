"""tests/unit/investment/market/regime/test_models.py"""
from __future__ import annotations

import time
import pytest

from iios.investment.market.market_constants import MarketRegime, TrendDirection, VolatilityLevel
from iios.investment.market.regime.models import (
    RegimeObservation,
    RegimeSnapshot,
    RegimeType,
    StrategyCompatibility,
    TransitionEvent,
    TransitionType,
    _REGIME_TYPE_TO_MARKET_REGIME,
    regime_type_to_market_regime,
)


class TestRegimeTypeEnum:
    def test_has_15_values(self):
        assert len(RegimeType) == 15

    def test_all_expected_values_present(self):
        expected = {
            "bull", "bear", "sideways", "trending", "ranging", "expansion",
            "contraction", "recovery", "distribution", "accumulation",
            "volatile", "calm", "transition", "crisis", "unknown",
        }
        assert {r.value for r in RegimeType} == expected


class TestTransitionTypeEnum:
    def test_has_7_values(self):
        assert len(TransitionType) == 7

    def test_all_expected_values_present(self):
        expected = {
            "emerging_trend", "trend_failure", "reversal",
            "volatility_expansion", "volatility_compression",
            "regime_shift", "regime_persistence",
        }
        assert {t.value for t in TransitionType} == expected


class TestRegimeTypeToMarketRegime:
    def test_mapping_covers_all_regime_types(self):
        for rt in RegimeType:
            result = regime_type_to_market_regime(rt)
            assert isinstance(result, MarketRegime)

    def test_bull_maps_to_bull(self):
        assert regime_type_to_market_regime(RegimeType.BULL) == MarketRegime.BULL

    def test_bear_maps_to_bear(self):
        assert regime_type_to_market_regime(RegimeType.BEAR) == MarketRegime.BEAR

    def test_crisis_maps_to_crisis(self):
        assert regime_type_to_market_regime(RegimeType.CRISIS) == MarketRegime.CRISIS

    def test_unknown_maps_to_unknown(self):
        assert regime_type_to_market_regime(RegimeType.UNKNOWN) == MarketRegime.UNKNOWN

    def test_expansion_maps_to_expansion(self):
        assert regime_type_to_market_regime(RegimeType.EXPANSION) == MarketRegime.EXPANSION

    def test_contraction_maps_to_contraction(self):
        assert regime_type_to_market_regime(RegimeType.CONTRACTION) == MarketRegime.CONTRACTION

    def test_recovery_maps_to_recovery(self):
        assert regime_type_to_market_regime(RegimeType.RECOVERY) == MarketRegime.RECOVERY


class TestRegimeObservation:
    def test_is_frozen(self):
        obs = RegimeObservation(
            trend_direction=TrendDirection.UP,
            trend_confirmed=True,
            trend_leg_count=2,
            trend_strength="strong",
            trend_phase="impulse",
            structure_phase="markup",
            volatility=VolatilityLevel.MODERATE,
            in_consolidation=False,
            consolidation_bars=0,
            consolidation_compression=1.0,
            has_active_breakout=False,
            breakout_bullish=False,
            advance_decline_ratio=1.5,
            quality_score=75.0,
            bar_count=50,
        )
        with pytest.raises((AttributeError, TypeError)):
            obs.trend_confirmed = False  # type: ignore[misc]

    def test_all_fields_accessible(self):
        obs = RegimeObservation(
            trend_direction=TrendDirection.DOWN,
            trend_confirmed=False,
            trend_leg_count=1,
            trend_strength="weak",
            trend_phase="correction",
            structure_phase="markdown",
            volatility=VolatilityLevel.HIGH,
            in_consolidation=True,
            consolidation_bars=15,
            consolidation_compression=0.8,
            has_active_breakout=True,
            breakout_bullish=False,
            advance_decline_ratio=0.4,
            quality_score=60.0,
            bar_count=100,
        )
        assert obs.trend_direction == TrendDirection.DOWN
        assert obs.consolidation_bars == 15
        assert obs.advance_decline_ratio == 0.4


class TestRegimeSnapshot:
    def test_default_values(self):
        snap = RegimeSnapshot()
        assert snap.primary == RegimeType.UNKNOWN
        assert snap.confidence == 0.0
        assert isinstance(snap.secondary, list)
        assert isinstance(snap.metadata, dict)

    def test_to_dict_has_expected_keys(self):
        snap = RegimeSnapshot(
            market_id="M1",
            symbol="SYM",
            primary=RegimeType.BULL,
            confidence=0.8,
        )
        d = snap.to_dict()
        expected_keys = {
            "regime_id", "market_id", "symbol", "primary", "secondary",
            "confidence", "stability", "persistence_score", "duration_bars",
            "transition_probability", "market_regime", "timestamp", "metadata",
        }
        assert expected_keys.issubset(d.keys())

    def test_primary_serialized_as_value(self):
        snap = RegimeSnapshot(primary=RegimeType.BEAR)
        assert snap.to_dict()["primary"] == "bear"

    def test_secondary_serialized_as_list_of_values(self):
        snap = RegimeSnapshot(secondary=[RegimeType.VOLATILE, RegimeType.TRENDING])
        d = snap.to_dict()
        assert d["secondary"] == ["volatile", "trending"]


class TestTransitionEvent:
    def test_default_values(self):
        evt = TransitionEvent()
        assert evt.from_regime == RegimeType.UNKNOWN
        assert evt.to_regime == RegimeType.UNKNOWN
        assert evt.confirmed is False

    def test_to_dict_has_expected_keys(self):
        evt = TransitionEvent(
            from_regime=RegimeType.BULL,
            to_regime=RegimeType.DISTRIBUTION,
            transition_type=TransitionType.TREND_FAILURE,
        )
        d = evt.to_dict()
        expected_keys = {
            "event_id", "market_id", "from_regime", "to_regime",
            "transition_type", "probability", "confidence", "trigger",
            "bars_since_signal", "confirmed", "timestamp", "metadata",
        }
        assert expected_keys.issubset(d.keys())
        assert d["transition_type"] == "trend_failure"


class TestStrategyCompatibility:
    def _make(self) -> StrategyCompatibility:
        return StrategyCompatibility(
            regime=RegimeType.BULL,
            allowed=["trend_following", "breakout"],
            discouraged=["mean_reversion"],
            blocked=["defensive"],
        )

    def test_is_allowed_true(self):
        c = self._make()
        assert c.is_allowed("trend_following") is True

    def test_is_allowed_false_when_not_in_allowed(self):
        c = self._make()
        assert c.is_allowed("mean_reversion") is False

    def test_is_allowed_false_when_blocked(self):
        c = self._make()
        assert c.is_allowed("defensive") is False

    def test_is_blocked_true(self):
        c = self._make()
        assert c.is_blocked("defensive") is True

    def test_is_blocked_false(self):
        c = self._make()
        assert c.is_blocked("trend_following") is False

    def test_is_discouraged_true(self):
        c = self._make()
        assert c.is_discouraged("mean_reversion") is True

    def test_is_discouraged_false_for_blocked(self):
        # blocked takes precedence — is_discouraged should return False for blocked
        c = self._make()
        # "defensive" is blocked but not in discouraged list
        assert c.is_discouraged("defensive") is False

    def test_to_dict_has_all_keys(self):
        c = self._make()
        d = c.to_dict()
        assert "regime" in d
        assert "allowed" in d
        assert "discouraged" in d
        assert "blocked" in d
        assert "preferred_timeframes" in d
        assert "preferred_risk_profile" in d
        assert "max_position_size_pct" in d
