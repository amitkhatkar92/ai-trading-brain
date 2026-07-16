"""iios/execution/brokers/broker_statistics.py
==================================================
Statistics dataclasses for the Broker Abstraction Layer.

BrokerStatistics  — per-broker operation counters and timing.
RegistryStatistics — aggregate across all registered brokers.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


# ── Per-broker statistics ─────────────────────────────────────────────────────

@dataclass
class BrokerStatistics:
    """Mutable statistics for a single broker."""

    broker_id:         str
    created_at:        float = field(default_factory=time.time)

    # Connection
    connection_count:     int = 0
    disconnection_count:  int = 0

    # Requests by type
    order_requests:       int = 0
    modify_requests:      int = 0
    cancel_requests:      int = 0
    position_requests:    int = 0
    balance_requests:     int = 0
    heartbeat_count:      int = 0
    health_check_count:   int = 0

    # Outcomes
    successful_requests:  int = 0
    failed_requests:      int = 0

    # Timing (milliseconds)
    _total_duration_ms:  float = field(default=0.0, repr=False)
    _request_count:      int   = field(default=0,   repr=False)

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record_request(
        self,
        request_type: str,
        *,
        succeeded:   bool  = True,
        duration_ms: float = 0.0,
    ) -> None:
        with self._lock:
            rt = request_type.upper()
            if rt == "ORDER":
                self.order_requests += 1
            elif rt == "MODIFY":
                self.modify_requests += 1
            elif rt == "CANCEL":
                self.cancel_requests += 1
            elif rt == "POSITION":
                self.position_requests += 1
            elif rt == "BALANCE":
                self.balance_requests += 1
            elif rt == "HEARTBEAT":
                self.heartbeat_count += 1
            elif rt == "HEALTH":
                self.health_check_count += 1

            if succeeded:
                self.successful_requests += 1
            else:
                self.failed_requests += 1

            self._total_duration_ms += duration_ms
            self._request_count     += 1

    def record_connection(self) -> None:
        with self._lock:
            self.connection_count += 1

    def record_disconnection(self) -> None:
        with self._lock:
            self.disconnection_count += 1

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def total_requests(self) -> int:
        return self.successful_requests + self.failed_requests

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def avg_response_ms(self) -> float:
        if self._request_count == 0:
            return 0.0
        return self._total_duration_ms / self._request_count

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":          self.broker_id,
            "created_at":         self.created_at,
            "connection_count":   self.connection_count,
            "total_requests":     self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests":    self.failed_requests,
            "success_rate":       round(self.success_rate, 4),
            "avg_response_ms":    round(self.avg_response_ms, 2),
            "order_requests":     self.order_requests,
            "modify_requests":    self.modify_requests,
            "cancel_requests":    self.cancel_requests,
            "position_requests":  self.position_requests,
            "balance_requests":   self.balance_requests,
            "heartbeat_count":    self.heartbeat_count,
            "health_check_count": self.health_check_count,
        }

    def __repr__(self) -> str:
        return (
            f"BrokerStatistics(broker={self.broker_id!r}, "
            f"requests={self.total_requests}, "
            f"success_rate={self.success_rate:.0%})"
        )


# ── Registry-level aggregate statistics ───────────────────────────────────────

@dataclass
class RegistryStatistics:
    """Aggregate statistics across all registered brokers."""

    total_registered:  int
    connected_count:   int
    healthy_count:     int
    capacity:          int
    utilisation_pct:   float

    total_requests:    int
    successful_requests: int
    failed_requests:   int
    avg_response_ms:   float

    broker_stats:      list[dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_registered":   self.total_registered,
            "connected_count":    self.connected_count,
            "healthy_count":      self.healthy_count,
            "capacity":           self.capacity,
            "utilisation_pct":    round(self.utilisation_pct, 2),
            "total_requests":     self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests":    self.failed_requests,
            "success_rate":       round(self.success_rate, 4),
            "avg_response_ms":    round(self.avg_response_ms, 2),
        }
