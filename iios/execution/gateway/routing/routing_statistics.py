"""iios/execution/gateway/routing/routing_statistics.py
==================================================
RoutingStatistics — lightweight accumulator for routing metrics.

Thread safety is NOT embedded here — the caller (RoutingManager)
serialises writes behind its own lock.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RoutingStatistics:
    """
    Mutable accumulator of routing performance data.

    Intended to be owned by RoutingManager.  All mutators must be
    called under the manager's internal lock.
    """

    routing_requests:      int   = 0
    successful_routes:     int   = 0
    failed_routes:         int   = 0
    failovers:             int   = 0
    total_routing_time_ms: float = 0.0
    policy_usage:          Dict[str, int] = field(default_factory=dict)
    broker_utilization:    Dict[str, int] = field(default_factory=dict)
    last_updated_at:       float          = field(default_factory=time.time)

    # ── Mutators ──────────────────────────────────────────────────────────────

    def record_routing(
        self,
        *,
        is_success:      bool,
        routing_time_ms: float,
        policy_id:       Optional[str] = None,
    ) -> None:
        self.routing_requests      += 1
        self.total_routing_time_ms += max(0.0, routing_time_ms)
        if is_success:
            self.successful_routes += 1
        else:
            self.failed_routes += 1
        if policy_id:
            self.record_policy_usage(policy_id)
        self.last_updated_at = time.time()

    def record_failover(self) -> None:
        self.failovers           += 1
        self.last_updated_at      = time.time()

    def record_broker_utilization(self, broker_id: str) -> None:
        self.broker_utilization[broker_id] = (
            self.broker_utilization.get(broker_id, 0) + 1
        )
        self.last_updated_at = time.time()

    def record_policy_usage(self, policy_id: str) -> None:
        self.policy_usage[policy_id] = self.policy_usage.get(policy_id, 0) + 1
        self.last_updated_at         = time.time()

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def success_rate(self) -> float:
        if self.routing_requests == 0:
            return 0.0
        return self.successful_routes / self.routing_requests

    @property
    def failure_rate(self) -> float:
        if self.routing_requests == 0:
            return 0.0
        return self.failed_routes / self.routing_requests

    @property
    def average_routing_time_ms(self) -> float:
        if self.routing_requests == 0:
            return 0.0
        return self.total_routing_time_ms / self.routing_requests

    @property
    def failover_rate(self) -> float:
        if self.successful_routes == 0:
            return 0.0
        return self.failovers / self.successful_routes

    # ── Utilities ─────────────────────────────────────────────────────────────

    def reset(self) -> None:
        self.routing_requests      = 0
        self.successful_routes     = 0
        self.failed_routes         = 0
        self.failovers             = 0
        self.total_routing_time_ms = 0.0
        self.policy_usage          = {}
        self.broker_utilization    = {}
        self.last_updated_at       = time.time()

    def copy(self) -> "RoutingStatistics":
        return RoutingStatistics(
            routing_requests=self.routing_requests,
            successful_routes=self.successful_routes,
            failed_routes=self.failed_routes,
            failovers=self.failovers,
            total_routing_time_ms=self.total_routing_time_ms,
            policy_usage=dict(self.policy_usage),
            broker_utilization=dict(self.broker_utilization),
            last_updated_at=self.last_updated_at,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "routing_requests":       self.routing_requests,
            "successful_routes":      self.successful_routes,
            "failed_routes":          self.failed_routes,
            "failovers":              self.failovers,
            "total_routing_time_ms":  self.total_routing_time_ms,
            "average_routing_time_ms": self.average_routing_time_ms,
            "success_rate":           self.success_rate,
            "failure_rate":           self.failure_rate,
            "failover_rate":          self.failover_rate,
            "policy_usage":           dict(self.policy_usage),
            "broker_utilization":     dict(self.broker_utilization),
            "last_updated_at":        self.last_updated_at,
        }
