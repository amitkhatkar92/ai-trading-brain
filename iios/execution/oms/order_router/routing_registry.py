"""iios/execution/oms/order_router/routing_registry.py
==================================================
RoutingRegistry — IIOS v1.0 lifecycle-aware store of BrokerCapabilities.

Maintains the set of known brokers available for routing evaluation.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from iios.execution.oms.order_router.constants import (
    REGISTRY_SYSTEM_ID,
    VERSION,
)
from iios.execution.oms.order_router.exceptions import (
    RouterCapacityError,
    RouterNotRunning,
)
from iios.execution.oms.order_router.routing_context import BrokerCapabilities


class RoutingRegistry(LifecycleAwareMixin):
    """
    Manages registered BrokerCapabilities instances.

    Thread-safe. Brokers are indexed by broker_id.
    """

    def __init__(self, max_brokers: int = 256) -> None:
        super().__init__()
        self._max_brokers = max_brokers
        self._brokers: dict[str, BrokerCapabilities] = {}
        self._lock    = threading.RLock()
        self._log     = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
        self._audit   = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        self._log.info("RoutingRegistry started.", max_brokers=self._max_brokers)

    def _on_stop(self) -> None:
        self._audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        self._log.info("RoutingRegistry stopped.")

    # ── Internal guard ────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RouterNotRunning("RoutingRegistry is not running")

    # ── Registration ─────────────────────────────────────────────────────────

    def register(self, capabilities: BrokerCapabilities) -> None:
        self._assert_running()
        if not capabilities.broker_id:
            raise ValueError("BrokerCapabilities.broker_id must be non-empty")
        with self._lock:
            if (capabilities.broker_id not in self._brokers and
                    len(self._brokers) >= self._max_brokers):
                raise RouterCapacityError(
                    f"Registry at capacity ({self._max_brokers} brokers)"
                )
            self._brokers[capabilities.broker_id] = capabilities
        self._log.debug("Registered broker.", broker_id=capabilities.broker_id)

    def unregister(self, broker_id: str) -> bool:
        self._assert_running()
        with self._lock:
            existed = broker_id in self._brokers
            self._brokers.pop(broker_id, None)
        if existed:
            self._log.debug("Unregistered broker.", broker_id=broker_id)
        return existed

    def update(self, capabilities: BrokerCapabilities) -> None:
        """Replace capabilities for an existing broker."""
        self._assert_running()
        self.register(capabilities)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, broker_id: str) -> Optional[BrokerCapabilities]:
        self._assert_running()
        with self._lock:
            return self._brokers.get(broker_id)

    def all(self) -> list[BrokerCapabilities]:
        self._assert_running()
        with self._lock:
            return list(self._brokers.values())

    def available(self) -> list[BrokerCapabilities]:
        self._assert_running()
        with self._lock:
            return [b for b in self._brokers.values() if b.is_available]

    def contains(self, broker_id: str) -> bool:
        with self._lock:
            return broker_id in self._brokers

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._brokers)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "size":        len(self._brokers),
                "max_brokers": self._max_brokers,
                "broker_ids":  sorted(self._brokers.keys()),
            }
