"""tests/unit/investment/portfolio/risk/test_liquidity_risk.py"""
import pytest
from iios.investment.portfolio.risk.liquidity_risk import analyze_liquidity_risk, LiquidityRiskResult
from iios.investment.portfolio.risk.risk_types import RiskLevel, RiskPosition


def test_liquidity_empty():
    r = analyze_liquidity_risk([])
    assert r.avg_liquidity_score == 0.0


def test_liquidity_returns_result(positions_5_diverse):
    r = analyze_liquidity_risk(positions_5_diverse, "p1")
    assert isinstance(r, LiquidityRiskResult)


def test_avg_liquidity_in_range(positions_5_diverse):
    r = analyze_liquidity_risk(positions_5_diverse)
    assert 0.0 <= r.avg_liquidity_score <= 1.0


def test_illiquid_weight_in_range(positions_5_diverse):
    r = analyze_liquidity_risk(positions_5_diverse)
    assert 0.0 <= r.illiquid_weight <= 1.0


def test_liquid_plus_semiliquid_plus_illiquid_approx_one(positions_5_diverse):
    r = analyze_liquidity_risk(positions_5_diverse)
    total = r.liquid_weight + r.semi_liquid_weight + r.illiquid_weight
    total_weight = sum(p.weight for p in positions_5_diverse)
    assert abs(total - total_weight) < 0.01


def test_lvar_gt_var(positions_5_diverse):
    r = analyze_liquidity_risk(positions_5_diverse)
    from iios.investment.portfolio.risk.market_risk import analyze_market_risk
    mr = analyze_market_risk(positions_5_diverse)
    assert r.lvar_95_1d >= mr.var_95_1d


def test_risk_level_valid(positions_5_diverse):
    r = analyze_liquidity_risk(positions_5_diverse)
    assert r.risk_level in list(RiskLevel)


def test_illiquid_portfolio_warning():
    illiquid = [
        RiskPosition(
            symbol=f"ILL{i}", weight=0.25, sector="private",
            industry="private_equity", asset_class="equity",
            country="IN", currency="INR",
            risk_score=0.7, conviction=0.6, confidence=0.6,
            liquidity=0.10, credit_quality=0.50,
        )
        for i in range(4)
    ]
    r = analyze_liquidity_risk(illiquid)
    assert r.illiquid_weight > 0.5
    assert len(r.warnings) > 0


def test_to_dict(positions_5_diverse):
    d = analyze_liquidity_risk(positions_5_diverse).to_dict()
    assert "avg_liquidity_score" in d
