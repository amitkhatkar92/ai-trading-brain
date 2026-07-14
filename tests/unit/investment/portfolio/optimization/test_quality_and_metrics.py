"""test_quality_and_metrics.py — Tests for Quality, Score, Metrics, Health, Statistics."""
import time
import pytest

from iios.investment.portfolio.optimization.optimization_quality import (
    OptimizationQualityAssessor,
)
from iios.investment.portfolio.optimization.optimization_score import (
    OptimizationScoreCalculator,
    OptimizationScoreHistory,
)
from iios.investment.portfolio.optimization.optimization_metrics import (
    compute_optimization_metrics,
)
from iios.investment.portfolio.optimization.optimization_health import (
    HealthStatus,
    OptimizationHealthMonitor,
)
from iios.investment.portfolio.optimization.optimization_statistics import (
    OptimizationRunMetric,
    OptimizationStatistics,
)
from iios.investment.portfolio.optimization.optimization_plan import (
    OptimizationPlan,
    OptimizedPosition,
)
from iios.investment.portfolio.optimization.optimization_types import (
    ConvergenceStatus,
    OptimizationQualityGrade,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _good_plan(n=5):
    w = 1.0 / n
    positions = tuple(
        OptimizedPosition(
            symbol           = f"S{i}",
            optimized_weight = w,
            optimized_capital= w * 1_000_000,
            prior_weight     = w,
            sector           = "tech" if i < 2 else "finance",
            asset_class      = "equity",
            expected_return_proxy= 0.65,
            risk_proxy       = 0.25,
        )
        for i in range(n)
    )
    return OptimizationPlan(
        portfolio_id          = "p1",
        positions             = positions,
        total_capital         = 1_000_000.0,
        optimized_invested    = 1_000_000.0,
        converged             = True,
        convergence           = ConvergenceStatus.CONVERGED,
        objective_improvement = 0.10,
        diversification_ratio = 1.20,
        sharpe_proxy          = 2.5,
        expected_return       = 0.65,
        portfolio_risk        = 0.26,
    )


def _make_validation_report(is_valid=True, failures=0):
    from iios.investment.portfolio.optimization.optimization_validator import (
        OptimizationValidationReport,
    )
    return OptimizationValidationReport(
        plan_id      = "p1",
        portfolio_id = "p1",
        findings     = (),
        total        = 5,
        passed       = 5 - failures,
        warnings     = 0,
        failures     = failures,
        is_valid     = is_valid,
    )


def _make_constraint_report(is_feasible=True, violations=0):
    from iios.investment.portfolio.optimization.constraint_validator import (
        ConstraintValidationReport,
    )
    return ConstraintValidationReport(
        plan_id      = "p1",
        portfolio_id = "p1",
        checks       = (),
        total        = 3,
        satisfied    = 3 - violations,
        warnings     = 0,
        violations   = violations,
        is_feasible  = is_feasible,
    )


# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------

class TestOptimizationQualityAssessor:
    def test_good_plan_has_acceptable_score(self):
        assessor = OptimizationQualityAssessor(acceptable_threshold=0.50)
        plan     = _good_plan()
        val_rpt  = _make_validation_report(is_valid=True)
        cst_rpt  = _make_constraint_report(is_feasible=True)
        report   = assessor.assess(plan, val_rpt, cst_rpt)
        assert report.is_acceptable

    def test_failed_plan_is_not_acceptable(self):
        assessor = OptimizationQualityAssessor(acceptable_threshold=0.55)
        plan     = OptimizationPlan(portfolio_id="p", positions=())
        val_rpt  = _make_validation_report(is_valid=False, failures=3)
        cst_rpt  = _make_constraint_report(is_feasible=False, violations=2)
        report   = assessor.assess(plan, val_rpt, cst_rpt)
        assert not report.is_acceptable

    def test_report_has_dimension_scores(self):
        assessor = OptimizationQualityAssessor()
        plan     = _good_plan()
        report   = assessor.assess(plan, _make_validation_report(), _make_constraint_report())
        assert len(report.dimension_scores) > 0

    def test_overall_score_in_range(self):
        assessor = OptimizationQualityAssessor()
        plan     = _good_plan()
        report   = assessor.assess(plan, _make_validation_report(), _make_constraint_report())
        assert 0.0 <= report.overall_score <= 1.0

    def test_grade_is_enum(self):
        assessor = OptimizationQualityAssessor()
        plan     = _good_plan()
        report   = assessor.assess(plan, _make_validation_report(), _make_constraint_report())
        assert report.grade in OptimizationQualityGrade


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------

class TestOptimizationScoreCalculator:
    def test_score_in_range(self):
        calc    = OptimizationScoreCalculator()
        q_rpt   = OptimizationQualityAssessor().assess(
            _good_plan(), _make_validation_report(), _make_constraint_report()
        )
        score   = calc.calculate(q_rpt)
        assert 0.0 <= score.overall <= 1.0

    def test_gate_passed_for_good_plan(self):
        calc  = OptimizationScoreCalculator(governance_gate=0.40)
        q_rpt = OptimizationQualityAssessor(acceptable_threshold=0.40).assess(
            _good_plan(), _make_validation_report(), _make_constraint_report()
        )
        score = calc.calculate(q_rpt)
        assert score.gate_passed

    def test_delta_computed_with_previous(self):
        calc  = OptimizationScoreCalculator()
        q_rpt = OptimizationQualityAssessor().assess(
            _good_plan(), _make_validation_report(), _make_constraint_report()
        )
        s1 = calc.calculate(q_rpt)
        s2 = calc.calculate(q_rpt, previous_score=s1)
        assert s2.delta_overall is not None


class TestOptimizationScoreHistory:
    def test_records_and_retrieves(self):
        calc  = OptimizationScoreCalculator()
        q_rpt = OptimizationQualityAssessor().assess(
            _good_plan(), _make_validation_report(), _make_constraint_report()
        )
        score = calc.calculate(q_rpt)
        hist  = OptimizationScoreHistory("p1", max_size=10)
        hist.record(score)
        assert hist.latest() == score
        assert hist.count() == 1

    def test_max_size_bounded(self):
        calc  = OptimizationScoreCalculator()
        q_rpt = OptimizationQualityAssessor().assess(
            _good_plan(), _make_validation_report(), _make_constraint_report()
        )
        hist = OptimizationScoreHistory("p1", max_size=3)
        for _ in range(5):
            hist.record(calc.calculate(q_rpt))
        assert hist.count() == 3

    def test_best_has_highest_score(self):
        calc  = OptimizationScoreCalculator()
        hist  = OptimizationScoreHistory("p1")
        q_good = OptimizationQualityAssessor(acceptable_threshold=0.40).assess(
            _good_plan(), _make_validation_report(), _make_constraint_report()
        )
        q_bad  = OptimizationQualityAssessor(acceptable_threshold=0.90).assess(
            OptimizationPlan(portfolio_id="p"),
            _make_validation_report(is_valid=False, failures=3),
            _make_constraint_report(is_feasible=False, violations=2),
        )
        s_good = calc.calculate(q_good)
        s_bad  = calc.calculate(q_bad)
        hist.record(s_bad)
        hist.record(s_good)
        assert hist.best().overall >= s_bad.overall


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class TestComputeOptimizationMetrics:
    def test_metrics_positions_count(self):
        plan = _good_plan(5)
        m    = compute_optimization_metrics(plan)
        assert m.total_positions == 5

    def test_utilisation_rate(self):
        plan = _good_plan(5)
        m    = compute_optimization_metrics(plan)
        assert 0.0 <= m.utilisation_rate <= 1.0

    def test_hhi_in_range(self):
        plan = _good_plan(5)
        m    = compute_optimization_metrics(plan)
        assert 0.0 < m.hhi <= 1.0

    def test_effective_n_positive(self):
        plan = _good_plan(5)
        m    = compute_optimization_metrics(plan)
        assert m.effective_n > 0


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestOptimizationHealthMonitor:
    def test_healthy_with_no_errors(self):
        mon = OptimizationHealthMonitor(window=10)
        for _ in range(5):
            mon.record_run(succeeded=True, duration_ms=100.0)
        rpt = mon.check(active_portfolios=2)
        assert rpt.overall_status == HealthStatus.HEALTHY
        assert rpt.is_healthy

    def test_degraded_with_high_error_rate(self):
        mon = OptimizationHealthMonitor(window=20)
        for _ in range(6):
            mon.record_run(succeeded=False, duration_ms=50.0)
        for _ in range(4):
            mon.record_run(succeeded=True, duration_ms=50.0)
        rpt = mon.check()
        assert rpt.overall_status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)

    def test_error_rate_computed_correctly(self):
        mon = OptimizationHealthMonitor(window=10)
        mon.record_run(succeeded=False, duration_ms=100.0)
        mon.record_run(succeeded=True,  duration_ms=100.0)
        rpt = mon.check()
        assert abs(rpt.error_rate - 0.5) < 0.01

    def test_active_portfolios_in_report(self):
        mon = OptimizationHealthMonitor()
        rpt = mon.check(active_portfolios=7)
        assert rpt.active_portfolios == 7


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestOptimizationStatistics:
    def _metric(self, succeeded=True, pid="p1", quality=0.75):
        return OptimizationRunMetric(
            portfolio_id          = pid,
            succeeded             = succeeded,
            positions_optimized   = 5,
            total_capital         = 1_000_000.0,
            utilisation_rate      = 0.95,
            objective_improvement = 0.05,
            quality_score         = quality,
            duration_ms           = 200.0,
        )

    def test_records_accumulate(self):
        stats = OptimizationStatistics()
        for _ in range(3):
            stats.record(self._metric())
        assert stats.count() == 3

    def test_portfolio_count(self):
        stats = OptimizationStatistics()
        stats.record(self._metric(pid="p1"))
        stats.record(self._metric(pid="p2"))
        assert stats.portfolio_count() == 2

    def test_success_rate_in_snapshot(self):
        stats = OptimizationStatistics()
        stats.record(self._metric(succeeded=True))
        stats.record(self._metric(succeeded=False))
        snap = stats.snapshot()
        assert abs(snap.success_rate - 0.5) < 0.01

    def test_max_size_bounded(self):
        stats = OptimizationStatistics(max_runs=5)
        for _ in range(10):
            stats.record(self._metric())
        assert stats.count() == 5

    def test_for_portfolio_filter(self):
        stats = OptimizationStatistics()
        for _ in range(3):
            stats.record(self._metric(pid="A"))
        stats.record(self._metric(pid="B"))
        subset = stats.for_portfolio("A")
        assert subset.count() == 3
