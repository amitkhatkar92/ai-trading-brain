"""tests/unit/investment/company/financials/test_income_statement.py
Tests for IncomeStatementEngine, RevenueAnalyzer, ExpenseAnalyzer, ProfitAnalyzer.
"""
import pytest

from iios.investment.company.financials.revenue_analyzer import RevenueAnalyzer
from iios.investment.company.financials.expense_analyzer import ExpenseAnalyzer
from iios.investment.company.financials.profit_analyzer import ProfitAnalyzer
from iios.investment.company.financials.income_statement_engine import IncomeStatementEngine
from iios.investment.company.financials.income_statement import IncomeStatement


class TestRevenueAnalyzer:
    def test_revenue_values(self, sample_is):
        m = RevenueAnalyzer().analyze(sample_is)
        assert m.revenue == 10000.0

    def test_revenue_per_share(self, sample_is):
        m = RevenueAnalyzer().analyze(sample_is)
        assert m.revenue_per_share == pytest.approx(10000.0 / 50.0)

    def test_other_income_pct(self, annual_period):
        is_ = IncomeStatement(
            period=annual_period,
            revenue=1000.0,
            other_income=100.0,
            total_income=1100.0,
        )
        m = RevenueAnalyzer().analyze(is_)
        assert m.other_income_pct == pytest.approx(100 / 1100 * 100, rel=1e-3)

    def test_no_shares_no_per_share(self, annual_period):
        is_ = IncomeStatement(period=annual_period, revenue=5000.0)
        m = RevenueAnalyzer().analyze(is_)
        assert m.revenue_per_share is None


class TestExpenseAnalyzer:
    def test_cogs_pct(self, sample_is):
        m = ExpenseAnalyzer().analyze(sample_is)
        assert m.cogs_pct == pytest.approx(65.0)

    def test_tax_rate(self, sample_is):
        m = ExpenseAnalyzer().analyze(sample_is)
        assert m.tax_rate == pytest.approx(25.0)

    def test_interest_pct(self, sample_is):
        m = ExpenseAnalyzer().analyze(sample_is)
        assert m.interest_pct == pytest.approx(1.5)

    def test_da_pct(self, sample_is):
        m = ExpenseAnalyzer().analyze(sample_is)
        assert m.da_pct == pytest.approx(2.0)


class TestProfitAnalyzer:
    def test_margins_extracted(self, sample_is):
        m = ProfitAnalyzer().analyze(sample_is)
        assert m.gross_margin == pytest.approx(35.0)
        assert m.ebitda_margin == pytest.approx(27.0)
        assert m.net_margin == pytest.approx(17.625)
        assert m.basic_eps == pytest.approx(35.25)

    def test_none_when_no_revenue(self, annual_period):
        is_ = IncomeStatement(period=annual_period, gross_profit=1000.0)
        m = ProfitAnalyzer().analyze(is_)
        assert m.gross_margin is None


class TestIncomeStatementEngine:
    def test_full_analysis(self, sample_is):
        engine = IncomeStatementEngine()
        intel = engine.analyze(sample_is)
        assert intel.period_label == sample_is.period.label
        assert intel.revenue.revenue == 10000.0
        assert intel.profit.net_margin == pytest.approx(17.625)
        assert intel.expenses.cogs_pct == pytest.approx(65.0)

    def test_to_dict_structure(self, sample_is):
        d = IncomeStatementEngine().analyze(sample_is).to_dict()
        assert "revenue" in d
        assert "expenses" in d
        assert "profit" in d
