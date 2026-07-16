"""iios/execution/oms/order_router/routing_strategy.py
==================================================
RoutingStrategy — algorithm that ranks eligible candidates and
selects the best routing target.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from iios.execution.oms.order_router.exceptions import NoCandidatesError, RoutingStrategyError
from iios.execution.oms.order_router.routing_candidate import RoutingCandidate
from iios.execution.oms.order_router.routing_context import RoutingContext


@dataclass
class RoutingStrategy:
    """
    Stateless strategy for ranking and selecting a RoutingCandidate.

    select() always returns the single best candidate or raises
    NoCandidatesError if none are eligible.
    """
    strategy_id: str = "default_ranking"
    description: str = "Rank by score descending; tie-break by priority then broker_id."

    def rank(
        self,
        candidates: list[RoutingCandidate],
        context: RoutingContext,
    ) -> list[RoutingCandidate]:
        """
        Return eligible candidates sorted by score (descending).
        Tie-break by broker priority (descending) then broker_id (ascending).
        """
        eligible = [c for c in candidates if c.is_eligible]
        return sorted(
            eligible,
            key=lambda c: (
                -c.score,
                -(c.capabilities.priority if c.capabilities else 0),
                c.broker_id,
            ),
        )

    def select(
        self,
        candidates: list[RoutingCandidate],
        context: RoutingContext,
    ) -> RoutingCandidate:
        """
        Select the best candidate or raise NoCandidatesError.
        """
        ranked = self.rank(candidates, context)
        if not ranked:
            raise NoCandidatesError(
                context.order_id,
                context={"discarded": [c.to_dict() for c in candidates]},
            )
        return ranked[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "description": self.description,
        }
