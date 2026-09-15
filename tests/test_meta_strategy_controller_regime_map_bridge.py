"""
tests/test_meta_strategy_controller_regime_map_bridge.py
===========================================================
Self-Learning Ecosystem -- Post-roadmap Priority 5: proves
MetaStrategyController's new _effective_regime_map() bridge is
byte-identical to the original static _REGIME_MAP today (zero active
demotions in a fresh environment) and fails open to the static map if
the refinement engine itself raises.

T01  _effective_regime_map() with no demotions returns the exact same
     candidate set as the raw _REGIME_MAP for every regime
T02  get_active_strategies() behavior is unchanged when the refinement
     engine reports zero demotions (regression -- proves the bridge
     didn't alter any existing selection logic)
T03  _effective_regime_map() fails open to the raw _REGIME_MAP if
     regime_map_refinement_engine.get_effective_regime_map() raises
"""
from __future__ import annotations

from unittest.mock import patch

from models.market_data import RegimeLabel, VolatilityLevel
from strategy_lab.meta_strategy_controller import MetaStrategyController, _REGIME_MAP


class _FakeSnapshot:
    """Minimal duck-typed stand-in -- get_active_strategies() only reads
    .regime and .volatility off the snapshot it's given."""
    def __init__(self, regime, volatility=VolatilityLevel.LOW, vix=15.0):
        self.regime = regime
        self.volatility = volatility
        self.vix = vix


def test_t01_effective_map_matches_static_with_no_demotions():
    controller = MetaStrategyController()
    effective = controller._effective_regime_map()
    for regime, candidates in _REGIME_MAP.items():
        assert set(effective.get(regime, [])) == set(candidates)


def test_t02_get_active_strategies_unchanged_with_zero_demotions():
    controller = MetaStrategyController()
    snapshot = _FakeSnapshot(RegimeLabel.BULL_TREND)
    passing = {"Breakout_Volume", "Momentum_Retest", "Trend_Pullback", "Mean_Reversion"}
    active = controller.get_active_strategies(snapshot, passing)
    # Same result whether read through the bridge or the raw static map,
    # since no demotion exists in a fresh test environment.
    expected = set(_REGIME_MAP[RegimeLabel.BULL_TREND.value]) & passing
    assert active == expected


def test_t03_fails_open_when_refinement_engine_raises():
    controller = MetaStrategyController()
    with patch(
        "strategy_lab.regime_map_refinement_engine.get_effective_regime_map",
        side_effect=RuntimeError("boom"),
    ):
        effective = controller._effective_regime_map()
    for regime, candidates in _REGIME_MAP.items():
        assert set(effective.get(regime, [])) == set(candidates)
