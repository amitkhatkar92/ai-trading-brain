"""iios/execution/planning/analytics/cost_estimator.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.planning_constants import (
    DEFAULT_COMMISSION_RATE,
    DEFAULT_OPPORTUNITY_RATE,
)
from iios.execution.planning.core.execution_cost import ExecutionCost


@dataclass
class CostEstimatorConfig:
    commission_rate:    float = DEFAULT_COMMISSION_RATE    # fraction of order_value
    opportunity_rate:   float = DEFAULT_OPPORTUNITY_RATE   # per-second holding cost factor
    min_commission:     float = 0.0                        # floor in currency units
    metadata:           dict  = field(default_factory=dict)


class CostEstimator:
    """Estimates transaction costs for an execution plan.

    All formulas are broker-independent.

    estimated_cost = commission + market_impact + slippage + opportunity_cost

    CostEstimator itself only handles commission + opportunity_cost.
    MarketImpact and Slippage are delegated to their respective estimators.
    The PlanningManager assembles the full cost.
    """

    def __init__(self, config: CostEstimatorConfig | None = None) -> None:
        self._cfg = config or CostEstimatorConfig()

    def estimate_commission(self, order_value: float) -> float:
        commission = order_value * self._cfg.commission_rate
        return max(commission, self._cfg.min_commission)

    def estimate_opportunity_cost(
        self,
        order_value: float,
        execution_window_sec: float = 0.0,
    ) -> float:
        if execution_window_sec <= 0:
            return 0.0
        return order_value * self._cfg.opportunity_rate * (execution_window_sec / 3_600.0)

    def estimate(
        self,
        plan_id:             str   = "",
        order_value:         float = 0.0,
        execution_window_sec: float = 0.0,
        slippage:            float = 0.0,
        market_impact:       float = 0.0,
    ) -> ExecutionCost:
        commission       = self.estimate_commission(order_value)
        opportunity_cost = self.estimate_opportunity_cost(order_value, execution_window_sec)
        cost             = ExecutionCost(
            plan_id               = plan_id,
            order_value           = order_value,
        )
        cost.with_commission(commission)
        cost.with_slippage(slippage)
        cost.with_impact(market_impact)
        cost.with_opportunity(opportunity_cost)
        return cost

    def to_dict(self) -> dict[str, Any]:
        return {
            "commission_rate":  self._cfg.commission_rate,
            "opportunity_rate": self._cfg.opportunity_rate,
            "min_commission":   self._cfg.min_commission,
        }
