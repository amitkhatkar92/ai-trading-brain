"""iios/execution/planning/routing/route_selector.py
Selects the best venue/route from a scored list.
"""
from __future__ import annotations

from iios.execution.planning.planning_constants import RoutingStrategy
from iios.execution.planning.planning_exceptions import NoSuitableVenueError
from iios.execution.planning.core.execution_route import ExecutionRoute
from iios.execution.planning.routing.route_registry import RouteRegistry, VenueInfo
from iios.execution.planning.routing.route_evaluator import RouteEvaluator, RouteScore


class RouteSelector:
    """
    Selects an ExecutionRoute from the registry based on the requested
    RoutingStrategy.

    All selection logic is deterministic and broker-independent.
    """

    def __init__(
        self,
        registry:  RouteRegistry  | None = None,
        evaluator: RouteEvaluator | None = None,
    ) -> None:
        self._registry  = registry  or RouteRegistry()
        self._evaluator = evaluator or RouteEvaluator()

    def select(
        self,
        strategy:       RoutingStrategy = RoutingStrategy.SINGLE_VENUE,
        order_value:    float           = 0.0,
        liquidity_score: float          = 50.0,
        preferred_venue: str            = "",
    ) -> ExecutionRoute:
        active = self._registry.active_venues()

        if not active:
            # Return a default "internal" route when no venues are registered.
            route = ExecutionRoute(
                routing_strategy = strategy,
                primary_venue    = "default",
            )
            return route

        # Honour explicit preferred venue if available
        if preferred_venue and self._registry.has_venue(preferred_venue):
            v = self._registry.get_venue(preferred_venue)
            return self._make_route(v, strategy)

        scores = self._evaluator.evaluate(active, order_value, liquidity_score)
        if not scores:
            raise NoSuitableVenueError()

        if strategy == RoutingStrategy.SINGLE_VENUE:
            return self._make_route(
                self._registry.get_venue(scores[0].venue_id), strategy
            )

        if strategy == RoutingStrategy.MULTI_VENUE:
            primary = scores[0].venue_id
            fallbacks = [s.venue_id for s in scores[1:3]]
            return ExecutionRoute(
                routing_strategy = strategy,
                primary_venue    = primary,
                backup_venues    = fallbacks,
                route_score      = scores[0].composite_score,
            )

        if strategy == RoutingStrategy.COST_BASED:
            best = max(scores, key=lambda s: s.cost_score)
            return self._make_route(self._registry.get_venue(best.venue_id), strategy)

        if strategy == RoutingStrategy.LATENCY_AWARE:
            best = max(scores, key=lambda s: s.latency_score)
            return self._make_route(self._registry.get_venue(best.venue_id), strategy)

        if strategy == RoutingStrategy.LIQUIDITY:
            best = max(scores, key=lambda s: s.liquidity_score)
            return self._make_route(self._registry.get_venue(best.venue_id), strategy)

        # Default: best composite
        return self._make_route(
            self._registry.get_venue(scores[0].venue_id), strategy
        )

    @staticmethod
    def _make_route(venue: VenueInfo, strategy: RoutingStrategy) -> ExecutionRoute:
        return ExecutionRoute(
            routing_strategy = strategy,
            primary_venue    = venue.venue_id,
        )
