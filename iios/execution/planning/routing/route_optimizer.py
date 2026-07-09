"""iios/execution/planning/routing/route_optimizer.py
Optimises a set of candidate routes for a given order context.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.routing.route_registry import RouteRegistry, VenueInfo
from iios.execution.planning.routing.route_evaluator import RouteEvaluator, RouteScore


@dataclass
class OptimizationResult:
    """Output of RouteOptimizer.optimize()."""

    winner:       RouteScore | None     = None
    all_scores:   list[RouteScore]      = field(default_factory=list)
    strategy_used: str                  = ""
    notes:        list[str]             = field(default_factory=list)
    metadata:     dict[str, Any]        = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "winner":        self.winner.to_dict() if self.winner else None,
            "all_scores":    [s.to_dict() for s in self.all_scores],
            "strategy_used": self.strategy_used,
            "notes":         self.notes,
        }


class RouteOptimizer:
    """
    Runs route evaluation and returns a ranked OptimizationResult.

    Optimisation here means selecting the composite-highest-scoring route;
    full ML-based optimisation is a future extension point.
    """

    def __init__(
        self,
        registry:  RouteRegistry  | None = None,
        evaluator: RouteEvaluator | None = None,
    ) -> None:
        self._registry  = registry  or RouteRegistry()
        self._evaluator = evaluator or RouteEvaluator()

    def optimize(
        self,
        order_value:    float = 0.0,
        liquidity_score: float = 50.0,
    ) -> OptimizationResult:
        active = self._registry.active_venues()
        if not active:
            return OptimizationResult(
                strategy_used = "default",
                notes         = ["No active venues; optimization skipped"],
            )

        scores = self._evaluator.evaluate(active, order_value, liquidity_score)
        return OptimizationResult(
            winner        = scores[0] if scores else None,
            all_scores    = scores,
            strategy_used = "composite_score",
            metadata      = {"n_venues": len(active)},
        )
