"""iios/execution/gateway/routing/routing_selector.py
==================================================
RoutingSelector — combines policy evaluation with strategy selection
to produce a final candidate choice and rejection record.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from .constants import RoutingStrategyType
from .routing_candidate import RoutingCandidate
from .routing_context import RoutingContext
from .routing_policy import RoutingPolicyBase
from .routing_strategy import RoutingStrategySelector


class RoutingSelector:
    """
    Stateless component that combines policy + strategy into one call.

    The caller is responsible for supplying an already-filtered
    `available_candidates` list (connected, authenticated, non-blacklisted).
    """

    def __init__(self) -> None:
        self._strategy_selector = RoutingStrategySelector()

    def select(
        self,
        available_candidates: List[RoutingCandidate],
        context:              RoutingContext,
        policy:               Optional[RoutingPolicyBase],
        strategy:             RoutingStrategyType,
    ) -> Tuple[Optional[RoutingCandidate], List[str]]:
        """
        Run policy filtering followed by strategy selection.

        Parameters
        ----------
        available_candidates:
            Candidates that are currently available (connected,
            authenticated, not blacklisted).
        context:
            The routing context for this request.
        policy:
            Policy to apply.  If None, all available candidates are used.
        strategy:
            Strategy to apply after policy filtering.

        Returns
        -------
        (selected, rejection_reasons):
            selected — the chosen RoutingCandidate, or None.
            rejection_reasons — why candidate(s) were rejected.
        """
        rejection_reasons: List[str] = []

        # ── Apply policy ──────────────────────────────────────────────────────
        if policy is not None:
            filtered = policy.evaluate(available_candidates, context)
            rejected_ids = (
                {c.broker_id for c in available_candidates}
                - {c.broker_id for c in filtered}
            )
            for bid in sorted(rejected_ids):
                rejection_reasons.append(
                    f"broker '{bid}' rejected by policy '{policy.policy_id}'"
                )
        else:
            filtered = list(available_candidates)

        if not filtered:
            if not available_candidates:
                rejection_reasons.append("no candidates are available")
            else:
                rejection_reasons.append(
                    "all candidates were rejected by the routing policy"
                )
            return None, rejection_reasons

        # ── Apply strategy ────────────────────────────────────────────────────
        selected = self._strategy_selector.select(filtered, context, strategy)

        if selected is None:
            rejection_reasons.append(
                f"strategy '{strategy.value}' could not select from "
                f"{len(filtered)} candidate(s)"
            )

        return selected, rejection_reasons

    def select_fallback(
        self,
        candidates: List[RoutingCandidate],
        context:    RoutingContext,
    ) -> Optional[RoutingCandidate]:
        """
        Emergency fallback selection from the full candidate pool.

        Used when the primary policy+strategy path produced no selection
        and the policy supports failover.
        """
        # Prefer highest priority available
        available = [c for c in candidates if c.is_available]
        if not available:
            return None
        return max(available, key=lambda c: (c.routing_priority, c.health_score))
