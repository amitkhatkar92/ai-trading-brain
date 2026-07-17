"""iios/execution/gateway/brokers/broker_statistics.py
==================================================
BrokerStatistics and BrokerStatisticsStore — per-broker counters and
derived metrics for the Broker Abstraction Layer.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

import copy
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BrokerStatistics:
    """
    Mutable statistics accumulator for a single broker.

    Thread safety is the caller's responsibility unless accessed
    via BrokerStatisticsStore which provides a per-broker lock.
    """

    broker_id: str

    # ── Request / response counts ─────────────────────────────────────────────
    requests:              int   = 0
    responses:             int   = 0
    failures:              int   = 0

    # ── Connection / session ──────────────────────────────────────────────────
    reconnect_count:        int   = 0
    authentication_count:   int   = 0
    session_expiry_count:   int   = 0

    # ── Latency accumulation ──────────────────────────────────────────────────
    total_latency_ms:       float = 0.0

    # ── Session duration ──────────────────────────────────────────────────────
    total_session_duration_secs: float = 0.0

    # ── Timestamp ─────────────────────────────────────────────────────────────
    last_updated_at: float = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def success_count(self) -> int:
        return max(0, self.responses - self.failures)

    @property
    def success_rate(self) -> float:
        return self.success_count / self.responses if self.responses else 0.0

    @property
    def failure_rate(self) -> float:
        return self.failures / self.responses if self.responses else 0.0

    @property
    def average_latency_ms(self) -> float:
        return self.total_latency_ms / self.responses if self.responses else 0.0

    @property
    def average_session_duration_secs(self) -> float:
        n = self.authentication_count
        return self.total_session_duration_secs / n if n else 0.0

    # ── Mutators ──────────────────────────────────────────────────────────────

    def record_request(self) -> None:
        self.requests       += 1
        self.last_updated_at = time.time()

    def record_response(self, latency_ms: float = 0.0) -> None:
        self.responses          += 1
        self.total_latency_ms   += max(0.0, latency_ms)
        self.last_updated_at     = time.time()

    def record_failure(self) -> None:
        self.failures        += 1
        self.last_updated_at  = time.time()

    def record_reconnect(self) -> None:
        self.reconnect_count  += 1
        self.last_updated_at   = time.time()

    def record_authentication(self) -> None:
        self.authentication_count += 1
        self.last_updated_at       = time.time()

    def record_session_expiry(self) -> None:
        self.session_expiry_count += 1
        self.last_updated_at       = time.time()

    def add_session_duration(self, duration_secs: float) -> None:
        self.total_session_duration_secs += max(0.0, duration_secs)
        self.last_updated_at              = time.time()

    def reset(self) -> None:
        self.requests                     = 0
        self.responses                    = 0
        self.failures                     = 0
        self.reconnect_count              = 0
        self.authentication_count         = 0
        self.session_expiry_count         = 0
        self.total_latency_ms             = 0.0
        self.total_session_duration_secs  = 0.0
        self.last_updated_at              = time.time()

    def copy(self) -> BrokerStatistics:
        return copy.copy(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "broker_id":                    self.broker_id,
            "requests":                     self.requests,
            "responses":                    self.responses,
            "failures":                     self.failures,
            "reconnect_count":              self.reconnect_count,
            "authentication_count":         self.authentication_count,
            "session_expiry_count":         self.session_expiry_count,
            "total_latency_ms":             self.total_latency_ms,
            "average_latency_ms":           self.average_latency_ms,
            "success_rate":                 self.success_rate,
            "failure_rate":                 self.failure_rate,
            "total_session_duration_secs":  self.total_session_duration_secs,
            "last_updated_at":              self.last_updated_at,
        }


# ── BrokerStatisticsStore ─────────────────────────────────────────────────────

class BrokerStatisticsStore:
    """
    Thread-safe store for per-broker BrokerStatistics instances.

    Provides get-or-create semantics so that the first access for a
    broker_id automatically initialises a statistics object.
    """

    def __init__(self) -> None:
        self._store: Dict[str, BrokerStatistics] = {}
        self._lock  = threading.Lock()

    # ── Access ────────────────────────────────────────────────────────────────

    def get_or_create(self, broker_id: str) -> BrokerStatistics:
        with self._lock:
            if broker_id not in self._store:
                self._store[broker_id] = BrokerStatistics(broker_id=broker_id)
            return self._store[broker_id]

    def get(self, broker_id: str) -> Optional[BrokerStatistics]:
        with self._lock:
            return self._store.get(broker_id)

    def get_snapshot(self, broker_id: str) -> Optional[BrokerStatistics]:
        """Return a copy so callers cannot mutate the stored instance."""
        with self._lock:
            stats = self._store.get(broker_id)
        return stats.copy() if stats is not None else None

    def remove(self, broker_id: str) -> None:
        with self._lock:
            self._store.pop(broker_id, None)

    def all(self) -> Dict[str, BrokerStatistics]:
        with self._lock:
            return {bid: stats.copy() for bid, stats in self._store.items()}

    def all_as_dict(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {bid: stats.to_dict() for bid, stats in self._store.items()}

    def registered_brokers(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
