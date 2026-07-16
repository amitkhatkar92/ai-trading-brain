"""iios/execution/oms/order_router/routing_result.py
==================================================
RoutingResult — full record of a completed routing operation.

Wraps RoutingDecision + full candidate list + diagnostics.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.order_router.routing_candidate import RoutingCandidate
from iios.execution.oms.order_router.routing_decision import RoutingDecision


@dataclass(frozen=True)
class RoutingResult:
    """
    Complete record of a routing operation.

    Contains the final RoutingDecision plus the full list of
    evaluated candidates for audit and diagnostics.
    """
    result_id:  str = field(default_factory=lambda: str(uuid.uuid4()))
    decision:   RoutingDecision = field(default_factory=RoutingDecision)
    request_id: str = ""
    order_id:   str = ""
    policy_type: str = ""
    elapsed_ms: float = 0.0
    candidates:  tuple[RoutingCandidate, ...] = field(default_factory=tuple)
    evaluated_at: float = field(default_factory=time.time)
    metadata:   dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.decision.succeeded

    @property
    def selected_broker_id(self) -> str:
        return self.decision.selected_broker_id

    @property
    def selected_exchange(self) -> str:
        return self.decision.selected_exchange

    @property
    def rejection_reason(self) -> str:
        return self.decision.rejection_reason

    def eligible_candidates(self) -> list[RoutingCandidate]:
        return [c for c in self.candidates if c.is_eligible]

    def discarded_candidates(self) -> list[RoutingCandidate]:
        return [c for c in self.candidates if not c.is_eligible]

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":    self.result_id,
            "request_id":   self.request_id,
            "order_id":     self.order_id,
            "policy_type":  self.policy_type,
            "elapsed_ms":   round(self.elapsed_ms, 3),
            "succeeded":    self.succeeded,
            "decision":     self.decision.to_dict(),
            "candidates":   [c.to_dict() for c in self.candidates],
            "evaluated_at": self.evaluated_at,
        }
