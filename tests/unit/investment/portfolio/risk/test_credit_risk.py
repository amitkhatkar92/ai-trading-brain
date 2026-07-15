"""tests/unit/investment/portfolio/risk/test_credit_risk.py"""
import pytest
from iios.investment.portfolio.risk.credit_risk import analyze_credit_risk, CreditRiskResult
from iios.investment.portfolio.risk.risk_types import RiskLevel, RiskPosition


def test_credit_risk_empty():
    r = analyze_credit_risk([])
    assert r.avg_credit_quality == 0.0


def test_credit_risk_returns_result(positions_5_diverse):
    r = analyze_credit_risk(positions_5_diverse, "p1")
    assert isinstance(r, CreditRiskResult)
    assert r.portfolio_id == "p1"


def test_credit_quality_in_range(positions_5_diverse):
    r = analyze_credit_risk(positions_5_diverse)
    assert 0.0 <= r.avg_credit_quality <= 1.0
    assert 0.0 <= r.min_credit_quality <= 1.0


def test_min_le_avg(positions_5_diverse):
    r = analyze_credit_risk(positions_5_diverse)
    assert r.min_credit_quality <= r.avg_credit_quality


def test_default_prob_positive(positions_5_diverse):
    r = analyze_credit_risk(positions_5_diverse)
    assert r.default_prob_proxy >= 0


def test_investment_grade_plus_junk_le_1(positions_5_diverse):
    r = analyze_credit_risk(positions_5_diverse)
    assert r.investment_grade_weight + r.junk_weight <= 1.001


def test_credit_risk_level_valid(positions_5_diverse):
    r = analyze_credit_risk(positions_5_diverse)
    assert r.risk_level in list(RiskLevel)


def test_credit_risk_to_dict(positions_5_diverse):
    d = analyze_credit_risk(positions_5_diverse).to_dict()
    assert "avg_credit_quality" in d
    assert "risk_level" in d


def test_credit_risk_high_risk_portfolio():
    junk = [
        RiskPosition(
            symbol=f"JUNK{i}", weight=0.25, sector="speculative",
            industry="high_yield", asset_class="equity",
            country="IN", currency="INR",
            risk_score=0.85, conviction=0.5, confidence=0.5,
            liquidity=0.30, credit_quality=0.20,
        )
        for i in range(4)
    ]
    r = analyze_credit_risk(junk)
    assert r.risk_level in (RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.CRITICAL)
    assert r.junk_weight > 0.5


def test_credit_risk_warnings_tuple(positions_5_diverse):
    r = analyze_credit_risk(positions_5_diverse)
    assert isinstance(r.warnings, tuple)
