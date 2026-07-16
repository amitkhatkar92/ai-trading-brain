"""iios/execution/oms/order_router/routing_decision.py
==================================================
RoutingDecision — immutable primary output of the Order Router.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RoutingDecision:
    """
    Immutable result of a routing operation.

    succeeded=True  → selected_broker_id/selected_exchange are valid
    succeeded=False → rejection_reason explains why routing failed
    """
    decision_id:         str   = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:            str   = ""
    selected_broker_id:  str   = ""
    selected_exchange:   str   = ""
    policy_applied:      str   = ""
    score:               float = 0.0
    candidates_evaluated: int  = 0
    routing_time_ms:     float = 0.0
    routing_request_id:  str   = ""
    decided_at:          float = field(default_factory=time.time)
    succeeded:           bool  = False
    rejection_reason:    str   = ""
    metadata:            dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id":          self.decision_id,
            "order_id":             self.order_id,
            "selected_broker_id":   self.selected_broker_id,
            "selected_exchange":    self.selected_exchange,
            "policy_applied":       self.policy_applied,
            "score":                round(self.score, 6),
            "candidates_evaluated": self.candidates_evaluated,
            "routing_time_ms":      round(self.routing_time_ms, 3),
            "routing_request_id":   self.routing_request_id,
            "decided_at":           self.decided_at,
            "succeeded":            self.succeeded,
            "rejection_reason":     self.rejection_reason,
        }
