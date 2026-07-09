"""iios/execution/planning/planning_factory.py
Convenience factory for construction of planning domain objects.
"""
from __future__ import annotations

from typing import Any

from iios.execution.planning.planning_constants import (
    DEFAULT_PRIORITY,
    ExecutionAlgorithm,
    ExecutionMode,
    ExecutionPlanStatus,
    RoutingStrategy,
)
from iios.execution.planning.core.execution_plan import ExecutionPlan
from iios.execution.planning.core.execution_route import ExecutionRoute
from iios.execution.planning.core.execution_schedule import ExecutionSchedule
from iios.execution.planning.core.execution_cost import ExecutionCost
from iios.execution.planning.core.execution_constraints import ExecutionConstraints
from iios.execution.planning.core.execution_instruction import ExecutionInstruction


class PlanningFactory:
    """Stateless factory — all methods are static."""

    @staticmethod
    def make_plan(
        order_id:         str              = "",
        execution_id:     str              = "",
        portfolio_id:     str              = "",
        strategy_id:      str              = "",
        decision_id:      str              = "",
        symbol:           str              = "",
        algorithm:        ExecutionAlgorithm = ExecutionAlgorithm.DIRECT,
        routing_strategy: RoutingStrategy  = RoutingStrategy.SINGLE_VENUE,
        execution_mode:   ExecutionMode    = ExecutionMode.IMMEDIATE,
        priority:         int              = DEFAULT_PRIORITY,
        status:           ExecutionPlanStatus = ExecutionPlanStatus.DRAFT,
        **kwargs: Any,
    ) -> ExecutionPlan:
        return ExecutionPlan(
            order_id         = order_id,
            execution_id     = execution_id,
            portfolio_id     = portfolio_id,
            strategy_id      = strategy_id,
            decision_id      = decision_id,
            symbol           = symbol,
            algorithm        = algorithm,
            routing_strategy = routing_strategy,
            execution_mode   = execution_mode,
            priority         = priority,
            status           = status,
        )

    @staticmethod
    def make_route(
        primary_venue:    str              = "default",
        routing_strategy: RoutingStrategy  = RoutingStrategy.SINGLE_VENUE,
        **kwargs: Any,
    ) -> ExecutionRoute:
        return ExecutionRoute(
            primary_venue    = primary_venue,
            routing_strategy = routing_strategy,
        )

    @staticmethod
    def make_cost(
        plan_id:     str   = "",
        order_value: float = 0.0,
    ) -> ExecutionCost:
        return ExecutionCost(plan_id=plan_id, order_value=order_value)

    @staticmethod
    def make_constraints(**kwargs: Any) -> ExecutionConstraints:
        return ExecutionConstraints(**kwargs)

    @staticmethod
    def make_instruction(
        plan_id:    str   = "",
        symbol:     str   = "",
        quantity:   float = 0.0,
        price:      float = 0.0,
        **kwargs: Any,
    ) -> ExecutionInstruction:
        return ExecutionInstruction(
            plan_id    = plan_id,
            symbol     = symbol,
            quantity   = quantity,
            price_limit = price or None,
        )
