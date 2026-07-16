"""iios/execution/oms/order_router/routing_candidate.py
==================================================
RoutingCandidate — a broker/exchange pair being evaluated.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.order_router.constants import CandidateScoreField
from iios.execution.oms.order_router.routing_context import BrokerCapabilities


@dataclass
class RoutingCandidate:
    """
    Represents a single broker/exchange pair under consideration.

    Scores accumulate as each routing rule evaluates the candidate.
    """
    broker_id:     str   = ""
    exchange:      str   = ""
    score:         float = 0.0
    is_eligible:   bool  = True
    discard_reason: str  = ""
    score_breakdown: dict[CandidateScoreField, float] = field(default_factory=dict)
    capabilities:  BrokerCapabilities | None = field(default=None, compare=False)
    metadata:      dict[str, Any] = field(default_factory=dict)

    def add_score(self, field: CandidateScoreField, value: float) -> None:
        """Accumulate a partial score from a routing rule."""
        self.score_breakdown[field] = self.score_breakdown.get(field, 0.0) + value
        self.score += value

    def discard(self, reason: str) -> None:
        """Mark this candidate as ineligible."""
        self.is_eligible   = False
        self.discard_reason = reason
        self.score         = 0.0
        self.score_breakdown.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":      self.broker_id,
            "exchange":       self.exchange,
            "score":          round(self.score, 6),
            "is_eligible":    self.is_eligible,
            "discard_reason": self.discard_reason,
            "score_breakdown": {k.value: round(v, 6) for k, v in self.score_breakdown.items()},
        }
