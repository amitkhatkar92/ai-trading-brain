"""iios/execution/planning/routing/routing_engine.py
Top-level routing coordinator.
"""
from __future__ import annotations

import threading

from iios.execution.planning.planning_constants import RoutingStrategy
from iios.execution.planning.core.execution_route import ExecutionRoute
from iios.execution.planning.routing.route_registry import RouteRegistry, VenueInfo
from iios.execution.planning.routing.route_evaluator import RouteEvaluator
from iios.execution.planning.routing.route_selector import RouteSelector
from iios.execution.planning.routing.route_optimizer import RouteOptimizer, OptimizationResult


class RoutingEngine:
    """
    Coordinates venue registry, evaluation, selection, and optimisation
    into a single public API for the PlanningManager.
    """

    def __init__(
        self,
        registry:  RouteRegistry  | None = None,
        evaluator: RouteEvaluator | None = None,
    ) -> None:
        self._lock      = threading.RLock()
        self._registry  = registry  or RouteRegistry()
        self._evaluator = evaluator or RouteEvaluator()
        self._selector  = RouteSelector(self._registry, self._evaluator)
        self._optimizer = RouteOptimizer(self._registry, self._evaluator)

    # ── venue management ──────────────────────────────────────────────────────

    def register_venue(self, info: VenueInfo, *, overwrite: bool = False) -> None:
        with self._lock:
            self._registry.register_venue(info, overwrite=overwrite)

    def has_venue(self, venue_id: str) -> bool:
        return self._registry.has_venue(venue_id)

    # ── routing ───────────────────────────────────────────────────────────────

    def select_route(
        self,
        strategy:        RoutingStrategy = RoutingStrategy.SINGLE_VENUE,
        order_value:     float           = 0.0,
        liquidity_score: float           = 50.0,
        preferred_venue: str             = "",
    ) -> ExecutionRoute:
        return self._selector.select(
            strategy        = strategy,
            order_value     = order_value,
            liquidity_score = liquidity_score,
            preferred_venue = preferred_venue,
        )

    def optimize(
        self,
        order_value:     float = 0.0,
        liquidity_score: float = 50.0,
    ) -> OptimizationResult:
        return self._optimizer.optimize(order_value, liquidity_score)

    def registry(self) -> RouteRegistry:
        return self._registry

    def statistics(self) -> dict:
        return self._registry.statistics()
