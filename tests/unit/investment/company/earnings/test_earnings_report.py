"""tests/unit/investment/company/earnings/test_earnings_report.py"""
import time
import pytest

from iios.investment.company.earnings.earnings_report import (
    EarningsReport, TrendDirection, EarningsQualityLabel,
    ProfitCyclePhase, EarningsType, MomentumLabel,
)
from tests.unit.investment.company.earnings.conftest import make_report


class TestEarningsReport:
    def test_effective_eps_diluted_preferred(self, single_report):
        single_report.diluted_eps = 9.8
        single_report.basic_eps   = 10.0
        assert single_report.effective_eps() == 9.8

    def test_effective_eps_falls_back_to_basic(self, single_report):
        single_report.diluted_eps = None
        single_report.basic_eps   = 10.0
        assert single_report.effective_eps() == 10.0

    def test_effective_earnings_uses_to_common(self, single_report):
        single_report.net_income_to_common = 90.0
        single_report.net_income = 95.0
        assert single_report.effective_earnings() == 90.0

    def test_is_profitable_true(self, single_report):
        assert single_report.is_profitable() is True

    def test_is_profitable_false_when_loss(self, single_report):
        single_report.net_income_to_common = -10.0
        single_report.net_income           = -10.0
        assert single_report.is_profitable() is False

    def test_cash_quality_clamps(self, single_report):
        single_report.ocf_to_net_income = 2.5
        assert single_report.cash_quality() == pytest.approx(1.0)
        single_report.ocf_to_net_income = -0.5
        assert single_report.cash_quality() == pytest.approx(0.0)

    def test_cash_quality_none_when_no_ratio(self, single_report):
        single_report.ocf_to_net_income = None
        assert single_report.cash_quality() is None

    def test_high_accruals_flag(self):
        r = make_report(2024, accruals=0.15)
        assert r.has_high_accruals is True

    def test_cash_backed_flag(self):
        r = make_report(2024, ocf_to_ni=0.9)
        assert r.is_cash_backed is True

    def test_to_dict_contains_key_fields(self, single_report):
        d = single_report.to_dict()
        for key in ["period_label", "revenue", "net_margin", "roe", "roic",
                    "accruals_ratio", "is_profitable", "effective_eps"]:
            assert key in d, f"Missing key: {key}"

    def test_to_dict_is_profitable(self, single_report):
        d = single_report.to_dict()
        assert d["is_profitable"] is True


class TestEarningsEnums:
    def test_trend_direction_values(self):
        assert TrendDirection.ACCELERATING.value == "accelerating"
        assert TrendDirection.INSUFFICIENT.value == "insufficient_data"

    def test_quality_label_values(self):
        assert EarningsQualityLabel.HIGH.value == "high"
        assert EarningsQualityLabel.LOW.value  == "low"

    def test_profit_cycle_values(self):
        assert ProfitCyclePhase.EXPANSION.value == "expansion"
        assert ProfitCyclePhase.TROUGH.value    == "trough"

    def test_momentum_label_values(self):
        assert MomentumLabel.STRONG_POSITIVE.value == "strong_positive"

    def test_from_snapshot_none_on_empty(self):
        class EmptySnap:
            ttm_is = None
            latest_annual_is = None
            ratios = {}
            cashflow_metrics = {}
            income_metrics = {}
            balance_sheet_metrics = {}
            total_assets = None
            latest_quarterly_bs = None
            latest_annual_bs = None
            ttm_cf = None
            latest_annual_cf = None
        result = EarningsReport.from_snapshot(EmptySnap(), "annual")
        assert result is None
