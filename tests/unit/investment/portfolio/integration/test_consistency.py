"""tests/unit/investment/portfolio/integration/test_consistency.py

Tests for consistency_rules.py, consistency_validator.py, validation_report.py.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.integration.consistency_rules import (
    check_allocation_weights_sum,
    check_construction_allocation_position_count,
    check_diversification_hhi,
    check_optimization_vs_construction_quality,
    check_rebalancing_vs_allocation_drift,
    check_recommendation_vs_risk_budget,
    check_risk_performance_drawdown,
)
from iios.investment.portfolio.integration.consistency_validator import ConsistencyValidator
from iios.investment.portfolio.integration.integration_types import ValidationStatus


class TestConsistencyRules:
    def test_weights_sum_ok(self):
        data = {"equity_weight": 0.60, "bond_weight": 0.25,
                "cash_weight": 0.10, "alternative_weight": 0.05}
        triggered, _ = check_allocation_weights_sum(data, tolerance=0.02)
        assert triggered is False

    def test_weights_sum_fail(self):
        data = {"equity_weight": 0.70, "bond_weight": 0.25,
                "cash_weight": 0.10, "alternative_weight": 0.05}  # sum = 1.10
        triggered, _ = check_allocation_weights_sum(data, tolerance=0.02)
        assert triggered is True

    def test_position_count_consistent(self):
        triggered, _ = check_construction_allocation_position_count(20, 22, tolerance=5)
        assert triggered is False

    def test_position_count_inconsistent(self):
        triggered, _ = check_construction_allocation_position_count(20, 35, tolerance=5)
        assert triggered is True

    def test_position_count_none_allocation(self):
        triggered, _ = check_construction_allocation_position_count(20, None, tolerance=5)
        assert triggered is False  # skipped

    def test_optimization_quality_consistent(self):
        triggered, _ = check_optimization_vs_construction_quality(0.70, 0.80, max_gap=0.40)
        assert triggered is False

    def test_optimization_quality_inconsistent(self):
        triggered, _ = check_optimization_vs_construction_quality(0.20, 0.80, max_gap=0.40)
        assert triggered is True

    def test_drawdown_consistent(self):
        triggered, _ = check_risk_performance_drawdown(0.10, 0.11, tolerance=0.05)
        assert triggered is False

    def test_drawdown_inconsistent(self):
        triggered, _ = check_risk_performance_drawdown(0.10, 0.20, tolerance=0.05)
        assert triggered is True

    def test_rebalancing_drift_acknowledged(self):
        triggered, _ = check_rebalancing_vs_allocation_drift("minor", 0.10, 0.05)
        assert triggered is True   # 0.10 > 0.05 but drift level is "minor"

    def test_rebalancing_drift_not_triggered(self):
        triggered, _ = check_rebalancing_vs_allocation_drift("significant", 0.10, 0.05)
        assert triggered is False  # both significant

    def test_recommendation_risk_conflict(self):
        triggered, _ = check_recommendation_vs_risk_budget("aggressive_positioning", 0.95, 0.90)
        assert triggered is True

    def test_recommendation_risk_no_conflict(self):
        triggered, _ = check_recommendation_vs_risk_budget("no_action", 0.95, 0.90)
        assert triggered is False

    def test_hhi_high(self):
        triggered, _ = check_diversification_hhi(0.50, 0.40)
        assert triggered is True

    def test_hhi_ok(self):
        triggered, _ = check_diversification_hhi(0.10, 0.40)
        assert triggered is False


class TestConsistencyValidator:
    def test_healthy_portfolio_passes(self, healthy_contributions):
        validator = ConsistencyValidator()
        merged    = {}
        for eid, data in healthy_contributions.items():
            merged[eid.value] = data
        report = validator.validate(merged, "P-OK")
        assert report.is_consistent
        assert report.n_failed == 0

    def test_empty_merged_warns(self):
        validator = ConsistencyValidator()
        report    = validator.validate({}, "P-EMPTY")
        assert report.n_warnings >= 1

    def test_conflicting_weights_fails(self):
        merged = {
            "allocation": {
                "equity_weight": 0.70, "bond_weight": 0.25,
                "cash_weight": 0.10, "alternative_weight": 0.05,
                "equity_drift": 0.01,
            }
        }
        validator = ConsistencyValidator()
        report    = validator.validate(merged, "P-FAIL")
        # Weights sum to 1.10 → FAILED
        assert not report.is_consistent
        assert report.n_failed >= 1

    def test_report_has_checks(self, healthy_contributions):
        validator = ConsistencyValidator()
        merged    = {eid.value: d for eid, d in healthy_contributions.items()}
        report    = validator.validate(merged, "P-CH")
        assert len(report.checks) >= 3

    def test_consistency_score_range(self, healthy_contributions):
        validator = ConsistencyValidator()
        merged    = {eid.value: d for eid, d in healthy_contributions.items()}
        report    = validator.validate(merged, "P-SC")
        assert 0.0 <= report.consistency_score <= 1.0

    def test_to_dict(self, healthy_contributions):
        validator = ConsistencyValidator()
        merged    = {eid.value: d for eid, d in healthy_contributions.items()}
        report    = validator.validate(merged, "P-D")
        d         = report.to_dict()
        assert "is_consistent" in d
        assert "consistency_score" in d
