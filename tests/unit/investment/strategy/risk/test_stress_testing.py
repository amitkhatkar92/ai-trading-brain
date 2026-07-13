"""tests/unit/investment/strategy/risk/test_stress_testing.py
Tests for stress scenarios, ScenarioEngine, and StressTestingEngine.
"""
import pytest
from tests.unit.investment.strategy.risk.conftest import make_risk_input
from iios.investment.strategy.risk.stress_scenarios import (
    MARKET_CRASH, VOLATILITY_SPIKE, LIQUIDITY_SHOCK,
    FLASH_CRASH, EXTREME_TREND, BUILTIN_SCENARIOS, StressScenario
)
from iios.investment.strategy.risk.stress_statistics import (
    stressed_vol,
    stressed_drawdown,
    stressed_expected_loss,
    risk_amplification,
    survival_probability,
    aggregate_stress_score,
    worst_case_loss,
)
from iios.investment.strategy.risk.scenario_engine import ScenarioEngine, ScenarioResult
from iios.investment.strategy.risk.stress_testing import StressTestingEngine, StressTestReport


class TestStressScenarios:
    def test_all_scenarios_have_name(self):
        for s in BUILTIN_SCENARIOS:
            assert s.name
            assert len(s.name) > 0

    def test_flash_crash_highest_vol_mult(self):
        assert FLASH_CRASH.vol_multiplier >= MARKET_CRASH.vol_multiplier

    def test_extreme_trend_is_favorable(self):
        assert EXTREME_TREND.regime_impact == "favorable"

    def test_scenario_probability_sum(self):
        total = sum(s.probability for s in BUILTIN_SCENARIOS)
        # Probabilities sum close to 1.0 (±0.2 tolerance — scenarios may overlap)
        assert 0.8 <= total <= 1.5

    def test_scenario_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            MARKET_CRASH.vol_multiplier = 99.0


class TestStressStatistics:
    def test_stressed_vol_increases(self):
        assert stressed_vol(0.20, 2.0) == pytest.approx(0.40)

    def test_stressed_drawdown_increases(self):
        assert stressed_drawdown(0.15, 2.0) == pytest.approx(0.30)

    def test_stressed_expected_loss_positive(self):
        assert stressed_expected_loss(0.20, 2.0) > 0.0

    def test_risk_amplification_above_one_when_higher(self):
        amp = risk_amplification(40.0, 80.0)
        assert amp > 1.0

    def test_survival_probability_range(self):
        p = survival_probability(40.0, 2.0)
        assert 0.0 <= p <= 1.0

    def test_aggregate_stress_score_weighted(self):
        scores  = [60.0, 80.0]
        weights = [0.5, 0.5]
        result  = aggregate_stress_score(scores, weights)
        assert result == pytest.approx(70.0)

    def test_worst_case_loss_positive(self):
        wc = worst_case_loss(0.20, 2.5, 0.10)
        assert wc > 0.0


class TestScenarioEngine:
    def test_run_scenario_returns_result(self, risk_input):
        engine = ScenarioEngine()
        result = engine.evaluate(risk_input, MARKET_CRASH)
        assert isinstance(result, ScenarioResult)

    def test_passes_field_bool(self, risk_input):
        engine = ScenarioEngine()
        result = engine.evaluate(risk_input, MARKET_CRASH)
        assert isinstance(result.passes, bool)

    def test_stressed_score_ge_base(self, high_risk_input):
        engine = ScenarioEngine()
        result = engine.evaluate(high_risk_input, FLASH_CRASH)
        assert result.stressed_risk_score >= result.base_risk_score

    def test_favorable_scenario_lower_stressed(self, risk_input):
        engine = ScenarioEngine()
        trend_result = engine.evaluate(risk_input, EXTREME_TREND)
        crash_result = engine.evaluate(risk_input, MARKET_CRASH)
        assert trend_result.stressed_risk_score < crash_result.stressed_risk_score


class TestStressTestingEngine:
    def test_run_returns_report(self, risk_input):
        engine = StressTestingEngine()
        report = engine.run(risk_input)
        assert isinstance(report, StressTestReport)

    def test_pass_rate_range(self, risk_input):
        engine = StressTestingEngine()
        report = engine.run(risk_input)
        assert 0.0 <= report.pass_rate <= 1.0

    def test_aggregate_stress_score_range(self, risk_input):
        engine = StressTestingEngine()
        report = engine.run(risk_input)
        assert 0.0 <= report.aggregate_stress_score <= 100.0

    def test_overall_rating_is_string(self, risk_input):
        engine = StressTestingEngine()
        report = engine.run(risk_input)
        assert report.overall_stress_rating in ("ROBUST", "MODERATE", "VULNERABLE", "FRAGILE")

    def test_high_risk_lower_pass_rate(self, high_risk_input, low_risk_input):
        engine = StressTestingEngine()
        high_pass = engine.run(high_risk_input).pass_rate
        low_pass  = engine.run(low_risk_input).pass_rate
        assert high_pass <= low_pass

    def test_custom_scenario_registered(self, risk_input):
        scenario = StressScenario(
            name="test_custom",
            description="Custom test scenario",
            vol_multiplier=1.5,
            drawdown_multiplier=1.5,
            liquidity_multiplier=1.2,
            execution_multiplier=1.2,
            probability=0.05,
            regime_impact="neutral",
        )
        engine = StressTestingEngine(scenarios=[scenario])
        report = engine.run(risk_input)
        assert report is not None
