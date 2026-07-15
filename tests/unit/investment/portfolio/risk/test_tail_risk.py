"""tests/unit/investment/portfolio/risk/test_tail_risk.py"""
import pytest
from iios.investment.portfolio.risk.tail_risk import analyze_tail_risk, TailRiskResult
from iios.investment.portfolio.risk.risk_types import RiskLevel


def test_tail_risk_empty():
    r = analyze_tail_risk([])
    assert r.var_99_1d == 0.0


def test_tail_risk_returns_result(positions_5_diverse):
    r = analyze_tail_risk(positions_5_diverse, "p1")
    assert isinstance(r, TailRiskResult)


def test_var999_gt_var99(positions_5_diverse):
    r = analyze_tail_risk(positions_5_diverse)
    assert r.var_999_1d >= r.var_99_1d


def test_cvar99_gt_var99(positions_5_diverse):
    r = analyze_tail_risk(positions_5_diverse)
    assert r.cvar_99_1d >= r.var_99_1d


def test_cvar99_gt_cvar95(positions_5_diverse):
    r = analyze_tail_risk(positions_5_diverse)
    assert r.cvar_99_1d >= r.cvar_95_1d


def test_skewness_negative_for_risky():
    from iios.investment.portfolio.risk.risk_types import RiskPosition
    risky = [
        RiskPosition(
            symbol="R1", weight=0.5, sector="tech", industry="startup",
            asset_class="equity", country="IN", currency="INR",
            risk_score=0.90, conviction=0.9, confidence=0.9,
            liquidity=0.30, credit_quality=0.30,
        ),
        RiskPosition(
            symbol="R2", weight=0.5, sector="tech", industry="startup",
            asset_class="equity", country="IN", currency="INR",
            risk_score=0.85, conviction=0.9, confidence=0.9,
            liquidity=0.25, credit_quality=0.25,
        ),
    ]
    r = analyze_tail_risk(risky)
    assert r.skewness_proxy < 0


def test_black_swan_loss_positive(positions_5_diverse):
    r = analyze_tail_risk(positions_5_diverse)
    assert r.black_swan_1pct_loss > 0


def test_systemic_risk_positive(positions_5_diverse):
    r = analyze_tail_risk(positions_5_diverse)
    assert r.systemic_risk_proxy >= 0


def test_risk_level_valid(positions_5_diverse):
    r = analyze_tail_risk(positions_5_diverse)
    assert r.risk_level in list(RiskLevel)


def test_top_tail_contributor_set(positions_5_diverse):
    r = analyze_tail_risk(positions_5_diverse)
    assert r.top_tail_contributor != ""


def test_to_dict(positions_5_diverse):
    d = analyze_tail_risk(positions_5_diverse).to_dict()
    assert "var_99_1d" in d
    assert "skewness_proxy" in d
