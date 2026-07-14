"""tests/unit/investment/portfolio/construction/test_quality.py

Tests for ConstructionQualityAssessor, ScoreCalculator, ScoreHistory,
ConstructionHealthMonitor, and ConstructionStatistics.
"""
from __future__ import annotations

import time
import pytest

from iios.investment.portfolio.construction.construction_engine import (
    BlueprintAssembler,
    WeightAssigner,
)
from iios.investment.portfolio.construction.construction_health import (
    ConstructionHealthMonitor,
    EngineHealthReport,
)
from iios.investment.portfolio.construction.construction_quality import (
    ConstructionQualityAssessor,
    ConstructionQualityReport,
)
from iios.investment.portfolio.construction.construction_score import (
    ConstructionScore,
    ScoreCalculator,
    ScoreHistory,
)
from iios.investment.portfolio.construction.construction_statistics import (
    ConstructionStatistics,
    ConstructionStatisticsSnapshot,
    RunMetric,
)
from iios.investment.portfolio.construction.construction_types import HealthStatus
from iios.investment.portfolio.construction.constraint_engine import ConstraintEngine
from iios.investment.portfolio.construction.constraint_registry import ConstraintRegistry
from iios.investment.portfolio.construction.portfolio_blueprint import ConstructionRequest
from iios.investment.portfolio.construction.portfolio_statistics import compute_statistics
from iios.investment.portfolio.construction.portfolio_validator import PortfolioValidator
from iios.investment.portfolio.construction.construction_validator import ConstructionValidator
from iios.investment.portfolio.construction.readiness_validator import ReadinessValidator
from tests.unit.investment.portfolio.construction.conftest import make_recs


def _full_pipeline(n: int = 8):
    """Run the full construction pipeline and return all reports."""
    recs = make_recs(n)
    req  = ConstructionRequest(portfolio_id="PF-Q", min_holdings=2, max_holdings=30)
    assigner  = WeightAssigner()
    weights   = assigner.assign(recs, req)
    assembler = BlueprintAssembler()
    bp = assembler.assemble(weights, recs, req)

    reg               = ConstraintRegistry()
    constraint_engine = ConstraintEngine(reg)
    constraint_report = constraint_engine.evaluate(bp)

    pv = PortfolioValidator()
    portfolio_report = pv.validate(bp)

    cv = ConstructionValidator()
    construction_report = cv.validate(bp, req)

    rv = ReadinessValidator()
    readiness = rv.validate(bp, constraint_report, portfolio_report, construction_report)

    stats = compute_statistics(bp)
    return bp, portfolio_report, construction_report, constraint_report, readiness, stats


class TestConstructionQualityAssessor:
    def test_produces_report(self):
        bp, pr, cvr, cr, rd, stats = _full_pipeline(8)
        assessor = ConstructionQualityAssessor()
        report = assessor.assess(bp, pr, cvr, cr, rd, stats=stats)
        assert isinstance(report, ConstructionQualityReport)

    def test_score_in_range(self):
        bp, pr, cvr, cr, rd, stats = _full_pipeline(8)
        assessor = ConstructionQualityAssessor()
        report = assessor.assess(bp, pr, cvr, cr, rd, stats=stats)
        assert 0.0 <= report.overall_score <= 1.0

    def test_seven_dimension_scores(self):
        bp, pr, cvr, cr, rd, stats = _full_pipeline(8)
        assessor = ConstructionQualityAssessor()
        report = assessor.assess(bp, pr, cvr, cr, rd, stats=stats)
        assert len(report.dimension_scores) == 7

    def test_healthy_with_good_blueprint(self):
        bp, pr, cvr, cr, rd, stats = _full_pipeline(10)
        assessor = ConstructionQualityAssessor(acceptable_threshold=0.0)
        report = assessor.assess(bp, pr, cvr, cr, rd, stats=stats)
        assert report.is_acceptable

    def test_report_to_dict(self):
        bp, pr, cvr, cr, rd, stats = _full_pipeline(5)
        assessor = ConstructionQualityAssessor()
        report = assessor.assess(bp, pr, cvr, cr, rd, stats=stats)
        d = report.to_dict()
        assert "overall_score" in d
        assert "health_status" in d
        assert "dimension_scores" in d
        assert "completeness_score" in d

    def test_constraint_compliance_perfect_empty_registry(self):
        bp, pr, cvr, cr, rd, stats = _full_pipeline(5)
        assessor = ConstructionQualityAssessor()
        report = assessor.assess(bp, pr, cvr, cr, rd, stats=stats)
        # Empty constraint registry → compliance = 1.0
        assert report.constraint_compliance_score == 1.0


class TestScoreCalculator:
    def _make_quality_report(self) -> ConstructionQualityReport:
        bp, pr, cvr, cr, rd, stats = _full_pipeline(8)
        assessor = ConstructionQualityAssessor(acceptable_threshold=0.0)
        return assessor.assess(bp, pr, cvr, cr, rd, stats=stats)

    def test_produces_score(self):
        report = self._make_quality_report()
        calc   = ScoreCalculator()
        score  = calc.calculate(report)
        assert isinstance(score, ConstructionScore)

    def test_grade_assigned(self):
        report = self._make_quality_report()
        calc   = ScoreCalculator()
        score  = calc.calculate(report)
        assert score.grade in ("A", "B", "C", "D", "F")

    def test_delta_none_on_first(self):
        report = self._make_quality_report()
        calc   = ScoreCalculator()
        score  = calc.calculate(report)
        assert score.delta_overall is None

    def test_delta_computed_on_second(self):
        report1 = self._make_quality_report()
        calc    = ScoreCalculator()
        score1  = calc.calculate(report1)
        score2  = calc.calculate(report1, previous_score=score1)
        assert score2.delta_overall == 0.0   # same report → delta = 0

    def test_gate_passed_above_threshold(self):
        report = self._make_quality_report()
        calc   = ScoreCalculator(governance_gate=0.0)
        score  = calc.calculate(report)
        assert score.gate_passed

    def test_gate_failed_above_threshold(self):
        report = self._make_quality_report()
        calc   = ScoreCalculator(governance_gate=1.0)
        score  = calc.calculate(report)
        assert not score.gate_passed

    def test_score_to_dict(self):
        report = self._make_quality_report()
        calc   = ScoreCalculator()
        score  = calc.calculate(report)
        d = score.to_dict()
        assert "overall" in d
        assert "grade" in d
        assert "gate_passed" in d


class TestScoreHistory:
    def _make_score(self, overall: float = 0.75) -> ConstructionScore:
        return ConstructionScore(
            blueprint_id = "BP",
            portfolio_id = "PF",
            overall      = overall,
            grade        = "B",
            health_status= HealthStatus.HEALTHY,
            is_acceptable= True,
            gate_passed  = True,
        )

    def test_empty(self):
        h = ScoreHistory("PF")
        assert h.count() == 0
        assert h.latest() is None
        assert h.best() is None

    def test_record_and_latest(self):
        h = ScoreHistory("PF")
        s = self._make_score(0.80)
        h.record(s)
        assert h.latest() is s

    def test_best(self):
        h = ScoreHistory("PF")
        h.record(self._make_score(0.60))
        h.record(self._make_score(0.90))
        h.record(self._make_score(0.70))
        assert h.best().overall == 0.90

    def test_recent(self):
        h = ScoreHistory("PF")
        for i in range(5):
            h.record(self._make_score(0.5 + i * 0.05))
        assert len(h.recent(3)) == 3

    def test_trend_positive(self):
        h = ScoreHistory("PF")
        prev = self._make_score(0.60)
        h.record(prev)
        scores = [0.65, 0.70, 0.75, 0.80, 0.85]
        for i, s in enumerate(scores):
            h.record(ConstructionScore(
                blueprint_id = "BP",
                portfolio_id = "PF",
                overall      = s,
                grade        = "B",
                health_status= HealthStatus.HEALTHY,
                is_acceptable= True,
                gate_passed  = True,
                delta_overall= round(s - scores[i - 1] if i > 0 else 0.05, 4),
            ))
        trend = h.trend()
        assert trend is not None and trend > 0


class TestConstructionHealthMonitor:
    def test_initial_health_unknown_runs(self):
        m = ConstructionHealthMonitor()
        report = m.check()
        assert isinstance(report, EngineHealthReport)
        # No runs yet
        assert report.total_runs == 0

    def test_healthy_after_good_runs(self):
        m = ConstructionHealthMonitor()
        for _ in range(10):
            m.record_run(success=True, duration_ms=100.0)
        report = m.check()
        assert report.overall_status == HealthStatus.HEALTHY

    def test_degraded_on_high_error_rate(self):
        m = ConstructionHealthMonitor()
        for _ in range(8):
            m.record_run(success=True, duration_ms=100.0)
        for _ in range(2):
            m.record_run(success=False, duration_ms=200.0)
        report = m.check()
        # 20% error rate → UNHEALTHY
        assert report.error_rate >= 0.19

    def test_is_healthy_property(self):
        m = ConstructionHealthMonitor()
        m.record_run(success=True, duration_ms=50.0)
        report = m.check()
        assert report.is_healthy == (report.overall_status == HealthStatus.HEALTHY)

    def test_report_to_dict(self):
        m = ConstructionHealthMonitor()
        m.record_run(success=True, duration_ms=100.0)
        d = m.check().to_dict()
        assert "overall_status" in d
        assert "error_rate" in d
        assert "checks" in d


class TestConstructionStatistics:
    def _metric(self, success: bool = True, slots: int = 10, quality: float = 0.75) -> RunMetric:
        return RunMetric(
            portfolio_id  = "PF",
            succeeded     = success,
            slots_built   = slots,
            duration_ms   = 100.0,
            quality_score = quality,
        )

    def test_empty_snapshot(self):
        stats = ConstructionStatistics()
        snap = stats.snapshot()
        assert snap.total_runs == 0

    def test_record_success(self):
        stats = ConstructionStatistics()
        stats.record(self._metric(True))
        snap = stats.snapshot()
        assert snap.total_runs == 1
        assert snap.success_runs == 1
        assert snap.success_rate == 1.0

    def test_record_failure(self):
        stats = ConstructionStatistics()
        stats.record(self._metric(True))
        stats.record(self._metric(False))
        snap = stats.snapshot()
        assert snap.failed_runs == 1
        assert snap.success_rate == 0.5

    def test_avg_quality_score(self):
        stats = ConstructionStatistics()
        stats.record(self._metric(True, quality=0.8))
        stats.record(self._metric(True, quality=0.6))
        snap = stats.snapshot()
        assert abs(snap.avg_quality_score - 0.7) < 0.01

    def test_portfolio_count(self):
        stats = ConstructionStatistics()
        stats.record(RunMetric(portfolio_id="PF-A", succeeded=True, slots_built=5))
        stats.record(RunMetric(portfolio_id="PF-B", succeeded=True, slots_built=5))
        snap = stats.snapshot()
        assert snap.portfolios_served == 2

    def test_for_portfolio_filter(self):
        stats = ConstructionStatistics()
        stats.record(RunMetric(portfolio_id="PF-A", succeeded=True, slots_built=5))
        stats.record(RunMetric(portfolio_id="PF-B", succeeded=True, slots_built=5))
        pf_a = stats.for_portfolio("PF-A")
        assert pf_a.count() == 1

    def test_recent_n(self):
        stats = ConstructionStatistics()
        for _ in range(10):
            stats.record(self._metric())
        assert len(stats.recent(5)) == 5

    def test_snapshot_to_dict(self):
        stats = ConstructionStatistics()
        stats.record(self._metric())
        d = stats.snapshot().to_dict()
        assert "total_runs" in d
        assert "success_rate" in d
        assert "p95_duration_ms" in d
