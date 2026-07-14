"""test_capital_allocation.py — PositionAllocator, CashManager, rules."""
import pytest
from iios.investment.portfolio.allocation.position_allocator import PositionAllocator
from iios.investment.portfolio.allocation.cash_manager import CashManager
from iios.investment.portfolio.allocation.allocation_rules import (
    CashReserveRule,
    MaxPositionCapRule,
    MinPositionSizeRule,
    NegativeLongBlockRule,
    default_rule_chain,
)
from iios.investment.portfolio.allocation.allocation_plan import AllocationRequest
from iios.investment.portfolio.allocation.allocation_types import AllocationMethod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _req(**kw):
    defaults = dict(
        portfolio_id     = "pf-1",
        blueprint_id     = "bp-1",
        total_capital    = 1_000_000.0,
        cash_reserve_pct = 0.05,
        method           = AllocationMethod.BLUEPRINT_WEIGHT,
        max_position_weight = 0.40,
        min_position_weight = 0.005,
        min_trade_size      = 100.0,
        allow_short         = False,
    )
    defaults.update(kw)
    return AllocationRequest(**defaults)


# ---------------------------------------------------------------------------
# PositionAllocator — BLUEPRINT_WEIGHT
# ---------------------------------------------------------------------------

class TestPositionAllocatorBlueprintWeight:
    def test_basic_allocation(self, single_slot_blueprint, standard_request):
        allocator = PositionAllocator()
        allocs    = allocator.allocate(single_slot_blueprint, standard_request)
        assert len(allocs) == 1
        alloc = allocs[0]
        assert alloc.symbol == "RELIA.NS"
        # target_weight = 0.30, investable = 950_000 → 285_000
        assert abs(alloc.allocated_capital - 285_000.0) < 1.0

    def test_multiple_slots(self, multi_slot_blueprint, standard_request):
        allocator = PositionAllocator()
        allocs    = allocator.allocate(multi_slot_blueprint, standard_request)
        assert len(allocs) == 5
        symbols = {a.symbol for a in allocs}
        assert "RELIA.NS" in symbols
        assert "TCS.NS" in symbols

    def test_capital_roughly_conserved(self, multi_slot_blueprint, standard_request):
        allocator = PositionAllocator()
        allocs    = allocator.allocate(multi_slot_blueprint, standard_request)
        total_allocated = sum(abs(a.allocated_capital) for a in allocs)
        # Should be ≤ investable (≤ 950_000) after cash reserve
        assert total_allocated <= standard_request.total_capital

    def test_empty_blueprint(self, standard_request):
        from tests.unit.investment.portfolio.allocation.conftest import _Blueprint
        bp     = _Blueprint(slots=())
        allocs = PositionAllocator().allocate(bp, standard_request)
        assert allocs == ()

    def test_excluded_symbols(self, multi_slot_blueprint, standard_request):
        req = AllocationRequest(
            **{**standard_request.to_dict(),
               "symbols_excluded": frozenset({"RELIA.NS"}),
               "method": AllocationMethod.BLUEPRINT_WEIGHT,
               "requested_at": standard_request.requested_at,
               "metadata": {},
            }
        )
        allocs  = PositionAllocator().allocate(multi_slot_blueprint, req)
        symbols = {a.symbol for a in allocs}
        assert "RELIA.NS" not in symbols


# ---------------------------------------------------------------------------
# PositionAllocator — EQUAL
# ---------------------------------------------------------------------------

class TestPositionAllocatorEqual:
    def test_equal_allocation(self, multi_slot_blueprint):
        req    = _req(method=AllocationMethod.EQUAL, max_position_weight=1.0)
        allocs = PositionAllocator().allocate(multi_slot_blueprint, req)
        # All should be ≈ equal
        caps   = [abs(a.allocated_capital) for a in allocs]
        if len(caps) > 1:
            diff = max(caps) - min(caps)
            assert diff < 1.0, f"Not equal: {caps}"


# ---------------------------------------------------------------------------
# PositionAllocator — CONVICTION
# ---------------------------------------------------------------------------

class TestPositionAllocatorConviction:
    def test_conviction_ordering(self, multi_slot_blueprint):
        req    = _req(method=AllocationMethod.CONVICTION, max_position_weight=1.0)
        allocs = PositionAllocator().allocate(multi_slot_blueprint, req)
        # RELIA.NS has conviction 0.8 > TCS.NS 0.7 → RELIA gets more
        relia = next(a for a in allocs if a.symbol == "RELIA.NS")
        tcs   = next(a for a in allocs if a.symbol == "TCS.NS")
        assert relia.allocated_capital >= tcs.allocated_capital


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class TestMaxPositionCapRule:
    def test_caps_large_position(self):
        rule = MaxPositionCapRule()
        req  = _req(max_position_weight=0.20, total_capital=1_000_000.0)
        weights = {"A": 300_000.0, "B": 100_000.0}
        rule.apply(weights, req)
        assert weights["A"] <= 200_000.0 + 0.01
        assert weights["B"] == pytest.approx(100_000.0)

    def test_no_change_when_within_cap(self):
        rule    = MaxPositionCapRule()
        req     = _req(max_position_weight=0.50)
        weights = {"A": 200_000.0}
        rule.apply(weights, req)
        assert weights["A"] == pytest.approx(200_000.0)


class TestMinPositionSizeRule:
    def test_removes_small_positions(self):
        rule    = MinPositionSizeRule()
        req     = _req(min_trade_size=500.0)
        weights = {"A": 200.0, "B": 600.0}
        rule.apply(weights, req)
        assert "A" not in weights
        assert "B" in weights

    def test_keeps_above_threshold(self):
        rule    = MinPositionSizeRule()
        req     = _req(min_trade_size=100.0)
        weights = {"A": 500.0}
        rule.apply(weights, req)
        assert "A" in weights


class TestCashReserveRule:
    def test_scales_down_over_allocated(self):
        rule    = CashReserveRule()
        req     = _req(cash_reserve_pct=0.10, total_capital=1_000_000.0)
        # 90% reserve → investable = 900_000; but positions total 950_000
        weights = {"A": 500_000.0, "B": 450_000.0}
        rule.apply(weights, req)
        total = sum(abs(v) for v in weights.values())
        assert total <= 900_000.0 + 1.0

    def test_no_change_within_reserve(self):
        rule    = CashReserveRule()
        req     = _req(cash_reserve_pct=0.10, total_capital=1_000_000.0)
        weights = {"A": 400_000.0, "B": 300_000.0}   # 700_000 < 900_000
        orig_a  = weights["A"]
        rule.apply(weights, req)
        assert weights["A"] == pytest.approx(orig_a)


class TestNegativeLongBlockRule:
    def test_removes_negative_when_shorts_not_allowed(self):
        rule    = NegativeLongBlockRule()
        req     = _req(allow_short=False)
        weights = {"A": 200_000.0, "B": -50_000.0}
        rule.apply(weights, req)
        assert "B" not in weights
        assert "A" in weights

    def test_keeps_negative_when_shorts_allowed(self):
        rule    = NegativeLongBlockRule()
        req     = _req(allow_short=True)
        weights = {"A": 200_000.0, "B": -50_000.0}
        rule.apply(weights, req)
        assert "B" in weights


# ---------------------------------------------------------------------------
# CashManager
# ---------------------------------------------------------------------------

class TestCashManager:
    def _req(self, cash_reserve_pct=0.05, total_capital=1_000_000.0):
        return _req(cash_reserve_pct=cash_reserve_pct, total_capital=total_capital)

    def test_basic_cash_computation(self):
        mgr   = CashManager()
        req   = self._req()
        pos   = mgr.compute(1_000_000.0, 900_000.0, req)
        assert pos.cash_capital == pytest.approx(100_000.0, abs=1.0)
        assert pos.is_above_minimum
        assert pos.is_within_maximum

    def test_shortfall_when_invested_too_much(self):
        mgr  = CashManager()
        req  = self._req(cash_reserve_pct=0.10)
        # invested = 950_000, reserve needed = 100_000 → cash only 50_000
        pos  = mgr.compute(1_000_000.0, 950_000.0, req)
        assert pos.shortfall > 0
        assert not pos.is_above_minimum

    def test_zero_total_capital(self):
        mgr = CashManager()
        req = _req(total_capital=0.0)
        pos = mgr.compute(0.0, 0.0, req)
        assert pos.cash_capital == 0.0
        assert pos.cash_pct == 0.0

    def test_to_cash_allocation(self):
        mgr  = CashManager()
        req  = self._req()
        pos  = mgr.compute(1_000_000.0, 900_000.0, req)
        ca   = pos.to_cash_allocation()
        assert ca.cash_capital == pos.cash_capital
