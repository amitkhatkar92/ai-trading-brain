"""Tests for risk-adjusted returns and performance ratios."""
import pytest
from iios.investment.portfolio.performance.risk_adjusted_returns import (
    compute_risk_adjusted_returns,
)
from iios.investment.portfolio.performance.performance_ratios import (
    compute_all_ratios,
)
from iios.investment.portfolio.performance.ratio_statistics import RatioStatistics


class TestRiskAdjustedReturns:
    def test_sharpe_positive_for_good_return(self, positions_diverse):
        r = compute_risk_adjusted_returns(
            positions_diverse, portfolio_return=0.20, portfolio_id="p1"
        )
        assert r.sharpe_ratio > 0.0

    def test_sharpe_negative_for_poor_return(self, positions_diverse):
        r = compute_risk_adjusted_returns(
            positions_diverse, portfolio_return=0.03, portfolio_id="p1"
        )
        assert r.sharpe_ratio < 0.0

    def test_sortino_geq_sharpe_for_normal_dist(self, positions_diverse):
        # Sortino should be >= Sharpe when downside dev <= vol
        r = compute_risk_adjusted_returns(
            positions_diverse, portfolio_return=0.15, portfolio_id="p1"
        )
        # Proxied: sortino uses 70% of vol as downside dev
        assert r.sortino_ratio >= r.sharpe_ratio * 0.9  # approx

    def test_calmar_zero_when_no_drawdown(self, positions_diverse):
        r = compute_risk_adjusted_returns(
            positions_diverse, portfolio_return=0.15,
            max_drawdown=0.0, portfolio_id="p1"
        )
        assert r.calmar_ratio == 0.0

    def test_calmar_positive_with_drawdown(self, positions_diverse):
        r = compute_risk_adjusted_returns(
            positions_diverse, portfolio_return=0.15,
            max_drawdown=0.10, portfolio_id="p1"
        )
        assert r.calmar_ratio > 0.0

    def test_omega_positive(self, positions_diverse):
        r = compute_risk_adjusted_returns(
            positions_diverse, portfolio_return=0.15, portfolio_id="p1"
        )
        assert r.omega_ratio >= 0.0

    def test_omega_with_return_series(self, positions_diverse, monthly_returns_positive):
        r = compute_risk_adjusted_returns(
            positions_diverse, portfolio_return=0.15, portfolio_id="p1",
            return_series=monthly_returns_positive
        )
        assert r.omega_ratio > 0.0
        assert r.used_return_series is True

    def test_treynor_scales_with_beta(self, positions_diverse):
        r1 = compute_risk_adjusted_returns(
            positions_diverse, portfolio_return=0.15, beta=0.8, portfolio_id="p1"
        )
        r2 = compute_risk_adjusted_returns(
            positions_diverse, portfolio_return=0.15, beta=1.6, portfolio_id="p1"
        )
        # Higher beta → lower treynor for same return
        assert r1.treynor_ratio > r2.treynor_ratio

    def test_to_dict(self, positions_diverse):
        r = compute_risk_adjusted_returns(
            positions_diverse, portfolio_return=0.15, portfolio_id="p1"
        )
        d = r.to_dict()
        assert "sharpe_ratio" in d
        assert "sortino_ratio" in d
        assert "calmar_ratio" in d

    def test_zero_positions(self):
        r = compute_risk_adjusted_returns([], portfolio_return=0.10, portfolio_id="p1")
        assert isinstance(r.sharpe_ratio, float)


class TestPerformanceRatios:
    def test_information_ratio_positive_alpha(self, positions_diverse):
        rar = compute_risk_adjusted_returns(positions_diverse, 0.20, portfolio_id="p1")
        ratios = compute_all_ratios(rar, benchmark_return=0.12, tracking_error=0.05)
        assert ratios.information_ratio > 0.0

    def test_information_ratio_negative_alpha(self, positions_diverse):
        rar = compute_risk_adjusted_returns(positions_diverse, 0.08, portfolio_id="p1")
        ratios = compute_all_ratios(rar, benchmark_return=0.12, tracking_error=0.05)
        assert ratios.information_ratio < 0.0

    def test_modigliani_ratio(self, positions_diverse):
        rar = compute_risk_adjusted_returns(positions_diverse, 0.15, portfolio_id="p1")
        ratios = compute_all_ratios(rar, benchmark_return=0.12, benchmark_vol=0.16)
        # M² = sharpe × bmk_vol + rf
        expected = rar.sharpe_ratio * 0.16 + 0.065
        assert abs(ratios.modigliani_ratio - expected) < 0.001

    def test_upside_potential_ratio_positive_for_good_returns(
        self, positions_diverse, monthly_returns_positive
    ):
        rar = compute_risk_adjusted_returns(positions_diverse, 0.15, portfolio_id="p1")
        ratios = compute_all_ratios(rar, return_series=monthly_returns_positive)
        assert ratios.upside_potential_ratio > 0.0

    def test_to_dict(self, positions_diverse):
        rar = compute_risk_adjusted_returns(positions_diverse, 0.15, portfolio_id="p1")
        ratios = compute_all_ratios(rar, benchmark_return=0.12)
        d = ratios.to_dict()
        assert "sharpe" in d
        assert "information_ratio" in d


class TestRatioStatistics:
    def test_empty_snapshot(self):
        stats = RatioStatistics()
        snap = stats.snapshot()
        assert snap.n_runs == 0

    def test_record_and_snapshot(self, positions_diverse):
        stats = RatioStatistics()
        for i in range(5):
            rar = compute_risk_adjusted_returns(
                positions_diverse, 0.10 + i * 0.02, portfolio_id="p1"
            )
            ratios = compute_all_ratios(rar)
            stats.record(ratios)
        snap = stats.snapshot()
        assert snap.n_runs == 5
        assert 0.0 <= snap.pct_above_sharpe_1 <= 1.0

    def test_max_runs_trimming(self, positions_diverse):
        stats = RatioStatistics(max_runs=3)
        for i in range(10):
            rar = compute_risk_adjusted_returns(
                positions_diverse, 0.15, portfolio_id="p1"
            )
            ratios = compute_all_ratios(rar)
            stats.record(ratios)
        snap = stats.snapshot()
        assert snap.n_runs == 3
