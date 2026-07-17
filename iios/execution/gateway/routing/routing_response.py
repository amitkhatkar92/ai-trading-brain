"""iios/execution/gateway/routing/routing_response.py
==================================================
RoutingDecision — immutable outcome of a routing evaluation.

The RoutingDecision carries the selected broker ID plus full
audit metadata: policy used, strategy applied, candidates
evaluated, failover status, and timing.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    FAILED_OUTCOMES,
    ROUTED_OUTCOMES,
    RoutingOutcome,
    RoutingStrategyType,
    VERSION,
)


@dataclass(frozen=True)
class RoutingDecision:
    """
    Immutable result of a single routing evaluation.

    Fields
    ------
    decision_id:
        Unique ID for this decision.
    request_id:
        Correlates back to RoutingRequest.request_id.
    routing_id:
        Correlates back to RoutingContext.routing_id.
    selected_broker_id:
        ID of the chosen broker; None when routing fails.
    selected_broker_name:
        Name of the chosen broker; None when routing fails.
    policy_id:
        The policy that was applied; None if no policy was used.
    strategy:
        The selection strategy that produced the decision.
    outcome:
        Categorical routing outcome.
    failover_used:
        True when the selected broker is a failover, not the primary.
    candidates_evaluated:
        Number of candidates that passed policy filtering.
    candidates_available:
        Number of candidates that were connected and authenticated.
    rejection_reasons:
        Reasons why candidates were rejected by the policy.
    routing_time_ms:
        Wall time from routing start to decision.
    decided_at:
        Unix timestamp when the decision was recorded.
    version:
        Routing Framework version string.
    metadata:
        Arbitrary key-value pairs.
    """

    decision_id:          str
    request_id:           str
    routing_id:           str
    selected_broker_id:   Optional[str]
    selected_broker_name: Optional[str]
    policy_id:            Optional[str]
    strategy:             Optional[RoutingStrategyType]
    outcome:              RoutingOutcome
    failover_used:        bool
    candidates_evaluated: int
    candidates_available: int
    rejection_reasons:    Tuple[str, ...]
    routing_time_ms:      float
    decided_at:           float
    version:              str                = VERSION
    metadata:             Dict[str, Any]     = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_routed(self) -> bool:
        return self.outcome in ROUTED_OUTCOMES

    @property
    def is_failed(self) -> bool:
        return self.outcome in FAILED_OUTCOMES

    @property
    def is_failover(self) -> bool:
        return self.outcome == RoutingOutcome.FAILOVER_ROUTED

    @property
    def has_selection(self) -> bool:
        return self.selected_broker_id is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":          self.decision_id,
            "request_id":           self.request_id,
            "routing_id":           self.routing_id,
            "selected_broker_id":   self.selected_broker_id,
            "selected_broker_name": self.selected_broker_name,
            "policy_id":            self.policy_id,
            "strategy":             self.strategy.value if self.strategy else None,
            "outcome":              self.outcome.value,
            "is_routed":            self.is_routed,
            "failover_used":        self.failover_used,
            "candidates_evaluated": self.candidates_evaluated,
            "candidates_available": self.candidates_available,
            "rejection_reasons":    list(self.rejection_reasons),
            "routing_time_ms":      self.routing_time_ms,
            "decided_at":           self.decided_at,
            "version":              self.version,
            "metadata":             dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"RoutingDecision("
            f"outcome={self.outcome.value!r}, "
            f"broker={self.selected_broker_id!r}, "
            f"routing_time_ms={self.routing_time_ms:.1f}"
            f")"
        )


# ── Factory functions ─────────────────────────────────────────────────────────

def make_routed_decision(
    request_id:           str,
    routing_id:           str,
    selected_broker_id:   str,
    selected_broker_name: str,
    *,
    policy_id:            Optional[str] = None,
    strategy:             Optional[RoutingStrategyType] = None,
    failover_used:        bool = False,
    candidates_evaluated: int = 0,
    candidates_available: int = 0,
    routing_time_ms:      float = 0.0,
    metadata:             Optional[Dict[str, Any]] = None,
) -> RoutingDecision:
    """Create a successful RoutingDecision."""
    outcome = RoutingOutcome.FAILOVER_ROUTED if failover_used else RoutingOutcome.ROUTED
    return RoutingDecision(
        decision_id=str(uuid.uuid4()),
        request_id=request_id,
        routing_id=routing_id,
        selected_broker_id=selected_broker_id,
        selected_broker_name=selected_broker_name,
        policy_id=policy_id,
        strategy=strategy,
        outcome=outcome,
        failover_used=failover_used,
        candidates_evaluated=candidates_evaluated,
        candidates_available=candidates_available,
        rejection_reasons=(),
        routing_time_ms=max(0.0, routing_time_ms),
        decided_at=time.time(),
        metadata=dict(metadata or {}),
    )


def make_failed_decision(
    request_id:           str,
    routing_id:           str,
    outcome:              RoutingOutcome,
    *,
    policy_id:            Optional[str] = None,
    strategy:             Optional[RoutingStrategyType] = None,
    candidates_evaluated: int = 0,
    candidates_available: int = 0,
    rejection_reasons:    Tuple[str, ...] = (),
    routing_time_ms:      float = 0.0,
    metadata:             Optional[Dict[str, Any]] = None,
) -> RoutingDecision:
    """Create a failed RoutingDecision."""
    return RoutingDecision(
        decision_id=str(uuid.uuid4()),
        request_id=request_id,
        routing_id=routing_id,
        selected_broker_id=None,
        selected_broker_name=None,
        policy_id=policy_id,
        strategy=strategy,
        outcome=outcome,
        failover_used=False,
        candidates_evaluated=candidates_evaluated,
        candidates_available=candidates_available,
        rejection_reasons=rejection_reasons,
        routing_time_ms=max(0.0, routing_time_ms),
        decided_at=time.time(),
        metadata=dict(metadata or {}),
    )
