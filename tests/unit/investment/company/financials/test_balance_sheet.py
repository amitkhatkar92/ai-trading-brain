"""tests/unit/investment/company/financials/test_balance_sheet.py
Tests for BalanceSheetEngine, AssetAnalyzer, LiabilityAnalyzer, EquityAnalyzer.
"""
import pytest

from iios.investment.company.financials.asset_analyzer import AssetAnalyzer
from iios.investment.company.financials.liability_analyzer import LiabilityAnalyzer
from iios.investment.company.financials.equity_analyzer import EquityAnalyzer
from iios.investment.company.financials.balance_sheet_engine import BalanceSheetEngine
from iios.investment.company.financials.balance_sheet import BalanceSheet


class TestAssetAnalyzer:
    def test_current_asset_ratio(self, sample_bs):
        m = AssetAnalyzer().analyze(sample_bs)
        # 1800 / 5150 × 100
        assert m.current_asset_ratio == pytest.approx(1800 / 5150 * 100, rel=1e-3)

    def test_cash_ratio(self, sample_bs):
        m = AssetAnalyzer().analyze(sample_bs)
        assert m.cash_ratio_to_assets == pytest.approx(500 / 5150 * 100, rel=1e-3)

    def test_goodwill_ratio(self, sample_bs):
        m = AssetAnalyzer().analyze(sample_bs)
        assert m.goodwill_ratio == pytest.approx(200 / 5150 * 100, rel=1e-3)

    def test_none_total_assets_returns_none(self, annual_period):
        bs = BalanceSheet(period=annual_period, total_current_assets=100.0)
        m = AssetAnalyzer().analyze(bs)
        assert m.current_asset_ratio is None

    def test_to_dict(self, sample_bs):
        d = AssetAnalyzer().analyze(sample_bs).to_dict()
        assert "current_asset_ratio" in d
        assert "total_assets" in d


class TestLiabilityAnalyzer:
    def test_total_debt(self, sample_bs):
        m = LiabilityAnalyzer().analyze(sample_bs)
        assert m.total_debt == pytest.approx(1500.0)

    def test_not_over_leveraged(self, sample_bs):
        m = LiabilityAnalyzer().analyze(sample_bs)
        # 1500 / 2850 < 2 → not over leveraged
        assert m.is_over_leveraged is False

    def test_over_leveraged(self, annual_period):
        bs = BalanceSheet(
            period=annual_period,
            long_term_debt=6000.0,
            total_equity=1000.0,
            total_liabilities=6000.0,
            total_assets=7000.0,
        )
        m = LiabilityAnalyzer().analyze(bs)
        assert m.is_over_leveraged is True

    def test_current_liabilities_ratio(self, sample_bs):
        m = LiabilityAnalyzer().analyze(sample_bs)
        assert m.current_liabilities_ratio == pytest.approx(1100 / 2300 * 100, rel=1e-3)


class TestEquityAnalyzer:
    def test_equity_to_assets(self, sample_bs):
        m = EquityAnalyzer().analyze(sample_bs)
        assert m.equity_to_assets == pytest.approx(2850 / 5150 * 100, rel=1e-3)

    def test_not_negative_equity(self, sample_bs):
        assert EquityAnalyzer().analyze(sample_bs).is_negative_equity is False

    def test_negative_equity(self, annual_period):
        bs = BalanceSheet(period=annual_period, total_equity=-500.0, total_assets=1000.0)
        m = EquityAnalyzer().analyze(bs)
        assert m.is_negative_equity is True

    def test_retained_earnings_ratio(self, sample_bs):
        m = EquityAnalyzer().analyze(sample_bs)
        assert m.retained_earnings_ratio == pytest.approx(1850 / 2850 * 100, rel=1e-3)


class TestBalanceSheetEngine:
    def test_full_analysis(self, sample_bs):
        engine = BalanceSheetEngine()
        intel = engine.analyze(sample_bs)
        assert intel.period_label == sample_bs.period.label
        assert intel.current_ratio == pytest.approx(1800 / 1100, rel=1e-3)
        assert intel.working_capital == pytest.approx(700.0)
        assert intel.debt_to_equity == pytest.approx(1500 / 2850, rel=1e-3)
        assert intel.is_net_cash_positive is False

    def test_net_cash_positive(self, annual_period):
        bs = BalanceSheet(
            period=annual_period,
            cash_and_equivalents=5000.0,
            long_term_debt=1000.0,
            total_current_assets=5500.0,
            total_current_liabilities=500.0,
            total_equity=4000.0,
            total_assets=6000.0,
        )
        intel = BalanceSheetEngine().analyze(bs)
        assert intel.is_net_cash_positive is True

    def test_to_dict_structure(self, sample_bs):
        d = BalanceSheetEngine().analyze(sample_bs).to_dict()
        assert "assets" in d
        assert "liabilities" in d
        assert "equity" in d
        assert "current_ratio" in d
