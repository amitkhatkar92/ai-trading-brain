"""tests/unit/investment/market/volatility/test_volatility_confidence.py"""
from __future__ import annotations

import pytest

from iios.investment.market.volatility.confidence_score import compute_confidence
from iios.investment.market.volatility.volatility_confidence import VolatilityConfidenceCalculator
from iios.investment.market.volatility.models import (
    VolatilityEstimate,
    VolatilityRegimeType,
    VolatilityTransitionType,
)
from tests.unit.investment.market.volatility.conftest import (
    make_vol_state,
    make_behaviour,
    make_regime_snap,
)


def _estimates(n: int = 2, confidence: float = 0.80):
    return {
        f"est_{i}": VolatilityEstimate(
            estimator_name=f"est_{i}",
            raw_value=0.01,
            annualized_pct=20.0,
            window_bars=20,
            confidence=confidence,
        )
        for i in range(n)
    }


class TestComputeConfidence:
    def test_all_fields_in_range(self):
        state   = make_vol_state()
        regime  = make_regime_snap()
        beh     = make_behaviour()
        ests    = _estimates()
        cs = compute_confidence(state, regime, beh, ests)
        for field_name, val in cs.to_dict().items():
            assert 0.0 <= val <= 1.0, f"{field_name} out of range"

    def test_uninitialised_state_lowers_vol_confidence(self):
        state_init   = make_vol_state(is_initialized=True)
        state_uninit = make_vol_state(is_initialized=False)
        regime = make_regime_snap()
        beh    = make_behaviour()
        ests   = _estimates()
        init_cs   = compute_confidence(state_init, regime, beh, ests)
        uninit_cs = compute_confidence(state_uninit, regime, beh, ests)
        assert init_cs.volatility_confidence > uninit_cs.volatility_confidence

    def test_more_estimators_raise_confidence(self):
        state  = make_vol_state()
        regime = make_regime_snap()
        beh    = make_behaviour()
        one_est   = compute_confidence(state, regime, beh, _estimates(1))
        three_est = compute_confidence(state, regime, beh, _estimates(3))
        assert three_est.volatility_confidence >= one_est.volatility_confidence

    def test_no_estimators_handles_gracefully(self):
        state  = make_vol_state()
        regime = make_regime_snap()
        beh    = make_behaviour()
        cs = compute_confidence(state, regime, beh, {})
        assert 0.0 <= cs.volatility_confidence <= 1.0

    def test_high_persistence_raises_forecast_confidence(self):
        state_high = make_vol_state(volatility_persistence=0.90)
        state_low  = make_vol_state(volatility_persistence=0.20)
        regime = make_regime_snap()
        beh    = make_behaviour()
        ests   = _estimates()
        high_cs = compute_confidence(state_high, regime, beh, ests)
        low_cs  = compute_confidence(state_low,  regime, beh, ests)
        assert high_cs.forecast_confidence > low_cs.forecast_confidence

    def test_long_duration_increases_regime_stability(self):
        state  = make_vol_state()
        beh    = make_behaviour()
        ests   = _estimates()
        snap_short = make_regime_snap(duration_bars=2)
        snap_long  = make_regime_snap(duration_bars=30)
        short_cs = compute_confidence(state, snap_short, beh, ests)
        long_cs  = compute_confidence(state, snap_long,  beh, ests)
        assert long_cs.regime_stability >= short_cs.regime_stability

    def test_transition_probability_matches_regime(self):
        state  = make_vol_state()
        beh    = make_behaviour()
        ests   = _estimates()
        regime = make_regime_snap(transition_probability=0.40)
        cs = compute_confidence(state, regime, beh, ests)
        assert cs.transition_probability == 0.40


class TestVolatilityConfidenceCalculator:
    def test_delegates_to_compute_confidence(self):
        calc   = VolatilityConfidenceCalculator()
        state  = make_vol_state()
        regime = make_regime_snap()
        beh    = make_behaviour()
        ests   = _estimates()
        cs = calc.calculate(state, regime, beh, ests)
        for v in cs.to_dict().values():
            assert 0.0 <= v <= 1.0
