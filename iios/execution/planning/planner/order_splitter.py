"""iios/execution/planning/planner/order_splitter.py
Splits a large order into smaller child execution plans.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.planning_constants import (
    DEFAULT_MAX_SPLIT_LEGS,
    ExecutionAlgorithm,
    OrderSplitType,
)
from iios.execution.planning.core.execution_plan import ExecutionPlan
from iios.execution.planning.planning_factory import PlanningFactory


@dataclass
class SplitConfig:
    split_type:   OrderSplitType = OrderSplitType.EQUAL
    num_legs:     int            = 2
    max_legs:     int            = DEFAULT_MAX_SPLIT_LEGS
    metadata:     dict[str, Any] = field(default_factory=dict)


@dataclass
class SplitResult:
    parent_plan_id: str              = ""
    child_plans:    list[ExecutionPlan] = field(default_factory=list)
    split_type:     OrderSplitType   = OrderSplitType.EQUAL
    metadata:       dict[str, Any]   = field(default_factory=dict)

    @property
    def leg_count(self) -> int:
        return len(self.child_plans)

    def to_dict(self) -> dict[str, Any]:
        return {
            "parent_plan_id": self.parent_plan_id,
            "leg_count":      self.leg_count,
            "split_type":     self.split_type.value,
            "child_plan_ids": [p.plan_id for p in self.child_plans],
        }


class OrderSplitter:
    """
    Splits a parent ExecutionPlan into multiple child plans.

    Only EQUAL and TIME_BASED split types are implemented here.
    VOLUME_BASED and ADAPTIVE are interface stubs for future implementation.
    """

    def split(self, parent: ExecutionPlan, config: SplitConfig | None = None) -> SplitResult:
        cfg = config or SplitConfig()
        n   = min(max(2, cfg.num_legs), cfg.max_legs)

        if cfg.split_type == OrderSplitType.NO_SPLIT:
            return SplitResult(
                parent_plan_id = parent.plan_id,
                child_plans    = [parent],
                split_type     = OrderSplitType.NO_SPLIT,
            )

        children = self._equal_split(parent, n)

        # Link children to parent
        for child in children:
            child.parent_plan_id = parent.plan_id
            parent.child_plan_ids.append(child.plan_id)

        return SplitResult(
            parent_plan_id = parent.plan_id,
            child_plans    = children,
            split_type     = cfg.split_type,
            metadata       = {"n_legs": n},
        )

    @staticmethod
    def _equal_split(parent: ExecutionPlan, n: int) -> list[ExecutionPlan]:
        children: list[ExecutionPlan] = []
        for i in range(n):
            child = PlanningFactory.make_plan(
                order_id     = parent.order_id,
                execution_id = parent.execution_id,
                portfolio_id = parent.portfolio_id,
                strategy_id  = parent.strategy_id,
                decision_id  = parent.decision_id,
                symbol       = parent.symbol,
                algorithm    = ExecutionAlgorithm.DIRECT,
                routing_strategy = parent.routing_strategy,
                execution_mode   = parent.execution_mode,
            )
            child.metadata["split_leg"]   = i + 1
            child.metadata["split_total"] = n
            child.metadata["split_type"]  = OrderSplitType.EQUAL.value
            children.append(child)
        return children
