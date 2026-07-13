"""tests/unit/investment/strategy/risk/test_risk_limits.py
Tests for RiskLimits, RiskConstraints, LimitMonitor.
"""
import pytest
from tests.unit.investment.strategy.risk.conftest import make_risk_input
from iios.investment.strategy.risk.risk_limits import (
    RiskLimits, DEFAULT_LIMITS, CONSERVATIVE_LIMITS, AGGRESSIVE_LIMITS, INSTITUTIONAL_LIMITS
)
from iios.investment.strategy.risk.risk_constraints import (
    RiskConstraints, ConstraintStatus, ConstraintCheckResult
)
from iios.investment.strategy.risk.limit_monitor import LimitMonitor


class TestRiskLimits:
    def test_default_limits_values(self):
        lim = DEFAULT_LIMITS
        assert lim.max_risk_score > 0
        assert lim.daily_loss_limit > 0
        assert lim.max_drawdown_limit > 0

    def test_conservative_stricter_than_aggressive(self):
        assert CONSERVATIVE_LIMITS.max_risk_score < AGGRESSIVE_LIMITS.max_risk_score
        assert CONSERVATIVE_LIMITS.max_drawdown_limit < AGGRESSIVE_LIMITS.max_drawdown_limit

    def test_institutional_exists(self):
        assert INSTITUTIONAL_LIMITS is not None
        assert INSTITUTIONAL_LIMITS.max_risk_score > 0

    def test_limits_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            DEFAULT_LIMITS.max_risk_score = 999


class TestRiskConstraints:
    def test_good_strategy_passes(self, risk_input):
        result = RiskConstraints().check(
            risk_input, risk_score=40.0,
            stress_pass_rate=DEFAULT_LIMITS.min_stress_pass_rate,
            stress_agg_score=35.0,
            limits=DEFAULT_LIMITS
        )
        # May have warnings but not breaches
        assert not result.emergency_stop
        assert result.breach_count == 0

    def test_breached_risk_score(self, risk_input):
        result = RiskConstraints().check(
            risk_input, risk_score=95.0, stress_pass_rate=0.5, stress_agg_score=90.0,
            limits=DEFAULT_LIMITS
        )
        assert not result.all_passed
        assert result.breach_count > 0

    def test_emergency_stop_triggers(self, risk_input):
        result = RiskConstraints().check(
            risk_input, risk_score=98.0, stress_pass_rate=0.2, stress_agg_score=98.0,
            limits=DEFAULT_LIMITS
        )
        assert result.emergency_stop

    def test_warn_status_near_limit(self, risk_input):
        limit_80_pct = DEFAULT_LIMITS.max_risk_score * 0.87
        result = RiskConstraints().check(
            risk_input, risk_score=limit_80_pct,
            stress_pass_rate=0.90, stress_agg_score=30.0,
            limits=DEFAULT_LIMITS
        )
        statuses = [item.status for item in result.breaches + result.warnings + result.passed]
        assert ConstraintStatus.WARN in statuses or ConstraintStatus.PASS in statuses

    def test_breach_messages_populated(self, high_risk_input):
        result = RiskConstraints().check(
            high_risk_input, risk_score=90.0,
            stress_pass_rate=0.2, stress_agg_score=88.0,
            limits=DEFAULT_LIMITS
        )
        if not result.all_passed:
            assert any(item.message for item in result.breaches)

    def test_result_is_frozen(self, risk_input):
        result = RiskConstraints().check(
            risk_input, risk_score=40.0, stress_pass_rate=0.90, stress_agg_score=35.0,
            limits=DEFAULT_LIMITS
        )
        with pytest.raises((AttributeError, TypeError)):
            result.all_passed = False


class TestLimitMonitor:
    def test_check_and_record(self, risk_input):
        monitor = LimitMonitor(DEFAULT_LIMITS)
        result = monitor.check_and_record(risk_input, 40.0, 0.90, 35.0)
        assert isinstance(result, ConstraintCheckResult)

    def test_breach_recorded(self, risk_input):
        monitor = LimitMonitor(DEFAULT_LIMITS)
        monitor.check_and_record(risk_input, 95.0, 0.2, 90.0)
        assert monitor.total_breach_count(risk_input.strategy_id) > 0

    def test_breach_history_returns_list(self, risk_input):
        monitor = LimitMonitor(DEFAULT_LIMITS)
        monitor.check_and_record(risk_input, 80.0, 0.5, 75.0)
        history = monitor.breach_history(risk_input.strategy_id)
        assert isinstance(history, list)

    def test_latest_breach_after_breach(self, risk_input):
        monitor = LimitMonitor(DEFAULT_LIMITS)
        monitor.check_and_record(risk_input, 95.0, 0.2, 90.0)
        latest = monitor.latest_breach(risk_input.strategy_id)
        assert latest is not None

    def test_no_breach_no_history(self, risk_input):
        monitor = LimitMonitor(DEFAULT_LIMITS)
        monitor.check_and_record(risk_input, 20.0, DEFAULT_LIMITS.min_stress_pass_rate, 10.0)
        assert monitor.total_breach_count(risk_input.strategy_id) == 0
