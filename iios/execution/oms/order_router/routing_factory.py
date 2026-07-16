"""iios/execution/oms/order_router/routing_factory.py
==================================================
RoutingFactory — creates RoutingDecision and RoutingResult objects.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

import time
from typing import Any, Optional

from iios.execution.oms.order_router.constants import FACTORY_SYSTEM_ID
from iios.execution.oms.order_router.routing_candidate import RoutingCandidate
from iios.execution.oms.order_router.routing_context import RoutingContext
from iios.execution.oms.order_router.routing_decision import RoutingDecision
from iios.execution.oms.order_router.routing_result import RoutingResult


class RoutingFactory:
    """
    Stateless factory for RoutingDecision and RoutingResult.
    """

    __slots__ = ("_system_id",)

    def __init__(self) -> None:
        self._system_id = FACTORY_SYSTEM_ID

    def make_success_decision(
        self,
        *,
        order_id:          str,
        broker_id:         str,
        exchange:          str,
        policy_applied:    str,
        score:             float,
        candidates_total:  int,
        routing_time_ms:   float,
        request_id:        str,
        metadata:          dict[str, Any] | None = None,
    ) -> RoutingDecision:
        return RoutingDecision(
            order_id            = order_id,
            selected_broker_id  = broker_id,
            selected_exchange   = exchange,
            policy_applied      = policy_applied,
            score               = score,
            candidates_evaluated = candidates_total,
            routing_time_ms     = routing_time_ms,
            routing_request_id  = request_id,
            succeeded           = True,
            rejection_reason    = "",
            metadata            = metadata or {},
        )

    def make_rejected_decision(
        self,
        *,
        order_id:         str,
        reason:           str,
        policy_applied:   str,
        candidates_total: int,
        routing_time_ms:  float,
        request_id:       str,
        metadata:         dict[str, Any] | None = None,
    ) -> RoutingDecision:
        return RoutingDecision(
            order_id            = order_id,
            selected_broker_id  = "",
            selected_exchange   = "",
            policy_applied      = policy_applied,
            score               = 0.0,
            candidates_evaluated = candidates_total,
            routing_time_ms     = routing_time_ms,
            routing_request_id  = request_id,
            succeeded           = False,
            rejection_reason    = reason,
            metadata            = metadata or {},
        )

    def make_result(
        self,
        *,
        decision:    RoutingDecision,
        request_id:  str,
        order_id:    str,
        policy_type: str,
        elapsed_ms:  float,
        candidates:  list[RoutingCandidate],
        metadata:    dict[str, Any] | None = None,
    ) -> RoutingResult:
        return RoutingResult(
            decision    = decision,
            request_id  = request_id,
            order_id    = order_id,
            policy_type = policy_type,
            elapsed_ms  = elapsed_ms,
            candidates  = tuple(candidates),
            metadata    = metadata or {},
        )
