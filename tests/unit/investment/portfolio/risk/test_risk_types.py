"""tests/unit/investment/portfolio/risk/test_risk_types.py"""
import math
import pytest

from iios.investment.portfolio.risk.risk_types import (
    DrawdownLevel, RiskGrade, RiskLevel, RiskPosition,
    bucket_weights, cvar_parametric, drawdown_to_level,
    hhi, portfolio_variance, portfolio_volatility,
    positions_from_plan, risk_score_to_grade, risk_score_to_level,
    var_parametric, weighted_average, NORMAL_Z_95, NORMAL_Z_99,
    TRADING_DAYS,
)


# ── Enum sanity ──────────────────────────────────────────────────────────────

def test_risk_grade_values():
    assert RiskGrade.A == "A"
    assert RiskGrade.F == "F"


def test_risk_level_order():
    levels = list(RiskLevel)
    assert levels[0] == RiskLevel.VERY_LOW
    assert levels[-1] == RiskLevel.CRITICAL


def test_drawdown_level_values():
    assert DrawdownLevel.NONE == "none"
    assert DrawdownLevel.EXTREME == "extreme"


# ── RiskPosition ─────────────────────────────────────────────────────────────

def test_risk_position_frozen(pos_equity_tech):
    with pytest.raises((TypeError, AttributeError)):
        pos_equity_tech.weight = 0.99  # type: ignore[misc]


def test_risk_position_annual_vol(pos_equity_tech):
    v = pos_equity_tech.annual_volatility
    # risk_score=0.55 → annual_vol = 0.05 + 0.55*0.55 = 0.3525
    assert abs(v - (0.05 + 0.55 * 0.55)) < 1e-9


def test_risk_position_daily_vol(pos_equity_tech):
    ann = pos_equity_tech.annual_volatility
    daily = pos_equity_tech.daily_volatility
    assert abs(daily - ann / math.sqrt(TRADING_DAYS)) < 1e-9


def test_risk_position_is_foreign_currency(pos_intl):
    assert pos_intl.is_foreign_currency is True


def test_risk_position_domestic_currency(pos_equity_tech):
    assert pos_equity_tech.is_foreign_currency is False


# ── positions_from_plan ───────────────────────────────────────────────────────

def test_positions_from_plan_list(positions_5_diverse):
    result = positions_from_plan(positions_5_diverse)
    assert len(result) == 5
    assert all(isinstance(p, RiskPosition) for p in result)


def test_positions_from_plan_duck_type(mock_plan_diverse, positions_5_diverse):
    result = positions_from_plan(mock_plan_diverse)
    assert len(result) == len(positions_5_diverse)


def test_positions_from_plan_empty():
    result = positions_from_plan([])
    assert result == []


# ── portfolio_variance / volatility ──────────────────────────────────────────

def test_portfolio_variance_positive(positions_5_diverse):
    v = portfolio_variance(positions_5_diverse)
    assert v >= 0


def test_portfolio_volatility_equals_sqrt_var(positions_5_diverse):
    var  = portfolio_variance(positions_5_diverse)
    vol  = portfolio_volatility(positions_5_diverse)
    assert abs(vol - math.sqrt(var)) < 1e-12


def test_portfolio_variance_single(single_position):
    var = portfolio_variance(single_position)
    # portfolio_variance uses annual_volatility → var = (w * annual_vol)^2 for single pos
    annual_vol = single_position[0].annual_volatility
    assert abs(var - annual_vol ** 2) < 1e-9


def test_portfolio_variance_empty():
    assert portfolio_variance([]) == 0.0


# ── var_parametric / cvar_parametric ─────────────────────────────────────────

def test_var_parametric_positive():
    v = var_parametric(0.01, NORMAL_Z_95, 1)
    assert v > 0


def test_var_parametric_scales_with_horizon():
    v1  = var_parametric(0.01, NORMAL_Z_95, 1)
    v10 = var_parametric(0.01, NORMAL_Z_95, 10)
    assert abs(v10 - v1 * math.sqrt(10)) < 1e-9


def test_cvar_gt_var():
    vol  = 0.015
    var  = var_parametric(vol, NORMAL_Z_95, 1)
    cvar = cvar_parametric(vol, NORMAL_Z_95, 1)
    assert cvar > var


def test_var_zero_vol():
    assert var_parametric(0, NORMAL_Z_95, 1) == 0.0


# ── weighted_average ──────────────────────────────────────────────────────────

def test_weighted_average_risk_score(positions_5_diverse):
    wa = weighted_average(positions_5_diverse, "risk_score")
    assert 0.0 <= wa <= 1.0


def test_weighted_average_empty():
    assert weighted_average([], "risk_score") == 0.0


# ── bucket_weights ────────────────────────────────────────────────────────────

def test_bucket_weights_sums_to_total(positions_5_diverse):
    bw = bucket_weights(positions_5_diverse, "sector")
    total = sum(bw.values())
    expected = sum(p.weight for p in positions_5_diverse)
    assert abs(total - expected) < 1e-9


def test_bucket_weights_empty():
    assert bucket_weights([], "sector") == {}


# ── hhi ───────────────────────────────────────────────────────────────────────

def test_hhi_uniform():
    # 4 equal weights → HHI = 0.25
    weights = [0.25, 0.25, 0.25, 0.25]
    assert abs(hhi(weights) - 0.25) < 1e-9


def test_hhi_single():
    assert abs(hhi([1.0]) - 1.0) < 1e-9


def test_hhi_empty():
    assert hhi([]) == 0.0


def test_hhi_between_zero_and_one(positions_5_diverse):
    weights = [p.weight for p in positions_5_diverse]
    h = hhi(weights)
    assert 0.0 <= h <= 1.0


# ── risk_score_to_level / grade ───────────────────────────────────────────────

@pytest.mark.parametrize("score,expected", [
    (0.0,  RiskLevel.VERY_LOW),
    (0.10, RiskLevel.VERY_LOW),
    (0.25, RiskLevel.LOW),
    (0.40, RiskLevel.MODERATE),
    (0.60, RiskLevel.HIGH),
    (0.75, RiskLevel.VERY_HIGH),
    (0.95, RiskLevel.CRITICAL),
    (1.0,  RiskLevel.CRITICAL),
])
def test_risk_score_to_level(score, expected):
    assert risk_score_to_level(score) == expected


@pytest.mark.parametrize("score,expected", [
    (0.10, RiskGrade.A),
    (0.25, RiskGrade.B),
    (0.45, RiskGrade.C),
    (0.65, RiskGrade.D),
    (0.85, RiskGrade.F),
])
def test_risk_score_to_grade(score, expected):
    assert risk_score_to_grade(score) == expected


# ── drawdown_to_level ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("dd,expected", [
    (0.0,  DrawdownLevel.NONE),
    (0.03, DrawdownLevel.MINIMAL),
    (0.10, DrawdownLevel.MODERATE),
    (0.22, DrawdownLevel.SEVERE),
    (0.45, DrawdownLevel.EXTREME),
])
def test_drawdown_to_level(dd, expected):
    assert drawdown_to_level(dd) == expected
