"""iios/investment/portfolio/allocation/capital_allocator.py
Computes current vs target allocation deviations from a Portfolio.
"""
from __future__ import annotations

from iios.investment.portfolio.core.portfolio import Portfolio
from iios.investment.portfolio.allocation.allocation_constraints import AllocationConstraints
from iios.investment.portfolio.allocation.allocation_report import AllocationReport
from iios.investment.portfolio.portfolio_constants import AllocationStatus


class CapitalAllocator:
    """
    Pure computation — derives current allocation per asset class,
    compares to targets, and flags rebalancing needs.
    """

    def compute(
        self,
        portfolio:   Portfolio,
        constraints: AllocationConstraints | None = None,
    ) -> AllocationReport:
        nav = portfolio.total_nav
        con = constraints or AllocationConstraints()

        if nav <= 0:
            return AllocationReport(
                portfolio_id = portfolio.portfolio_id,
                status       = AllocationStatus.UNKNOWN,
            )

        # Build current allocations by asset class
        current: dict[str, float] = {}
        for pos in portfolio.positions.values():
            ac = pos.asset_class.value
            current[ac] = current.get(ac, 0.0) + pos.market_value / nav

        # Include cash as its own pseudo-asset class
        current["cash"] = portfolio.cash / nav if nav > 0 else 0.0

        targets = dict(con.target_allocations)

        deviations:      dict[str, float] = {}
        rebalance_flags: dict[str, bool]  = {}
        all_keys = set(current) | set(targets)
        for key in all_keys:
            act = current.get(key, 0.0)
            tgt = targets.get(key, 0.0)
            dev = act - tgt
            deviations[key]      = round(dev, 6)
            rebalance_flags[key] = abs(dev) > con.rebalance_threshold

        rebalancing_needed = any(rebalance_flags.values())

        # Score: average of (1 - abs_deviation / 0.20) capped 0–100
        # Perfect = all deviations 0 → score 100
        # 20% deviation on all → score 0
        if targets:
            scores = [
                max(0.0, 1.0 - abs(deviations.get(k, 0.0)) / 0.20)
                for k in targets
            ]
            alloc_score = sum(scores) / len(scores) * 100
        else:
            alloc_score = 50.0   # no targets → neutral

        notes: list[str] = []
        for k, flag in rebalance_flags.items():
            if flag:
                notes.append(
                    f"{k}: deviation {deviations[k]:+.1%} exceeds "
                    f"rebalance threshold {con.rebalance_threshold:.1%}"
                )

        status = (
            AllocationStatus.WITHIN_LIMITS if not rebalancing_needed
            else AllocationStatus.OVERALLOCATED
        )

        return AllocationReport(
            portfolio_id        = portfolio.portfolio_id,
            current_allocations = {k: round(v, 6) for k, v in current.items()},
            target_allocations  = targets,
            deviations          = deviations,
            rebalance_flags     = rebalance_flags,
            rebalancing_needed  = rebalancing_needed,
            allocation_score    = round(alloc_score, 2),
            status              = status,
            notes               = notes,
        )
