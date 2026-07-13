"""tests/unit/investment/company/growth/test_earnings_growth.py"""
from __future__ import annotations

import pytest

from iios.investment.company.growth.earnings_growth import EarningsGrowthEngine
from iios.investment.company.growth.eps_growth import compute_eps_cagr_profile
from iios.investment.company.growth.margin_growth import MarginGrowthEngine
from iios.investment.company.growth.cashflow_growth import CashflowGrowthEngine
from iios.investment.company.growth.growth_profile import (
    EarningsGrowthProfile, MarginGrowthProfile, CashflowGrowthProfile,
    GrowthTrend, GrowthLabel,
)


@pytest.fixture
def e_engine():
    return EarningsGrowthEngine()


@pytest.fixture
def m_engine():
    return MarginGrowthEngine()


@pytest.fixture
def cf_engine():
    return CashflowGrowthEngine()


# ── EarningsGrowthEngine ───────────────────────────────────────────────────────

class TestEarningsGrowthEngine:
    def test_from_cagr_eps(self, e_engine):
        result = e_engine.compute(cagr_eps=0.18, eps_direction="improving", history_depth=7)
        assert isinstance(result, EarningsGrowthProfile)
        assert result.eps_cagr.best_available == pytest.approx(0.18)

    def test_direction_sets_trend(self, e_engine):
        result = e_engine.compute(cagr_eps=0.10, eps_direction="improving")
        assert result.trend not in (GrowthTrend.INSUFFICIENT_DATA,)

    def test_declining_trend(self, e_engine):
        result = e_engine.compute(cagr_eps=-0.05, eps_direction="declining")
        assert result.eps_cagr.label == GrowthLabel.NEGATIVE

    def test_no_data(self, e_engine):
        result = e_engine.compute()
        assert result.eps_cagr.best_available is None

    def test_eps_series_overrides_cagr(self, e_engine):
        series = [1.0, 1.2, 1.44, 1.728, 2.0736]  # ~20% CAGR
        result = e_engine.compute(cagr_eps=0.05, eps_series=series, history_depth=5)
        # The explicit series should dominate
        assert result.eps_cagr.best_available is not None
        assert result.eps_cagr.best_available > 0.15

    def test_net_income_series(self, e_engine):
        series = [100.0, 115.0, 132.25, 152.09]
        result = e_engine.compute(
            cagr_eps=0.10,
            net_income_series=series,
            history_depth=4,
        )
        assert result.net_income_cagr.best_available is not None

    def test_explanation_populated(self, e_engine):
        result = e_engine.compute(cagr_eps=0.15, eps_direction="improving")
        assert len(result.explanation) > 0


class TestEpsCAGRProfile:
    def test_from_series(self):
        series = [1.0, 1.1, 1.21, 1.331, 1.4641, 1.61051]
        profile = compute_eps_cagr_profile(
            cagr_eps=None,
            eps_direction=None,
            eps_series=series,
            history_depth=6,
        )
        assert profile.best_available is not None
        assert abs(profile.best_available - 0.10) < 0.01

    def test_from_cagr_eps_alone(self):
        profile = compute_eps_cagr_profile(
            cagr_eps=0.22,
            eps_direction="improving",
            history_depth=5,
        )
        assert profile.cagr_3y == pytest.approx(0.22)
        assert profile.best_available == pytest.approx(0.22)

    def test_none(self):
        profile = compute_eps_cagr_profile(None, None, None, 0)
        assert profile.best_available is None


# ── MarginGrowthEngine ─────────────────────────────────────────────────────────

class TestMarginGrowthEngine:
    def test_expanding_margins(self, m_engine):
        result = m_engine.compute(
            current_net_margin=0.15,
            avg_net_margin=0.10,
        )
        assert isinstance(result, MarginGrowthProfile)
        assert result.is_expanding is True
        assert result.is_contracting is False
        assert result.net_margin_expansion_bps > 0

    def test_contracting_margins(self, m_engine):
        result = m_engine.compute(
            current_net_margin=0.05,
            avg_net_margin=0.12,
        )
        assert result.is_contracting is True
        assert result.net_margin_expansion_bps < 0

    def test_stable_margins(self, m_engine):
        result = m_engine.compute(
            current_net_margin=0.10,
            avg_net_margin=0.10,
        )
        assert result.is_expanding is False
        assert result.is_contracting is False

    def test_no_data(self, m_engine):
        result = m_engine.compute()
        assert result.net_margin_expansion_bps is None

    def test_basis_points_calculation(self, m_engine):
        result = m_engine.compute(
            current_net_margin=0.12,
            avg_net_margin=0.10,
        )
        assert abs(result.net_margin_expansion_bps - 200.0) < 0.1

    def test_volatile_margins(self, m_engine):
        result = m_engine.compute(
            current_net_margin=0.12,
            avg_net_margin=0.10,
            margin_volatility=0.8,
        )
        assert result.trend == GrowthTrend.VOLATILE


# ── CashflowGrowthEngine ───────────────────────────────────────────────────────

class TestCashflowGrowthEngine:
    def test_fcf_margin_computed(self, cf_engine):
        result = cf_engine.compute(
            current_revenue=1_000_000.0,
            current_fcf=120_000.0,
            avg_fcf_margin=0.10,
        )
        assert isinstance(result, CashflowGrowthProfile)
        assert result.current_fcf_margin == pytest.approx(0.12)

    def test_fcf_margin_expanding(self, cf_engine):
        result = cf_engine.compute(
            current_revenue=1_000_000.0,
            current_fcf=150_000.0,
            avg_fcf_margin=0.08,
        )
        assert result.fcf_margin_trend == GrowthTrend.ACCELERATING

    def test_fcf_margin_contracting(self, cf_engine):
        result = cf_engine.compute(
            current_revenue=1_000_000.0,
            current_fcf=50_000.0,
            avg_fcf_margin=0.12,
        )
        assert result.fcf_margin_trend == GrowthTrend.DECELERATING

    def test_fcf_from_series(self, cf_engine):
        series = [100_000.0, 115_000.0, 132_250.0, 152_088.0, 174_901.0]
        result = cf_engine.compute(
            current_revenue=1_000_000.0,
            fcf_series=series,
        )
        assert result.fcf_cagr.best_available is not None
        assert result.fcf_cagr.best_available > 0

    def test_no_data(self, cf_engine):
        result = cf_engine.compute()
        assert result.current_fcf_margin is None
