"""tests/unit/investment/company/ownership/test_capital_allocation.py"""
from __future__ import annotations

import pytest

from iios.investment.company.ownership.capital_allocation_engine import OwnershipCapitalAllocationEngine
from iios.investment.company.ownership.ownership_profile import (
    OwnershipCapitalAllocationProfile, CapitalAllocationQuality,
)
from iios.investment.company.ownership.capital_return import (
    score_dividend_sustainability,
    score_total_shareholder_return_quality,
    score_cash_return_policy,
)
from iios.investment.company.ownership.capital_deployment import (
    score_capex_quality, score_cash_utilization,
)
from iios.investment.company.ownership.capital_efficiency import (
    score_asset_utilization,
    score_capital_efficiency_composite,
)


@pytest.fixture
def engine():
    return OwnershipCapitalAllocationEngine()


class TestOwnershipCapitalAllocationEngine:
    def test_returns_profile(self, engine):
        result = engine.compute()
        assert isinstance(result, OwnershipCapitalAllocationProfile)

    def test_strong_capital_allocator(self, engine):
        result = engine.compute(
            avg_roic=0.22, avg_roe=0.20, fcf_margin=0.15,
            avg_ocf_to_ni=1.1, payout_ratio=0.30, eps_cagr=0.18,
            revenue_cagr=0.14, total_equity=500_000, total_debt=100_000,
        )
        assert result.overall_capital_score >= 60.0

    def test_poor_allocator(self, engine):
        result = engine.compute(
            avg_roic=0.02, fcf_margin=-0.05,
            payout_ratio=0.95, total_equity=100_000, total_debt=500_000,
        )
        assert result.overall_capital_score < 50.0

    def test_quality_label(self, engine):
        result = engine.compute()
        assert isinstance(result.capital_quality, CapitalAllocationQuality)

    def test_all_scores_in_range(self, engine):
        result = engine.compute(avg_roic=0.15, fcf_margin=0.10, payout_ratio=0.35)
        for s in [
            result.dividend_policy_score, result.buyback_quality_score,
            result.reinvestment_score, result.debt_management_score,
            result.capex_efficiency_score, result.cash_utilization_score,
            result.overall_capital_score,
        ]:
            assert 0.0 <= s <= 100.0

    def test_low_debt_better(self, engine):
        low  = engine.compute(total_equity=500_000, total_debt=100_000)
        high = engine.compute(total_equity=500_000, total_debt=2_000_000)
        assert low.debt_management_score > high.debt_management_score

    def test_management_boost(self, engine, mock_management):
        without = engine.compute(avg_roic=0.15, payout_ratio=0.35)
        with_ms = engine.compute(avg_roic=0.15, payout_ratio=0.35,
                                 management_snapshot=mock_management)
        assert with_ms.overall_capital_score >= without.overall_capital_score - 0.01


class TestDividendSustainability:
    def test_low_payout_sustainable(self):
        s = score_dividend_sustainability(0.30, 0.15, 1.1, 12.0)
        assert s >= 70.0

    def test_high_payout_risky(self):
        s = score_dividend_sustainability(0.90, -0.05, 0.60, 5.0)
        assert s < 40.0

    def test_no_data(self):
        s = score_dividend_sustainability(None, None, None, None)
        assert 30.0 <= s <= 60.0


class TestTotalShareholderReturn:
    def test_high_quality(self):
        s = score_total_shareholder_return_quality(0.30, 0.20, 0.15, 0.18)
        assert s >= 65.0

    def test_none_inputs(self):
        s = score_total_shareholder_return_quality(None, None, None, None)
        assert 0.0 <= s <= 100.0


class TestCashReturnPolicy:
    def test_strong_fcf_coverage(self):
        s = score_cash_return_policy(
            fcf=150_000, net_income=80_000, payout_ratio=0.30
        )
        assert s >= 80.0

    def test_negative_fcf(self):
        s = score_cash_return_policy(-50_000, 80_000, 0.30)
        assert s <= 20.0


class TestCapexQuality:
    def test_high_roic_high_growth(self):
        s = score_capex_quality(-80_000, 1_000_000, 0.15, 0.20)
        assert s >= 65.0

    def test_no_data(self):
        s = score_capex_quality(None, None, None, None)
        assert s == pytest.approx(50.0)


class TestCashUtilization:
    def test_optimal_cash(self):
        s = score_cash_utilization(200_000, 1_000_000, 120_000)
        assert s >= 75.0

    def test_excess_cash(self):
        s_low  = score_cash_utilization(200_000, 1_000_000, 120_000)
        s_high = score_cash_utilization(800_000, 1_000_000, 120_000)
        assert s_low >= s_high


class TestAssetUtilization:
    def test_high_ratio(self):
        assert score_asset_utilization(1_500_000, 1_000_000) >= 80.0

    def test_low_ratio(self):
        assert score_asset_utilization(100_000, 1_000_000) < 40.0


class TestCapitalEfficiencyComposite:
    def test_all_inputs(self):
        s = score_capital_efficiency_composite(0.18, 0.20, 0.12, 1_000_000, 900_000)
        assert 0.0 <= s <= 100.0

    def test_no_inputs(self):
        s = score_capital_efficiency_composite(None, None, None)
        assert 0.0 <= s <= 100.0
