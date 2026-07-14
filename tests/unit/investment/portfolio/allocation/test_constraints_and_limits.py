"""test_constraints_and_limits.py — Exposure limits, policy, history, statistics."""
import pytest
from iios.investment.portfolio.allocation.exposure_limits import (
    ExposureCheck,
    ExposureLimitChecker,
    ExposureOutcome,
)
from iios.investment.portfolio.allocation.allocation_policy import (
    AGGRESSIVE_POLICY,
    BALANCED_POLICY,
    CONSERVATIVE_POLICY,
    AllocationPolicy,
    CashPolicy,
    ExposurePolicy,
    PositionSizingPolicy,
)
from iios.investment.portfolio.allocation.allocation_history import (
    AllocationHistory,
    AllocationRecord,
)
from iios.investment.portfolio.allocation.allocation_snapshot import (
    AllocationHolding,
    AllocationSnapshot,
)
from iios.investment.portfolio.allocation.allocation_statistics import (
    AllocationRunMetric,
    AllocationStatistics,
)


# ---------------------------------------------------------------------------
# ExposureLimitChecker
# ---------------------------------------------------------------------------

class TestExposureLimitChecker:
    def test_sector_within_limit(self):
        checker = ExposureLimitChecker()
        checks  = checker.check_sector({"energy": 0.25}, 0.40)
        assert all(c.passed for c in checks)

    def test_sector_over_limit(self):
        checker = ExposureLimitChecker()
        checks  = checker.check_sector({"it": 0.55}, 0.40)
        violations = [c for c in checks if c.is_violation]
        assert len(violations) == 1
        assert violations[0].key == "it"

    def test_sector_warning_just_over(self):
        checker = ExposureLimitChecker()
        # 40.5% when limit is 40% → excess = 0.5% ≤ 1% tolerance → WARNING
        checks  = checker.check_sector({"sector_a": 0.405}, 0.40)
        assert checks[0].outcome == ExposureOutcome.WARNING

    def test_asset_class_within_limit(self):
        checker = ExposureLimitChecker()
        checks  = checker.check_asset_class({"equity": 0.70}, 0.80)
        assert all(c.passed for c in checks)

    def test_check_all(self):
        checker = ExposureLimitChecker()
        checks  = checker.check_all(
            sector_weights       = {"energy": 0.30, "it": 0.45},
            asset_class_weights  = {"equity": 0.75},
            max_sector_pct       = 0.40,
            max_asset_class_pct  = 0.80,
        )
        it_check = next((c for c in checks if c.key == "it"), None)
        assert it_check is not None
        assert it_check.is_violation

    def test_skip_zero_weights(self):
        checker = ExposureLimitChecker()
        checks  = checker.check_sector({"energy": 0.0, "it": 0.20}, 0.40)
        # energy with 0 weight should be skipped
        assert all(c.key != "energy" for c in checks)

    def test_to_dict(self):
        c = ExposureCheck(dimension="sector", key="energy", outcome=ExposureOutcome.PASSED,
                          actual_pct=0.25, limit_pct=0.40)
        d = c.to_dict()
        assert d["dimension"] == "sector"
        assert d["outcome"]   == "passed"


# ---------------------------------------------------------------------------
# AllocationPolicy
# ---------------------------------------------------------------------------

class TestAllocationPolicy:
    def test_conservative_policy(self):
        p = CONSERVATIVE_POLICY
        assert p.policy_name == "conservative"
        assert p.cash.min_cash_reserve_pct > BALANCED_POLICY.cash.min_cash_reserve_pct

    def test_balanced_policy(self):
        p = BALANCED_POLICY
        assert p.policy_name == "balanced"
        assert 0.0 < p.sizing.max_position_weight < 1.0

    def test_aggressive_policy(self):
        p = AGGRESSIVE_POLICY
        assert p.policy_name == "aggressive"
        assert p.cash.min_cash_reserve_pct < BALANCED_POLICY.cash.min_cash_reserve_pct

    def test_to_dict(self):
        d = BALANCED_POLICY.to_dict()
        assert "method" in d
        assert "cash" in d
        assert "sizing" in d
        assert "exposure" in d


# ---------------------------------------------------------------------------
# AllocationHistory
# ---------------------------------------------------------------------------

def _snap(**kw):
    defaults = dict(
        portfolio_id     = "pf-1",
        plan_id          = "plan-1",
        blueprint_id     = "bp-1",
        plan_version     = 1,
        total_capital    = 1_000_000.0,
        invested_capital = 900_000.0,
        cash_capital     = 100_000.0,
        utilisation_rate = 0.90,
        is_valid         = True,
        is_ready         = True,
        quality_score    = 0.80,
    )
    defaults.update(kw)
    return AllocationSnapshot(**defaults)


class TestAllocationHistory:
    def test_record_and_latest(self):
        hist = AllocationHistory("pf-1")
        snap = _snap()
        rec  = hist.record(snap, status="completed", quality_score=0.80)
        assert isinstance(rec, AllocationRecord)
        latest = hist.latest()
        assert latest is not None
        assert latest.plan_id == "plan-1"

    def test_max_snapshots_enforced(self):
        hist = AllocationHistory("pf-1", max_snapshots=3)
        for i in range(5):
            hist.record(_snap(plan_version=i), quality_score=0.70)
        assert hist.count() == 3

    def test_recent(self):
        hist = AllocationHistory("pf-1")
        for i in range(5):
            hist.record(_snap(plan_version=i))
        recent = hist.recent(3)
        assert len(recent) == 3

    def test_reset(self):
        hist = AllocationHistory("pf-1")
        hist.record(_snap())
        hist.reset()
        assert hist.count() == 0
        assert hist.latest() is None

    def test_all_records(self):
        hist = AllocationHistory("pf-1")
        hist.record(_snap(plan_version=1))
        hist.record(_snap(plan_version=2))
        records = hist.all_records()
        assert len(records) == 2

    def test_to_dict(self):
        hist = AllocationHistory("pf-1")
        hist.record(_snap())
        d = hist.to_dict()
        assert d["portfolio_id"] == "pf-1"
        assert d["count"] == 1


# ---------------------------------------------------------------------------
# AllocationStatistics
# ---------------------------------------------------------------------------

def _metric(succeeded=True, duration_ms=100.0, portfolio_id="pf-1"):
    return AllocationRunMetric(
        portfolio_id     = portfolio_id,
        succeeded        = succeeded,
        positions_out    = 5,
        total_capital    = 1_000_000.0,
        utilisation_rate = 0.90,
        quality_score    = 0.80,
        duration_ms      = duration_ms,
    )


class TestAllocationStatistics:
    def test_record_and_snapshot(self):
        stats = AllocationStatistics()
        stats.record(_metric())
        snap  = stats.snapshot()
        assert snap.total_runs == 1
        assert snap.success_runs == 1
        assert snap.success_rate == pytest.approx(1.0)

    def test_success_rate_mixed(self):
        stats = AllocationStatistics()
        stats.record(_metric(succeeded=True))
        stats.record(_metric(succeeded=False))
        snap = stats.snapshot()
        assert snap.success_rate == pytest.approx(0.5)

    def test_max_runs_enforced(self):
        stats = AllocationStatistics(max_runs=3)
        for _ in range(5):
            stats.record(_metric())
        assert stats.count() == 3

    def test_portfolio_count(self):
        stats = AllocationStatistics()
        stats.record(_metric(portfolio_id="pf-A"))
        stats.record(_metric(portfolio_id="pf-B"))
        assert stats.portfolio_count() == 2

    def test_empty_snapshot(self):
        snap = AllocationStatistics().snapshot()
        assert snap.total_runs == 0
        assert snap.success_rate == 0.0
