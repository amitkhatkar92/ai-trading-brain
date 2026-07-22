"""
portfolio_allocation_engine.py — iios.portfolio.optimization
=============================================================
Generates AllocationPlan for all 8 AllocationCapability types.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from .constants import AllocationCapability, VERSION
from .portfolio_candidate import PortfolioCandidate
from .portfolio_optimization_strategy import PortfolioOptimizationStrategy
from .portfolio_solution import AllocationPlan


class PortfolioAllocationEngine:
    """
    Generates an AllocationPlan from a candidate and strategy.

    Allocation logic (in order of precedence):
    1. If the candidate inputs contain a key matching the capability
       value (e.g., ``"capital"`` for CAPITAL), use that dict directly.
    2. If ``position_snapshot`` is in the inputs, generate equal-weight
       allocations over the snapshot's assets.
    3. Fall back to a single-asset ``{"PORTFOLIO": 1.0}`` plan.
    """

    def generate(
        self,
        candidate:       PortfolioCandidate,
        strategy:        PortfolioOptimizationStrategy,
        inputs:          Dict[str, Any],
        capability:      AllocationCapability = AllocationCapability.CAPITAL,
    ) -> AllocationPlan:
        """
        Generate an AllocationPlan for the given candidate.

        Parameters
        ----------
        candidate :  The portfolio candidate being allocated.
        strategy :   Strategy providing configuration hints.
        inputs :     External input snapshots.
        capability : Which allocation capability to use.
        """
        allocations = self._resolve_allocations(
            candidate, inputs, capability
        )
        total = sum(allocations.values())

        return AllocationPlan(
            plan_id           = str(uuid.uuid4()),
            candidate_id      = candidate.candidate_id,
            portfolio_id      = candidate.portfolio_id,
            allocation_type   = capability,
            allocations       = allocations,
            total             = total,
            generated_at      = time.time(),
            metadata          = {
                "strategy_name": strategy.name,
                "strategy_type": strategy.strategy_type.value,
            },
            framework_version = VERSION,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_allocations(
        self,
        candidate:  PortfolioCandidate,
        inputs:     Dict[str, Any],
        capability: AllocationCapability,
    ) -> Dict[str, float]:
        merged = {**inputs, **candidate.inputs}

        # 1. Explicit allocation data keyed by capability value
        key = capability.value
        if key in merged and isinstance(merged[key], dict):
            raw = merged[key]
            return {str(k): float(v) for k, v in raw.items()}

        # 2. Equal-weight from position_snapshot
        snapshot = merged.get("position_snapshot") or merged.get("positions")
        if snapshot and isinstance(snapshot, dict) and snapshot:
            assets = list(snapshot.keys())
            weight = 1.0 / len(assets)
            return {a: weight for a in assets}

        # 3. Default single-asset
        return {"PORTFOLIO": 1.0}
