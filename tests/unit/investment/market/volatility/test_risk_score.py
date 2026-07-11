"""tests/unit/investment/market/volatility/test_risk_score.py"""
from __future__ import annotations

import pytest

from iios.investment.market.volatility import risk_score as rs
from iios.investment.market.volatility.risk_profile import RiskProfileBuilder
from iios.investment.market.volatility.risk_statistics import RiskStatistics, RiskStats
from iios.investment.market.volatility.models import (
    RiskLevel,
    RiskProfile,
    VolatilityRegimeType,
)
from tests.unit.investment.market.volatility.conftest import make_vol_state, make_behaviour


def _state(normalized: float = 0.50, persistence: float = 0.60, stability: float = 0.70, range_ratio: float = 1.0):
    return make_vol_state(
        normalized_volatility=normalized,
        volatility_persistence=persistence,
        volatility_stability=stability,
        bar_range_ratio=range_ratio,
    )


def _beh(expansion: float = 0.0, acceleration: float = 0.0):
    from iios.investment.market.volatility.models import VolatilityBehaviour
    return make_behaviour(
        expansion_score=expansion,
        acceleration=acceleration,
    )


class TestRiskScoreFunctions:
    def test_execution_risk_in_range(self):
        score = rs.execution_risk_score(
            _state(0.60), _beh(0.3), VolatilityRegimeType.ELEVATED
        )
        assert 0.0 <= score <= 1.0

    def test_shock_execution_higher(self):
        normal = rs.execution_risk_score(_state(0.60), _beh(), VolatilityRegimeType.NORMAL)
        shock  = rs.execution_risk_score(_state(0.60), _beh(), VolatilityRegimeType.SHOCK)
        assert shock > normal

    def test_gap_risk_in_range(self):
        score = rs.gap_risk_score(_state(0.50, range_ratio=2.0), _beh())
        assert 0.0 <= score <= 1.0

    def test_large_range_increases_gap_risk(self):
        low  = rs.gap_risk_score(_state(0.40, range_ratio=1.0), _beh())
        high = rs.gap_risk_score(_state(0.40, range_ratio=3.0), _beh())
        assert high > low

    def test_overnight_risk_shock_high(self):
        score = rs.overnight_risk_score(_state(0.80), VolatilityRegimeType.SHOCK)
        assert score > 0.70

    def test_overnight_risk_normal(self):
        score = rs.overnight_risk_score(_state(0.40), VolatilityRegimeType.NORMAL)
        assert score < 0.50

    def test_portfolio_risk_extreme(self):
        score = rs.portfolio_risk_score(_state(0.85), VolatilityRegimeType.EXTREME)
        assert score > 0.60

    def test_market_risk_in_range(self):
        score = rs.market_risk_score(_state(0.50), _beh(acceleration=0.2))
        assert 0.0 <= score <= 1.0

    def test_strategy_risk_in_range(self):
        score = rs.strategy_risk_score(_state(0.50), VolatilityRegimeType.NORMAL, _beh())
        assert 0.0 <= score <= 1.0


class TestRiskProfileBuilder:
    def test_builds_profile(self):
        builder = RiskProfileBuilder()
        state   = _state(0.50)
        beh     = _beh()
        profile = builder.build(state, VolatilityRegimeType.NORMAL, beh)
        assert isinstance(profile, RiskProfile)

    def test_all_components_in_range(self):
        builder = RiskProfileBuilder()
        for regime in list(VolatilityRegimeType):
            profile = builder.build(_state(0.50), regime, _beh())
            assert 0.0 <= profile.execution_risk <= 1.0
            assert 0.0 <= profile.gap_risk <= 1.0
            assert 0.0 <= profile.overall_risk <= 1.0

    def test_risk_level_increases_with_vol(self):
        builder = RiskProfileBuilder()
        low_prof  = builder.build(_state(0.10), VolatilityRegimeType.LOW, _beh())
        high_prof = builder.build(_state(0.90), VolatilityRegimeType.EXTREME, _beh(0.8))
        assert high_prof.overall_risk > low_prof.overall_risk

    def test_risk_level_mapping(self):
        builder = RiskProfileBuilder()
        for regime in [VolatilityRegimeType.NORMAL, VolatilityRegimeType.SHOCK]:
            profile = builder.build(_state(0.50), regime, _beh())
            assert profile.risk_level in list(RiskLevel)

    def test_risk_score_is_overall_times_100(self):
        builder = RiskProfileBuilder()
        profile = builder.build(_state(0.50), VolatilityRegimeType.NORMAL, _beh())
        assert abs(profile.risk_score - profile.overall_risk * 100) < 0.01


class TestRiskStatistics:
    def _make_profile(self, overall: float, level: RiskLevel) -> RiskProfile:
        return RiskProfile(
            execution_risk=overall,
            gap_risk=overall,
            overnight_risk=overall,
            portfolio_risk=overall,
            strategy_risk=overall,
            market_risk=overall,
            overall_risk=overall,
            risk_level=level,
            risk_score=overall * 100,
        )

    def test_initial_stats(self):
        stats = RiskStatistics()
        s = stats.stats()
        assert s.total_bars == 0

    def test_record_increments(self):
        stats = RiskStatistics()
        stats.record(self._make_profile(0.3, RiskLevel.MODERATE))
        assert stats.stats().total_bars == 1

    def test_high_risk_counted(self):
        stats = RiskStatistics()
        stats.record(self._make_profile(0.7, RiskLevel.HIGH))
        assert stats.stats().high_risk_bars == 1

    def test_extreme_counted(self):
        stats = RiskStatistics()
        stats.record(self._make_profile(0.9, RiskLevel.EXTREME))
        s = stats.stats()
        assert s.extreme_risk_bars == 1
        assert s.high_risk_bars == 1

    def test_reset(self):
        stats = RiskStatistics()
        stats.record(self._make_profile(0.7, RiskLevel.HIGH))
        stats.reset()
        s = stats.stats()
        assert s.total_bars == 0
        assert s.high_risk_bars == 0

    def test_avg_risk_computed(self):
        stats = RiskStatistics()
        for overall in [0.2, 0.4, 0.6]:
            stats.record(self._make_profile(overall, RiskLevel.MODERATE))
        s = stats.stats()
        assert abs(s.avg_overall_risk - 0.4) < 0.01
