"""iios/investment/portfolio/allocation/allocation_engine.py"""
from __future__ import annotations

import threading

from iios.investment.portfolio.core.portfolio import Portfolio
from iios.investment.portfolio.allocation.allocation_constraints import AllocationConstraints
from iios.investment.portfolio.allocation.allocation_report import AllocationReport
from iios.investment.portfolio.allocation.capital_allocator import CapitalAllocator


class AllocationEngine:
    """Orchestrates capital allocation analysis with per-portfolio constraints."""

    def __init__(
        self,
        allocator: CapitalAllocator | None = None,
        default_constraints: AllocationConstraints | None = None,
    ) -> None:
        self._lock                 = threading.RLock()
        self._allocator            = allocator or CapitalAllocator()
        self._default_constraints  = default_constraints or AllocationConstraints()
        self._portfolio_constraints: dict[str, AllocationConstraints] = {}

    def set_constraints(self, portfolio_id: str, constraints: AllocationConstraints) -> None:
        with self._lock:
            self._portfolio_constraints[portfolio_id] = constraints

    def get_constraints(self, portfolio_id: str) -> AllocationConstraints:
        with self._lock:
            return self._portfolio_constraints.get(portfolio_id, self._default_constraints)

    def analyze(
        self,
        portfolio:   Portfolio,
        constraints: AllocationConstraints | None = None,
    ) -> AllocationReport:
        effective = constraints or self.get_constraints(portfolio.portfolio_id)
        return self._allocator.compute(portfolio, effective)
