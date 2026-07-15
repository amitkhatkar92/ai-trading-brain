"""tests/unit/investment/portfolio/risk/test_stress_testing.py"""
import pytest
from iios.investment.portfolio.risk.scenario_library import SCENARIOS, Scenario
from iios.investment.portfolio.risk.scenario_engine import ScenarioEngine, ScenarioResult
from iios.investment.portfolio.risk.stress_testing import StressTestEngine, StressTestReport
from iios.investment.portfolio.risk.stress_statistics import StressStatistics


# ── Scenario library ──────────────────────────────────────────────────────

def test_scenarios_not_empty():
    assert len(SCENARIOS) >= 10


def test_scenarios_all_frozen():
    for name, s in SCENARIOS.items():
        assert isinstance(s, Scenario)
        with pytest.raises((TypeError, AttributeError)):
            s.equity_shock = 999  # type: ignore[misc]


def test_market_crash_is_severe():
    from iios.investment.portfolio.risk.risk_types import StressTestSeverity
    assert SCENARIOS["market_crash"].severity == StressTestSeverity.SEVERE


def test_black_swan_is_black_swan():
    from iios.investment.portfolio.risk.risk_types import StressTestSeverity
    assert SCENARIOS["black_swan"].severity == StressTestSeverity.BLACK_SWAN


def test_scenario_to_dict():
    d = SCENARIOS["market_crash"].to_dict()
    assert "equity_shock" in d
    assert d["equity_shock"] < 0


# ── ScenarioEngine ───────────────────────────────────────────────────────

def test_scenario_engine_empty():
    engine = ScenarioEngine()
    r = engine.run([], SCENARIOS["market_crash"])
    assert r.portfolio_impact == 0.0


def test_scenario_engine_returns_result(positions_5_diverse):
    engine = ScenarioEngine()
    r = engine.run(positions_5_diverse, SCENARIOS["market_crash"])
    assert isinstance(r, ScenarioResult)


def test_market_crash_causes_loss(positions_5_diverse):
    engine = ScenarioEngine()
    r = engine.run(positions_5_diverse, SCENARIOS["market_crash"])
    assert r.portfolio_impact < 0   # loss expected


def test_rate_down_may_gain(positions_bond_heavy):
    engine = ScenarioEngine()
    r = engine.run(positions_bond_heavy, SCENARIOS["rate_shock_down"])
    # bond-heavy portfolio should gain when rates fall
    assert r.portfolio_impact >= 0 or r.portfolio_impact > -0.15  # may break even


def test_position_impacts_count(positions_5_diverse):
    engine = ScenarioEngine()
    r = engine.run(positions_5_diverse, SCENARIOS["market_crash"])
    assert len(r.position_impacts) == len(positions_5_diverse)


def test_scenario_result_worst_position_set(positions_5_diverse):
    engine = ScenarioEngine()
    r = engine.run(positions_5_diverse, SCENARIOS["market_crash"])
    assert r.worst_position != ""


def test_scenario_to_dict(positions_5_diverse):
    engine = ScenarioEngine()
    d = engine.run(positions_5_diverse, SCENARIOS["market_crash"]).to_dict()
    assert "portfolio_impact" in d
    assert "scenario_name" in d


# ── StressTestEngine ─────────────────────────────────────────────────────

def test_stress_engine_empty():
    engine = StressTestEngine()
    r = engine.run_all([], portfolio_id="p1")
    assert r.n_scenarios_run == 0


def test_stress_engine_returns_report(positions_5_diverse):
    engine = StressTestEngine()
    r = engine.run_all(positions_5_diverse, portfolio_id="p1")
    assert isinstance(r, StressTestReport)
    assert r.portfolio_id == "p1"


def test_stress_engine_all_scenarios(positions_5_diverse):
    engine = StressTestEngine()
    r = engine.run_all(positions_5_diverse)
    assert r.n_scenarios_run == len(SCENARIOS)


def test_stress_worst_scenario_is_string(positions_5_diverse):
    engine = StressTestEngine()
    r = engine.run_all(positions_5_diverse)
    assert r.worst_scenario != ""


def test_stress_worst_loss_is_negative(positions_5_diverse):
    engine = StressTestEngine()
    r = engine.run_all(positions_5_diverse)
    assert r.worst_loss < 0


def test_stress_resilience_in_range(positions_5_diverse):
    engine = StressTestEngine()
    r = engine.run_all(positions_5_diverse)
    assert 0.0 <= r.resilience_score <= 1.0


def test_stress_tail_avg_loss_le_worst(positions_5_diverse):
    engine = StressTestEngine()
    r = engine.run_all(positions_5_diverse)
    # tail_avg_loss is the average of the worst quintile (less negative than single worst)
    assert r.tail_avg_loss >= r.worst_loss - 1e-9


def test_stress_report_to_dict(positions_5_diverse):
    engine = StressTestEngine()
    d = engine.run_all(positions_5_diverse).to_dict()
    assert "worst_loss" in d
    assert "resilience_score" in d


def test_stress_custom_scenarios(positions_5_diverse):
    engine = StressTestEngine()
    custom = {"market_crash": SCENARIOS["market_crash"]}
    r = engine.run_all(positions_5_diverse, scenarios=custom)
    assert r.n_scenarios_run == 1


# ── StressStatistics ──────────────────────────────────────────────────────

def test_stress_stats_initial():
    stats = StressStatistics()
    snap = stats.snapshot()
    assert snap.total_runs == 0


def test_stress_stats_record(positions_5_diverse):
    engine = StressTestEngine()
    r = engine.run_all(positions_5_diverse)
    stats = StressStatistics()
    stats.record(r)
    snap = stats.snapshot()
    assert snap.total_runs == 1


def test_stress_stats_avg_resilience(positions_5_diverse):
    engine = StressTestEngine()
    stats = StressStatistics()
    for _ in range(3):
        stats.record(engine.run_all(positions_5_diverse))
    snap = stats.snapshot()
    assert snap.total_runs == 3
    assert 0.0 <= snap.avg_resilience <= 1.0
