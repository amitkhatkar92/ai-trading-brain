"""tests/unit/investment/portfolio/risk/test_market_risk.py"""
import math
import pytest

from iios.investment.portfolio.risk.market_risk import analyze_market_risk, MarketRiskResult
from iios.investment.portfolio.risk.risk_types import RiskLevel


def test_market_risk_empty():
    r = analyze_market_risk([])
    assert r.portfolio_vol_annual == 0.0
    assert r.var_95_1d == 0.0


def test_market_risk_returns_result(positions_5_diverse):
    r = analyze_market_risk(positions_5_diverse, "p1")
    assert isinstance(r, MarketRiskResult)
    assert r.portfolio_id == "p1"


def test_market_risk_vol_positive(positions_5_diverse):
    r = analyze_market_risk(positions_5_diverse)
    assert r.portfolio_vol_annual > 0
    assert r.portfolio_vol_daily > 0


def test_market_risk_daily_vs_annual(positions_5_diverse):
    r = analyze_market_risk(positions_5_diverse)
    # annual = daily * sqrt(252), within rounding tolerance
    assert abs(r.portfolio_vol_annual - r.portfolio_vol_daily * math.sqrt(252)) < 1e-4


def test_market_risk_var_ordering(positions_5_diverse):
    r = analyze_market_risk(positions_5_diverse)
    # 99% VaR > 95% VaR
    assert r.var_99_1d > r.var_95_1d


def test_market_risk_10d_var_gt_1d(positions_5_diverse):
    r = analyze_market_risk(positions_5_diverse)
    assert r.var_95_10d > r.var_95_1d


def test_market_risk_cvar_gt_var(positions_5_diverse):
    r = analyze_market_risk(positions_5_diverse)
    assert r.cvar_95_1d >= r.var_95_1d


def test_market_risk_diversification_benefit(positions_5_diverse):
    r = analyze_market_risk(positions_5_diverse)
    # diversification benefit should be ≥ 0
    assert r.diversification_benefit >= 0


def test_market_risk_single_position(single_position):
    r = analyze_market_risk(single_position)
    assert r.portfolio_vol_annual > 0
    # Single position → diversification_benefit ≈ 0
    assert r.diversification_benefit >= 0


def test_market_risk_risk_level_valid(positions_5_diverse):
    r = analyze_market_risk(positions_5_diverse)
    assert r.risk_level in list(RiskLevel)


def test_market_risk_high_risk_positions():
    from iios.investment.portfolio.risk.risk_types import RiskPosition
    high = [
        RiskPosition(
            symbol="HIGH1", weight=0.5, sector="tech", industry="startup",
            asset_class="equity", country="IN", currency="INR",
            risk_score=0.90, conviction=0.9, confidence=0.9,
            liquidity=0.5, credit_quality=0.3,
        ),
        RiskPosition(
            symbol="HIGH2", weight=0.5, sector="tech", industry="startup",
            asset_class="equity", country="IN", currency="INR",
            risk_score=0.95, conviction=0.9, confidence=0.9,
            liquidity=0.5, credit_quality=0.3,
        ),
    ]
    r = analyze_market_risk(high)
    assert r.risk_level in (RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.CRITICAL)


def test_market_risk_warnings_type(positions_5_diverse):
    r = analyze_market_risk(positions_5_diverse)
    assert isinstance(r.warnings, tuple)


def test_market_risk_to_dict(positions_5_diverse):
    r = analyze_market_risk(positions_5_diverse)
    d = r.to_dict()
    assert "var_95_1d" in d
    assert "portfolio_vol_annual" in d
