"""test_validation.py — AllocationValidator, readiness."""
import pytest
from iios.investment.portfolio.allocation.allocation_plan import (
    AllocationPlan,
    CashAllocation,
    PositionAllocation,
)
from iios.investment.portfolio.allocation.allocation_types import AllocationDirection
from iios.investment.portfolio.allocation.allocation_validator import (
    AllocationValidator,
    FindingOutcome,
    build_allocation_report,
)
from iios.investment.portfolio.allocation.allocation_readiness import (
    AllocationReadinessValidator,
)
from iios.investment.portfolio.allocation.exposure_limits import ExposureCheck, ExposureOutcome


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _long(symbol, capital):
    return PositionAllocation(
        symbol           = symbol,
        direction        = AllocationDirection.LONG,
        allocated_capital= capital,
    )


def _plan(allocations, total=1_000_000.0, cash=None):
    invested = sum(abs(a.allocated_capital) for a in allocations)
    _cash    = cash if cash is not None else (total - invested)
    return AllocationPlan(
        portfolio_id     = "pf-test",
        total_capital    = total,
        invested_capital = invested,
        cash_capital     = _cash,
        utilisation_rate = invested / total if total > 0 else 0.0,
        allocations      = tuple(allocations),
        cash             = CashAllocation(cash_capital=_cash, cash_weight=_cash/total),
    )


# ---------------------------------------------------------------------------
# AllocationValidator
# ---------------------------------------------------------------------------

class TestAllocationValidator:
    def test_valid_plan_passes(self):
        plan = _plan([_long("A", 300_000.0), _long("B", 200_000.0)])
        v    = AllocationValidator()
        r    = v.validate(plan)
        assert r.is_valid
        assert r.failures == 0

    def test_capital_not_conserved(self):
        # Invest 900k but set cash to 200k → total = 1.1M ≠ 1M
        plan = _plan([_long("A", 900_000.0)], total=1_000_000.0, cash=200_000.0)
        r    = AllocationValidator().validate(plan)
        assert not r.is_valid

    def test_negative_long_fails(self):
        neg = PositionAllocation(
            symbol           = "BAD.NS",
            direction        = AllocationDirection.LONG,
            allocated_capital= -50_000.0,
        )
        plan = _plan([neg, _long("B", 900_000.0)], total=1_000_000.0, cash=150_000.0)
        r    = AllocationValidator().validate(plan)
        assert not r.is_valid

    def test_zero_positions_warning(self):
        plan = _plan([], total=1_000_000.0, cash=1_000_000.0)
        r    = AllocationValidator().validate(plan)
        # 0 positions → warning not failure
        assert r.warnings > 0

    def test_over_utilised_fails(self):
        # Invest 1.05M in a 1M plan → utilisation 105%
        plan = _plan([_long("A", 1_050_000.0)], total=1_000_000.0, cash=-50_000.0)
        r    = AllocationValidator().validate(plan)
        assert not r.is_valid

    def test_pass_rate_all_pass(self):
        plan = _plan([_long("A", 500_000.0)])
        r    = AllocationValidator().validate(plan)
        assert r.pass_rate > 0.5   # most checks pass

    def test_to_dict(self):
        plan = _plan([_long("A", 500_000.0)])
        r    = AllocationValidator().validate(plan)
        d    = r.to_dict()
        assert "is_valid" in d
        assert "findings" in d


# ---------------------------------------------------------------------------
# AllocationReadinessValidator
# ---------------------------------------------------------------------------

class TestAllocationReadinessValidator:
    def test_ready_valid_plan(self):
        plan = _plan([_long("A", 900_000.0)])
        v    = AllocationValidator()
        rpt  = v.validate(plan)
        rv   = AllocationReadinessValidator()
        ra   = rv.validate(plan, rpt, [])
        assert ra.is_ready

    def test_not_ready_when_validation_fails(self):
        plan = _plan([_long("A", 900_000.0)], total=1_000_000.0, cash=200_000.0)
        v    = AllocationValidator()
        rpt  = v.validate(plan)
        rv   = AllocationReadinessValidator()
        ra   = rv.validate(plan, rpt, [])
        # capital not conserved → blocking reason → not ready
        assert not ra.is_ready
        assert len(ra.blocking_reasons) > 0

    def test_not_ready_with_exposure_violation(self):
        plan = _plan([_long("A", 900_000.0)])
        v    = AllocationValidator()
        rpt  = v.validate(plan)
        bad_check = ExposureCheck(
            dimension  = "sector",
            key        = "it",
            outcome    = ExposureOutcome.VIOLATED,
            actual_pct = 0.60,
            limit_pct  = 0.40,
            message    = "sector:it 60% exceeds 40% limit",
        )
        rv = AllocationReadinessValidator()
        ra = rv.validate(plan, rpt, [bad_check])
        assert not ra.is_ready

    def test_to_dict(self):
        plan = _plan([_long("A", 900_000.0)])
        rpt  = AllocationValidator().validate(plan)
        ra   = AllocationReadinessValidator().validate(plan, rpt)
        d    = ra.to_dict()
        assert "is_ready" in d
        assert "blocking_reasons" in d
