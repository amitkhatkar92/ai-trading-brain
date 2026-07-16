"""iios/execution/oms/order_router/routing_statistics.py
==================================================
RoutingStatistics — thread-safe counters for the Order Router.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.order_router.constants import RoutingPolicyType


@dataclass
class RoutingStatistics:
    """Thread-safe statistics for the Order Router."""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    _total_requests:   int   = 0
    _successful:       int   = 0
    _rejected:         int   = 0
    _failed:           int   = 0
    _expired:          int   = 0
    _total_time_ms:    float = 0.0
    _min_time_ms:      float = float("inf")
    _max_time_ms:      float = 0.0
    _policy_counts:    dict[str, int]   = field(default_factory=dict)
    _broker_counts:    dict[str, int]   = field(default_factory=dict)
    _created_at:       float = field(default_factory=time.time)
    _last_updated_at:  float = field(default_factory=time.time)

    # ── Mutators ──────────────────────────────────────────────────────────────

    def record_request(self) -> None:
        with self._lock:
            self._total_requests += 1
            self._last_updated_at = time.time()

    def record_success(
        self,
        routing_time_ms: float,
        policy: str = "",
        broker_id: str = "",
    ) -> None:
        with self._lock:
            self._successful += 1
            self._total_time_ms += routing_time_ms
            if routing_time_ms < self._min_time_ms:
                self._min_time_ms = routing_time_ms
            if routing_time_ms > self._max_time_ms:
                self._max_time_ms = routing_time_ms
            if policy:
                self._policy_counts[policy] = self._policy_counts.get(policy, 0) + 1
            if broker_id:
                self._broker_counts[broker_id] = self._broker_counts.get(broker_id, 0) + 1
            self._last_updated_at = time.time()

    def record_rejection(self, routing_time_ms: float = 0.0) -> None:
        with self._lock:
            self._rejected += 1
            self._total_time_ms += routing_time_ms
            self._last_updated_at = time.time()

    def record_failure(self) -> None:
        with self._lock:
            self._failed += 1
            self._last_updated_at = time.time()

    def record_expiry(self) -> None:
        with self._lock:
            self._expired += 1
            self._last_updated_at = time.time()

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def total_requests(self) -> int:
        with self._lock:
            return self._total_requests

    @property
    def successful(self) -> int:
        with self._lock:
            return self._successful

    @property
    def rejected(self) -> int:
        with self._lock:
            return self._rejected

    @property
    def failed(self) -> int:
        with self._lock:
            return self._failed

    @property
    def expired(self) -> int:
        with self._lock:
            return self._expired

    @property
    def avg_routing_time_ms(self) -> float:
        with self._lock:
            if self._successful + self._rejected == 0:
                return 0.0
            return self._total_time_ms / (self._successful + self._rejected)

    @property
    def min_routing_time_ms(self) -> float:
        with self._lock:
            return 0.0 if self._min_time_ms == float("inf") else self._min_time_ms

    @property
    def max_routing_time_ms(self) -> float:
        with self._lock:
            return self._max_time_ms

    def policy_usage(self) -> dict[str, int]:
        with self._lock:
            return dict(self._policy_counts)

    def broker_distribution(self) -> dict[str, int]:
        with self._lock:
            return dict(self._broker_counts)

    def reset(self) -> None:
        with self._lock:
            self._total_requests  = 0
            self._successful      = 0
            self._rejected        = 0
            self._failed          = 0
            self._expired         = 0
            self._total_time_ms   = 0.0
            self._min_time_ms     = float("inf")
            self._max_time_ms     = 0.0
            self._policy_counts   = {}
            self._broker_counts   = {}
            self._last_updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_requests":     self._total_requests,
                "successful":         self._successful,
                "rejected":           self._rejected,
                "failed":             self._failed,
                "expired":            self._expired,
                "avg_routing_time_ms": (
                    self._total_time_ms / (self._successful + self._rejected)
                    if (self._successful + self._rejected) > 0 else 0.0
                ),
                "min_routing_time_ms": 0.0 if self._min_time_ms == float("inf") else self._min_time_ms,
                "max_routing_time_ms": self._max_time_ms,
                "policy_usage":        dict(self._policy_counts),
                "broker_distribution": dict(self._broker_counts),
                "created_at":          self._created_at,
                "last_updated_at":     self._last_updated_at,
            }
