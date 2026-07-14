"""test_optimization_types.py — Tests for enums, constants, and types."""
import pytest

from iios.investment.portfolio.optimization.optimization_types import (
    ConvergenceStatus,
    ObjectiveType,
    OptimizationMethod,
    OptimizationQualityGrade,
    OptimizationRunStatus,
    WeightChangeStatus,
    DEFAULT_MIN_WEIGHT,
    DEFAULT_MAX_WEIGHT,
    DEFAULT_RISK_AVERSION,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_QUALITY_GATE,
    WEIGHT_SUM_TOLERANCE,
    OPTIMIZATION_PLAN_SCHEMA_VERSION,
    OPTIMIZATION_RESULT_SCHEMA_VERSION,
)


class TestOptimizationMethod:
    def test_all_methods_are_str(self):
        for m in OptimizationMethod:
            assert isinstance(m.value, str)

    def test_expected_methods_exist(self):
        expected = [
            "mean_variance", "minimum_variance", "maximum_sharpe",
            "maximum_sortino", "maximum_calmar", "risk_parity",
            "equal_risk_contribution", "maximum_diversification",
            "black_litterman", "hierarchical_risk_parity",
            "equal_weight", "maximum_utility", "minimum_turnover",
        ]
        values = {m.value for m in OptimizationMethod}
        for e in expected:
            assert e in values, f"Missing method: {e}"

    def test_custom_method_exists(self):
        assert OptimizationMethod.CUSTOM.value == "custom"


class TestObjectiveType:
    def test_all_are_str(self):
        for o in ObjectiveType:
            assert isinstance(o.value, str)

    def test_key_objectives(self):
        types = {o.value for o in ObjectiveType}
        assert "maximize_sharpe" in types
        assert "minimize_risk" in types
        assert "maximize_return" in types


class TestConvergenceStatus:
    def test_values(self):
        assert ConvergenceStatus.CONVERGED.value == "converged"
        assert ConvergenceStatus.ANALYTICAL.value == "analytical"
        assert ConvergenceStatus.TRIVIAL.value == "trivial"
        # Actual value is 'max_iter' (abbreviated)
        values = {c.value for c in ConvergenceStatus}
        assert any("max" in v for v in values)


class TestWeightChangeStatus:
    def test_ordering(self):
        values = {w.value for w in WeightChangeStatus}
        for v in ("minimal", "small", "moderate", "large"):
            assert v in values


class TestOptimizationRunStatus:
    def test_statuses(self):
        assert OptimizationRunStatus.CONVERGED.value == "converged"
        assert OptimizationRunStatus.FAILED.value == "failed"


class TestQualityGrade:
    def test_grades(self):
        grades = {g.value.upper() for g in OptimizationQualityGrade}
        for g in ("A", "B", "C", "D", "F"):
            assert g in grades


class TestConstants:
    def test_weight_defaults(self):
        assert DEFAULT_MIN_WEIGHT == 0.0
        assert 0.0 < DEFAULT_MAX_WEIGHT <= 1.0

    def test_risk_aversion_positive(self):
        assert DEFAULT_RISK_AVERSION > 0

    def test_iterations_positive(self):
        assert DEFAULT_MAX_ITERATIONS > 0

    def test_quality_gate_in_range(self):
        assert 0.0 < DEFAULT_QUALITY_GATE < 1.0

    def test_weight_sum_tolerance_small(self):
        assert WEIGHT_SUM_TOLERANCE < 0.01

    def test_schema_versions_nonempty(self):
        assert OPTIMIZATION_PLAN_SCHEMA_VERSION
        assert OPTIMIZATION_RESULT_SCHEMA_VERSION
