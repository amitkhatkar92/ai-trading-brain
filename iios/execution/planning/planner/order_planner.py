"""iios/execution/planning/planner/order_planner.py
Core planner: generates an ExecutionPlan from a planning request.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.planning_constants import (
    DEFAULT_PRIORITY,
    ExecutionAlgorithm,
    ExecutionMode,
    ExecutionPlanStatus,
    RoutingStrategy,
)
from iios.execution.planning.core.execution_plan import ExecutionPlan
from iios.execution.planning.core.execution_cost import ExecutionCost
from iios.execution.planning.core.execution_route import ExecutionRoute
from iios.execution.planning.analytics.cost_estimator import CostEstimator
from iios.execution.planning.analytics.slippage_estimator import SlippageEstimator
from iios.execution.planning.analytics.impact_estimator import ImpactEstimator
from iios.execution.planning.analytics.liquidity_estimator import LiquidityEstimator
from iios.execution.planning.routing.routing_engine import RoutingEngine
from iios.execution.planning.planner.execution_scheduler import ExecutionScheduler, ScheduleRequest


@dataclass
class PlanRequest:
    """Input to OrderPlanner.plan()."""

    order_id:            str              = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id:        str              = ""
    portfolio_id:        str              = ""
    strategy_id:         str              = ""
    decision_id:         str              = ""
    symbol:              str              = ""
    order_value:         float            = 0.0
    quantity:            float            = 0.0
    price:               float            = 0.0

    routing_strategy:    RoutingStrategy  = RoutingStrategy.SINGLE_VENUE
    execution_mode:      ExecutionMode    = ExecutionMode.IMMEDIATE
    algorithm:           ExecutionAlgorithm = ExecutionAlgorithm.DIRECT
    priority:            int              = DEFAULT_PRIORITY
    preferred_venue:     str              = ""

    # Scheduling
    window_sec:          float            = 3_600.0
    urgency:             str              = "normal"

    # Market context (optional)
    adv:                 float | None     = None
    participation_rate:  float | None     = None

    request_id:          str              = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:            dict[str, Any]   = field(default_factory=dict)


@dataclass
class PlanResult:
    plan:           ExecutionPlan
    request_id:     str   = ""
    duration_ms:    float = 0.0
    metadata:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id":     self.plan.plan_id,
            "request_id":  self.request_id,
            "status":      self.plan.status.value,
            "duration_ms": self.duration_ms,
        }


class OrderPlanner:
    """
    Generates a complete ExecutionPlan for a given PlanRequest.

    Pipeline:
    1. Route selection
    2. Liquidity estimation
    3. Cost / slippage / impact estimation
    4. Schedule assignment
    5. Plan assembly
    """

    def __init__(
        self,
        routing_engine:     RoutingEngine      | None = None,
        cost_estimator:     CostEstimator      | None = None,
        slippage_estimator: SlippageEstimator  | None = None,
        impact_estimator:   ImpactEstimator    | None = None,
        liquidity_estimator: LiquidityEstimator | None = None,
        scheduler:          ExecutionScheduler | None = None,
    ) -> None:
        self._routing   = routing_engine      or RoutingEngine()
        self._cost      = cost_estimator      or CostEstimator()
        self._slippage  = slippage_estimator  or SlippageEstimator()
        self._impact    = impact_estimator    or ImpactEstimator()
        self._liquidity = liquidity_estimator or LiquidityEstimator()
        self._scheduler = scheduler           or ExecutionScheduler()

    def plan(self, req: PlanRequest) -> PlanResult:
        t0 = time.time()

        # 1 – Route
        route = self._routing.select_route(
            strategy        = req.routing_strategy,
            order_value     = req.order_value,
            preferred_venue = req.preferred_venue,
        )

        # 2 – Liquidity
        liq = self._liquidity.estimate(
            order_value = req.order_value,
            adv         = req.adv,
            order_id    = req.order_id,
        )
        route.route_score                  = liq.liquidity_score
        route.estimated_fill_probability  = liq.fill_probability

        # 3 – Cost
        slippage = self._slippage.estimate(
            req.order_value,
            liq.participation_rate if req.participation_rate is None else req.participation_rate,
        )
        impact  = self._impact.estimate(
            req.order_value,
            liq.participation_rate if req.participation_rate is None else req.participation_rate,
        )
        cost = self._cost.estimate(
            plan_id             = "",    # filled after plan creation
            order_value         = req.order_value,
            execution_window_sec = req.window_sec,
            slippage            = slippage,
            market_impact       = impact,
        )

        # 4 – Build plan
        plan = ExecutionPlan(
            order_id         = req.order_id,
            execution_id     = req.execution_id,
            portfolio_id     = req.portfolio_id,
            strategy_id      = req.strategy_id,
            decision_id      = req.decision_id,
            symbol           = req.symbol,
            routing_strategy = req.routing_strategy,
            execution_mode   = req.execution_mode,
            algorithm        = req.algorithm,
            priority         = req.priority,
            route            = route,
            estimated_cost   = cost,
            status           = ExecutionPlanStatus.VALIDATED,
        )
        plan.metadata.update(req.metadata)
        cost.plan_id = plan.plan_id

        # 5 – Schedule
        self._scheduler.schedule(
            plan,
            ScheduleRequest(
                plan_id          = plan.plan_id,
                window_sec       = req.window_sec,
                urgency          = req.urgency,
            ),
        )

        duration_ms = (time.time() - t0) * 1_000
        return PlanResult(
            plan        = plan,
            request_id  = req.request_id,
            duration_ms = round(duration_ms, 2),
        )
