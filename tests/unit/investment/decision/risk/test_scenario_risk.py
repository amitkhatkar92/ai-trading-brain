"""tests/unit/investment/decision/risk/test_scenario_risk.py
Tests for StressScenario, ScenarioRegistry, ScenarioRiskAnalyzer.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.risk.risk_constants import ScenarioType
from iios.investment.decision.risk.scenario_registry import ScenarioRegistry
from iios.investment.decision.risk.scenario_risk import ScenarioRiskAnalyzer, ScenarioRiskResult
from iios.investment.decision.risk.scenario_statistics import ScenarioStatisticsTracker
from iios.investment.decision.risk.stress_scenarios import DEFAULT_SCENARIOS, StressScenario


# ─── StressScenario ───────────────────────────────────────────────────────────

class TestStressScenario:
    def test_base_case_multipliers_are_one(self):
        base = next(s for s in DEFAULT_SCENARIOS if s.scenario_type == ScenarioType.BASE_CASE)
        stressed = base.apply(50.0, 50.0, 50.0, 50.0, 50.0)
        for v in stressed.values():
            assert v == pytest.approx(50.0)

    def test_bear_market_amplifies_risk(self):
        bear = next(s for s in DEFAULT_SCENARIOS if s.scenario_type == ScenarioType.BEAR_MARKET)
        stressed = bear.apply(50.0, 50.0, 50.0, 50.0, 50.0)
        assert all(v > 50.0 for v in stressed.values())

    def test_bull_market_reduces_risk(self):
        bull = next(s for s in DEFAULT_SCENARIOS if s.scenario_type == ScenarioType.BULL_MARKET)
        stressed = bull.apply(50.0, 50.0, 50.0, 50.0, 50.0)
        assert all(v < 50.0 for v in stressed.values())

    def test_apply_clamped_at_100(self):
        flash = next(s for s in DEFAULT_SCENARIOS if s.scenario_type == ScenarioType.FLASH_CRASH)
        stressed = flash.apply(100.0, 100.0, 100.0, 100.0, 100.0)
        assert all(v <= 100.0 for v in stressed.values())

    def test_to_dict_has_required_keys(self):
        s = DEFAULT_SCENARIOS[0]
        d = s.to_dict()
        assert "scenario_type" in d and "probability" in d

    def test_default_scenarios_count(self):
        assert len(DEFAULT_SCENARIOS) == 9

    def test_probabilities_sum_to_approximately_one(self):
        total = sum(s.probability for s in DEFAULT_SCENARIOS)
        assert 0.90 <= total <= 1.15


# ─── ScenarioRegistry ────────────────────────────────────────────────────────

class TestScenarioRegistry:
    def test_loads_defaults(self):
        reg = ScenarioRegistry()
        assert reg.count() == 9

    def test_get_existing(self):
        reg = ScenarioRegistry()
        s = reg.get(ScenarioType.BASE_CASE)
        assert s is not None
        assert s.scenario_type == ScenarioType.BASE_CASE

    def test_get_missing_returns_none(self):
        reg = ScenarioRegistry(load_defaults=False)
        assert reg.get(ScenarioType.BULL_MARKET) is None

    def test_register_replaces(self):
        reg = ScenarioRegistry()
        new_base = StressScenario(
            scenario_type=ScenarioType.BASE_CASE, name="Custom Base",
            description="d", probability=0.50,
            market_multiplier=1.0, company_multiplier=1.0,
            strategy_multiplier=1.0, execution_multiplier=1.0,
            confidence_multiplier=1.0,
        )
        reg.register(new_base)
        assert reg.get(ScenarioType.BASE_CASE).name == "Custom Base"

    def test_remove(self):
        reg = ScenarioRegistry()
        reg.remove(ScenarioType.FLASH_CRASH)
        assert reg.get(ScenarioType.FLASH_CRASH) is None
        assert reg.count() == 8

    def test_all_scenarios_returns_list(self):
        reg = ScenarioRegistry()
        all_s = reg.all_scenarios()
        assert len(all_s) == 9
        assert isinstance(all_s, list)

    def test_empty_registry(self):
        reg = ScenarioRegistry(load_defaults=False)
        assert reg.count() == 0
        assert reg.all_scenarios() == []


# ─── ScenarioRiskAnalyzer ─────────────────────────────────────────────────────

class TestScenarioRiskAnalyzer:
    def setup_method(self):
        self.analyzer = ScenarioRiskAnalyzer()

    def test_returns_result(self):
        r = self.analyzer.analyze(40.0, 30.0, 35.0, 25.0, 20.0)
        assert isinstance(r, ScenarioRiskResult)

    def test_scenario_count_equals_9(self):
        r = self.analyzer.analyze(40.0, 30.0, 35.0, 25.0, 20.0)
        assert r.scenario_count == 9

    def test_worst_case_ge_average(self):
        r = self.analyzer.analyze(40.0, 30.0, 35.0, 25.0, 20.0)
        assert r.worst_case_risk >= r.average_risk

    def test_blended_risk_between_avg_and_worst(self):
        r = self.analyzer.analyze(40.0, 30.0, 35.0, 25.0, 20.0)
        assert r.average_risk <= r.blended_risk <= r.worst_case_risk + 1.0  # rounding

    def test_all_entries_in_range(self):
        r = self.analyzer.analyze(50.0, 50.0, 50.0, 50.0, 50.0)
        for e in r.entries:
            assert 0.0 <= e.stressed_risk <= 100.0

    def test_zero_risk_inputs(self):
        r = self.analyzer.analyze(0.0, 0.0, 0.0, 0.0, 0.0)
        assert r.worst_case_risk == pytest.approx(0.0, abs=1.0)

    def test_max_risk_inputs(self):
        r = self.analyzer.analyze(100.0, 100.0, 100.0, 100.0, 100.0)
        assert r.worst_case_risk <= 100.0

    def test_empty_registry_returns_zero(self):
        analyzer = ScenarioRiskAnalyzer(ScenarioRegistry(load_defaults=False))
        r = analyzer.analyze(50.0, 50.0, 50.0, 50.0, 50.0)
        assert r.scenario_count == 0
        assert r.worst_case_risk == 0.0

    def test_to_dict_structure(self):
        r = self.analyzer.analyze(40.0, 30.0, 35.0, 25.0, 20.0)
        d = r.to_dict()
        assert "entries" in d and "worst_case_risk" in d

    def test_bear_market_is_worst_vs_bull(self):
        r = self.analyzer.analyze(60.0, 60.0, 60.0, 60.0, 60.0)
        bear_entry = next(e for e in r.entries if e.scenario_type == "bear_market")
        bull_entry = next(e for e in r.entries if e.scenario_type == "bull_market")
        assert bear_entry.stressed_risk > bull_entry.stressed_risk


# ─── ScenarioStatisticsTracker ───────────────────────────────────────────────

class TestScenarioStatisticsTracker:
    def test_initial_summary(self):
        t = ScenarioStatisticsTracker()
        s = t.summary()
        assert s.total_runs == 0

    def test_record_success(self):
        t = ScenarioStatisticsTracker()
        t.record_success(blended_risk=30.0, worst_risk=60.0, scenario_count=9)
        s = t.summary()
        assert s.successful == 1
        assert s.avg_blended_risk == pytest.approx(30.0)

    def test_record_failure(self):
        t = ScenarioStatisticsTracker()
        t.record_failure()
        assert t.summary().failed == 1

    def test_success_rate(self):
        t = ScenarioStatisticsTracker()
        t.record_success(20.0, 50.0, 9)
        t.record_success(40.0, 70.0, 9)
        t.record_failure()
        s = t.summary()
        assert s.success_rate == pytest.approx(2 / 3, abs=0.01)

    def test_reset(self):
        t = ScenarioStatisticsTracker()
        t.record_success(30.0, 60.0, 9)
        t.reset()
        assert t.summary().total_runs == 0
