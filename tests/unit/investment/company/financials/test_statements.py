"""tests/unit/investment/company/financials/test_statements.py
Tests for FinancialPeriod, BalanceSheet, IncomeStatement, CashFlowStatement, FinancialStatement.
"""
import pytest

from iios.investment.company.financials.financial_period import (
    FinancialPeriod, PeriodType, AccountingStandard,
)
from iios.investment.company.financials.balance_sheet import BalanceSheet
from iios.investment.company.financials.income_statement import IncomeStatement
from iios.investment.company.financials.cash_flow_statement import CashFlowStatement
from iios.investment.company.financials.financial_statement import FinancialStatement


class TestFinancialPeriod:
    def test_annual_label(self):
        p = FinancialPeriod.annual(2024, "2023-04-01", "2024-03-31")
        assert p.label == "FY24"
        assert p.period_type is PeriodType.ANNUAL

    def test_quarterly_label(self):
        p = FinancialPeriod.quarterly(2024, 1, "2023-04-01", "2023-06-30")
        assert p.label == "Q1FY24"
        assert p.quarter == 1

    def test_ttm_label(self):
        p = FinancialPeriod(PeriodType.TTM, 2024, None, "2023-04-01", "2024-03-31")
        assert "TTM" in p.label

    def test_to_dict(self):
        p = FinancialPeriod.annual(2023, "2022-04-01", "2023-03-31")
        d = p.to_dict()
        assert d["fiscal_year"] == 2023
        assert d["period_type"] == "annual"
        assert "label" in d

    def test_frozen(self):
        p = FinancialPeriod.annual(2024, "2023-04-01", "2024-03-31")
        with pytest.raises(Exception):
            p.fiscal_year = 9999  # type: ignore


class TestBalanceSheet:
    def test_total_debt(self, sample_bs):
        assert sample_bs.total_debt == pytest.approx(1500.0)

    def test_net_cash(self, sample_bs):
        assert sample_bs.net_cash == pytest.approx(500.0 - 1500.0)

    def test_working_capital(self, sample_bs):
        assert sample_bs.working_capital == pytest.approx(1800.0 - 1100.0)

    def test_completeness_not_zero(self, sample_bs):
        assert sample_bs.completeness_pct() > 0

    def test_to_dict_keys(self, sample_bs):
        d = sample_bs.to_dict()
        assert "total_assets" in d
        assert "total_equity" in d
        assert "net_cash" in d
        assert "working_capital" in d
        assert "completeness_pct" in d

    def test_from_dict(self, annual_period, bs_data_dict):
        bs = BalanceSheet.from_dict(bs_data_dict, annual_period)
        assert bs.total_assets == 5150.0
        assert bs.cash_and_equivalents == 500.0
        assert bs.period.label == "FY24"

    def test_from_dict_ignores_none(self, annual_period):
        bs = BalanceSheet.from_dict({"revenue": None, "total_assets": 1000.0}, annual_period)
        assert bs.total_assets == 1000.0

    def test_no_debt_returns_none(self, annual_period):
        bs = BalanceSheet(period=annual_period)
        assert bs.total_debt is None

    def test_all_none_net_cash(self, annual_period):
        bs = BalanceSheet(period=annual_period)
        assert bs.net_cash is None


class TestIncomeStatement:
    def test_gross_margin(self, sample_is):
        assert sample_is.gross_margin == pytest.approx(35.0)

    def test_ebitda_margin(self, sample_is):
        assert sample_is.ebitda_margin == pytest.approx(27.0)

    def test_net_margin(self, sample_is):
        assert sample_is.net_margin == pytest.approx(17.625)

    def test_completeness(self, sample_is):
        assert sample_is.completeness_pct() == pytest.approx(100.0)

    def test_to_dict_has_margins(self, sample_is):
        d = sample_is.to_dict()
        assert d["gross_margin"] == pytest.approx(35.0)
        assert d["net_margin"] is not None

    def test_from_dict(self, annual_period, is_data_dict):
        is_ = IncomeStatement.from_dict(is_data_dict, annual_period)
        assert is_.revenue == 10000.0
        assert is_.gross_profit == 3500.0

    def test_margin_none_when_no_revenue(self, annual_period):
        is_ = IncomeStatement(period=annual_period, gross_profit=500.0)
        assert is_.gross_margin is None


class TestCashFlowStatement:
    def test_free_cash_flow(self, sample_cf):
        # FCF = OCF - |CapEx| = 1862.5 - 400 = 1462.5
        assert sample_cf.free_cash_flow == pytest.approx(1462.5)

    def test_completeness(self, sample_cf):
        assert sample_cf.completeness_pct() == pytest.approx(100.0)

    def test_to_dict(self, sample_cf):
        d = sample_cf.to_dict()
        assert d["free_cash_flow"] == pytest.approx(1462.5)
        assert "operating_cash_flow" in d

    def test_from_dict(self, annual_period, cf_data_dict):
        cf = CashFlowStatement.from_dict(cf_data_dict, annual_period)
        assert cf.operating_cash_flow == 1862.5
        assert cf.capital_expenditure == -400.0

    def test_fcf_no_capex(self, annual_period):
        cf = CashFlowStatement(period=annual_period, operating_cash_flow=1000.0)
        assert cf.free_cash_flow == pytest.approx(1000.0)


class TestFinancialStatement:
    def test_is_complete_true(self, annual_period, sample_bs, sample_is, sample_cf):
        stmt = FinancialStatement(
            period=annual_period,
            balance_sheet=sample_bs,
            income_statement=sample_is,
            cash_flow=sample_cf,
        )
        assert stmt.is_complete is True

    def test_is_complete_false(self, annual_period, sample_bs):
        stmt = FinancialStatement(period=annual_period, balance_sheet=sample_bs)
        assert stmt.is_complete is False

    def test_completeness_pct_full(self, annual_period, sample_bs, sample_is, sample_cf):
        stmt = FinancialStatement(
            period=annual_period,
            balance_sheet=sample_bs,
            income_statement=sample_is,
            cash_flow=sample_cf,
        )
        assert stmt.completeness_pct() > 0

    def test_version_tracking(self, annual_period, sample_bs):
        stmt = FinancialStatement(period=annual_period, balance_sheet=sample_bs)
        stmt.stamp_version(source="bse", restated=False)
        assert stmt.current_version == 2
        assert len(stmt.versions) == 1

    def test_to_dict(self, annual_period, sample_bs, sample_is, sample_cf):
        stmt = FinancialStatement(
            period=annual_period,
            balance_sheet=sample_bs,
            income_statement=sample_is,
            cash_flow=sample_cf,
        )
        d = stmt.to_dict()
        assert d["is_complete"] is True
        assert "balance_sheet" in d
        assert "income_statement" in d
