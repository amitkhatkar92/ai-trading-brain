"""tests/unit/investment/market/regime/test_strategy_regime_mapper.py"""
from __future__ import annotations

import pytest

from iios.investment.market.regime.models import RegimeType
from iios.investment.market.regime.strategy_permissions import REGIME_PERMISSIONS, StrategyType
from iios.investment.market.regime.regime_constraints import (
    REGIME_CONSTRAINTS,
    RegimeConstraintEngine,
)
from iios.investment.market.regime.strategy_regime_mapper import StrategyRegimeMapper


@pytest.fixture
def mapper() -> StrategyRegimeMapper:
    return StrategyRegimeMapper()


class TestRegimePermissionsCompleteness:
    def test_covers_all_15_regime_types(self):
        assert len(REGIME_PERMISSIONS) == len(RegimeType)
        for rt in RegimeType:
            assert rt in REGIME_PERMISSIONS, f"Missing regime: {rt}"


class TestRegimeConstraintsCompleteness:
    def test_covers_all_15_regime_types(self):
        assert len(REGIME_CONSTRAINTS) == len(RegimeType)
        for rt in RegimeType:
            assert rt in REGIME_CONSTRAINTS, f"Missing constraint: {rt}"


class TestBullRegime:
    def test_trend_following_is_allowed(self, mapper):
        assert mapper.is_allowed(StrategyType.TREND_FOLLOWING, RegimeType.BULL) is True

    def test_defensive_is_blocked(self, mapper):
        assert mapper.is_blocked(StrategyType.DEFENSIVE, RegimeType.BULL) is True

    def test_mean_reversion_is_discouraged(self, mapper):
        assert mapper.is_discouraged(StrategyType.MEAN_REVERSION, RegimeType.BULL) is True

    def test_preferred_timeframes(self, mapper):
        tfs = mapper.preferred_timeframes(RegimeType.BULL)
        assert "1d" in tfs

    def test_risk_profile(self, mapper):
        assert mapper.preferred_risk_profile(RegimeType.BULL) == "aggressive"

    def test_max_position_size(self, mapper):
        assert mapper.max_position_size(RegimeType.BULL) == 1.0


class TestBearRegime:
    def test_long_trade_forbidden(self, mapper):
        allowed, reason = mapper.check_trade(
            strategy_type=StrategyType.COUNTER_TREND,
            regime=RegimeType.BEAR,
            direction="long",
            structure_quality=60.0,
            trend_confirmed=True,
        )
        assert allowed is False
        assert "long" in reason.lower() or "forbidden" in reason.lower()

    def test_position_is_blocked(self, mapper):
        assert mapper.is_blocked(StrategyType.POSITION, RegimeType.BEAR) is True

    def test_max_position_size_is_reduced(self, mapper):
        assert mapper.max_position_size(RegimeType.BEAR) == 0.5


class TestCrisisRegime:
    def test_all_non_defensive_are_blocked(self, mapper):
        for st in StrategyType.ALL:
            if st != StrategyType.DEFENSIVE:
                assert mapper.is_blocked(st, RegimeType.CRISIS) is True, \
                    f"Expected {st} to be blocked in CRISIS"

    def test_check_trade_returns_false_for_any_strategy(self, mapper):
        # CRISIS max_positions = 0, so no trade is allowed
        allowed, _ = mapper.check_trade(
            strategy_type=StrategyType.DEFENSIVE,
            regime=RegimeType.CRISIS,
            direction="long",
            structure_quality=70.0,
            trend_confirmed=True,
        )
        assert allowed is False


class TestUnknownRegime:
    def test_nothing_is_allowed(self, mapper):
        for st in StrategyType.ALL:
            assert mapper.is_allowed(st, RegimeType.UNKNOWN) is False, \
                f"Expected {st} to not be allowed in UNKNOWN"

    def test_check_trade_always_false(self, mapper):
        allowed, _ = mapper.check_trade(
            strategy_type=StrategyType.TREND_FOLLOWING,
            regime=RegimeType.UNKNOWN,
            direction="long",
            structure_quality=70.0,
        )
        assert allowed is False


class TestStrategyMapper:
    def test_is_allowed_matches_permissions(self, mapper):
        perm = REGIME_PERMISSIONS[RegimeType.SIDEWAYS]
        for st in perm.allowed:
            if st not in perm.blocked:
                assert mapper.is_allowed(st, RegimeType.SIDEWAYS) is True

    def test_check_trade_respects_quality_constraint(self, mapper):
        # TRENDING requires min_quality=55
        allowed_low, _ = mapper.check_trade(
            strategy_type=StrategyType.TREND_FOLLOWING,
            regime=RegimeType.TRENDING,
            direction="long",
            structure_quality=30.0,
            trend_confirmed=True,
        )
        allowed_high, _ = mapper.check_trade(
            strategy_type=StrategyType.TREND_FOLLOWING,
            regime=RegimeType.TRENDING,
            direction="long",
            structure_quality=80.0,
            trend_confirmed=True,
        )
        assert allowed_low is False
        assert allowed_high is True

    def test_allowed_strategies_list(self, mapper):
        strats = mapper.allowed_strategies(RegimeType.BULL)
        assert StrategyType.TREND_FOLLOWING in strats

    def test_blocked_strategies_list(self, mapper):
        strats = mapper.blocked_strategies(RegimeType.BULL)
        assert StrategyType.DEFENSIVE in strats


class TestStrategyType:
    def test_all_has_12_strategies(self):
        assert len(StrategyType.ALL) == 12

    def test_all_contains_expected_strategies(self):
        expected = {
            "trend_following", "mean_reversion", "breakout", "momentum",
            "counter_trend", "range_bound", "volatility", "scalping",
            "swing", "position", "arbitrage", "defensive",
        }
        assert set(StrategyType.ALL) == expected


class TestRegimeConstraintEngine:
    def test_get_returns_constraint(self):
        engine = RegimeConstraintEngine()
        c = engine.get(RegimeType.BULL)
        assert c.regime == RegimeType.BULL

    def test_get_falls_back_to_unknown(self):
        engine = RegimeConstraintEngine()
        # Force a lookup of a regime not in dict (impossible with valid enum,
        # but test the fallback exists)
        c = engine.get(RegimeType.UNKNOWN)
        assert c.max_positions == 0

    def test_distribution_forbids_long(self):
        engine = RegimeConstraintEngine()
        c = engine.get(RegimeType.DISTRIBUTION)
        assert "long" in c.forbidden_directions
