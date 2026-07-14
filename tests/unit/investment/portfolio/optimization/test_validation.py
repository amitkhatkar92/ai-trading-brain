"""test_validation.py — Tests for OptimizationValidator and OptimizationReadinessValidator."""
import pytest

from iios.investment.portfolio.optimization.optimization_plan import (
    OptimizationPlan,
    OptimizedPosition,
)
from iios.investment.portfolio.optimization.optimization_types import (
    ConvergenceStatus,
)
from iios.investment.portfolio.optimization.optimization_validator import (
    OptimizationValidator,
)
from iios.investment.portfolio.optimization.optimization_readiness import (
    OptimizationReadinessValidator,
)
from iios.investment.portfolio.optimization.optimization_constraints import (
    default_constraint_set,
)
from iios.investment.portfolio.optimization.constraint_validator import (
    ConstraintValidator,
)


def _valid_plan(n=5, converged=True):
    w = 1.0 / n
    positions = tuple(
        OptimizedPosition(
            symbol           = f"S{i}",
            optimized_weight = w,
            optimized_capital= w * 1_000_000,
            sector           = "tech",
            asset_class      = "equity",
        )
        for i in range(n)
    )
    return OptimizationPlan(
        portfolio_id          = "p1",
        positions             = positions,
        total_capital         = 1_000_000.0,
        optimized_invested    = 1_000_000.0,
        converged             = converged,
        convergence           = ConvergenceStatus.CONVERGED if converged else ConvergenceStatus.MAX_ITERATIONS,
        objective_improvement = 0.05,
    )


@pytest.fixture
def opt_validator():
    return OptimizationValidator()


@pytest.fixture
def readiness_validator():
    return OptimizationReadinessValidator()


class TestOptimizationValidator:
    def test_valid_plan_passes(self, opt_validator):
        plan   = _valid_plan()
        report = opt_validator.validate(plan)
        assert report.is_valid

    def test_report_has_findings(self, opt_validator):
        plan   = _valid_plan()
        report = opt_validator.validate(plan)
        assert report.total > 0

    def test_empty_plan_warns(self, opt_validator):
        # Empty positions is treated as a WARNING by the validator (not a blocking failure)
        plan   = OptimizationPlan(portfolio_id="p", positions=())
        report = opt_validator.validate(plan)
        assert report.warnings > 0   # at least one warning about no positions

    def test_weight_sum_violation_fails(self, opt_validator):
        positions = tuple(
            OptimizedPosition(symbol=f"S{i}", optimized_weight=0.30)
            for i in range(5)   # sum = 1.50 — INVALID
        )
        plan   = OptimizationPlan(portfolio_id="p", positions=positions)
        report = opt_validator.validate(plan)
        assert not report.is_valid

    def test_pass_rate_in_range(self, opt_validator):
        plan   = _valid_plan()
        report = opt_validator.validate(plan)
        assert 0.0 <= report.pass_rate <= 1.0

    def test_failed_findings_populated_on_failure(self, opt_validator):
        # A weight-sum violation is a real failure
        positions = tuple(
            OptimizedPosition(symbol=f"S{i}", optimized_weight=0.30)
            for i in range(5)   # sum = 1.50 — INVALID
        )
        plan   = OptimizationPlan(portfolio_id="p", positions=positions)
        report = opt_validator.validate(plan)
        assert len(report.failed_findings) > 0


class TestOptimizationReadinessValidator:
    def _make_validation_report(self, is_valid=True):
        from iios.investment.portfolio.optimization.optimization_validator import (
            OptimizationValidationReport,
        )
        return OptimizationValidationReport(
            plan_id    = "p1",
            portfolio_id="p1",
            findings   = (),
            total      = 5,
            passed     = 5 if is_valid else 3,
            warnings   = 0,
            failures   = 0 if is_valid else 2,
            is_valid   = is_valid,
        )

    def test_valid_plan_is_ready(self, readiness_validator):
        plan     = _valid_plan()
        val_rpt  = self._make_validation_report(is_valid=True)
        assess   = readiness_validator.validate(plan, val_rpt)
        assert assess.is_ready

    def test_failed_validation_blocks_readiness(self, readiness_validator):
        plan     = _valid_plan()
        val_rpt  = self._make_validation_report(is_valid=False)

        # Inject failures into report
        from iios.investment.portfolio.optimization.optimization_validator import (
            OptimizationValidationReport,
            ValidationFinding,
        )
        from iios.investment.portfolio.optimization.optimization_types import ConstraintOutcome
        f = ValidationFinding(
            category = "test",
            outcome  = ConstraintOutcome.VIOLATED,
            rule     = "test_rule",
            message  = "Test failure",
        )
        bad_report = OptimizationValidationReport(
            plan_id      = "p1",
            portfolio_id = "p1",
            findings     = (f,),
            total        = 1,
            passed       = 0,
            warnings     = 0,
            failures     = 1,
            is_valid     = False,
        )
        assess = readiness_validator.validate(plan, bad_report)
        assert not assess.is_ready
        assert len(assess.blocking_reasons) > 0

    def test_with_constraint_report(self, readiness_validator):
        plan    = _valid_plan()
        val_rpt = self._make_validation_report(is_valid=True)
        cs      = default_constraint_set()
        c_valid = ConstraintValidator()
        c_rpt   = c_valid.validate(plan, cs)
        assess  = readiness_validator.validate(plan, val_rpt, c_rpt)
        assert isinstance(assess.is_ready, bool)
