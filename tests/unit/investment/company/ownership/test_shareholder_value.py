"""tests/unit/investment/company/ownership/test_shareholder_value.py"""
from __future__ import annotations

import pytest

from iios.investment.company.ownership.value_creation import ShareholderValueEngine
from iios.investment.company.ownership.ownership_profile import (
    ShareholderValueProfile, ShareholderValueLabel,
)
from iios.investment.company.ownership.economic_return import (
    score_economic_value_added,
    score_earnings_power,
    score_growth_value,
)
from iios.investment.company.ownership.capital_productivity import (
    score_capital_productivity, score_reinvestment_effectiveness,
)


@pytest.fixture
def engine():
    return ShareholderValueEngine()


class TestShareholderValueEngine:
    def test_returns_profile(self, engine):
        result = engine.compute()
        assert isinstance(result, ShareholderValueProfile)

    def test_high_value_creator(self, engine):
        result = engine.compute(
            avg_roic=0.22, avg_roe=0.20, fcf_margin=0.15,
            eps_cagr=0.18, revenue_cagr=0.14,
            net_margin=0.12, avg_net_margin=0.10,
            consistency_score=80.0, sustainability_score=72.0,
        )
        assert result.overall_value_score >= 60.0
        assert result.value_label in (
            ShareholderValueLabel.EXCEPTIONAL, ShareholderValueLabel.STRONG,
            ShareholderValueLabel.ADEQUATE,
        )

    def test_value_destroyer(self, engine):
        result = engine.compute(
            avg_roic=0.03, avg_roe=0.02, fcf_margin=-0.05,
            eps_cagr=-0.10, revenue_cagr=-0.05,
            net_margin=-0.03, avg_net_margin=-0.02,
        )
        assert result.overall_value_score < 45.0

    def test_all_scores_in_range(self, engine):
        result = engine.compute(avg_roic=0.15, fcf_margin=0.10, eps_cagr=0.12)
        for s in [
            result.economic_return_score, result.capital_productivity_score,
            result.dividend_sustainability_score, result.earnings_power_score,
            result.growth_value_score, result.overall_value_score,
        ]:
            assert 0.0 <= s <= 100.0

    def test_growth_snapshot_boost(self, engine, mock_growth):
        without = engine.compute(avg_roic=0.15, eps_cagr=0.12)
        with_gs = engine.compute(avg_roic=0.15, eps_cagr=0.12, growth_snapshot=mock_growth)
        assert with_gs.growth_value_score >= without.growth_value_score - 0.01

    def test_management_boost(self, engine, mock_management):
        without = engine.compute(avg_roic=0.15)
        with_ms = engine.compute(avg_roic=0.15, management_snapshot=mock_management)
        assert with_ms.capital_productivity_score >= without.capital_productivity_score - 0.01


class TestEconomicReturn:
    def test_high_roic(self):
        s = score_economic_value_added(0.22, 0.20, 0.15)
        assert s >= 75.0

    def test_low_roic(self):
        s = score_economic_value_added(0.05, 0.06, -0.02)
        assert s < 40.0

    def test_no_data(self):
        s = score_economic_value_added(None, None, None)
        assert 0.0 <= s <= 100.0


class TestEarningsPower:
    def test_strong_margins(self):
        s = score_earnings_power(0.15, 0.12, 0.18, 80.0)
        assert s >= 75.0

    def test_negative_margins(self):
        s = score_earnings_power(-0.05, -0.03, -0.10, 20.0)
        assert s < 20.0

    def test_none(self):
        s = score_earnings_power(None, None, None, None)
        assert 0.0 <= s <= 100.0


class TestGrowthValue:
    def test_strong_growth(self):
        s = score_growth_value(0.20, 0.18, 75.0)
        assert s >= 80.0

    def test_negative_growth(self):
        s = score_growth_value(-0.05, -0.10, 20.0)
        assert s < 25.0

    def test_none(self):
        s = score_growth_value(None, None, None)
        assert s == pytest.approx(50.0)


class TestCapitalProductivity:
    def test_high_productivity(self):
        s = score_capital_productivity(
            fcf=120_000, total_equity=500_000, total_debt=100_000,
            avg_roic=0.20, revenue_cagr=0.15,
        )
        assert s >= 60.0

    def test_negative_fcf(self):
        s = score_capital_productivity(
            fcf=-50_000, total_equity=500_000, total_debt=100_000,
            avg_roic=0.03, revenue_cagr=-0.05,
        )
        assert s < 30.0

    def test_none_inputs(self):
        s = score_capital_productivity(None, None, None, None, None)
        assert 0.0 <= s <= 100.0


class TestReinvestmentEffectiveness:
    def test_high_growth_high_roic(self):
        s = score_reinvestment_effectiveness(0.20, 0.22, -80_000, 1_000_000)
        assert s >= 75.0

    def test_none(self):
        s = score_reinvestment_effectiveness(None, None, None, None)
        assert s == pytest.approx(50.0)
