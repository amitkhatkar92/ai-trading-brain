"""tests/unit/investment/market/volatility/test_models.py"""
from __future__ import annotations

import pytest
from iios.investment.market.volatility.models import (
    VolatilityRegimeType,
    VolatilityBehaviour,
    VolatilityEventType,
    RiskLevel,
    StrategyType,
    VolatilityTransitionType,
    VolatilityEstimate,
    VolatilityEvent,
    VolatilityState,
    VolatilityRegimeSnapshot,
    BehaviourSnapshot,
    RiskProfile,
    StrategyCompatibility,
    ConfidenceScore,
)


class TestEnums:
    def test_regime_types_complete(self):
        values = {r.value for r in VolatilityRegimeType}
        assert "very_low" in values
        assert "shock" in values
        assert "compression" in values
        assert "expansion" in values
        assert "recovery" in values
        assert len(values) == 11   # including UNKNOWN

    def test_behaviour_types(self):
        assert VolatilityBehaviour.EXPANDING in list(VolatilityBehaviour)
        assert VolatilityBehaviour.COMPRESSING in list(VolatilityBehaviour)
        assert VolatilityBehaviour.CLIMAX in list(VolatilityBehaviour)
        assert VolatilityBehaviour.STABLE in list(VolatilityBehaviour)

    def test_strategy_types(self):
        values = {s.value for s in StrategyType}
        assert "momentum" in values
        assert "options" in values
        assert "portfolio_rebalancing" in values

    def test_risk_level_ordering(self):
        levels = list(RiskLevel)
        assert len(levels) == 6


class TestVolatilityEstimate:
    def test_to_dict_fields(self):
        est = VolatilityEstimate(
            estimator_name="test", raw_value=0.01, annualized_pct=15.87,
            window_bars=20, confidence=0.9,
        )
        d = est.to_dict()
        assert d["estimator_name"] == "test"
        assert d["annualized_pct"] == 15.87
        assert d["window_bars"] == 20
        assert 0.0 <= d["confidence"] <= 1.0


class TestVolatilityEvent:
    def test_to_dict_with_regime_change(self):
        ev = VolatilityEvent(
            event_type=VolatilityEventType.REGIME_CHANGE,
            symbol="TEST",
            timeframe="1d",
            bar_index=5,
            severity=0.7,
            from_regime=VolatilityRegimeType.NORMAL,
            to_regime=VolatilityRegimeType.HIGH,
        )
        d = ev.to_dict()
        assert d["event_type"] == "regime_change"
        assert d["from_regime"] == "normal"
        assert d["to_regime"] == "high"
        assert d["severity"] == 0.7

    def test_to_dict_without_regime(self):
        ev = VolatilityEvent(
            event_type=VolatilityEventType.SPIKE,
            symbol="X",
            timeframe="1d",
            bar_index=0,
            severity=0.5,
        )
        d = ev.to_dict()
        assert d["from_regime"] is None
        assert d["to_regime"] is None


class TestVolatilityState:
    def test_to_dict_complete(self):
        from tests.unit.investment.market.volatility.conftest import make_vol_state
        state = make_vol_state()
        d = state.to_dict()
        assert "realized_volatility" in d
        assert "normalized_volatility" in d
        assert "volatility_persistence" in d
        assert "bars_processed" in d
        assert isinstance(d["is_initialized"], bool)


class TestStrategyCompatibility:
    def test_is_permitted(self):
        sc = StrategyCompatibility(
            permissions={"momentum": True, "mean_reversion": False},
            recommended=["momentum"],
            restricted=["mean_reversion"],
        )
        assert sc.is_permitted("momentum") is True
        assert sc.is_permitted("mean_reversion") is False
        assert sc.is_permitted("unknown") is False

    def test_to_dict(self):
        sc = StrategyCompatibility(
            permissions={"momentum": True},
            recommended=["momentum"],
            restricted=[],
        )
        d = sc.to_dict()
        assert d["permissions"]["momentum"] is True
        assert "recommended" in d


class TestRiskProfile:
    def test_to_dict(self):
        rp = RiskProfile(
            execution_risk=0.3,
            gap_risk=0.2,
            overnight_risk=0.4,
            portfolio_risk=0.35,
            strategy_risk=0.3,
            market_risk=0.4,
            overall_risk=0.35,
            risk_level=RiskLevel.MODERATE,
            risk_score=35.0,
        )
        d = rp.to_dict()
        assert d["risk_level"] == "moderate"
        assert 0 <= d["overall_risk"] <= 1


class TestConfidenceScore:
    def test_all_fields_in_range(self):
        cs = ConfidenceScore(
            volatility_confidence=0.8,
            forecast_confidence=0.7,
            regime_stability=0.6,
            expected_persistence=0.75,
            transition_probability=0.15,
        )
        d = cs.to_dict()
        for v in d.values():
            assert 0.0 <= v <= 1.0
