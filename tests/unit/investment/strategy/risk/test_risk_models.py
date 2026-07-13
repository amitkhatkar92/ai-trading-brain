"""tests/unit/investment/strategy/risk/test_risk_models.py
Tests for StrategyRiskInput and risk_statistics functions.
"""
import math
import pytest
from tests.unit.investment.strategy.risk.conftest import make_risk_input
from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.risk_statistics import (
    clamp,
    parametric_var,
    parametric_cvar,
    expected_daily_loss,
    expected_weekly_loss,
    expected_monthly_loss,
    vol_risk_score,
    drawdown_risk_score,
    sharpe_risk_score,
    tail_risk_score,
    regime_mismatch_penalty,
    vol_level_penalty,
)


# ── StrategyRiskInput ────────────────────────────────────────────────────────

class TestStrategyRiskInput:
    def test_frozen(self, risk_input):
        with pytest.raises((AttributeError, TypeError)):
            risk_input.strategy_id = "changed"

    def test_regime_mismatch_true(self):
        inp = make_risk_input(
            current_regime="ranging",
            supported_regimes=("trending",)
        )
        assert inp.regime_mismatch is True

    def test_regime_mismatch_false(self):
        inp = make_risk_input(
            current_regime="trending",
            supported_regimes=("trending", "ranging")
        )
        assert inp.regime_mismatch is False

    def test_daily_vol_property(self, risk_input):
        expected = risk_input.annualized_vol / math.sqrt(252)
        assert abs(risk_input.daily_vol - expected) < 1e-10

    def test_valid_positive_values(self, risk_input):
        assert risk_input.evaluation_score > 0
        assert risk_input.annualized_vol > 0
        assert risk_input.max_drawdown >= 0


# ── clamp ─────────────────────────────────────────────────────────────────────

class TestClamp:
    def test_in_range(self):
        assert clamp(50.0) == 50.0

    def test_below_min(self):
        assert clamp(-5.0) == 0.0

    def test_above_max(self):
        assert clamp(105.0) == 100.0

    def test_boundary_zero(self):
        assert clamp(0.0) == 0.0

    def test_boundary_hundred(self):
        assert clamp(100.0) == 100.0

    def test_custom_bounds(self):
        assert clamp(150.0, lo=0.0, hi=200.0) == 150.0
        assert clamp(-1.0, lo=0.0, hi=200.0) == 0.0


# ── VaR & CVaR ───────────────────────────────────────────────────────────────

class TestVaR:
    def test_parametric_var_positive(self):
        v = parametric_var(0.0, 0.01, 0.95)
        assert v > 0.0

    def test_parametric_var_higher_confidence(self):
        v95 = parametric_var(0.0, 0.01, 0.95)
        v99 = parametric_var(0.0, 0.01, 0.99)
        assert v99 > v95

    def test_parametric_cvar_greater_than_var(self):
        var = parametric_var(0.0, 0.01, 0.95)
        cvar = parametric_cvar(0.0, 0.01, 0.95)
        assert cvar >= var

    def test_expected_daily_loss_positive(self):
        loss = expected_daily_loss(0.20, 0.95)
        assert loss > 0.0

    def test_expected_weekly_loss_greater_than_daily(self):
        daily = expected_daily_loss(0.20, 0.95)
        weekly = expected_weekly_loss(0.20, 0.95)
        assert weekly > daily

    def test_expected_monthly_loss_greater_than_weekly(self):
        weekly = expected_weekly_loss(0.20, 0.95)
        monthly = expected_monthly_loss(0.20, 0.95)
        assert monthly > weekly


# ── risk score functions ──────────────────────────────────────────────────────

class TestRiskScoreFunctions:
    def test_vol_risk_score_low_vol(self):
        assert vol_risk_score(0.05) == 0.0   # below low threshold

    def test_vol_risk_score_high_vol(self):
        score = vol_risk_score(0.60)
        assert score >= 100.0 or score == pytest.approx(100.0, abs=1e-6)

    def test_vol_risk_score_mid(self):
        score = vol_risk_score(0.20)
        assert 0.0 < score < 100.0

    def test_drawdown_risk_score_zero(self):
        assert drawdown_risk_score(0.0) == 0.0

    def test_drawdown_risk_score_ceiling(self):
        assert drawdown_risk_score(0.40) == pytest.approx(100.0)

    def test_drawdown_risk_score_partial(self):
        score = drawdown_risk_score(0.20)
        assert 0.0 < score < 100.0

    def test_sharpe_risk_score_high_sharpe(self):
        score = sharpe_risk_score(3.0)
        assert score < 20.0

    def test_sharpe_risk_score_negative(self):
        score = sharpe_risk_score(-0.5)
        assert score >= 80.0

    def test_tail_risk_score_range(self):
        score = tail_risk_score(0.30, 0.50)
        assert 0.0 <= score <= 100.0

    def test_regime_mismatch_penalty_true(self):
        assert regime_mismatch_penalty(True) > 0.0

    def test_regime_mismatch_penalty_false(self):
        assert regime_mismatch_penalty(False) == 0.0

    def test_vol_level_penalty_extreme(self):
        assert vol_level_penalty("extreme") > vol_level_penalty("high")

    def test_vol_level_penalty_low(self):
        assert vol_level_penalty("low") == 0.0

    def test_vol_level_penalty_normal(self):
        assert vol_level_penalty("normal") >= 0.0
