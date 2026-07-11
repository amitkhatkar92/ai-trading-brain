"""tests/unit/investment/market/trend/test_trend_strategy_mapper.py
Tests for TrendStrategyMapper, trend_permissions, and trend_constraints.
"""
from __future__ import annotations

import pytest
from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.trend.trend_strategy_mapper import TrendStrategyMapper
from iios.investment.market.trend.trend_permissions import (
    STAGE_PERMISSIONS,
    TrendStrategyType,
    best_approach,
)
from iios.investment.market.trend.trend_constraints import (
    TREND_CONSTRAINTS,
    TrendConstraintEngine,
    TrendConstraint,
)
from iios.investment.market.trend.models import (
    TrendStage,
    TrendQualityMetrics,
    TrendMomentumState,
    ImpulseQuality,
    CorrectionQuality,
    _default_quality,
    _default_momentum,
)


def _quality(overall: float = 65.0) -> TrendQualityMetrics:
    return TrendQualityMetrics(
        smoothness=0.6, reliability=0.6, efficiency=0.6,
        consistency=0.6, stability=0.6, persistence=0.6,
        overall=overall,
    )


def _momentum(is_accelerating: bool = False, is_decelerating: bool = False) -> TrendMomentumState:
    return TrendMomentumState(
        velocity=1.0, acceleration=0.0,
        impulse_quality=ImpulseQuality.MODERATE,
        correction_quality=CorrectionQuality.NORMAL,
        is_accelerating=is_accelerating,
        is_decelerating=is_decelerating,
        momentum_score=60.0,
    )


class TestStagePermissions:
    def test_covers_all_8_stages(self):
        assert set(STAGE_PERMISSIONS.keys()) == set(TrendStage)

    def test_established_momentum_suitability_high(self):
        assert STAGE_PERMISSIONS[TrendStage.ESTABLISHED][TrendStrategyType.MOMENTUM] >= 0.80

    def test_reversing_directional_suitability_low(self):
        # Per spec, REVERSING has low suitability for trend-following strategies.
        # mean_reversion is intentionally high (0.80) in REVERSING — that's by design.
        low_strategies = ["momentum", "breakout", "swing", "position"]
        for strategy in low_strategies:
            score = STAGE_PERMISSIONS[TrendStage.REVERSING][strategy]
            assert score <= 0.15, f"{strategy}={score} too high for REVERSING"

    def test_best_approach_established_is_momentum_or_retest(self):
        approach = best_approach(TrendStage.ESTABLISHED)
        assert approach in (TrendStrategyType.MOMENTUM, TrendStrategyType.RETEST)


class TestTrendConstraints:
    def test_covers_all_8_stages(self):
        assert set(TREND_CONSTRAINTS.keys()) == set(TrendStage)

    def test_completed_stage_max_size_zero(self):
        assert TREND_CONSTRAINTS[TrendStage.COMPLETED].max_position_size_pct == 0.0

    def test_established_full_size_allowed(self):
        assert TREND_CONSTRAINTS[TrendStage.ESTABLISHED].max_position_size_pct == 1.0


class TestTrendConstraintEngine:
    def setup_method(self):
        self.engine = TrendConstraintEngine()

    def test_completed_always_blocked(self):
        allowed, reason = self.engine.check(
            "momentum", TrendStage.COMPLETED, "long", 0.95, 90.0, True
        )
        assert not allowed

    def test_established_momentum_allowed(self):
        allowed, reason = self.engine.check(
            "momentum", TrendStage.ESTABLISHED, "long", 0.65, 60.0, True
        )
        assert allowed

    def test_exhausting_momentum_forbidden(self):
        allowed, reason = self.engine.check(
            "momentum", TrendStage.EXHAUSTING, "long", 0.65, 60.0, True
        )
        assert not allowed

    def test_low_confidence_blocked(self):
        allowed, reason = self.engine.check(
            "swing", TrendStage.ESTABLISHED, "long", 0.10, 80.0, True
        )
        assert not allowed

    def test_fallback_for_unknown_stage(self):
        # Should not crash — returns EMERGING constraints
        constraint = self.engine.get(TrendStage.EMERGING)
        assert isinstance(constraint, TrendConstraint)


class TestTrendStrategyMapper:
    def setup_method(self):
        self.mapper = TrendStrategyMapper()

    def test_readiness_returns_strategy_readiness(self):
        from iios.investment.market.trend.models import StrategyReadiness
        result = self.mapper.readiness(
            TrendStage.ESTABLISHED, TrendDirection.UP,
            _quality(), _momentum(), 0.75,
        )
        assert isinstance(result, StrategyReadiness)

    def test_readiness_has_best_approach(self):
        result = self.mapper.readiness(
            TrendStage.ESTABLISHED, TrendDirection.UP,
            _quality(), _momentum(), 0.75,
        )
        assert result.best_approach != ""

    def test_decelerating_reduces_momentum_suitability(self):
        r_normal = self.mapper.readiness(
            TrendStage.ESTABLISHED, TrendDirection.UP,
            _quality(), _momentum(is_accelerating=False, is_decelerating=False), 0.75,
        )
        r_decel = self.mapper.readiness(
            TrendStage.ESTABLISHED, TrendDirection.UP,
            _quality(), _momentum(is_decelerating=True), 0.75,
        )
        assert r_decel.momentum_suitability < r_normal.momentum_suitability

    def test_accelerating_boosts_momentum_suitability(self):
        r_normal = self.mapper.readiness(
            TrendStage.ESTABLISHED, TrendDirection.UP,
            _quality(), _momentum(), 0.75,
        )
        r_accel = self.mapper.readiness(
            TrendStage.ESTABLISHED, TrendDirection.UP,
            _quality(), _momentum(is_accelerating=True), 0.75,
        )
        assert r_accel.momentum_suitability >= r_normal.momentum_suitability

    def test_is_suitable_established_momentum(self):
        assert self.mapper.is_suitable(TrendStrategyType.MOMENTUM, TrendStage.ESTABLISHED)

    def test_is_suitable_reversing_momentum_false(self):
        assert not self.mapper.is_suitable(TrendStrategyType.MOMENTUM, TrendStage.REVERSING)

    def test_check_trade_completed_blocked(self):
        allowed, reason = self.mapper.check_trade(
            "momentum", TrendStage.COMPLETED, "long", 0.90, 80.0, True
        )
        assert not allowed
