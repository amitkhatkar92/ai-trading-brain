"""Tests for performance_types.py"""
import pytest
from iios.investment.portfolio.performance.performance_types import (
    PerformanceGrade, PerformanceLevel, PerformanceTrend,
    ReturnPeriod, AttributionMethod, BenchmarkType, RunStatus,
    PerformancePosition, positions_from_plan,
    portfolio_return, portfolio_expected_return, portfolio_vol_proxy,
    downside_deviation, sharpe_from_positions, normalize_sharpe, normalize_alpha,
    performance_score_to_grade, performance_score_to_level,
    RISK_FREE_RATE_ANNUAL, EQUITY_PREMIUM_PROXY, TRADING_DAYS,
    SCORE_EXCELLENT, SCORE_GOOD, SCORE_AVERAGE, SHARPE_EXCELLENT,
)


class TestEnums:
    def test_performance_grade_values(self):
        assert PerformanceGrade.A.value == "A"
        assert PerformanceGrade.F.value == "F"
        assert len(list(PerformanceGrade)) == 5

    def test_performance_level_values(self):
        assert PerformanceLevel.EXCELLENT.value == "excellent"
        assert PerformanceLevel.POOR.value == "poor"

    def test_performance_trend_values(self):
        assert PerformanceTrend.IMPROVING.value == "improving"
        assert PerformanceTrend.STABLE.value == "stable"

    def test_attribution_method(self):
        assert AttributionMethod.BRINSON.value == "brinson"

    def test_benchmark_type(self):
        assert BenchmarkType.BROAD_MARKET.value == "broad_market"
        assert BenchmarkType.RISK_FREE.value == "risk_free"

    def test_run_status(self):
        assert RunStatus.SUCCESS.value == "success"
        assert RunStatus.FAILED.value == "failed"


class TestConstants:
    def test_risk_free_rate(self):
        assert RISK_FREE_RATE_ANNUAL == 0.065
        assert EQUITY_PREMIUM_PROXY == 0.065

    def test_trading_days(self):
        assert TRADING_DAYS == 252

    def test_score_thresholds(self):
        assert SCORE_EXCELLENT == 0.75
        assert SCORE_EXCELLENT > SCORE_GOOD > SCORE_AVERAGE

    def test_sharpe_thresholds(self):
        assert SHARPE_EXCELLENT == 2.0


class TestPerformancePosition:
    def test_defaults(self):
        p = PerformancePosition(symbol="TCS", weight=0.5)
        assert p.symbol == "TCS"
        assert p.weight == 0.5
        assert p.conviction == 0.60   # default per spec
        assert p.risk_score == 0.25   # default per spec

    def test_annual_vol_proxy_bounds(self):
        p = PerformancePosition(symbol="X", weight=1.0, risk_score=0.0)
        assert p.annual_vol_proxy >= 0.05
        p2 = PerformancePosition(symbol="X", weight=1.0, risk_score=1.0)
        assert p2.annual_vol_proxy <= 0.60

    def test_annual_vol_proxy_scales_with_risk(self):
        low  = PerformancePosition(symbol="X", weight=1.0, risk_score=0.2)
        high = PerformancePosition(symbol="X", weight=1.0, risk_score=0.8)
        assert low.annual_vol_proxy < high.annual_vol_proxy

    def test_contribution(self):
        p = PerformancePosition(symbol="X", weight=0.4, period_return=0.10)
        assert abs(p.contribution - 0.04) < 1e-9

    def test_active_contribution(self):
        p = PerformancePosition(symbol="X", weight=0.5,
                                period_return=0.10,
                                benchmark_period_return=0.05)
        assert abs(p.active_contribution - 0.025) < 1e-9

    def test_expected_return_from_conviction(self):
        # expected_return_annual is a stored field (defaults 0.0); the
        # _estimate_expected_return helper is used in positions_from_plan.
        from iios.investment.portfolio.performance.performance_types import _estimate_expected_return
        neutral_est = _estimate_expected_return(0.5, 0.25)
        assert abs(neutral_est - RISK_FREE_RATE_ANNUAL) < 1e-9

        bullish_est = _estimate_expected_return(1.0, 0.25)
        assert bullish_est > neutral_est

    def test_frozen(self):
        p = PerformancePosition(symbol="X", weight=1.0)
        with pytest.raises((AttributeError, TypeError)):
            p.weight = 0.5  # type: ignore


class TestPositionsFromPlan:
    def test_plain_list(self, positions_diverse):
        result = positions_from_plan(positions_diverse)
        assert result == positions_diverse

    def test_duck_typed_plan(self, mock_plan_with_positions, positions_diverse):
        result = positions_from_plan(mock_plan_with_positions)
        assert len(result) == len(positions_diverse)

    def test_empty_list(self):
        result = positions_from_plan([])
        assert result == []

    def test_unknown_object(self):
        result = positions_from_plan(object())
        assert result == []


class TestPortfolioUtilities:
    def test_portfolio_return_weighted(self, positions_diverse):
        r = portfolio_return(positions_diverse)
        # weights sum to 1, so it's weighted avg of period_returns
        expected = sum(p.weight * p.period_return for p in positions_diverse)
        assert abs(r - expected) < 1e-9

    def test_portfolio_return_empty(self):
        assert portfolio_return([]) == 0.0

    def test_portfolio_expected_return(self, positions_diverse):
        r = portfolio_expected_return(positions_diverse)
        assert r > 0.0

    def test_portfolio_vol_proxy_positive(self, positions_diverse):
        v = portfolio_vol_proxy(positions_diverse)
        assert v > 0.0
        assert v <= 0.60

    def test_portfolio_vol_proxy_empty(self):
        assert portfolio_vol_proxy([]) == 0.0

    def test_downside_deviation_above_target(self):
        returns = [0.05, 0.06, 0.07, 0.08]
        dd = downside_deviation(returns, target=0.01)
        assert dd == 0.0   # all above target

    def test_downside_deviation_mixed(self):
        returns = [0.02, -0.03, 0.01, -0.05]
        dd = downside_deviation(returns, target=0.0)
        assert dd > 0.0

    def test_sharpe_from_positions(self, positions_diverse):
        s = sharpe_from_positions(positions_diverse, realized_return=0.15)
        # sharpe = (0.15 - 0.065) / vol
        assert isinstance(s, float)


class TestNormalization:
    def test_normalize_sharpe_excellent(self):
        assert normalize_sharpe(2.0) == 1.0

    def test_normalize_sharpe_zero(self):
        # sharpe <= 0 → 0.0 (no credit for below-zero performance)
        assert normalize_sharpe(0.0) == 0.0

    def test_normalize_sharpe_negative(self):
        assert normalize_sharpe(-1.0) < 0.1

    def test_normalize_alpha_excellent(self):
        assert normalize_alpha(0.05) == 1.0

    def test_normalize_alpha_zero(self):
        # alpha <= 0 → 0.0 (no credit for zero/negative alpha)
        assert normalize_alpha(0.0) == 0.0


class TestScoreToGrade:
    def test_excellent(self):
        assert performance_score_to_grade(0.80) == PerformanceGrade.A

    def test_good(self):
        assert performance_score_to_grade(0.60) == PerformanceGrade.B

    def test_poor(self):
        assert performance_score_to_grade(0.10) == PerformanceGrade.F

    def test_level_excellent(self):
        assert performance_score_to_level(0.80) == PerformanceLevel.EXCELLENT

    def test_level_poor(self):
        assert performance_score_to_level(0.10) == PerformanceLevel.POOR
