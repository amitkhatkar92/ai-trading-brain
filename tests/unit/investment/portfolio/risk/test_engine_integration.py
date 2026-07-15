"""tests/unit/investment/portfolio/risk/test_engine_integration.py

End-to-end integration tests for PortfolioRiskEngine.
"""
import pytest
from iios.investment.portfolio.risk.portfolio_risk_engine import (
    MonitoringReport, PortfolioRiskEngine, RiskIntegrationRefs,
)
from iios.investment.portfolio.risk.portfolio_risk_profile import PortfolioRiskProfile
from iios.investment.portfolio.risk.portfolio_risk_score import RiskScoreCalculator
from iios.investment.portfolio.risk.risk_quality import RiskQualityAssessor


# ── Lifecycle ─────────────────────────────────────────────────────────────

def test_engine_starts_stopped():
    engine = PortfolioRiskEngine()
    assert engine.is_running is False


def test_engine_start_stop():
    engine = PortfolioRiskEngine()
    engine.start()
    assert engine.is_running
    engine.stop()
    assert not engine.is_running


def test_engine_version():
    assert PortfolioRiskEngine.VERSION == "1.0.0"


# ── Registration ───────────────────────────────────────────────────────────

def test_register_portfolio():
    engine = PortfolioRiskEngine()
    engine.register_portfolio("p1")
    assert engine.is_registered("p1")


def test_deregister_portfolio():
    engine = PortfolioRiskEngine()
    engine.register_portfolio("p1")
    engine.deregister_portfolio("p1")
    assert not engine.is_registered("p1")


def test_unregistered_portfolio_not_found():
    engine = PortfolioRiskEngine()
    assert not engine.is_registered("nonexistent")


# ── evaluate() ────────────────────────────────────────────────────────────

def test_evaluate_returns_profile(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    profile = engine.evaluate("p1", mock_plan_diverse)
    assert isinstance(profile, PortfolioRiskProfile)
    assert profile.portfolio_id == "p1"


def test_evaluate_frozen_profile(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    profile = engine.evaluate("p1", mock_plan_diverse)
    with pytest.raises((TypeError, AttributeError)):
        profile.overall_risk_score = 999  # type: ignore[misc]


def test_evaluate_profile_score_in_range(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    profile = engine.evaluate("p1", mock_plan_diverse)
    assert 0.0 <= profile.overall_risk_score <= 1.0


def test_evaluate_has_created_at(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    profile = engine.evaluate("p1", mock_plan_diverse)
    assert profile.created_at != ""


def test_evaluate_n_positions(mock_plan_diverse, positions_5_diverse):
    engine = PortfolioRiskEngine()
    profile = engine.evaluate("p1", mock_plan_diverse)
    assert profile.n_positions == len(positions_5_diverse)


def test_evaluate_risk_grade_valid(mock_plan_diverse):
    from iios.investment.portfolio.risk.risk_types import RiskGrade
    engine = PortfolioRiskEngine()
    profile = engine.evaluate("p1", mock_plan_diverse)
    assert profile.risk_grade in [g.value for g in RiskGrade]


def test_evaluate_concentrated_higher_risk(
    mock_plan_diverse, mock_plan_concentrated
):
    engine = PortfolioRiskEngine()
    p_div  = engine.evaluate("pdiv",  mock_plan_diverse)
    p_conc = engine.evaluate("pconc", mock_plan_concentrated)
    # concentrated should have higher position_hhi
    assert p_conc.position_hhi >= p_div.position_hhi


def test_evaluate_stress_resilience_present(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    profile = engine.evaluate("p1", mock_plan_diverse)
    assert profile.stress_worst_scenario != ""
    assert 0.0 <= profile.stress_resilience_score <= 1.0


def test_evaluate_auto_registers(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    engine.evaluate("pnew", mock_plan_diverse, auto_register=True)
    assert engine.is_registered("pnew")


# ── History and queries ───────────────────────────────────────────────────

def test_current_profile_after_evaluate(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    profile = engine.evaluate("p1", mock_plan_diverse)
    current = engine.current_profile("p1")
    assert current is not None
    assert current.profile_id == profile.profile_id


def test_history_grows(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    engine.evaluate("p1", mock_plan_diverse)
    engine.evaluate("p1", mock_plan_diverse)
    assert len(engine.history("p1")) == 2


def test_history_n_limit(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    for _ in range(5):
        engine.evaluate("p1", mock_plan_diverse)
    assert len(engine.history("p1", n=2)) == 2


def test_best_profile_lowest_score(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    profiles = [engine.evaluate("p1", mock_plan_diverse) for _ in range(3)]
    best = engine.best_profile("p1")
    assert best is not None
    assert best.overall_risk_score == min(p.overall_risk_score for p in profiles)


def test_quality_score_after_evaluate(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    engine.evaluate("p1", mock_plan_diverse)
    qs = engine.quality_score("p1")
    assert qs is not None
    assert 0.0 <= qs <= 1.0


# ── Statistics & Health ───────────────────────────────────────────────────

def test_statistics_snapshot(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    engine.evaluate("p1", mock_plan_diverse)
    snap = engine.statistics_snapshot()
    assert snap.total_runs == 1
    assert snap.success_runs == 1


def test_health_after_evaluate(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    engine.evaluate("p1", mock_plan_diverse)
    h = engine.health()
    assert h.is_healthy is True
    assert h.total_runs == 1


# ── Monitor ───────────────────────────────────────────────────────────────

def test_monitor_portfolio_returns_report(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    r = engine.monitor_portfolio("p1", mock_plan_diverse)
    assert isinstance(r, MonitoringReport)
    assert r.portfolio_id == "p1"


def test_monitor_report_to_dict(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    d = engine.monitor_portfolio("p1", mock_plan_diverse).to_dict()
    assert "overall_risk_score" in d


def test_monitor_handles_empty_plan():
    engine = PortfolioRiskEngine()
    r = engine.monitor_portfolio("pempty", [])
    assert isinstance(r, MonitoringReport)
    assert r.portfolio_id == "pempty"


# ── Integration refs ──────────────────────────────────────────────────────

def test_configure_integrations():
    engine = PortfolioRiskEngine()
    refs = RiskIntegrationRefs(portfolio_framework=object())
    engine.configure_integrations(refs)
    # no exception


# ── Event callback ────────────────────────────────────────────────────────

def test_event_callback_called(mock_plan_diverse):
    events = []
    engine = PortfolioRiskEngine(event_callback=lambda e, v: events.append((e, v)))
    engine.evaluate("p1", mock_plan_diverse)
    assert len(events) == 1
    assert events[0][0] == "risk_evaluated"
    assert isinstance(events[0][1], PortfolioRiskProfile)


# ── profile.to_dict() ─────────────────────────────────────────────────────

def test_profile_to_dict(mock_plan_diverse):
    engine = PortfolioRiskEngine()
    profile = engine.evaluate("p1", mock_plan_diverse)
    d = profile.to_dict()
    required_keys = [
        "profile_id", "portfolio_id", "n_positions",
        "overall_risk_score", "risk_grade", "is_acceptable",
        "var_95_1d", "stress_worst_scenario",
    ]
    for k in required_keys:
        assert k in d, f"Missing key: {k}"
