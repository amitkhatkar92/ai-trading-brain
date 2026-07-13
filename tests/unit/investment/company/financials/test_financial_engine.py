"""tests/unit/investment/company/financials/test_financial_engine.py
Integration tests for FinancialStatementEngine — primary engine tests.
"""
import pytest

from iios.investment.company.financials.financial_statement_engine import FinancialStatementEngine
from iios.investment.company.financials.financial_period import (
    FinancialPeriod, PeriodType, AccountingStandard,
)


def make_annual_period(fy: int) -> FinancialPeriod:
    return FinancialPeriod.annual(fy, f"{fy-1}-04-01", f"{fy}-03-31")


def make_quarterly_period(fy: int, q: int) -> FinancialPeriod:
    months = {1: ("04", "06"), 2: ("07", "09"), 3: ("10", "12"), 4: ("01", "03")}
    sm, em = months[q]
    yr = fy - 1 if q != 4 else fy
    return FinancialPeriod.quarterly(fy, q, f"{fy-1}-{sm}-01", f"{yr}-{em}-30")


SAMPLE_BS = {
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

SAMPLE_IS = {
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
    "depreciation_amortization": 200.0,
}

SAMPLE_CF = {
    "operating_cash_flow": 1862.5,
    "capital_expenditure": -400.0,
    "investing_cash_flow": -550.0,
    "debt_issued": 200.0,
    "debt_repaid": -300.0,
    "dividends_paid": -250.0,
    "financing_cash_flow": -350.0,
    "net_change_in_cash": 962.5,
    "ending_cash": 962.5,
    "depreciation_amortization_cf": 200.0,
}


class TestFinancialStatementEngineBasic:
    def test_update_returns_snapshot(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        snap = engine.update("RELIANCE", period, bs_data=SAMPLE_BS, is_data=SAMPLE_IS, cf_data=SAMPLE_CF)
        assert snap.ticker == "RELIANCE"
        assert snap.has_annual is True

    def test_get_snapshot(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        engine.update("TCS", period, bs_data=SAMPLE_BS)
        snap = engine.get_snapshot("TCS")
        assert snap is not None
        assert snap.ticker == "TCS"

    def test_unknown_ticker_returns_none(self):
        engine = FinancialStatementEngine()
        assert engine.get_snapshot("UNKNOWN_TICKER_XYZ") is None

    def test_ratios_computed(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        snap = engine.update("WIPRO", period, bs_data=SAMPLE_BS, is_data=SAMPLE_IS, cf_data=SAMPLE_CF)
        assert snap.ratios
        assert "current_ratio" in snap.ratios
        assert snap.ratios["current_ratio"] == pytest.approx(1800 / 1100, rel=1e-3)

    def test_balance_sheet_metrics(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        snap = engine.update("HDFC", period, bs_data=SAMPLE_BS, is_data=SAMPLE_IS, cf_data=SAMPLE_CF)
        bsm = snap.balance_sheet_metrics
        assert bsm["working_capital"] == pytest.approx(700.0)
        assert bsm["is_net_cash_positive"] is False

    def test_income_metrics(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        snap = engine.update("INFY", period, bs_data=SAMPLE_BS, is_data=SAMPLE_IS, cf_data=SAMPLE_CF)
        im = snap.income_metrics
        assert im["gross_margin"] == pytest.approx(35.0)
        assert im["net_margin"] == pytest.approx(17.625)

    def test_cashflow_metrics(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        snap = engine.update("SBI", period, bs_data=SAMPLE_BS, is_data=SAMPLE_IS, cf_data=SAMPLE_CF)
        cfm = snap.cashflow_metrics
        assert cfm["is_fcf_positive"] is True
        assert cfm["is_returning_capital"] is True

    def test_quality_score_perfect_data(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        snap = engine.update("ITC", period, bs_data=SAMPLE_BS, is_data=SAMPLE_IS, cf_data=SAMPLE_CF)
        assert snap.quality_score > 50.0

    def test_timeline_populated(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        snap = engine.update("BAJAJ", period, bs_data=SAMPLE_BS)
        assert len(snap.timeline) == 1
        assert snap.timeline[0]["label"] == "FY24"


class TestTTMConstruction:
    def _make_quarter_is(self, q: int) -> dict:
        return {
            "revenue":           2500.0,
            "cost_of_revenue":   1625.0,
            "gross_profit":       875.0,
            "ebitda":             675.0,
            "ebit":               625.0,
            "interest_expense":    37.5,
            "ebt":                587.5,
            "tax_expense":        146.875,
            "net_income":         440.625,
            "net_income_to_common": 440.625,
            "basic_eps":            8.8125,
            "diluted_eps":          8.70,
            "shares_outstanding_basic": 50.0,
            "shares_outstanding_diluted": 50.64,
        }

    def test_ttm_is_constructed_from_4_quarters(self):
        engine = FinancialStatementEngine()
        for q in range(1, 5):
            period = make_quarterly_period(2024, q)
            engine.update("KOTAK", period, is_data=self._make_quarter_is(q))
        snap = engine.get_snapshot("KOTAK")
        assert snap.has_ttm is True
        # TTM revenue = 4 × 2500 = 10000
        assert snap.ttm_is.revenue == pytest.approx(10000.0)

    def test_ttm_not_built_with_fewer_than_4_quarters(self):
        engine = FinancialStatementEngine()
        for q in range(1, 3):   # only 2 quarters
            period = make_quarterly_period(2024, q)
            engine.update("AXIS", period, is_data=self._make_quarter_is(q))
        snap = engine.get_snapshot("AXIS")
        assert snap.has_ttm is False


class TestVersioning:
    def test_second_update_same_period_increments_version(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        engine.update("MARUTI", period, bs_data=SAMPLE_BS)
        stmt_v1 = engine.get_statement("MARUTI", "FY24")
        v1 = stmt_v1.current_version

        engine.update("MARUTI", period, bs_data={**SAMPLE_BS, "total_assets": 5200.0})
        stmt_v2 = engine.get_statement("MARUTI", "FY24")
        assert stmt_v2.current_version > v1

    def test_restated_update_tracked(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        engine.update("TATA", period, bs_data=SAMPLE_BS)
        engine.update("TATA", period, bs_data={**SAMPLE_BS, "total_assets": 6000.0}, restated=True)
        summary = engine.restatement_summary("TATA")
        assert summary["total_restatements"] >= 1


class TestHistoryAndQueryAPIs:
    def test_multi_year_annual_history(self):
        engine = FinancialStatementEngine()
        for fy in range(2018, 2025):
            period = make_annual_period(fy)
            engine.update("LT", period, bs_data=SAMPLE_BS, is_data=SAMPLE_IS)
        history = engine.get_annual_history("LT", n=5)
        assert len(history) == 5

    def test_get_balance_sheet(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        engine.update("NESTL", period, bs_data=SAMPLE_BS, is_data=SAMPLE_IS)
        bs = engine.get_balance_sheet("NESTL")
        assert bs is not None
        assert bs.total_assets == 5150.0

    def test_get_income_statement(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        engine.update("PIDLIT", period, is_data=SAMPLE_IS)
        is_ = engine.get_income_statement("PIDLIT")
        assert is_ is not None
        assert is_.revenue == 10000.0

    def test_get_ratio(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        engine.update("AAPL", period, bs_data=SAMPLE_BS, is_data=SAMPLE_IS)
        val = engine.get_ratio("AAPL", "gross_margin")
        assert val == pytest.approx(35.0)

    def test_get_ratio_series(self):
        engine = FinancialStatementEngine()
        for fy in range(2021, 2025):
            period = make_annual_period(fy)
            engine.update("DRRD", period, bs_data=SAMPLE_BS, is_data=SAMPLE_IS, cf_data=SAMPLE_CF)
        series = engine.get_ratio_series("DRRD", "gross_margin", n=3)
        assert len(series) == 3
        for label, val in series:
            assert val == pytest.approx(35.0)

    def test_known_tickers(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        engine.update("ALPHA", period, bs_data=SAMPLE_BS)
        engine.update("BETA", period, bs_data=SAMPLE_BS)
        tickers = engine.known_tickers()
        assert "ALPHA" in tickers
        assert "BETA" in tickers

    def test_timeline_multi_period(self):
        engine = FinancialStatementEngine()
        for fy in [2022, 2023, 2024]:
            period = make_annual_period(fy)
            engine.update("WIPRO2", period, bs_data=SAMPLE_BS)
        snap = engine.get_snapshot("WIPRO2")
        assert snap.periods_available == 3
        labels = [e["label"] for e in snap.timeline]
        assert "FY24" in labels

    def test_snapshot_convenience_properties(self):
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        snap = engine.update("SUNP", period, bs_data=SAMPLE_BS, is_data=SAMPLE_IS, cf_data=SAMPLE_CF)
        assert snap.revenue == pytest.approx(10000.0)
        assert snap.total_assets == pytest.approx(5150.0)
        assert snap.free_cash_flow == pytest.approx(1462.5)


class TestCallbackAndConcurrency:
    def test_callback_fires_on_update(self):
        results = []
        engine = FinancialStatementEngine(on_snapshot_updated=results.append)
        period = make_annual_period(2024)
        engine.update("CB_TEST", period, bs_data=SAMPLE_BS)
        assert len(results) == 1
        assert results[0].ticker == "CB_TEST"

    def test_thread_safety(self):
        import threading
        engine = FinancialStatementEngine()
        errors = []

        def worker(ticker_num: int) -> None:
            try:
                period = make_annual_period(2024)
                engine.update(f"TICKER_{ticker_num}", period, bs_data=SAMPLE_BS)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == [], f"Thread safety errors: {errors}"
        assert len(engine.known_tickers()) == 20

    def test_partial_data_update(self):
        """Engine handles update with only balance sheet (no IS or CF)."""
        engine = FinancialStatementEngine()
        period = make_annual_period(2024)
        snap = engine.update("PARTIAL", period, bs_data=SAMPLE_BS)
        assert snap.latest_annual_bs is not None
        assert snap.latest_annual_is is None
        assert snap.latest_annual_cf is None
