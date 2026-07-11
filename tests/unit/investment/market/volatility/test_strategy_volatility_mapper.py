"""tests/unit/investment/market/volatility/test_strategy_volatility_mapper.py"""
from __future__ import annotations

import pytest

from iios.investment.market.volatility.strategy_volatility_mapper import StrategyVolatilityMapper
from iios.investment.market.volatility.strategy_permissions import (
    get_permissions,
    get_recommended,
    get_restricted,
)
from iios.investment.market.volatility.volatility_constraints import get_constraints
from iios.investment.market.volatility.models import (
    StrategyType,
    StrategyCompatibility,
    VolatilityBehaviour,
    VolatilityRegimeType,
)
from tests.unit.investment.market.volatility.conftest import make_vol_state, make_behaviour


def _evaluate(
    regime: VolatilityRegimeType,
    normalized: float = 0.50,
    behaviour: VolatilityBehaviour = VolatilityBehaviour.STABLE,
    expansion_score: float = 0.0,
    compression_score: float = 0.0,
) -> StrategyCompatibility:
    mapper = StrategyVolatilityMapper()
    state = make_vol_state(normalized_volatility=normalized)
    beh = make_behaviour(
        behaviour=behaviour,
        expansion_score=expansion_score,
        compression_score=compression_score,
    )
    return mapper.evaluate(regime, state, beh)


class TestStrategyPermissions:
    def test_all_strategy_types_covered(self):
        perms = get_permissions(VolatilityRegimeType.NORMAL)
        for st in StrategyType:
            assert st.value in perms

    def test_normal_regime_all_permitted(self):
        perms = get_permissions(VolatilityRegimeType.NORMAL)
        # In NORMAL regime most strategies should be allowed
        assert perms[StrategyType.MOMENTUM.value] is True
        assert perms[StrategyType.BREAKOUT.value] is True
        assert perms[StrategyType.SWING_TRADING.value] is True

    def test_shock_only_options(self):
        perms = get_permissions(VolatilityRegimeType.SHOCK)
        assert perms[StrategyType.OPTIONS.value] is True
        assert perms[StrategyType.MOMENTUM.value] is False
        assert perms[StrategyType.MEAN_REVERSION.value] is False

    def test_very_low_no_momentum(self):
        perms = get_permissions(VolatilityRegimeType.VERY_LOW)
        assert perms[StrategyType.MOMENTUM.value] is False

    def test_compression_includes_breakout(self):
        perms = get_permissions(VolatilityRegimeType.COMPRESSION)
        assert perms[StrategyType.BREAKOUT.value] is True

    def test_recommended_subset_of_permitted(self):
        for regime in VolatilityRegimeType:
            perms = get_permissions(regime)
            recs  = get_recommended(regime)
            for r in recs:
                assert perms.get(r, False) is True, f"{r} recommended but not permitted in {regime}"

    def test_restricted_complement_of_permitted(self):
        for regime in VolatilityRegimeType:
            perms = get_permissions(regime)
            rests = get_restricted(regime)
            for r in rests:
                assert not perms.get(r, True), f"{r} restricted but permitted in {regime}"


class TestStrategyVolatilityMapper:
    def test_returns_compatibility_object(self):
        compat = _evaluate(VolatilityRegimeType.NORMAL)
        assert isinstance(compat, StrategyCompatibility)

    def test_shock_halts_trading(self):
        compat = _evaluate(VolatilityRegimeType.SHOCK)
        assert compat.is_permitted(StrategyType.MOMENTUM.value) is False
        assert compat.is_permitted(StrategyType.BREAKOUT.value) is False

    def test_options_permitted_high_vol(self):
        compat = _evaluate(VolatilityRegimeType.HIGH)
        assert compat.is_permitted(StrategyType.OPTIONS.value) is True

    def test_breakout_enabled_during_compression(self):
        compat = _evaluate(
            VolatilityRegimeType.COMPRESSION,
            behaviour=VolatilityBehaviour.COMPRESSING,
            compression_score=0.70,
        )
        assert compat.is_permitted(StrategyType.BREAKOUT.value) is True

    def test_mean_reversion_disabled_during_climax(self):
        compat = _evaluate(
            VolatilityRegimeType.ELEVATED,
            behaviour=VolatilityBehaviour.CLIMAX,
        )
        assert compat.is_permitted(StrategyType.MEAN_REVERSION.value) is False

    def test_momentum_enabled_during_persistent(self):
        compat = _evaluate(
            VolatilityRegimeType.NORMAL,
            normalized=0.40,
            behaviour=VolatilityBehaviour.PERSISTENT,
        )
        assert compat.is_permitted(StrategyType.MOMENTUM.value) is True

    def test_restricted_not_in_recommended(self):
        for regime in VolatilityRegimeType:
            compat = _evaluate(regime)
            restricted_set = set(compat.restricted)
            for r in compat.recommended:
                assert r not in restricted_set


class TestVolatilityConstraints:
    def test_all_regimes_have_constraints(self):
        for regime in VolatilityRegimeType:
            c = get_constraints(regime)
            assert c.max_position_size_pct > 0

    def test_shock_constraints_most_restrictive(self):
        shock  = get_constraints(VolatilityRegimeType.SHOCK)
        normal = get_constraints(VolatilityRegimeType.NORMAL)
        assert shock.max_position_size_pct < normal.max_position_size_pct
        assert shock.halt_new_entries is True
        assert normal.halt_new_entries is False

    def test_constraints_to_dict(self):
        c = get_constraints(VolatilityRegimeType.NORMAL)
        d = c.to_dict()
        assert "max_position_size_pct" in d
        assert "halt_new_entries" in d

    def test_reduction_required_in_extreme(self):
        c = get_constraints(VolatilityRegimeType.EXTREME)
        assert c.reduce_exposure is True

    def test_confirmation_required_elevated(self):
        c = get_constraints(VolatilityRegimeType.ELEVATED)
        assert c.require_confirmation is True
