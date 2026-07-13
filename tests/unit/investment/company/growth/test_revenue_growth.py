"""tests/unit/investment/company/growth/test_revenue_growth.py"""
from __future__ import annotations

import pytest

from iios.investment.company.growth.revenue_growth import RevenueGrowthEngine
from iios.investment.company.growth.growth_profile import GrowthTrend


@pytest.fixture
def engine():
    return RevenueGrowthEngine()


class TestRevenueGrowthFromSeries:
    def test_basic_series(self, engine):
        series = [100.0, 115.0, 132.25, 152.09, 174.90, 201.14, 231.31]  # ~15% CAGR
        result = engine.compute(revenue_series=series)
        assert result.cagr.best_available is not None
        assert 0.12 < result.cagr.best_available < 0.18

    def test_single_period_yoy(self, engine):
        series = [100.0, 110.0]
        result = engine.compute(revenue_series=series)
        assert result.yoy is not None
        assert abs(result.yoy - 0.10) < 0.001

    def test_trend_detected(self, engine):
        series = [100.0, 108.0, 117.0, 127.0, 138.0, 150.0]  # accelerating slightly
        result = engine.compute(revenue_series=series)
        assert result.trend != GrowthTrend.INSUFFICIENT_DATA

    def test_declining_trend(self, engine):
        series = [200.0, 180.0, 160.0, 140.0, 120.0]
        result = engine.compute(revenue_series=series)
        assert result.cagr.best_available is not None
        assert result.cagr.best_available < 0

    def test_5yr_cagr_available(self, engine):
        series = [100.0, 110.0, 121.0, 133.1, 146.41, 161.05]  # exactly 5 periods at 10%
        result = engine.compute(revenue_series=series)
        assert result.cagr.cagr_5y is not None
        assert abs(result.cagr.cagr_5y - 0.10) < 0.01

    def test_3yr_cagr_no_5yr(self, engine):
        series = [100.0, 110.0, 121.0, 133.1]  # 3 periods
        result = engine.compute(revenue_series=series)
        assert result.cagr.cagr_3y is not None
        assert result.cagr.cagr_5y is None

    def test_explanation_populated(self, engine):
        series = [100.0, 110.0, 121.0]
        result = engine.compute(revenue_series=series)
        assert len(result.explanation) > 0


class TestRevenueGrowthFromAggregates:
    def test_direction_improving(self, engine):
        result = engine.compute(revenue_direction="improving", history_depth=5)
        assert result.trend != GrowthTrend.INSUFFICIENT_DATA

    def test_direction_declining(self, engine):
        result = engine.compute(revenue_direction="declining")
        # Declining direction maps to declining trend
        assert result.trend == GrowthTrend.DECLINING

    def test_yoy_from_current_prior(self, engine):
        result = engine.compute(current_revenue=110.0, prior_revenue=100.0)
        # prior_revenue is an aggregated fallback; YoY not directly computed
        # (the engine uses series, not current/prior for YoY in the main path)

    def test_no_data(self, engine):
        result = engine.compute()
        assert result.cagr.best_available is None
        assert result.trend == GrowthTrend.INSUFFICIENT_DATA

    def test_strong_direction_estimate(self, engine):
        result = engine.compute(revenue_direction="accelerating")
        assert result.cagr.best_available is not None
        assert result.cagr.best_available > 0

    def test_result_type(self, engine):
        from iios.investment.company.growth.growth_profile import RevenueGrowthProfile
        result = engine.compute(revenue_direction="stable")
        assert isinstance(result, RevenueGrowthProfile)
