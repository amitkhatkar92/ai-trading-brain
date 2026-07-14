"""test_allocation_plan.py — AllocationPlan, AllocationRequest, AllocationResult."""
import pytest
from iios.investment.portfolio.allocation.allocation_plan import (
    AllocationPlan,
    AllocationRequest,
    AllocationResult,
    CashAllocation,
    PositionAllocation,
)
from iios.investment.portfolio.allocation.allocation_types import (
    AllocationDirection,
    AllocationMethod,
    AllocationRunStatus,
)


class TestPositionAllocation:
    def _make(self, **kw):
        defaults = dict(
            symbol            = "RELIA.NS",
            name              = "Reliance",
            direction         = AllocationDirection.LONG,
            blueprint_weight  = 0.30,
            allocated_weight  = 0.285,
            allocated_capital = 285_000.0,
            min_capital       = 5_000.0,
            max_capital       = 350_000.0,
            sector            = "energy",
        )
        defaults.update(kw)
        return PositionAllocation(**defaults)

    def test_is_long(self):
        a = self._make(direction=AllocationDirection.LONG)
        assert a.is_long
        assert not a.is_short

    def test_is_short(self):
        a = self._make(direction=AllocationDirection.SHORT, allocated_capital=-50_000.0)
        assert a.is_short
        assert not a.is_long

    def test_abs_capital(self):
        a = self._make(allocated_capital=-50_000.0)
        assert a.abs_capital == 50_000.0

    def test_to_dict_round_trips(self):
        a   = self._make()
        d   = a.to_dict()
        assert d["symbol"] == "RELIA.NS"
        assert d["direction"] == "long"
        assert "allocated_capital" in d


class TestAllocationRequest:
    def test_defaults(self):
        req = AllocationRequest(
            portfolio_id   = "pf-1",
            blueprint_id   = "bp-1",
            total_capital  = 1_000_000.0,
        )
        assert req.currency == "INR"
        assert req.method   == AllocationMethod.BLUEPRINT_WEIGHT
        assert req.cash_reserve_pct == 0.05

    def test_to_dict_contains_key_fields(self):
        req = AllocationRequest(portfolio_id="pf-1", total_capital=500_000.0)
        d   = req.to_dict()
        assert "total_capital" in d
        assert "method" in d
        assert d["allow_short"] is False


class TestAllocationPlan:
    def _make_plan(self, allocations=()):
        return AllocationPlan(
            portfolio_id    = "pf-1",
            blueprint_id    = "bp-1",
            total_capital   = 1_000_000.0,
            invested_capital= 900_000.0,
            cash_capital    = 100_000.0,
            utilisation_rate= 0.90,
            allocations     = allocations,
            cash            = CashAllocation(cash_capital=100_000.0, cash_weight=0.10),
        )

    def test_properties_empty(self):
        plan = self._make_plan()
        assert plan.total_positions == 0
        assert plan.is_empty
        assert plan.long_count == 0
        assert plan.short_count == 0

    def test_properties_with_positions(self):
        alloc = PositionAllocation(
            symbol           = "RELIA.NS",
            direction        = AllocationDirection.LONG,
            allocated_capital= 300_000.0,
        )
        plan = self._make_plan(allocations=(alloc,))
        assert plan.total_positions == 1
        assert not plan.is_empty
        assert plan.symbols == ("RELIA.NS",)
        assert plan.long_count == 1

    def test_get_allocation_found(self):
        alloc = PositionAllocation(symbol="TCS.NS", allocated_capital=200_000.0)
        plan  = self._make_plan(allocations=(alloc,))
        found = plan.get_allocation("TCS.NS")
        assert found is not None
        assert found.symbol == "TCS.NS"

    def test_get_allocation_not_found(self):
        plan = self._make_plan()
        assert plan.get_allocation("XYZ.NS") is None

    def test_to_dict(self):
        plan = self._make_plan()
        d    = plan.to_dict()
        assert d["portfolio_id"] == "pf-1"
        assert "allocations" in d
        assert "cash" in d


class TestAllocationResult:
    def test_succeeded_on_completed(self):
        r = AllocationResult(status=AllocationRunStatus.COMPLETED)
        assert r.succeeded
        assert not r.failed

    def test_failed_on_failed(self):
        r = AllocationResult(status=AllocationRunStatus.FAILED)
        assert r.failed
        assert not r.succeeded

    def test_has_plan(self):
        plan = AllocationPlan()
        r    = AllocationResult(plan=plan)
        assert r.has_plan

    def test_no_plan(self):
        r = AllocationResult()
        assert not r.has_plan

    def test_to_dict(self):
        r = AllocationResult(status=AllocationRunStatus.COMPLETED, portfolio_id="pf-1")
        d = r.to_dict()
        assert d["portfolio_id"] == "pf-1"
        assert d["status"] == "completed"
