"""iios/execution/oms/order_router/routing_events.py
==================================================
Routing events — frozen dataclasses emitted during routing.

Events: RoutingStarted, CandidateEvaluated, RouteSelected,
         RoutingRejected, RoutingCompleted

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.order_router.constants import RoutingEventType


@dataclass(frozen=True)
class RoutingEvent:
    """Base routing event."""
    event_id:    str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:  RoutingEventType = RoutingEventType.ROUTING_STARTED
    order_id:    str  = ""
    request_id:  str  = ""
    occurred_at: float = field(default_factory=time.time)
    actor:       str  = "iios:execution:oms:order_router"
    metadata:    dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "order_id":    self.order_id,
            "request_id":  self.request_id,
            "occurred_at": self.occurred_at,
            "actor":       self.actor,
        }


def make_routing_started(order_id: str, request_id: str, policy: str = "") -> RoutingEvent:
    return RoutingEvent(
        event_type=RoutingEventType.ROUTING_STARTED,
        order_id=order_id,
        request_id=request_id,
        metadata={"policy": policy},
    )


def make_candidate_evaluated(
    order_id: str,
    request_id: str,
    broker_id: str,
    score: float,
    eligible: bool,
    discard_reason: str = "",
) -> RoutingEvent:
    return RoutingEvent(
        event_type=RoutingEventType.CANDIDATE_EVALUATED,
        order_id=order_id,
        request_id=request_id,
        metadata={
            "broker_id":      broker_id,
            "score":          score,
            "eligible":       eligible,
            "discard_reason": discard_reason,
        },
    )


def make_route_selected(
    order_id: str,
    request_id: str,
    decision_id: str,
    broker_id: str,
    exchange: str,
    score: float,
) -> RoutingEvent:
    return RoutingEvent(
        event_type=RoutingEventType.ROUTE_SELECTED,
        order_id=order_id,
        request_id=request_id,
        metadata={
            "decision_id": decision_id,
            "broker_id":   broker_id,
            "exchange":    exchange,
            "score":       score,
        },
    )


def make_routing_rejected(
    order_id: str,
    request_id: str,
    reason: str,
    decision_id: str = "",
) -> RoutingEvent:
    return RoutingEvent(
        event_type=RoutingEventType.ROUTING_REJECTED,
        order_id=order_id,
        request_id=request_id,
        metadata={"reason": reason, "decision_id": decision_id},
    )


def make_routing_completed(
    order_id: str,
    request_id: str,
    succeeded: bool,
    routing_time_ms: float,
    candidates_evaluated: int,
) -> RoutingEvent:
    return RoutingEvent(
        event_type=RoutingEventType.ROUTING_COMPLETED,
        order_id=order_id,
        request_id=request_id,
        metadata={
            "succeeded":            succeeded,
            "routing_time_ms":      routing_time_ms,
            "candidates_evaluated": candidates_evaluated,
        },
    )
