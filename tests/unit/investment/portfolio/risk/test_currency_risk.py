"""tests/unit/investment/portfolio/risk/test_currency_risk.py"""
import pytest
from iios.investment.portfolio.risk.currency_risk import analyze_currency_risk, CurrencyRiskResult
from iios.investment.portfolio.risk.risk_types import RiskLevel


def test_currency_empty():
    r = analyze_currency_risk([], "INR")
    assert r.foreign_weight == 0.0


def test_currency_domestic_only(positions_5_diverse):
    # Remove international positions
    domestic = [p for p in positions_5_diverse if p.currency == "INR"]
    r = analyze_currency_risk(domestic, "INR")
    assert r.foreign_weight == 0.0
    assert r.risk_level == RiskLevel.VERY_LOW


def test_currency_foreign_weight(positions_intl_heavy):
    r = analyze_currency_risk(positions_intl_heavy, "INR")
    assert r.foreign_weight > 0


def test_currency_n_currencies(positions_intl_heavy):
    r = analyze_currency_risk(positions_intl_heavy, "INR")
    assert r.n_currencies >= 2


def test_currency_hhi_range(positions_intl_heavy):
    r = analyze_currency_risk(positions_intl_heavy, "INR")
    assert 0.0 <= r.currency_hhi <= 1.0


def test_fx_shock_scales(positions_intl_heavy):
    r = analyze_currency_risk(positions_intl_heavy, "INR")
    assert r.fx_shock_impact_15pct < r.fx_shock_impact_30pct


def test_fx_shock_30_approx_double_15(positions_intl_heavy):
    r = analyze_currency_risk(positions_intl_heavy, "INR")
    assert abs(r.fx_shock_impact_30pct - r.fx_shock_impact_15pct * 2) < 1e-3


def test_risk_level_valid(positions_intl_heavy):
    r = analyze_currency_risk(positions_intl_heavy, "INR")
    assert r.risk_level in list(RiskLevel)


def test_warnings_tuple(positions_intl_heavy):
    r = analyze_currency_risk(positions_intl_heavy, "INR")
    assert isinstance(r.warnings, tuple)


def test_to_dict(positions_intl_heavy):
    d = analyze_currency_risk(positions_intl_heavy, "INR").to_dict()
    assert "foreign_weight" in d
    assert "n_currencies" in d
