"""
portfolio_rebalancing_engine.py — iios.portfolio.optimization
=============================================================
Generates RebalancingPlan for all 6 RebalancingCapability types.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List

from .constants import RebalancingCapability, VERSION
from .portfolio_candidate import PortfolioCandidate
from .portfolio_optimization_strategy import PortfolioOptimizationStrategy
from .portfolio_solution import RebalancingPlan


class PortfolioRebalancingEngine:
    """
    Generates a RebalancingPlan from a candidate and strategy.

    Rebalancing action logic (in order of precedence):
    1. If the candidate inputs contain a key
       ``"rebalancing_<capability_value>"`` (e.g., ``"rebalancing_threshold"``),
       use those actions directly.
    2. If both ``position_snapshot`` and ``target_allocation`` are
       present, compute delta actions.
    3. Return an empty-actions plan.
    """

    def generate(
        self,
        candidate:   PortfolioCandidate,
        strategy:    PortfolioOptimizationStrategy,
        inputs:      Dict[str, Any],
        capability:  RebalancingCapability = RebalancingCapability.THRESHOLD,
    ) -> RebalancingPlan:
        """
        Generate a RebalancingPlan for the given candidate.
        """
        actions, trigger = self._resolve_actions(candidate, inputs, capability)

        return RebalancingPlan(
            plan_id           = str(uuid.uuid4()),
            candidate_id      = candidate.candidate_id,
            portfolio_id      = candidate.portfolio_id,
            rebalancing_type  = capability,
            actions           = tuple(actions),
            trigger           = trigger,
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

    def _resolve_actions(
        self,
        candidate:  PortfolioCandidate,
        inputs:     Dict[str, Any],
        capability: RebalancingCapability,
    ):
        merged = {**inputs, **candidate.inputs}

        # 1. Explicit rebalancing action list (keyed by capability value)
        key = capability.value
        if key in merged and isinstance(merged[key], (list, tuple)):
            return list(merged[key]), capability.value

        # 2. Compute deltas from position_snapshot + target_allocation
        snapshot = merged.get("position_snapshot") or merged.get("positions")
        targets  = merged.get("target_allocation") or merged.get("target_allocations")
        if snapshot and targets and isinstance(snapshot, dict) and isinstance(targets, dict):
            actions = []
            all_assets = set(list(snapshot) + list(targets))
            for asset in sorted(all_assets):
                current = float(snapshot.get(asset, 0.0))
                target  = float(targets.get(asset, 0.0))
                delta   = target - current
                if abs(delta) > 1e-6:
                    actions.append(
                        {"asset": asset, "current": current,
                         "target": target, "delta": delta}
                    )
            return actions, "delta_from_snapshot"

        # 3. Empty plan
        return [], capability.value
