"""test_quality.py — Quality, scoring, metrics, health."""
import pytest
from iios.investment.portfolio.allocation.allocation_plan import (
    AllocationPlan,
    CashAllocation,
    PositionAllocation,
)
from iios.investment.portfolio.allocation.allocation_types import (
    AllocationDirection,
    AllocationQualityGrade,
)
from iios.investment.portfolio.allocation.allocation_quality import (
    AllocationQualityAssessor,
    AllocationQualityReport,
    _grade,
    _utilisation_score,
)
from iios.investment.portfolio.allocation.allocation_score import (
    AllocationScore,
    AllocationScoreCalculator,
    AllocationScoreHistory,
)
from iios.investment.portfolio.allocation.allocation_metrics import (
    AllocationMetrics,
    compute_allocation_metrics,
)
from iios.investment.portfolio.allocation.allocation_health import (
    AllocationHealthMonitor,
    HealthStatus,
)
from iios.investment.portfolio.allocation.allocation_validator import AllocationValidator
from iios.investment.portfolio.allocation.exposure_limits import ExposureCheck, ExposureOutcome


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _long(symbol, capital, sector="equity", conviction=0.7, confidence=0.8, risk=0.3):
    return PositionAllocation(
        symbol           = symbol,
        direction        = AllocationDirection.LONG,
        allocated_capital= capital,
        allocated_weight = capital / 1_000_000.0,
        sector           = sector,
        asset_class      = "equity",
        conviction       = conviction,
        confidence       = confidence,
        risk_score       = risk,
    )


def _plan(allocations, total=1_000_000.0):
    invested = sum(abs(a.allocated_capital) for a in allocations)
    cash     = max(0.0, total - invested)
    return AllocationPlan(
        portfolio_id     = "pf-test",
        plan_id          = "plan-test",
        total_capital    = total,
        invested_capital = invested,
        cash_capital     = cash,
        utilisation_rate = invested / total if total > 0 else 0.0,
        allocations      = tuple(allocations),
        cash             = CashAllocation(cash_capital=cash, cash_weight=cash / total),
    )


# ---------------------------------------------------------------------------
# Grade helper
# ---------------------------------------------------------------------------

class TestGrade:
    def test_a_grade(self):
        assert _grade(0.95) == AllocationQualityGrade.A

    def test_b_grade(self):
        assert _grade(0.80) == AllocationQualityGrade.B

    def test_c_grade(self):
        assert _grade(0.65) == AllocationQualityGrade.C

    def test_f_grade(self):
        assert _grade(0.30) == AllocationQualityGrade.F


class TestUtilisationScore:
    def test_full_utilisation(self):
        assert _utilisation_score(0.90) == pytest.approx(1.0)

    def test_zero_utilisation(self):
        assert _utilisation_score(0.0) == pytest.approx(0.0)

    def test_over_leveraged(self):
        assert _utilisation_score(1.10) < 1.0


# ---------------------------------------------------------------------------
# AllocationQualityAssessor
# ---------------------------------------------------------------------------

class TestAllocationQualityAssessor:
    def test_good_plan_gets_acceptable_score(self):
        plan = _plan([_long("A", 400_000.0), _long("B", 450_000.0)])
        rpt  = AllocationValidator().validate(plan)
        qa   = AllocationQualityAssessor(acceptable_threshold=0.60)
        qr   = qa.assess(plan, rpt, [])
        assert 0.0 <= qr.overall_score <= 1.0
        assert isinstance(qr.grade, AllocationQualityGrade)

    def test_empty_plan_low_score(self):
        plan = _plan([])
        rpt  = AllocationValidator().validate(plan)
        qa   = AllocationQualityAssessor()
        qr   = qa.assess(plan, rpt, [])
        # Utilisation is 0 → low score
        assert qr.overall_score < 0.60

    def test_exposure_violation_reduces_score(self):
        plan = _plan([_long("A", 900_000.0)])
        rpt  = AllocationValidator().validate(plan)
        bad  = [ExposureCheck(dimension="sector", key="it",
                              outcome=ExposureOutcome.VIOLATED,
                              actual_pct=0.90, limit_pct=0.40)]
        qa   = AllocationQualityAssessor()
        qr   = qa.assess(plan, rpt, bad)
        # exposure_compliance should pull score down
        assert qr.exposure_compliance_score < 1.0

    def test_to_dict(self):
        plan = _plan([_long("A", 900_000.0)])
        rpt  = AllocationValidator().validate(plan)
        qr   = AllocationQualityAssessor().assess(plan, rpt)
        d    = qr.to_dict()
        assert "overall_score" in d
        assert "grade" in d
        assert "dimension_scores" in d


# ---------------------------------------------------------------------------
# AllocationScoreCalculator & ScoreHistory
# ---------------------------------------------------------------------------

class TestAllocationScoreCalculator:
    def test_score_from_quality_report(self):
        plan = _plan([_long("A", 900_000.0)])
        rpt  = AllocationValidator().validate(plan)
        qr   = AllocationQualityAssessor().assess(plan, rpt)
        sc   = AllocationScoreCalculator(governance_gate=0.55)
        s    = sc.calculate(qr, None)
        assert isinstance(s, AllocationScore)
        assert 0.0 <= s.overall <= 1.0

    def test_delta_computed_with_previous(self):
        plan = _plan([_long("A", 900_000.0)])
        rpt  = AllocationValidator().validate(plan)
        qr   = AllocationQualityAssessor().assess(plan, rpt)
        sc   = AllocationScoreCalculator()
        prev = sc.calculate(qr, None)
        next_s = sc.calculate(qr, prev)
        assert next_s.delta_overall is not None
        assert next_s.delta_overall == pytest.approx(0.0, abs=0.001)

    def test_gate_passed(self):
        plan = _plan([_long("A", 900_000.0)])
        rpt  = AllocationValidator().validate(plan)
        qr   = AllocationQualityAssessor().assess(plan, rpt)
        sc   = AllocationScoreCalculator(governance_gate=0.01)  # Very low gate
        s    = sc.calculate(qr, None)
        assert s.gate_passed


class TestAllocationScoreHistory:
    def _score(self, overall=0.80):
        return AllocationScore(portfolio_id="pf-1", plan_id="plan-1", overall=overall,
                               grade=AllocationQualityGrade.B, is_acceptable=True)

    def test_record_and_latest(self):
        h = AllocationScoreHistory("pf-1")
        s = self._score()
        h.record(s)
        assert h.latest() == s

    def test_best(self):
        h = AllocationScoreHistory("pf-1")
        h.record(self._score(0.70))
        h.record(self._score(0.90))
        h.record(self._score(0.60))
        best = h.best()
        assert best.overall == pytest.approx(0.90)

    def test_trend(self):
        h = AllocationScoreHistory("pf-1")
        h.record(self._score(0.60))
        h.record(self._score(0.80))
        assert h.trend() == pytest.approx(0.20, abs=0.001)

    def test_trend_none_with_one_entry(self):
        h = AllocationScoreHistory("pf-1")
        h.record(self._score(0.70))
        assert h.trend() is None

    def test_max_size_enforced(self):
        h = AllocationScoreHistory("pf-1", max_size=3)
        for _ in range(5):
            h.record(self._score())
        assert h.count() == 3


# ---------------------------------------------------------------------------
# AllocationMetrics
# ---------------------------------------------------------------------------

class TestAllocationMetrics:
    def test_basic_metrics(self):
        plan = _plan([
            _long("A", 300_000.0, sector="energy"),
            _long("B", 250_000.0, sector="it"),
            _long("C", 350_000.0, sector="financials"),
        ])
        m = compute_allocation_metrics(plan)
        assert m.long_count == 3
        assert m.short_count == 0
        assert m.total_count == 3
        assert m.sector_count == 3
        assert m.hhi > 0

    def test_hhi_single_position(self):
        plan = _plan([_long("A", 950_000.0)])
        m    = compute_allocation_metrics(plan)
        # One position at 95% weight → HHI ≈ 0.95^2 = 0.9025
        assert m.hhi > 0.80

    def test_effective_n(self):
        plan = _plan([_long("A", 500_000.0), _long("B", 450_000.0)])
        m    = compute_allocation_metrics(plan)
        assert m.effective_n > 1.0

    def test_to_dict(self):
        plan = _plan([_long("A", 900_000.0)])
        m    = compute_allocation_metrics(plan)
        d    = m.to_dict()
        assert "hhi" in d
        assert "effective_n" in d


# ---------------------------------------------------------------------------
# AllocationHealthMonitor
# ---------------------------------------------------------------------------

class TestAllocationHealthMonitor:
    def test_healthy_on_all_success(self):
        hm = AllocationHealthMonitor()
        for _ in range(10):
            hm.record_run(succeeded=True, duration_ms=200.0)
        r = hm.check(active_portfolios=2)
        assert r.overall_status == HealthStatus.HEALTHY
        assert r.is_healthy

    def test_degraded_on_high_error_rate(self):
        hm = AllocationHealthMonitor()
        for i in range(10):
            hm.record_run(succeeded=(i % 3 != 0), duration_ms=200.0)  # ~33% error
        r = hm.check(active_portfolios=1)
        assert r.overall_status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)

    def test_uptime_increases(self):
        hm = AllocationHealthMonitor()
        r  = hm.check(active_portfolios=0)
        assert r.uptime_seconds >= 0.0

    def test_to_dict(self):
        hm = AllocationHealthMonitor()
        hm.record_run(succeeded=True, duration_ms=100.0)
        d = hm.check().to_dict()
        assert "overall_status" in d
        assert "checks" in d
