"""iios/execution/planning/core/execution_cost.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionCost:
    cost_id:                   str   = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id:                   str   = ""
    order_value:               float = 0.0
    estimated_commission:      float = 0.0
    estimated_slippage:        float = 0.0
    estimated_market_impact:   float = 0.0
    estimated_opportunity_cost: float = 0.0
    total_estimated_cost:      float = 0.0
    cost_bps:                  float = 0.0   # (total / order_value) * 10_000
    currency:                  str   = "INR"
    computed_at:               float = field(default_factory=time.time)
    metadata:                  dict  = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._recompute_total()

    def _recompute_total(self) -> None:
        self.total_estimated_cost = (
            self.estimated_commission
            + self.estimated_slippage
            + self.estimated_market_impact
            + self.estimated_opportunity_cost
        )
        if self.order_value > 0:
            self.cost_bps = (self.total_estimated_cost / self.order_value) * 10_000

    def with_commission(self, commission: float) -> "ExecutionCost":
        self.estimated_commission = commission
        self._recompute_total()
        return self

    def with_slippage(self, slippage: float) -> "ExecutionCost":
        self.estimated_slippage = slippage
        self._recompute_total()
        return self

    def with_impact(self, impact: float) -> "ExecutionCost":
        self.estimated_market_impact = impact
        self._recompute_total()
        return self

    def with_opportunity(self, opportunity: float) -> "ExecutionCost":
        self.estimated_opportunity_cost = opportunity
        self._recompute_total()
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "cost_id":                    self.cost_id,
            "plan_id":                    self.plan_id,
            "order_value":                self.order_value,
            "estimated_commission":       self.estimated_commission,
            "estimated_slippage":         self.estimated_slippage,
            "estimated_market_impact":    self.estimated_market_impact,
            "estimated_opportunity_cost": self.estimated_opportunity_cost,
            "total_estimated_cost":       self.total_estimated_cost,
            "cost_bps":                   self.cost_bps,
            "currency":                   self.currency,
        }
