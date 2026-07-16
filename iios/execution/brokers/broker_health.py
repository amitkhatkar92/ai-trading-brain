"""iios/execution/brokers/broker_health.py
==================================================
BrokerHealthRecord and BrokerHealthMonitor — tracks health status
for every registered broker.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.brokers.constants import (
    BrokerConnectionState,
    BrokerHealthStatus,
)
from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__, engine_id="iios:execution:brokers:health")


# ── Health record ─────────────────────────────────────────────────────────────

@dataclass
class BrokerHealthRecord:
    """Mutable health snapshot for a single broker."""

    broker_id:        str
    status:           BrokerHealthStatus    = BrokerHealthStatus.UNKNOWN
    connection_state: BrokerConnectionState = BrokerConnectionState.DISCONNECTED

    last_checked_at:  float = 0.0
    last_healthy_at:  float = 0.0
    last_unhealthy_at: float = 0.0

    check_count:     int   = 0
    healthy_count:   int   = 0
    unhealthy_count: int   = 0
    consecutive_failures: int = 0

    last_latency_ms: float = 0.0
    avg_latency_ms:  float = 0.0
    _latency_sum:    float = field(default=0.0, repr=False)

    error_message: str = ""
    record_id:     str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def is_healthy(self) -> bool:
        return self.status == BrokerHealthStatus.HEALTHY

    @property
    def is_connected(self) -> bool:
        return self.connection_state == BrokerConnectionState.CONNECTED

    @property
    def health_rate(self) -> float:
        if self.check_count == 0:
            return 0.0
        return self.healthy_count / self.check_count

    def record_healthy(self, latency_ms: float = 0.0) -> None:
        now = time.time()
        self.status           = BrokerHealthStatus.HEALTHY
        self.last_checked_at  = now
        self.last_healthy_at  = now
        self.check_count      += 1
        self.healthy_count    += 1
        self.consecutive_failures = 0
        self.last_latency_ms  = latency_ms
        self._latency_sum     += latency_ms
        self.avg_latency_ms   = self._latency_sum / self.check_count
        self.error_message    = ""

    def record_unhealthy(self, error_message: str = "") -> None:
        now = time.time()
        self.status           = BrokerHealthStatus.UNHEALTHY
        self.last_checked_at  = now
        self.last_unhealthy_at = now
        self.check_count      += 1
        self.unhealthy_count  += 1
        self.consecutive_failures += 1
        self.error_message    = error_message

    def record_degraded(self, latency_ms: float = 0.0) -> None:
        now = time.time()
        self.status          = BrokerHealthStatus.DEGRADED
        self.last_checked_at = now
        self.check_count     += 1
        self.last_latency_ms = latency_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":            self.broker_id,
            "status":               self.status.value,
            "connection_state":     self.connection_state.value,
            "is_healthy":           self.is_healthy,
            "is_connected":         self.is_connected,
            "health_rate":          round(self.health_rate, 4),
            "check_count":          self.check_count,
            "healthy_count":        self.healthy_count,
            "unhealthy_count":      self.unhealthy_count,
            "consecutive_failures": self.consecutive_failures,
            "last_latency_ms":      self.last_latency_ms,
            "avg_latency_ms":       round(self.avg_latency_ms, 2),
            "last_checked_at":      self.last_checked_at,
            "last_healthy_at":      self.last_healthy_at,
            "last_unhealthy_at":    self.last_unhealthy_at,
            "error_message":        self.error_message,
        }

    def __repr__(self) -> str:
        return (
            f"BrokerHealthRecord(broker={self.broker_id!r}, "
            f"status={self.status.value}, rate={self.health_rate:.0%})"
        )


# ── Health monitor ────────────────────────────────────────────────────────────

class BrokerHealthMonitor:
    """
    Thread-safe store of BrokerHealthRecord objects.

    Maintains one record per registered broker and provides
    aggregate health summaries.
    """

    def __init__(self) -> None:
        self._records: dict[str, BrokerHealthRecord] = {}
        self._lock    = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def register(self, broker_id: str) -> None:
        with self._lock:
            if broker_id not in self._records:
                self._records[broker_id] = BrokerHealthRecord(broker_id=broker_id)
                _log.info("Health monitor: registered broker.", broker_id=broker_id)

    def unregister(self, broker_id: str) -> None:
        with self._lock:
            self._records.pop(broker_id, None)

    # ── Updates ───────────────────────────────────────────────────────────────

    def record_healthy(self, broker_id: str, latency_ms: float = 0.0) -> None:
        with self._lock:
            if broker_id in self._records:
                self._records[broker_id].record_healthy(latency_ms)

    def record_unhealthy(self, broker_id: str, error_message: str = "") -> None:
        with self._lock:
            if broker_id in self._records:
                self._records[broker_id].record_unhealthy(error_message)

    def record_degraded(self, broker_id: str, latency_ms: float = 0.0) -> None:
        with self._lock:
            if broker_id in self._records:
                self._records[broker_id].record_degraded(latency_ms)

    def set_connection_state(
        self,
        broker_id: str,
        state:     BrokerConnectionState,
    ) -> None:
        with self._lock:
            if broker_id in self._records:
                self._records[broker_id].connection_state = state

    # ── Queries ───────────────────────────────────────────────────────────────

    def get(self, broker_id: str) -> BrokerHealthRecord | None:
        with self._lock:
            return self._records.get(broker_id)

    def all_records(self) -> list[BrokerHealthRecord]:
        with self._lock:
            return list(self._records.values())

    def healthy_broker_ids(self) -> list[str]:
        with self._lock:
            return [bid for bid, r in self._records.items() if r.is_healthy]

    def unhealthy_broker_ids(self) -> list[str]:
        with self._lock:
            return [
                bid for bid, r in self._records.items()
                if r.status == BrokerHealthStatus.UNHEALTHY
            ]

    @property
    def overall_status(self) -> BrokerHealthStatus:
        with self._lock:
            if not self._records:
                return BrokerHealthStatus.UNKNOWN
            statuses = {r.status for r in self._records.values()}
            if all(s == BrokerHealthStatus.HEALTHY for s in statuses):
                return BrokerHealthStatus.HEALTHY
            if BrokerHealthStatus.UNHEALTHY in statuses:
                return BrokerHealthStatus.UNHEALTHY
            return BrokerHealthStatus.DEGRADED

    def summary(self) -> dict[str, Any]:
        with self._lock:
            total    = len(self._records)
            healthy  = sum(1 for r in self._records.values() if r.is_healthy)
            return {
                "total_brokers":     total,
                "healthy_brokers":   healthy,
                "unhealthy_brokers": total - healthy,
                "overall_status":    self.overall_status.value,
            }
