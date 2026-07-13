"""tests/unit/investment/company/valuation/test_dcf_engine.py"""
from __future__ import annotations

import pytest
from iios.investment.company.valuation.dcf_engine import DCFEngine
from iios.investment.company.valuation.valuation_assumptions import (
    DCFAssumptions, WACCAssumptions,
)
from iios.investment.company.valuation.valuation_model import ValuationStatus


@pytest.fixture()
def engine():
    return DCFEngine()


@pytest.fixture()
def base_assumptions():
    return DCFAssumptions(
        wacc           = WACCAssumptions(wacc_override=0.12),
        near_term_growth  = 0.15,
        mid_term_growth   = 0.10,
        terminal_growth   = 0.04,
        projection_years  = 10,
        near_term_years   = 5,
        terminal_method   = "gordon",
    )


class TestDCFEngine:
    def test_basic_estimate_returns_computed(self, engine, base_assumptions):
        result = engine.estimate(
            assumptions        = base_assumptions,
            fcf_base           = 10_000.0,
            net_debt           = 5_000.0,
            shares_outstanding = 1000.0,
        )
        assert result.status == ValuationStatus.COMPUTED
        assert result.intrinsic_value > 0

    def test_none_fcf_returns_insufficient_data(self, engine, base_assumptions):
        result = engine.estimate(
            assumptions        = base_assumptions,
            fcf_base           = None,
            net_debt           = 0.0,
            shares_outstanding = 1000.0,
        )
        assert result.status == ValuationStatus.INSUFFICIENT_DATA

    def test_negative_fcf_returns_insufficient(self, engine, base_assumptions):
        result = engine.estimate(
            assumptions        = base_assumptions,
            fcf_base           = -5_000.0,
            net_debt           = 0.0,
            shares_outstanding = 1000.0,
        )
        assert result.status == ValuationStatus.INSUFFICIENT_DATA

    def test_high_net_debt_reduces_per_share(self, engine, base_assumptions):
        r_low  = engine.estimate(base_assumptions, 10_000.0, 0.0,       1000.0)
        r_high = engine.estimate(base_assumptions, 10_000.0, 50_000.0,  1000.0)
        assert r_low.intrinsic_value > r_high.intrinsic_value

    def test_higher_growth_increases_value(self, engine):
        low_g  = DCFAssumptions(wacc=WACCAssumptions(wacc_override=0.12), near_term_growth=0.05)
        high_g = DCFAssumptions(wacc=WACCAssumptions(wacc_override=0.12), near_term_growth=0.20)
        r_low  = engine.estimate(low_g,  10_000.0, 0.0, 1000.0)
        r_high = engine.estimate(high_g, 10_000.0, 0.0, 1000.0)
        assert r_high.intrinsic_value > r_low.intrinsic_value

    def test_fcf_multiple_terminal_method(self, engine):
        a = DCFAssumptions(
            wacc             = WACCAssumptions(wacc_override=0.12),
            terminal_method  = "multiple",
            terminal_fcf_multiple = 15.0,
        )
        result = engine.estimate(a, 10_000.0, 0.0, 1000.0)
        assert result.status == ValuationStatus.COMPUTED

    def test_value_range_ordered(self, engine, base_assumptions):
        result = engine.estimate(base_assumptions, 10_000.0, 0.0, 1000.0)
        assert result.value_low <= result.intrinsic_value <= result.value_high

    def test_wacc_equal_to_terminal_growth_guarded(self, engine):
        """Engine must handle wacc == terminal_growth gracefully."""
        a = DCFAssumptions(
            wacc           = WACCAssumptions(wacc_override=0.04),
            terminal_growth = 0.04,
        )
        result = engine.estimate(a, 10_000.0, 0.0, 1000.0)
        assert result.status == ValuationStatus.COMPUTED
        assert result.intrinsic_value > 0

    def test_confidence_below_one(self, engine, base_assumptions):
        result = engine.estimate(base_assumptions, 10_000.0, 0.0, 1000.0)
        assert 0 < result.confidence <= 1.0

    def test_explanation_present(self, engine, base_assumptions):
        result = engine.estimate(base_assumptions, 10_000.0, 0.0, 1000.0)
        assert len(result.explanation) > 0

    def test_zero_shares_returns_insufficient(self, engine, base_assumptions):
        result = engine.estimate(base_assumptions, 10_000.0, 0.0, 0.0)
        assert result.status == ValuationStatus.INSUFFICIENT_DATA
