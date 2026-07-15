"""tests/unit/investment/portfolio/recommendation/test_portfolio_rules.py

Tests for all pure rule functions in portfolio_rules.py.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.recommendation.portfolio_rules import (
    evaluate_aggressive_signal,
    evaluate_calmar_deterioration,
    evaluate_cash_deficiency,
    evaluate_cash_excess,
    evaluate_concentration,
    evaluate_construction_quality,
    evaluate_defensive_signal,
    evaluate_drawdown_severity,
    evaluate_equity_overweight,
    evaluate_equity_underweight,
    evaluate_hedge_signal,
    evaluate_information_ratio_poor,
    evaluate_insufficient_positions,
    evaluate_international_underweight,
    evaluate_optimization_quality,
    evaluate_rebalance_trigger,
    evaluate_risk_capacity,
    evaluate_risk_overextension,
    evaluate_sector_concentration,
    evaluate_sharpe_deterioration,
    evaluate_var_breach,
)
from iios.investment.portfolio.recommendation.recommendation_types import (
    EQUITY_OVERWEIGHT_THRESHOLD,
    EQUITY_UNDERWEIGHT_THRESHOLD,
    RISK_BUDGET_HIGH_THRESHOLD,
    VAR_CRITICAL_THRESHOLD,
)


class TestRiskRules:
    def test_risk_overextension_triggered(self):
        ok, msg = evaluate_risk_overextension(0.90, RISK_BUDGET_HIGH_THRESHOLD)
        assert ok is True
        assert "risk budget" in msg.lower()

    def test_risk_overextension_not_triggered(self):
        ok, msg = evaluate_risk_overextension(0.50, RISK_BUDGET_HIGH_THRESHOLD)
        assert ok is False

    def test_var_breach_triggered(self):
        ok, msg = evaluate_var_breach(0.95, VAR_CRITICAL_THRESHOLD)
        assert ok is True

    def test_var_breach_not_triggered(self):
        ok, msg = evaluate_var_breach(0.50, VAR_CRITICAL_THRESHOLD)
        assert ok is False

    def test_drawdown_severity_triggered(self):
        ok, msg = evaluate_drawdown_severity(0.20, 0.15)
        assert ok is True

    def test_drawdown_severity_not_triggered(self):
        ok, msg = evaluate_drawdown_severity(0.05, 0.15)
        assert ok is False

    def test_risk_capacity_exhausted(self):
        # risk_budget low → has capacity → triggered
        ok, msg = evaluate_risk_capacity(0.30, 0.40)
        assert ok is True

    def test_risk_capacity_normal(self):
        # risk_budget high → no spare capacity → not triggered
        ok, msg = evaluate_risk_capacity(0.80, 0.40)
        assert ok is False


class TestAllocationRules:
    def test_equity_overweight(self):
        # equity_drift > threshold → overweight
        drift = EQUITY_OVERWEIGHT_THRESHOLD + 0.01
        ok, _ = evaluate_equity_overweight(drift, EQUITY_OVERWEIGHT_THRESHOLD)
        assert ok is True

    def test_equity_not_overweight(self):
        ok, _ = evaluate_equity_overweight(0.02, EQUITY_OVERWEIGHT_THRESHOLD)
        assert ok is False

    def test_equity_underweight(self):
        # equity_drift < -threshold → underweight
        drift = -(EQUITY_UNDERWEIGHT_THRESHOLD + 0.01)
        ok, _ = evaluate_equity_underweight(drift, EQUITY_UNDERWEIGHT_THRESHOLD)
        assert ok is True

    def test_equity_not_underweight(self):
        ok, _ = evaluate_equity_underweight(0.02, EQUITY_UNDERWEIGHT_THRESHOLD)
        assert ok is False

    def test_cash_excess(self):
        ok, _ = evaluate_cash_excess(0.25, 0.20)
        assert ok is True

    def test_cash_deficiency(self):
        ok, _ = evaluate_cash_deficiency(0.01, 0.02)
        assert ok is True

    def test_international_underweight(self):
        ok, _ = evaluate_international_underweight(0.05, 0.10)
        assert ok is True


class TestDiversificationRules:
    def test_concentration_very_high(self):
        ok, _ = evaluate_concentration(0.45, 0.40)
        assert ok is True

    def test_concentration_normal(self):
        ok, _ = evaluate_concentration(0.10, 0.40)
        assert ok is False

    def test_insufficient_positions(self):
        ok, _ = evaluate_insufficient_positions(3.5, 5.0)
        assert ok is True

    def test_sufficient_positions(self):
        ok, _ = evaluate_insufficient_positions(10.0, 5.0)
        assert ok is False

    def test_sector_concentration_high(self):
        ok, _ = evaluate_sector_concentration(0.45, 0.40)
        assert ok is True


class TestPerformanceRules:
    def test_sharpe_poor(self):
        ok, _ = evaluate_sharpe_deterioration(0.10, 0.30)
        assert ok is True

    def test_sharpe_acceptable(self):
        ok, _ = evaluate_sharpe_deterioration(0.80, 0.30)
        assert ok is False

    def test_information_ratio_poor(self):
        ok, _ = evaluate_information_ratio_poor(0.10, 0.20)
        assert ok is True

    def test_calmar_poor(self):
        ok, _ = evaluate_calmar_deterioration(0.20, 0.50)
        assert ok is True


class TestQualityRules:
    def test_construction_quality_low(self):
        ok, _ = evaluate_construction_quality(0.30, 0.40)
        assert ok is True

    def test_construction_quality_good(self):
        ok, _ = evaluate_construction_quality(0.80, 0.40)
        assert ok is False

    def test_optimization_quality_low(self):
        ok, _ = evaluate_optimization_quality(0.25, 0.40)
        assert ok is True


class TestRebalancingRules:
    def test_rebalance_triggered(self):
        ok, _ = evaluate_rebalance_trigger(True, 0.80, 0.60)
        assert ok is True

    def test_rebalance_not_triggered(self):
        ok, _ = evaluate_rebalance_trigger(False, "minor")
        assert ok is False


class TestCompositeRules:
    def test_defensive_signal(self):
        # both risk and drawdown elevated
        ok, _ = evaluate_defensive_signal(
            risk_budget_utilization=0.92,
            max_drawdown=0.18,
            risk_threshold=0.85,
            drawdown_threshold=0.15,
        )
        assert ok is True

    def test_no_defensive_when_healthy(self):
        ok, _ = evaluate_defensive_signal(
            risk_budget_utilization=0.40,
            max_drawdown=0.05,
            risk_threshold=0.85,
            drawdown_threshold=0.15,
        )
        assert ok is False

    def test_hedge_signal_high_var(self):
        ok, _ = evaluate_hedge_signal(
            var_utilization=0.95,
            max_drawdown=0.10,
            var_threshold=0.90,
            drawdown_threshold=0.20,
        )
        assert ok is True

    def test_aggressive_signal_healthy(self):
        ok, _ = evaluate_aggressive_signal(
            risk_budget_utilization=0.30,
            sharpe_ratio=1.20,
            low_risk_threshold=0.40,
            good_sharpe_threshold=0.80,
        )
        assert ok is True

    def test_aggressive_not_triggered_with_high_risk(self):
        ok, _ = evaluate_aggressive_signal(
            risk_budget_utilization=0.90,
            sharpe_ratio=1.20,
            low_risk_threshold=0.40,
            good_sharpe_threshold=0.80,
        )
        assert ok is False
