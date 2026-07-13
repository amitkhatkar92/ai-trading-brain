"""tests/unit/investment/company/financials/conftest.py
Shared fixtures for financial statement tests.
"""
import pytest

from iios.investment.company.financials.financial_period import (
    FinancialPeriod, PeriodType, AccountingStandard,
)
from iios.investment.company.financials.balance_sheet import BalanceSheet
from iios.investment.company.financials.income_statement import IncomeStatement
from iios.investment.company.financials.cash_flow_statement import CashFlowStatement


@pytest.fixture
def annual_period():
    return FinancialPeriod.annual(
        fiscal_year=2024,
        start_date="2023-04-01",
        end_date="2024-03-31",
        standard=AccountingStandard.IND_AS,
    )


@pytest.fixture
def q1_period():
    return FinancialPeriod.quarterly(2024, 1, "2023-04-01", "2023-06-30")


@pytest.fixture
def q2_period():
    return FinancialPeriod.quarterly(2024, 2, "2023-07-01", "2023-09-30")


@pytest.fixture
def q3_period():
    return FinancialPeriod.quarterly(2024, 3, "2023-10-01", "2023-12-31")


@pytest.fixture
def q4_period():
    return FinancialPeriod.quarterly(2024, 4, "2024-01-01", "2024-03-31")


@pytest.fixture
def sample_bs(annual_period):
    return BalanceSheet(
        period=annual_period,
        cash_and_equivalents=500.0,
        short_term_investments=100.0,
        accounts_receivable=800.0,
        inventory=400.0,
        total_current_assets=1800.0,
        property_plant_equipment=3000.0,
        goodwill=200.0,
        intangible_assets=150.0,
        total_non_current_assets=3350.0,
        total_assets=5150.0,
        accounts_payable=600.0,
        short_term_debt=300.0,
        other_current_liabilities=200.0,
        total_current_liabilities=1100.0,
        long_term_debt=1200.0,
        total_non_current_liabilities=1200.0,
        total_liabilities=2300.0,
        common_stock=500.0,
        retained_earnings=1850.0,
        additional_paid_in_capital=500.0,
        total_equity=2850.0,
        total_liabilities_and_equity=5150.0,
    )


@pytest.fixture
def sample_is(annual_period):
    return IncomeStatement(
        period=annual_period,
        revenue=10000.0,
        cost_of_revenue=6500.0,
        gross_profit=3500.0,
        selling_general_admin=1000.0,
        depreciation_amortization=200.0,
        ebitda=2700.0,
        ebit=2500.0,
        interest_expense=150.0,
        ebt=2350.0,
        tax_expense=587.5,
        effective_tax_rate=25.0,
        net_income=1762.5,
        net_income_to_common=1762.5,
        basic_eps=35.25,
        diluted_eps=34.80,
        shares_outstanding_basic=50.0,
        shares_outstanding_diluted=50.64,
    )


@pytest.fixture
def sample_cf(annual_period):
    return CashFlowStatement(
        period=annual_period,
        net_income_cf=1762.5,
        depreciation_amortization_cf=200.0,
        changes_in_working_capital=-100.0,
        operating_cash_flow=1862.5,
        capital_expenditure=-400.0,
        acquisitions=-150.0,
        investing_cash_flow=-550.0,
        debt_issued=200.0,
        debt_repaid=-300.0,
        dividends_paid=-250.0,
        financing_cash_flow=-350.0,
        net_change_in_cash=962.5,
        beginning_cash=0.0,
        ending_cash=962.5,
    )


@pytest.fixture
def bs_data_dict():
    return {
        "cash_and_equivalents": 500.0,
        "accounts_receivable":  800.0,
        "inventory":            400.0,
        "total_current_assets": 1800.0,
        "property_plant_equipment": 3000.0,
        "total_assets": 5150.0,
        "accounts_payable": 600.0,
        "short_term_debt": 300.0,
        "total_current_liabilities": 1100.0,
        "long_term_debt": 1200.0,
        "total_liabilities": 2300.0,
        "total_equity": 2850.0,
        "total_liabilities_and_equity": 5150.0,
        "retained_earnings": 1850.0,
    }


@pytest.fixture
def is_data_dict():
    return {
        "revenue": 10000.0,
        "cost_of_revenue": 6500.0,
        "gross_profit": 3500.0,
        "ebitda": 2700.0,
        "ebit": 2500.0,
        "interest_expense": 150.0,
        "ebt": 2350.0,
        "tax_expense": 587.5,
        "net_income": 1762.5,
        "net_income_to_common": 1762.5,
        "basic_eps": 35.25,
        "diluted_eps": 34.80,
        "shares_outstanding_basic": 50.0,
        "shares_outstanding_diluted": 50.64,
    }


@pytest.fixture
def cf_data_dict():
    return {
        "operating_cash_flow": 1862.5,
        "capital_expenditure": -400.0,
        "investing_cash_flow": -550.0,
        "debt_issued": 200.0,
        "debt_repaid": -300.0,
        "dividends_paid": -250.0,
        "financing_cash_flow": -350.0,
        "net_change_in_cash": 962.5,
        "ending_cash": 962.5,
    }
