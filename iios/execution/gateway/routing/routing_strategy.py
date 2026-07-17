"""iios/execution/gateway/routing/routing_strategy.py
==================================================
RoutingStrategySelector — applies a selection algorithm to
policy-filtered candidates.

Strategies operate on the list returned by a RoutingPolicy.evaluate()
call and return at most one RoutingCandidate.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

import random
from typing import List, Optional

from .constants import RoutingStrategyType
from .routing_candidate import RoutingCandidate
from .routing_context import RoutingContext


class RoutingStrategySelector:
    """
    Stateless selector that converts a candidate list into a
    single selection according to the requested strategy.
    """

    # No instance state — all methods could be static; kept as instance
    # methods for consistent interface and future extensibility.

    def select(
        self,
        candidates:    List[RoutingCandidate],
        context:       RoutingContext,
        strategy_type: RoutingStrategyType,
    ) -> Optional[RoutingCandidate]:
        """
        Select one candidate according to *strategy_type*.

        Returns None if no suitable candidate is found.
        """
        if not candidates:
            return None

        if strategy_type == RoutingStrategyType.SINGLE_DESTINATION:
            return self._single(candidates)
        if strategy_type == RoutingStrategyType.PRIORITY_SELECTION:
            return self._priority(candidates)
        if strategy_type == RoutingStrategyType.WEIGHTED_SELECTION:
            return self._weighted(candidates)
        if strategy_type == RoutingStrategyType.CAPABILITY_MATCHING:
            return self._capability_match(candidates, context)
        if strategy_type == RoutingStrategyType.HEALTH_OPTIMIZED:
            return self._health_optimized(candidates)
        if strategy_type == RoutingStrategyType.FALLBACK_STRATEGY:
            return self._fallback(candidates)

        # Unknown strategy — fall back to single
        return self._single(candidates)

    # ── Concrete strategies ───────────────────────────────────────────────────

    def _single(self, candidates: List[RoutingCandidate]) -> Optional[RoutingCandidate]:
        """Return the first candidate as-is."""
        return candidates[0] if candidates else None

    def _priority(self, candidates: List[RoutingCandidate]) -> Optional[RoutingCandidate]:
        """Return the candidate with the highest routing_priority."""
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.routing_priority)

    def _weighted(self, candidates: List[RoutingCandidate]) -> Optional[RoutingCandidate]:
        """
        Select probabilistically by weight.

        Falls back to _priority when all weights are zero.
        """
        if not candidates:
            return None
        weights = [c.weight for c in candidates]
        if sum(weights) <= 0.0:
            return self._priority(candidates)
        chosen = random.choices(candidates, weights=weights, k=1)
        return chosen[0]

    def _capability_match(
        self,
        candidates: List[RoutingCandidate],
        context:    RoutingContext,
    ) -> Optional[RoutingCandidate]:
        """
        Select the candidate that supports the most required
        capabilities from the context.  Ties broken by priority.
        """
        if not candidates:
            return None
        required = context.required_capabilities
        if not required:
            return self._priority(candidates)

        def _score(c: RoutingCandidate) -> tuple:
            matched = sum(1 for cap in required if c.supports_capability(cap))
            return (matched, c.routing_priority)

        return max(candidates, key=_score)

    def _health_optimized(
        self, candidates: List[RoutingCandidate]
    ) -> Optional[RoutingCandidate]:
        """Return the candidate with the highest health_score."""
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.health_score)

    def _fallback(self, candidates: List[RoutingCandidate]) -> Optional[RoutingCandidate]:
        """
        Return the first available candidate.  The policy is expected
        to have ordered candidates with the most preferred first.
        """
        available = [c for c in candidates if c.is_available]
        if available:
            return available[0]
        return candidates[0] if candidates else None
