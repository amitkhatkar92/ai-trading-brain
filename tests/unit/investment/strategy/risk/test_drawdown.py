"""tests/unit/investment/strategy/risk/test_drawdown.py
Tests for drawdown statistics, DrawdownProfile, RecoveryAnalysis, DrawdownEngine.
"""
import math
import pytest
from tests.unit.investment.strategy.risk.conftest import make_risk_input
from iios.investment.strategy.risk.drawdown_statistics import (
    calmar_ratio,
    ulcer_index,
    pain_index,
    expected_drawdown,
    max_expected_drawdown,
    recovery_days_estimate,
    recovery_probability,
    drawdown_risk_score,
)
from iios.investment.strategy.risk.drawdown_profile import DrawdownProfile
from iios.investment.strategy.risk.recovery_analysis import (
    RecoveryAnalysis, RecoveryCategory, RecoveryReport
)
from iios.investment.strategy.risk.drawdown_engine import DrawdownEngine, DrawdownReport


class TestDrawdownStatistics:
    def test_calmar_ratio_positive(self):
        assert calmar_ratio(0.20, 0.10) > 0.0

    def test_calmar_ratio_zero_drawdown(self):
        # zero drawdown → denominator clipped to 0.001 → large positive value
        assert calmar_ratio(0.20, 0.0) > 100.0

    def test_ulcer_index_non_negative(self):
        drawdowns = [0.05, 0.10, 0.08, 0.03]
        assert ulcer_index(drawdowns) >= 0.0

    def test_ulcer_index_flat_series(self):
        drawdowns = [0.0, 0.0, 0.0]
        assert ulcer_index(drawdowns) == pytest.approx(0.0)

    def test_pain_index_non_negative(self):
        drawdowns = [0.05, 0.10, 0.08, 0.03]
        assert pain_index(drawdowns) >= 0.0

    def test_expected_drawdown_proportional(self):
        dd1 = expected_drawdown(0.20, 0.50)
        dd2 = expected_drawdown(0.40, 0.50)
        assert dd2 > dd1

    def test_max_expected_drawdown_positive(self):
        assert max_expected_drawdown(0.20) > 0.0

    def test_recovery_days_positive(self):
        days = recovery_days_estimate(0.10, 0.20)
        assert days > 0.0

    def test_recovery_days_zero_return(self):
        assert recovery_days_estimate(0.10, 0.0) == float("inf")

    def test_recovery_probability_range(self):
        p = recovery_probability(0.15, 0.55, 1.2)
        assert 0.0 <= p <= 1.0

    def test_drawdown_risk_score_zero(self):
        assert drawdown_risk_score(0.0, 0.0) == pytest.approx(0.0)

    def test_drawdown_risk_score_range(self):
        score = drawdown_risk_score(0.30, 0.10)
        assert 0.0 <= score <= 100.0


class TestDrawdownProfile:
    def test_from_evaluation_creates_profile(self, risk_input):
        profile = DrawdownProfile.from_evaluation(
            risk_input.strategy_id,
            risk_input.max_drawdown,
            risk_input.annualized_return,
            risk_input.annualized_vol,
            risk_input.win_rate,
            risk_input.sharpe_ratio,
        )
        assert profile.strategy_id == risk_input.strategy_id
        assert 0.0 <= profile.drawdown_risk_score <= 100.0

    def test_profile_is_frozen(self, risk_input):
        profile = DrawdownProfile.from_evaluation(
            risk_input.strategy_id,
            risk_input.max_drawdown,
            risk_input.annualized_return,
            risk_input.annualized_vol,
            risk_input.win_rate,
            risk_input.sharpe_ratio,
        )
        with pytest.raises((AttributeError, TypeError)):
            profile.max_drawdown = 0.99

    def test_high_drawdown_raises_score(self):
        low_dd  = DrawdownProfile.from_evaluation("s", 0.05, 0.20, 0.10, 0.60, 1.5)
        high_dd = DrawdownProfile.from_evaluation("s", 0.40, 0.10, 0.30, 0.40, 0.3)
        assert high_dd.drawdown_risk_score > low_dd.drawdown_risk_score


class TestRecoveryAnalysis:
    def test_returns_report(self, risk_input):
        report = RecoveryAnalysis().analyse(risk_input)
        assert isinstance(report, RecoveryReport)

    def test_category_enum(self, risk_input):
        report = RecoveryAnalysis().analyse(risk_input)
        assert report.recovery_category in list(RecoveryCategory)

    def test_resilience_score_range(self, risk_input):
        report = RecoveryAnalysis().analyse(risk_input)
        assert 0.0 <= report.resilience_score <= 100.0


class TestDrawdownEngine:
    def test_evaluate_returns_report(self, risk_input):
        report = DrawdownEngine().evaluate(risk_input)
        assert isinstance(report, DrawdownReport)
        assert 0.0 <= report.overall_drawdown_risk_score <= 100.0

    def test_high_drawdown_input_higher_risk(self, high_risk_input, low_risk_input):
        high = DrawdownEngine().evaluate(high_risk_input).overall_drawdown_risk_score
        low  = DrawdownEngine().evaluate(low_risk_input).overall_drawdown_risk_score
        assert high > low

    def test_report_contains_profile_and_recovery(self, risk_input):
        report = DrawdownEngine().evaluate(risk_input)
        assert report.profile is not None
        assert report.recovery is not None
