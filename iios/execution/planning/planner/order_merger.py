"""iios/execution/planning/planner/order_merger.py
Merges multiple execution plans into a single consolidated plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.core.execution_plan import ExecutionPlan
from iios.execution.planning.planning_factory import PlanningFactory


@dataclass
class MergeResult:
    merged_plan:    ExecutionPlan
    source_plan_ids: list[str] = field(default_factory=list)
    metadata:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "merged_plan_id":   self.merged_plan.plan_id,
            "source_plan_ids":  self.source_plan_ids,
            "n_merged":         len(self.source_plan_ids),
        }


class OrderMerger:
    """
    Merges compatible execution plans into a single consolidated plan.

    Plans are merged when they share the same symbol, portfolio, and strategy.
    The merged plan inherits the highest priority from the source plans.
    """

    def merge(self, plans: list[ExecutionPlan]) -> MergeResult:
        if not plans:
            raise ValueError("Cannot merge empty plan list")

        # Use first plan as template
        base = plans[0]
        merged = PlanningFactory.make_plan(
            order_id         = base.order_id,
            execution_id     = base.execution_id,
            portfolio_id     = base.portfolio_id,
            strategy_id      = base.strategy_id,
            decision_id      = base.decision_id,
            symbol           = base.symbol,
            algorithm        = base.algorithm,
            routing_strategy = base.routing_strategy,
            execution_mode   = base.execution_mode,
        )
        # Inherit highest priority
        merged.priority = max(p.priority for p in plans)
        merged.metadata["merged_from"] = [p.plan_id for p in plans]
        merged.metadata["n_merged"]    = len(plans)

        source_ids = [p.plan_id for p in plans]
        return MergeResult(
            merged_plan     = merged,
            source_plan_ids = source_ids,
        )
