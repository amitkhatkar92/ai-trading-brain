"""tests/unit/investment/company/financials/test_ratios.py
Tests for RatioRegistry, RatioCalculator, RatioHistory.
"""
import pytest

from iios.investment.company.financials.ratio_registry import RatioRegistry
from iios.investment.company.financials.ratio_calculator import RatioCalculator
from iios.investment.company.financials.ratio_history import RatioHistory, RatioPeriodSnapshot
from iios.investment.company.financials.financial_ratios import RatioCategory, RatioDefinition


class TestRatioRegistry:
    def test_standard_ratios_loaded(self):
        reg = RatioRegistry()
        assert "current_ratio" in reg.names()
        assert "roe" in reg.names()
        assert "debt_to_equity" in reg.names()
        assert "free_cash_flow" not in reg.names()   # not a ratio name

    def test_list_by_category(self):
        reg = RatioRegistry()
        liquidity = reg.list_by_category(RatioCategory.LIQUIDITY)
        names = [r.name for r in liquidity]
        assert "current_ratio" in names
        assert "quick_ratio" in names

    def test_custom_ratio_registration(self):
        reg = RatioRegistry()
        reg.register(RatioDefinition(
            name="custom_ratio",
            category=RatioCategory.PROFITABILITY,
            formula_description="Test ratio",
            unit="x",
            higher_is_better=True,
            calculator=lambda bs, is_, cf: 42.0,
        ))
        assert "custom_ratio" in reg.names()
        assert reg.get("custom_ratio").compute(None, None, None) == 42.0

    def test_singleton(self):
        a = RatioRegistry.get_instance()
        b = RatioRegistry.get_instance()
        assert a is b

    def test_all_ratios_have_calculators(self):
        reg = RatioRegistry()
        for defn in reg.list_all():
            assert defn.calculator is not None, f"No calculator for {defn.name}"


class TestRatioCalculator:
    def test_compute_all_returns_all_names(self, sample_bs, sample_is, sample_cf):
        calc = RatioCalculator()
        ratios = calc.compute_all(sample_bs, sample_is, sample_cf)
        reg = RatioRegistry.get_instance()
        for name in reg.names():
            assert name in ratios

    def test_current_ratio_value(self, sample_bs, sample_is, sample_cf):
        calc = RatioCalculator()
        ratios = calc.compute_all(sample_bs, sample_is, sample_cf)
        # 1800 / 1100
        assert ratios["current_ratio"] == pytest.approx(1800 / 1100, rel=1e-3)

    def test_gross_margin_value(self, sample_bs, sample_is, sample_cf):
        calc = RatioCalculator()
        ratios = calc.compute_all(sample_bs, sample_is, sample_cf)
        assert ratios["gross_margin"] == pytest.approx(35.0)

    def test_debt_to_equity(self, sample_bs, sample_is, sample_cf):
        calc = RatioCalculator()
        ratios = calc.compute_all(sample_bs, sample_is, sample_cf)
        assert ratios["debt_to_equity"] == pytest.approx(1500 / 2850, rel=1e-3)

    def test_none_inputs_dont_crash(self):
        calc = RatioCalculator()
        ratios = calc.compute_all(None, None, None)
        # All ratios return None when all inputs are None
        for v in ratios.values():
            assert v is None

    def test_compute_single(self, sample_bs, sample_is, sample_cf):
        calc = RatioCalculator()
        val = calc.compute_single("roe", sample_bs, sample_is, sample_cf)
        assert val is not None
        assert val > 0

    def test_compute_by_category(self, sample_bs, sample_is, sample_cf):
        calc = RatioCalculator()
        results = calc.compute_by_category(RatioCategory.LIQUIDITY, sample_bs, sample_is, sample_cf)
        assert len(results) >= 2
        names = [r.name for r in results]
        assert "current_ratio" in names

    def test_roic_formula(self, sample_bs, sample_is, sample_cf):
        calc = RatioCalculator()
        roic = calc.compute_single("roic", sample_bs, sample_is, sample_cf)
        # NOPAT = ebit * (1 - 0.25) = 2500 * 0.75 = 1875
        # IC = equity + debt = 2850 + 1500 = 4350
        # ROIC = 1875 / 4350 * 100 ≈ 43.1
        assert roic == pytest.approx(1875 / 4350 * 100, rel=1e-2)


class TestRatioHistory:
    def test_push_and_get_latest(self):
        rh = RatioHistory()
        snap = RatioPeriodSnapshot("FY24", "2024-03-31", {"current_ratio": 1.6})
        rh.push("RELIANCE", snap)
        latest = rh.get_latest("RELIANCE")
        assert latest.ratios["current_ratio"] == 1.6

    def test_history_order(self):
        rh = RatioHistory()
        for i in range(5):
            rh.push("TCS", RatioPeriodSnapshot(f"FY{20+i}", f"20{20+i}-03-31", {"roe": float(i)}))
        history = rh.get_history("TCS", n=3)
        assert len(history) == 3
        assert history[-1].ratios["roe"] == 4.0

    def test_ratio_series(self):
        rh = RatioHistory()
        for i in range(4):
            rh.push("INFY", RatioPeriodSnapshot(f"Q{i+1}FY24", f"2024-0{i+1}-01", {"net_margin": float(i + 10)}))
        series = rh.get_ratio_series("INFY", "net_margin", n=4)
        assert len(series) == 4
        assert series[-1][1] == 13.0

    def test_duplicate_period_overwrite(self):
        rh = RatioHistory()
        rh.push("HDFC", RatioPeriodSnapshot("FY24", "2024-03-31", {"roe": 15.0}))
        rh.push("HDFC", RatioPeriodSnapshot("FY24", "2024-03-31", {"roe": 18.0}))
        assert rh.period_count("HDFC") == 1
        assert rh.get_latest("HDFC").ratios["roe"] == 18.0

    def test_max_periods_enforced(self):
        rh = RatioHistory(max_periods=3)
        for i in range(10):
            rh.push("X", RatioPeriodSnapshot(f"FY{i}", f"20{i:02d}-03-31", {}))
        assert rh.period_count("X") == 3

    def test_unknown_ticker_returns_none(self):
        rh = RatioHistory()
        assert rh.get_latest("UNKNOWN") is None

    def test_all_tickers(self):
        rh = RatioHistory()
        rh.push("A", RatioPeriodSnapshot("P1", "2024-01-01", {}))
        rh.push("B", RatioPeriodSnapshot("P1", "2024-01-01", {}))
        assert set(rh.all_tickers()) == {"A", "B"}
