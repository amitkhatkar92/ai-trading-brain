"""tests/unit/investment/portfolio/risk/test_concentration_risk.py"""
import pytest
from iios.investment.portfolio.risk.concentration_risk import (
    analyze_concentration_risk, ConcentrationRiskResult,
)
from iios.investment.portfolio.risk.risk_types import RiskLevel


def test_concentration_empty():
    r = analyze_concentration_risk([])
    assert r.n_positions == 0


def test_concentration_returns_result(positions_5_diverse):
    r = analyze_concentration_risk(positions_5_diverse, "p1")
    assert isinstance(r, ConcentrationRiskResult)


def test_n_positions(positions_5_diverse):
    r = analyze_concentration_risk(positions_5_diverse)
    assert r.n_positions == 5


def test_hhi_in_range(positions_5_diverse):
    r = analyze_concentration_risk(positions_5_diverse)
    assert 0.0 <= r.position_hhi <= 1.0
    assert 0.0 <= r.sector_hhi <= 1.0
    assert 0.0 <= r.industry_hhi <= 1.0


def test_top1_le_top3_le_top5(positions_5_diverse):
    r = analyze_concentration_risk(positions_5_diverse)
    assert r.top1_weight <= r.top3_weight <= r.top5_weight


def test_concentrated_portfolio_high_risk(positions_3_concentrated):
    r = analyze_concentration_risk(positions_3_concentrated)
    assert r.has_high_concentration or r.risk_level in (
        RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.CRITICAL
    )


def test_concentrated_top_sector(positions_3_concentrated):
    r = analyze_concentration_risk(positions_3_concentrated)
    assert r.top_sector == "energy"
    assert r.top_sector_weight > 0.5


def test_diverse_portfolio_lower_risk(positions_5_diverse):
    from iios.investment.portfolio.risk.risk_types import RiskPosition
    concentrated = analyze_concentration_risk(positions_5_diverse)
    # diverse should have lower or equal concentration_score
    conc_3 = analyze_concentration_risk([
        RiskPosition(
            symbol="A", weight=0.8, sector="tech", industry="sw",
            asset_class="equity", country="IN", currency="INR",
            risk_score=0.5, conviction=0.7, confidence=0.7,
            liquidity=0.8, credit_quality=0.8,
        ),
        RiskPosition(
            symbol="B", weight=0.2, sector="finance", industry="banking",
            asset_class="equity", country="IN", currency="INR",
            risk_score=0.4, conviction=0.6, confidence=0.6,
            liquidity=0.8, credit_quality=0.8,
        ),
    ])
    assert conc_3.concentration_score >= concentrated.concentration_score


def test_risk_level_valid(positions_5_diverse):
    r = analyze_concentration_risk(positions_5_diverse)
    assert r.risk_level in list(RiskLevel)


def test_to_dict(positions_5_diverse):
    d = analyze_concentration_risk(positions_5_diverse).to_dict()
    assert "position_hhi" in d
    assert "top_sector" in d
