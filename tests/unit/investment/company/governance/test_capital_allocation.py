"""tests/unit/investment/company/governance/test_capital_allocation.py"""
from __future__ import annotations

import pytest

from iios.investment.company.governance.capital_allocation import CapitalAllocationEngine
from iios.investment.company.governance.management_profile import (
    CapitalAllocationProfile, CapitalAllocationLabel,
)


@pytest.fixture
def engine():
    return CapitalAllocationEngine()


class TestCapitalAllocationEngine:
    def test_returns_profile(self, engine):
        result = engine.compute()
        assert isinstance(result, CapitalAllocationProfile)

    def test_excellent_allocator(self, engine):
        result = engine.compute(
            avg_roic=0.22, avg_roe=0.20, fcf_margin=0.15,
            avg_ocf_to_ni=1.1, dividend_payout_ratio=0.30,
            debt_to_equity=0.4, eps_cagr=0.18, revenue_cagr=0.14,
        )
        assert result.overall_capital_score >= 65.0
        assert result.capital_label in (
            CapitalAllocationLabel.EXCEPTIONAL, CapitalAllocationLabel.DISCIPLINED,
            CapitalAllocationLabel.ADEQUATE,
        )

    def test_poor_allocator(self, engine):
        result = engine.compute(
            avg_roic=0.02, avg_roe=0.03, fcf_margin=-0.05,
            avg_ocf_to_ni=0.5, dividend_payout_ratio=0.90,
            debt_to_equity=4.0,
        )
        assert result.overall_capital_score < 45.0

    def test_high_debt_penalty(self, engine):
        low_debt  = engine.compute(debt_to_equity=0.3, avg_roic=0.15)
        high_debt = engine.compute(debt_to_equity=3.0, avg_roic=0.15)
        assert low_debt.debt_management_score > high_debt.debt_management_score
        assert low_debt.overall_capital_score > high_debt.overall_capital_score

    def test_high_payout_penalty(self, engine):
        fair_payout = engine.compute(dividend_payout_ratio=0.35)
        high_payout = engine.compute(dividend_payout_ratio=0.95)
        assert fair_payout.dividend_policy_score >= high_payout.dividend_policy_score

    def test_roic_drives_efficiency(self, engine):
        low_roic  = engine.compute(avg_roic=0.03)
        high_roic = engine.compute(avg_roic=0.25)
        assert high_roic.capital_efficiency_score > low_roic.capital_efficiency_score

    def test_all_scores_in_range(self, engine):
        result = engine.compute(avg_roic=0.15, fcf_margin=0.10, debt_to_equity=0.5)
        for score in [
            result.capital_efficiency_score, result.reinvestment_quality_score,
            result.dividend_policy_score, result.debt_management_score,
            result.overall_capital_score,
        ]:
            assert 0.0 <= score <= 100.0

    def test_label_consistency(self, engine):
        result = engine.compute()
        assert isinstance(result.capital_label, CapitalAllocationLabel)

    def test_sustainability_helps(self, engine):
        without_sus = engine.compute(avg_roic=0.15)
        with_sus    = engine.compute(avg_roic=0.15, sustainability=80.0)
        assert with_sus.reinvestment_quality_score >= without_sus.reinvestment_quality_score
