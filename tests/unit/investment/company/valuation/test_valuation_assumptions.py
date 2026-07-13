"""tests/unit/investment/company/valuation/test_valuation_assumptions.py"""
from __future__ import annotations

import pytest
from iios.investment.company.valuation.valuation_assumptions import (
    WACCAssumptions, DCFAssumptions, DDMAssumptions,
    RIMAssumptions, RelativeValuationAssumptions, ValuationAssumptions,
)


class TestWACCAssumptions:
    def test_default_cost_of_equity(self):
        w = WACCAssumptions()
        ke = w.cost_of_equity()
        # ke = rfr + beta * erp = 0.065 + 1.0 * 0.055
        assert abs(ke - 0.12) < 0.001

    def test_default_wacc(self):
        w = WACCAssumptions()
        wacc = w.wacc()
        # ke=0.12, kd_at=0.06, equity_w=0.70, debt_w=0.30
        expected = 0.12 * 0.70 + 0.06 * 0.30
        assert abs(wacc - expected) < 0.001

    def test_wacc_override(self):
        w = WACCAssumptions(wacc_override=0.15)
        assert abs(w.wacc() - 0.15) < 0.0001

    def test_custom_beta(self):
        w = WACCAssumptions(beta=1.5)
        ke = w.cost_of_equity()
        # 0.065 + 1.5 * 0.055 = 0.1475
        assert abs(ke - 0.1475) < 0.001

    def test_cost_of_debt_after_tax(self):
        w = WACCAssumptions(cost_of_debt=0.10, tax_rate=0.30)
        assert abs(w.cost_of_debt_after_tax() - 0.07) < 0.001

    def test_to_dict_keys(self):
        d = WACCAssumptions().to_dict()
        assert "computed_wacc" in d
        assert "cost_of_equity" in d
        assert "risk_free_rate" in d


class TestDCFAssumptions:
    def test_terminal_discount_check_valid(self):
        dcf = DCFAssumptions()
        # WACC ~10.2%, terminal growth 4% — should pass
        assert dcf.terminal_discount_check() is True

    def test_terminal_discount_check_fails_when_close(self):
        w = WACCAssumptions(wacc_override=0.04)
        dcf = DCFAssumptions(wacc=w, terminal_growth=0.04)
        # wacc == terminal_growth → should fail
        assert dcf.terminal_discount_check() is False

    def test_to_dict_contains_growth(self):
        d = DCFAssumptions().to_dict()
        assert "near_term_growth" in d
        assert "terminal_growth" in d
        assert "wacc" in d


class TestRelativeValuationAssumptions:
    def test_defaults_are_none(self):
        r = RelativeValuationAssumptions()
        assert r.target_pe is None
        assert r.target_ev_ebitda is None

    def test_explicit_targets(self):
        r = RelativeValuationAssumptions(target_pe=25.0, target_pb=4.0)
        assert r.target_pe == 25.0


class TestValuationAssumptions:
    def test_model_weights_sum_near_one(self):
        va = ValuationAssumptions()
        total = sum(va.model_weights.values())
        assert abs(total - 1.0) < 0.01

    def test_to_dict_serialisable(self):
        import json
        d = ValuationAssumptions().to_dict()
        # Should not raise
        json.dumps(d)
