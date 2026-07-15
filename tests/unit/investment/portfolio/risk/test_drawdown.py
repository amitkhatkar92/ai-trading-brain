"""tests/unit/investment/portfolio/risk/test_drawdown.py"""
import pytest
from iios.investment.portfolio.risk.drawdown_analysis import analyze_drawdown, DrawdownAnalysisResult
from iios.investment.portfolio.risk.drawdown_statistics import compute_drawdown_distribution
from iios.investment.portfolio.risk.drawdown_forecast import forecast_drawdown
from iios.investment.portfolio.risk.recovery_analysis import analyze_recovery
from iios.investment.portfolio.risk.risk_types import DrawdownLevel


# ── DrawdownAnalysisResult ────────────────────────────────────────────────

def test_drawdown_empty():
    r = analyze_drawdown([])
    assert r.max_drawdown_proxy == 0.0


def test_drawdown_returns_result(positions_5_diverse):
    r = analyze_drawdown(positions_5_diverse, "p1")
    assert isinstance(r, DrawdownAnalysisResult)
    assert r.portfolio_id == "p1"


def test_max_dd_positive(positions_5_diverse):
    r = analyze_drawdown(positions_5_diverse)
    assert r.max_drawdown_proxy > 0


def test_avg_dd_lt_max_dd(positions_5_diverse):
    r = analyze_drawdown(positions_5_diverse)
    assert r.avg_drawdown_proxy <= r.max_drawdown_proxy


def test_calmar_positive(positions_5_diverse):
    r = analyze_drawdown(positions_5_diverse)
    assert r.calmar_proxy > 0


def test_recovery_days_nonneg(positions_5_diverse):
    r = analyze_drawdown(positions_5_diverse)
    assert r.expected_recovery_days >= 0


def test_drawdown_level_valid(positions_5_diverse):
    r = analyze_drawdown(positions_5_diverse)
    assert r.drawdown_level in list(DrawdownLevel)


def test_high_risk_higher_dd():
    from iios.investment.portfolio.risk.risk_types import RiskPosition
    high_risk = [
        RiskPosition(
            symbol="H", weight=1.0, sector="tech", industry="startup",
            asset_class="equity", country="IN", currency="INR",
            risk_score=0.90, conviction=0.9, confidence=0.9,
            liquidity=0.5, credit_quality=0.4,
        )
    ]
    low_risk = [
        RiskPosition(
            symbol="L", weight=1.0, sector="bond", industry="sovereign",
            asset_class="bond", country="IN", currency="INR",
            risk_score=0.10, conviction=0.9, confidence=0.9,
            liquidity=0.98, credit_quality=0.98,
        )
    ]
    assert analyze_drawdown(high_risk).max_drawdown_proxy > analyze_drawdown(low_risk).max_drawdown_proxy


def test_drawdown_to_dict(positions_5_diverse):
    d = analyze_drawdown(positions_5_diverse).to_dict()
    assert "max_drawdown_proxy" in d
    assert "drawdown_level" in d


# ── DrawdownDistribution ──────────────────────────────────────────────────

def test_distribution_empty():
    r = compute_drawdown_distribution([])
    assert r.p50_drawdown == 0.0


def test_distribution_percentile_ordering(positions_5_diverse):
    r = compute_drawdown_distribution(positions_5_diverse)
    assert r.p50_drawdown <= r.p75_drawdown <= r.p90_drawdown <= r.p95_drawdown <= r.p99_drawdown


def test_distribution_in_range(positions_5_diverse):
    r = compute_drawdown_distribution(positions_5_diverse)
    assert 0.0 <= r.p99_drawdown <= 1.0


# ── DrawdownForecast ──────────────────────────────────────────────────────

def test_forecast_empty():
    r = forecast_drawdown([])
    assert r.expected_max_dd_30d == 0.0


def test_forecast_horizon_ordering(positions_5_diverse):
    r = forecast_drawdown(positions_5_diverse)
    assert r.expected_max_dd_30d <= r.expected_max_dd_90d <= r.expected_max_dd_252d


def test_forecast_probabilities_in_range(positions_5_diverse):
    r = forecast_drawdown(positions_5_diverse)
    for prob in (r.prob_dd_exceeds_5pct, r.prob_dd_exceeds_10pct, r.prob_dd_exceeds_20pct):
        assert 0.0 <= prob <= 1.0


def test_forecast_prob_decreasing_threshold(positions_5_diverse):
    r = forecast_drawdown(positions_5_diverse)
    assert r.prob_dd_exceeds_5pct >= r.prob_dd_exceeds_10pct >= r.prob_dd_exceeds_20pct


def test_forecast_confidence_range(positions_5_diverse):
    r = forecast_drawdown(positions_5_diverse)
    assert 0.0 <= r.forecast_confidence <= 1.0


# ── RecoveryAnalysis ──────────────────────────────────────────────────────

def test_recovery_empty():
    r = analyze_recovery([])
    assert r.expected_recovery_days == 0


def test_recovery_days_nonneg(positions_5_diverse):
    r = analyze_recovery(positions_5_diverse)
    assert r.expected_recovery_days >= 0


def test_recovery_larger_drawdown_longer(positions_5_diverse):
    # Higher reference drawdown → lower probability of recovering in 30 days
    r20 = analyze_recovery(positions_5_diverse, reference_drawdown=0.20)
    r10 = analyze_recovery(positions_5_diverse, reference_drawdown=0.10)
    assert r20.recovery_prob_30d <= r10.recovery_prob_30d


def test_recovery_prob_ordering(positions_5_diverse):
    r = analyze_recovery(positions_5_diverse)
    assert r.recovery_prob_30d <= r.recovery_prob_60d <= r.recovery_prob_90d


def test_recovery_trajectory_valid(positions_5_diverse):
    r = analyze_recovery(positions_5_diverse)
    assert r.recovery_trajectory in ("fast", "moderate", "slow")


def test_recovery_to_dict(positions_5_diverse):
    d = analyze_recovery(positions_5_diverse).to_dict()
    assert "expected_recovery_days" in d
    assert "recovery_trajectory" in d
