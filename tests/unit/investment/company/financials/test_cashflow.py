"""tests/unit/investment/company/financials/test_cashflow.py
Tests for CashFlowEngine and all sub-analyzers.
"""
import pytest

from iios.investment.company.financials.operating_cashflow import OperatingCashFlowAnalyzer
from iios.investment.company.financials.investing_cashflow import InvestingCashFlowAnalyzer
from iios.investment.company.financials.financing_cashflow import FinancingCashFlowAnalyzer
from iios.investment.company.financials.free_cashflow import FreeCashFlowAnalyzer
from iios.investment.company.financials.cashflow_engine import CashFlowEngine
from iios.investment.company.financials.cash_flow_statement import CashFlowStatement


class TestOperatingCashFlow:
    def test_ocf_value(self, sample_cf, sample_is):
        m = OperatingCashFlowAnalyzer().analyze(sample_cf, sample_is)
        assert m.operating_cash_flow == pytest.approx(1862.5)
        assert m.is_cash_generative is True

    def test_ocf_to_net_income(self, sample_cf, sample_is):
        m = OperatingCashFlowAnalyzer().analyze(sample_cf, sample_is)
        # 1862.5 / 1762.5 ≈ 1.0567
        assert m.ocf_to_net_income == pytest.approx(1862.5 / 1762.5, rel=1e-3)

    def test_negative_ocf(self, annual_period):
        cf = CashFlowStatement(period=annual_period, operating_cash_flow=-100.0)
        m = OperatingCashFlowAnalyzer().analyze(cf)
        assert m.is_cash_generative is False


class TestInvestingCashFlow:
    def test_capex_abs(self, sample_cf):
        m = InvestingCashFlowAnalyzer().analyze(sample_cf)
        assert m.capex_abs == pytest.approx(400.0)
        assert m.is_net_investor is True

    def test_capex_to_revenue(self, sample_cf, sample_is):
        m = InvestingCashFlowAnalyzer().analyze(sample_cf, sample_is)
        assert m.capex_to_revenue_pct == pytest.approx(400 / 10000 * 100)

    def test_no_capex(self, annual_period):
        cf = CashFlowStatement(period=annual_period, investing_cash_flow=100.0)
        m = InvestingCashFlowAnalyzer().analyze(cf)
        assert m.capex_abs is None
        assert m.is_net_investor is False


class TestFinancingCashFlow:
    def test_net_debt_change(self, sample_cf):
        m = FinancingCashFlowAnalyzer().analyze(sample_cf)
        # 200 - 300 = -100 → net repayer
        assert m.net_debt_change == pytest.approx(-100.0)
        assert m.is_net_borrower is False

    def test_returning_capital(self, sample_cf):
        m = FinancingCashFlowAnalyzer().analyze(sample_cf)
        # dividends_paid = -250 → returning capital
        assert m.is_returning_capital is True

    def test_no_capital_return(self, annual_period):
        cf = CashFlowStatement(period=annual_period, financing_cash_flow=0.0)
        m = FinancingCashFlowAnalyzer().analyze(cf)
        assert m.is_returning_capital is False


class TestFreeCashFlow:
    def test_fcf_value(self, sample_cf, sample_is):
        m = FreeCashFlowAnalyzer().analyze(sample_cf, sample_is)
        assert m.free_cash_flow == pytest.approx(1462.5)
        assert m.is_fcf_positive is True

    def test_ocf_covers_capex(self, sample_cf):
        m = FreeCashFlowAnalyzer().analyze(sample_cf)
        assert m.ocf_covers_capex is True

    def test_fcf_margin(self, sample_cf, sample_is):
        m = FreeCashFlowAnalyzer().analyze(sample_cf, sample_is)
        assert m.fcf_margin == pytest.approx(1462.5 / 10000 * 100, rel=1e-3)

    def test_negative_fcf(self, annual_period):
        cf = CashFlowStatement(
            period=annual_period,
            operating_cash_flow=100.0,
            capital_expenditure=-500.0,
        )
        m = FreeCashFlowAnalyzer().analyze(cf)
        assert m.is_fcf_positive is False


class TestCashFlowEngine:
    def test_full_analysis(self, sample_cf, sample_is):
        engine = CashFlowEngine()
        intel = engine.analyze(sample_cf, sample_is)
        assert intel.period_label == sample_cf.period.label
        assert intel.free_cf.free_cash_flow == pytest.approx(1462.5)
        assert intel.operating.is_cash_generative is True
        assert intel.investing.is_net_investor is True
        assert intel.financing.is_returning_capital is True

    def test_to_dict(self, sample_cf, sample_is):
        d = CashFlowEngine().analyze(sample_cf, sample_is).to_dict()
        assert "operating" in d
        assert "investing" in d
        assert "financing" in d
        assert "free_cf" in d
