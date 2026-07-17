"""iios/execution/gateway/brokers/broker_health.py
==================================================
BrokerHealthRecord and BrokerHealthMonitor.

Health records capture the result of a broker health check.
The monitor maintains the latest health status per broker and
exposes unhealthy broker discovery.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class BrokerHealthRecord:
    """
    Immutable snapshot of a single broker health check.

    Fields
    ------
    broker_id:
        The broker that was checked.
    is_healthy:
        True when the broker is responding normally.
    latency_ms:
        Round-trip latency of the health check in milliseconds.
    checked_at:
        Unix timestamp when the check was performed.
    error_message:
        Description of the failure; None when is_healthy is True.
    metadata:
        Arbitrary key-value pairs from the broker implementation.
    """

    broker_id:     str
    is_healthy:    bool
    latency_ms:    float
    checked_at:    float
    error_message: Optional[str]              = None
    metadata:      Dict[str, Any]             = field(default_factory=dict, compare=False)

    @property
    def age_ms(self) -> float:
        """Milliseconds since this health record was created."""
        return (time.time() - self.checked_at) * 1_000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "broker_id":     self.broker_id,
            "is_healthy":    self.is_healthy,
            "latency_ms":    self.latency_ms,
            "checked_at":    self.checked_at,
            "error_message": self.error_message,
            "metadata":      dict(self.metadata),
        }

    def __repr__(self) -> str:
        state = "healthy" if self.is_healthy else "unhealthy"
        return (
            f"BrokerHealthRecord("
            f"broker_id={self.broker_id!r}, "
            f"state={state!r}, "
            f"latency_ms={self.latency_ms:.2f}"
            f")"
        )


# ── BrokerHealthMonitor ───────────────────────────────────────────────────────

class BrokerHealthMonitor:
    """
    Thread-safe monitor that stores the latest health record per broker.

    The monitor does NOT perform health checks — it only stores results
    provided by the manager after calling ``broker.health()``.
    """

    def __init__(self) -> None:
        self._records: Dict[str, BrokerHealthRecord] = {}
        self._lock    = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def record_health(self, record: BrokerHealthRecord) -> None:
        """Store the latest health record for a broker."""
        with self._lock:
            self._records[record.broker_id] = record

    def remove(self, broker_id: str) -> None:
        """Remove the health record for a broker (called on de-registration)."""
        with self._lock:
            self._records.pop(broker_id, None)

    def clear(self) -> None:
        """Remove all health records."""
        with self._lock:
            self._records.clear()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_health(self, broker_id: str) -> Optional[BrokerHealthRecord]:
        """Return the latest health record for a broker, or None if not checked."""
        with self._lock:
            return self._records.get(broker_id)

    def is_healthy(self, broker_id: str) -> bool:
        """
        Return True if the broker has a recent health record marked healthy.

        Returns False if the broker has never been checked or is unhealthy.
        """
        with self._lock:
            record = self._records.get(broker_id)
        return record is not None and record.is_healthy

    def all_health(self) -> Dict[str, BrokerHealthRecord]:
        """Return a snapshot of all current health records."""
        with self._lock:
            return dict(self._records)

    def healthy_brokers(self) -> List[str]:
        """Return broker IDs with healthy status."""
        with self._lock:
            return [bid for bid, rec in self._records.items() if rec.is_healthy]

    def unhealthy_brokers(self) -> List[str]:
        """Return broker IDs with unhealthy status."""
        with self._lock:
            return [bid for bid, rec in self._records.items() if not rec.is_healthy]

    def broker_count(self) -> int:
        """Return number of brokers with a recorded health check."""
        with self._lock:
            return len(self._records)

    def healthy_count(self) -> int:
        with self._lock:
            return sum(1 for rec in self._records.values() if rec.is_healthy)

    def unhealthy_count(self) -> int:
        with self._lock:
            return sum(1 for rec in self._records.values() if not rec.is_healthy)


# ── Factory ───────────────────────────────────────────────────────────────────

def make_health_record(
    broker_id:     str,
    is_healthy:    bool,
    latency_ms:    float = 0.0,
    *,
    error_message: Optional[str] = None,
    metadata:      Optional[Dict[str, Any]] = None,
) -> BrokerHealthRecord:
    """Create a BrokerHealthRecord stamped at the current time."""
    return BrokerHealthRecord(
        broker_id=broker_id,
        is_healthy=is_healthy,
        latency_ms=max(0.0, latency_ms),
        checked_at=time.time(),
        error_message=error_message,
        metadata=dict(metadata or {}),
    )
