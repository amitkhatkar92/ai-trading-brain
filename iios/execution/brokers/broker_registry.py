"""iios/execution/brokers/broker_registry.py
==================================================
BrokerRegistry — thread-safe store of BrokerRecord objects.

Tracks registered broker metadata, capabilities, statistics,
and health records. This is a pure abstraction registry —
it does NOT hold live adapter instances.

IIOS v1.0: LifecycleAwareMixin, logging, audit, error handling.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from iios.common.errors.error_context import ErrorContext
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_REGISTRY,
    ACTOR_SYSTEM,
    DEFAULT_MAX_BROKERS,
    REGISTRY_SYSTEM_ID,
    VERSION,
    BrokerConnectionState,
    BrokerHealthStatus,
)
from .exceptions import (
    BrokerCapacityError,
    BrokerNotFoundError,
    BrokerNotRunningError,
    BrokerRegistrationError,
    DuplicateBrokerError,
)
from .broker_metadata import BrokerMetadata
from .broker_capabilities import BrokerCapabilities, capabilities_from_metadata
from .broker_health import BrokerHealthRecord, BrokerHealthMonitor
from .broker_statistics import BrokerStatistics, RegistryStatistics
from .broker_events import BrokerEvent, BrokerEventType, make_broker_event

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID,
                          component="BrokerRegistry")


@dataclass
class BrokerRecord:
    """Container for all data associated with one registered broker."""

    broker_id:    str
    metadata:     BrokerMetadata
    capabilities: BrokerCapabilities
    statistics:   BrokerStatistics   = field(init=False)
    registered_at: float             = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.statistics = BrokerStatistics(broker_id=self.broker_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":    self.broker_id,
            "registered_at": self.registered_at,
            "metadata":     self.metadata.to_dict(),
            "capabilities": self.capabilities.to_dict(),
            "statistics":   self.statistics.to_dict(),
        }


class BrokerRegistry(LifecycleAwareMixin):
    """
    IIOS v1.0 registry for broker metadata and capabilities.

    Thread-safe.  Supports registration, lookup, and bulk iteration.
    Owns a BrokerHealthMonitor.
    """

    SYSTEM_ID = REGISTRY_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_brokers: int = DEFAULT_MAX_BROKERS) -> None:
        self._records:   dict[str, BrokerRecord] = {}
        self._max_brokers = max_brokers
        self._health     = BrokerHealthMonitor()
        self._lock       = threading.RLock()
        self._listeners: list[Callable[[BrokerEvent], None]] = []

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION
        )
        _log.info("BrokerRegistry started.", capacity=self._max_brokers)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION
        )
        _log.info("BrokerRegistry stopped.", registered=len(self._records))

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    def _assert_running(self) -> None:
        if not self.is_running:
            raise BrokerNotRunningError(
                "BrokerRegistry must be started before use."
            )


    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        metadata:  BrokerMetadata,
        overwrite: bool = False,
    ) -> BrokerRecord:
        """Register a broker by its metadata."""
        self._assert_running()
        broker_id = metadata.broker_id
        with self._lock:
            if broker_id in self._records and not overwrite:
                raise DuplicateBrokerError(broker_id)
            if (
                len(self._records) >= self._max_brokers
                and broker_id not in self._records
            ):
                raise BrokerCapacityError(
                    f"BrokerRegistry capacity reached ({self._max_brokers})"
                )
            caps   = capabilities_from_metadata(metadata)
            record = BrokerRecord(
                broker_id    = broker_id,
                metadata     = metadata,
                capabilities = caps,
            )
            self._records[broker_id] = record
        self._health.register(broker_id)
        _log.info("Broker registered.", broker_id=broker_id)
        _audit.log_workflow_event(
            self.SYSTEM_ID, "register", "BROKER_REGISTERED",
            actor=ACTOR_REGISTRY, broker_id=broker_id,
        )
        event = make_broker_event(broker_id, BrokerEventType.BROKER_REGISTERED)
        self._dispatch(event)
        return record

    def unregister(self, broker_id: str) -> None:
        """Remove a broker from the registry."""
        self._assert_running()
        with self._lock:
            if broker_id not in self._records:
                raise BrokerNotFoundError(broker_id)
            del self._records[broker_id]
        self._health.unregister(broker_id)
        _log.info("Broker unregistered.", broker_id=broker_id)
        event = make_broker_event(broker_id, BrokerEventType.BROKER_UNREGISTERED)
        self._dispatch(event)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, broker_id: str) -> BrokerRecord:
        self._assert_running()
        with self._lock:
            record = self._records.get(broker_id)
        if record is None:
            raise BrokerNotFoundError(broker_id)
        return record

    def get_metadata(self, broker_id: str) -> BrokerMetadata:
        return self.get(broker_id).metadata

    def get_capabilities(self, broker_id: str) -> BrokerCapabilities:
        return self.get(broker_id).capabilities

    def get_statistics(self, broker_id: str) -> BrokerStatistics:
        return self.get(broker_id).statistics

    def get_health(self, broker_id: str) -> Optional[BrokerHealthRecord]:
        return self._health.get(broker_id)

    def contains(self, broker_id: str) -> bool:
        with self._lock:
            return broker_id in self._records

    def all_records(self) -> list[BrokerRecord]:
        with self._lock:
            return list(self._records.values())

    def all_broker_ids(self) -> list[str]:
        with self._lock:
            return list(self._records.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    # ── Health pass-through ───────────────────────────────────────────────────

    def record_health_update(
        self,
        broker_id:    str,
        is_healthy:   bool,
        latency_ms:   float = 0.0,
        error_message: str  = "",
    ) -> None:
        """Update the health record for a broker."""
        if is_healthy:
            self._health.record_healthy(broker_id, latency_ms)
        else:
            self._health.record_unhealthy(broker_id, error_message)

        et = (
            BrokerEventType.BROKER_HEALTHY
            if is_healthy
            else BrokerEventType.BROKER_UNHEALTHY
        )
        self._dispatch(make_broker_event(broker_id, et))

    def set_connection_state(
        self,
        broker_id: str,
        state:     BrokerConnectionState,
    ) -> None:
        self._health.set_connection_state(broker_id, state)
        et = (
            BrokerEventType.BROKER_CONNECTED
            if state == BrokerConnectionState.CONNECTED
            else BrokerEventType.BROKER_DISCONNECTED
        )
        self._dispatch(
            make_broker_event(broker_id, et, connection_state=state)
        )

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> RegistryStatistics:
        with self._lock:
            records    = list(self._records.values())
        health_summary = self._health.summary()
        total_req  = sum(r.statistics.total_requests for r in records)
        success    = sum(r.statistics.successful_requests for r in records)
        failed     = sum(r.statistics.failed_requests for r in records)
        avg_ms     = (
            sum(r.statistics.avg_response_ms for r in records) / len(records)
            if records else 0.0
        )
        return RegistryStatistics(
            total_registered   = len(records),
            connected_count    = health_summary["healthy_brokers"],
            healthy_count      = health_summary["healthy_brokers"],
            capacity           = self._max_brokers,
            utilisation_pct    = len(records) / self._max_brokers * 100,
            total_requests     = total_req,
            successful_requests = success,
            failed_requests    = failed,
            avg_response_ms    = avg_ms,
            broker_stats       = [r.statistics.to_dict() for r in records],
        )

    # ── Listeners ─────────────────────────────────────────────────────────────

    def add_listener(self, fn: Callable[[BrokerEvent], None]) -> None:
        with self._lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[BrokerEvent], None]) -> None:
        with self._lock:
            self._listeners = [f for f in self._listeners if f != fn]

    def _dispatch(self, event: BrokerEvent) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:
                _log.warning("Listener raised an exception — continuing.")

