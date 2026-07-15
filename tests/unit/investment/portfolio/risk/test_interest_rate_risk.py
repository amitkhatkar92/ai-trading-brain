"""tests/unit/investment/portfolio/risk/test_interest_rate_risk.py"""
import pytest
from iios.investment.portfolio.risk.interest_rate_risk import (
    analyze_interest_rate_risk, InterestRateRiskResult, DURATION_PROXY,
)
from iios.investment.portfolio.risk.risk_types import RiskLevel


def test_ir_empty():
    r = analyze_interest_rate_risk([])
    assert r.portfolio_duration_proxy == 0.0


def test_ir_equity_only(positions_5_diverse):
    equity_only = [p for p in positions_5_diverse if p.asset_class == "equity"]
    r = analyze_interest_rate_risk(equity_only)
    assert r.portfolio_duration_proxy == 0.0
    assert r.risk_level == RiskLevel.VERY_LOW


def test_ir_bond_heavy(positions_bond_heavy):
    r = analyze_interest_rate_risk(positions_bond_heavy)
    assert r.portfolio_duration_proxy > 0
    assert r.rate_sensitive_weight > 0


def test_ir_impact_100bps_positive(positions_bond_heavy):
    r = analyze_interest_rate_risk(positions_bond_heavy)
    assert r.impact_100bps > 0


def test_ir_impact_200bps_double_100(positions_bond_heavy):
    r = analyze_interest_rate_risk(positions_bond_heavy)
    assert abs(r.impact_200bps - 2 * r.impact_100bps) < 1e-9


def test_ir_impact_negative_is_gain(positions_bond_heavy):
    r = analyze_interest_rate_risk(positions_bond_heavy)
    assert r.impact_minus_100bps < 0   # negative = gain


def test_ir_risk_level_valid(positions_bond_heavy):
    r = analyze_interest_rate_risk(positions_bond_heavy)
    assert r.risk_level in list(RiskLevel)


def test_ir_asset_class_weights(positions_bond_heavy):
    r = analyze_interest_rate_risk(positions_bond_heavy)
    assert len(r.asset_class_weights) > 0


def test_ir_duration_proxy_values():
    assert DURATION_PROXY["bond"] == 7.0
    assert DURATION_PROXY["equity"] == 0.0
    assert DURATION_PROXY["cash"] == 0.1


def test_ir_to_dict(positions_bond_heavy):
    d = analyze_interest_rate_risk(positions_bond_heavy).to_dict()
    assert "portfolio_duration_proxy" in d
    assert "impact_100bps" in d
