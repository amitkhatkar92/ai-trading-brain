"""tests/unit/investment/company/valuation/test_scenarios.py"""
from __future__ import annotations

import pytest
from iios.investment.company.valuation.scenario_engine import ScenarioEngine
from iios.investment.company.valuation.valuation_assumptions import (
    DCFAssumptions, WACCAssumptions,
)


@pytest.fixture()
def engine():
    return ScenarioEngine()


@pytest.fixture()
def base_dcf():
    return DCFAssumptions(
        wacc            = WACCAssumptions(wacc_override=0.12),
        near_term_growth= 0.12,
        mid_term_growth = 0.08,
        terminal_growth = 0.04,
    )


class TestScenarioEngine:
    def test_returns_three_scenarios(self, engine, base_dcf):
        bull, base, bear = engine.run(
            base_assumptions   = base_dcf,
            fcf_base           = 10_000.0,
            net_debt           = 5_000.0,
            shares_outstanding = 1000.0,
            market_price       = 150.0,
        )
        assert bull is not None
        assert base is not None
        assert bear is not None

    def test_scenario_labels(self, engine, base_dcf):
        bull, base, bear = engine.run(base_dcf, 10_000.0, 0.0, 1000.0, 150.0)
        assert bull.scenario == "bull"
        assert base.scenario == "base"
        assert bear.scenario == "bear"

    def test_bull_higher_than_bear(self, engine, base_dcf):
        bull, base, bear = engine.run(base_dcf, 10_000.0, 0.0, 1000.0, 150.0)
        assert bull.fair_value is not None
        assert bear.fair_value is not None
        assert bull.fair_value > bear.fair_value

    def test_base_between_bull_and_bear(self, engine, base_dcf):
        bull, base, bear = engine.run(base_dcf, 10_000.0, 0.0, 1000.0, 150.0)
        assert bear.fair_value < base.fair_value < bull.fair_value

    def test_mos_computed_when_price_given(self, engine, base_dcf):
        bull, base, bear = engine.run(base_dcf, 10_000.0, 0.0, 1000.0, 150.0)
        for s in [bull, base, bear]:
            assert s.mos_pct is not None

    def test_no_result_without_fcf(self, engine, base_dcf):
        bull, base, bear = engine.run(base_dcf, None, 0.0, 1000.0, 150.0)
        assert bull is None
        assert base is None
        assert bear is None

    def test_assumptions_present_in_result(self, engine, base_dcf):
        bull, _, _ = engine.run(base_dcf, 10_000.0, 0.0, 1000.0, 150.0)
        assert "near_term_growth" in bull.assumptions
        assert "wacc" in bull.assumptions
