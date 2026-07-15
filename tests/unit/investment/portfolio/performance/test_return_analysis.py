"""Tests for return_analysis, return_statistics, rolling_returns, annualized_returns."""
import pytest
from iios.investment.portfolio.performance.return_analysis import (
    analyze_returns, total_return_from_nav, period_returns_from_nav,
)
from iios.investment.portfolio.performance.return_statistics import (
    compute_return_statistics,
)
from iios.investment.portfolio.performance.rolling_returns import (
    compute_rolling_returns, _rolling_compound,
)
from iios.investment.portfolio.performance.annualized_returns import (
    compute_annualized_returns, _compound, _geo_mean,
)


class TestReturnAnalysis:
    def test_analyze_from_positions(self, positions_diverse):
        r = analyze_returns(positions_diverse, portfolio_id="p1", period="1y", period_years=1.0)
        assert r.portfolio_id == "p1"
        assert r.n_positions == 5
        assert abs(r.total_period_return) < 1.0   # reasonable range
        assert r.annualized_return == pytest.approx(r.total_period_return, abs=0.01)

    def test_analyze_with_nav_series(self, positions_diverse, nav_series_growing):
        r = analyze_returns(positions_diverse, portfolio_id="p2", period="2y",
                            period_years=2.0, nav_series=nav_series_growing)
        assert r.total_period_return > 0.0
        assert r.annualized_return < r.total_period_return   # annualized < total for >1y

    def test_analyze_flat_nav(self, positions_diverse, nav_series_flat):
        r = analyze_returns(positions_diverse, portfolio_id="p3", period="1y",
                            period_years=1.0, nav_series=nav_series_flat)
        assert abs(r.total_period_return) < 0.001

    def test_top_contributor(self, positions_diverse):
        r = analyze_returns(positions_diverse, portfolio_id="p4", period="1y", period_years=1.0)
        assert r.top_contributor != ""
        assert r.top_contribution >= r.bottom_contribution

    def test_excess_return(self, positions_diverse):
        r = analyze_returns(positions_diverse, portfolio_id="p5", period="1y", period_years=1.0)
        assert isinstance(r.excess_return, float)

    def test_total_return_from_nav(self, nav_series_growing):
        tr = total_return_from_nav(nav_series_growing)
        assert tr > 0.0

    def test_period_returns_from_nav(self, nav_series_growing):
        rets = period_returns_from_nav(nav_series_growing)
        assert len(rets) == len(nav_series_growing) - 1
        assert all(r > -0.5 for r in rets)

    def test_empty_positions(self):
        r = analyze_returns([], portfolio_id="empty", period="1y", period_years=1.0)
        assert r.n_positions == 0
        assert r.total_period_return == 0.0


class TestReturnStatistics:
    def test_basic_stats(self, monthly_returns_positive):
        s = compute_return_statistics(monthly_returns_positive, portfolio_id="p1")
        assert s.n_observations == 12
        assert s.mean_return > 0.0
        assert s.std_return >= 0.0
        assert 0.0 <= s.win_rate <= 1.0

    def test_win_rate_all_positive(self, monthly_returns_positive):
        s = compute_return_statistics(monthly_returns_positive, portfolio_id="p1")
        assert s.win_rate == 1.0

    def test_mixed_returns(self, monthly_returns_mixed):
        s = compute_return_statistics(monthly_returns_mixed, portfolio_id="p1")
        assert s.win_rate < 1.0
        assert s.negative_periods > 0

    def test_percentiles_ordered(self, monthly_returns_mixed):
        s = compute_return_statistics(monthly_returns_mixed, portfolio_id="p1")
        assert s.p5_return <= s.p25_return <= s.median_return <= s.p75_return <= s.p95_return

    def test_annualized_vol(self, monthly_returns_positive):
        s = compute_return_statistics(monthly_returns_positive, portfolio_id="p1",
                                      annualize=True, periods_per_year=12)
        assert s.annual_vol > s.std_return

    def test_empty_returns(self):
        s = compute_return_statistics([], portfolio_id="p1")
        assert s.n_observations == 0

    def test_single_value(self):
        s = compute_return_statistics([0.05], portfolio_id="p1")
        assert s.n_observations == 1
        assert s.mean_return == pytest.approx(0.05)


class TestRollingReturns:
    def test_basic_rolling(self, monthly_returns_positive):
        r = compute_rolling_returns(monthly_returns_positive, windows=[1, 3, 6, 12])
        assert r.n_periods == 12
        assert r.latest_1m is not None
        assert r.latest_12m is not None

    def test_window_larger_than_data(self):
        r = compute_rolling_returns([0.01, 0.02], windows=[3, 6])
        assert len(r.windows) == 0

    def test_window_results(self, monthly_returns_positive):
        r = compute_rolling_returns(monthly_returns_positive, windows=[3])
        w = r.windows[0]
        assert w.window_size == 3
        assert w.min_return <= w.avg_return <= w.max_return

    def test_win_rate_range(self, monthly_returns_mixed):
        r = compute_rolling_returns(monthly_returns_mixed, windows=[3])
        if r.windows:
            assert 0.0 <= r.windows[0].win_rate <= 1.0

    def test_rolling_compound_simple(self):
        rets = [0.10, 0.10, 0.10]
        result = _rolling_compound(rets, 3)
        assert len(result) == 1
        expected = (1.1 ** 3) - 1
        assert abs(result[0] - expected) < 1e-9

    def test_empty(self):
        r = compute_rolling_returns([])
        assert r.n_periods == 0


class TestAnnualizedReturns:
    def test_cagr_12m(self, monthly_returns_positive):
        r = compute_annualized_returns(monthly_returns_positive, portfolio_id="p1")
        assert r.cagr_1y is not None
        assert r.cagr_1y > 0.0

    def test_cagr_since_inception(self, monthly_returns_positive):
        r = compute_annualized_returns(monthly_returns_positive, portfolio_id="p1")
        assert r.cagr_since_inception is not None

    def test_cagr_3y_none_when_short(self, monthly_returns_positive):
        r = compute_annualized_returns(monthly_returns_positive, portfolio_id="p1")
        assert r.cagr_3y is None   # only 12 months

    def test_cagr_3y_available(self, monthly_returns_positive):
        long_returns = monthly_returns_positive * 3
        r = compute_annualized_returns(long_returns, portfolio_id="p1")
        assert r.cagr_3y is not None

    def test_arithmetic_mean(self, monthly_returns_positive):
        r = compute_annualized_returns(monthly_returns_positive, portfolio_id="p1")
        expected = sum(monthly_returns_positive) / len(monthly_returns_positive)
        assert abs(r.arithmetic_mean - expected) < 1e-9

    def test_empty(self):
        r = compute_annualized_returns([], portfolio_id="p1")
        assert r.cagr_1y is None

    def test_compound_helper(self):
        assert abs(_compound([0.1, 0.1]) - 0.21) < 1e-9

    def test_geo_mean_positive(self):
        m = _geo_mean([0.01, 0.02, 0.03])
        assert m is not None and m > 0.0

    def test_geo_mean_empty(self):
        assert _geo_mean([]) is None
