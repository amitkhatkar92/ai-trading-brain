"""iios/execution/oms/order_queue/queue_registry.py
==================================================
QueueRegistry — IIOS v1.0 lifecycle-aware store of QueueEntry objects.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from iios.execution.oms.order_queue.constants import (
    DEFAULT_MAX_QUEUE_SIZE,
    REGISTRY_SYSTEM_ID,
    VERSION,
    QueueEntryState,
)
from iios.execution.oms.order_queue.exceptions import (
    QueueCapacityError,
    QueueEntryNotFoundError,
    QueueNotRunning,
)
from iios.execution.oms.order_queue.queue_entry import QueueEntry


class QueueRegistry(LifecycleAwareMixin):
    """
    Thread-safe store of active QueueEntry objects.

    Indexed by both entry_id and order_id for O(1) lookups.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_QUEUE_SIZE) -> None:
        super().__init__()
        self._max_size   = max_size
        self._by_id:     dict[str, QueueEntry] = {}
        self._by_order:  dict[str, str]        = {}   # order_id → entry_id
        self._lock       = threading.RLock()
        self._log        = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
        self._audit      = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        self._log.info("QueueRegistry started.", max_size=self._max_size)

    def _on_stop(self) -> None:
        self._audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        self._log.info("QueueRegistry stopped.", size=self.size)

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise QueueNotRunning("QueueRegistry is not running")

    # ── Registration ─────────────────────────────────────────────────────────

    def register(self, entry: QueueEntry) -> None:
        self._assert_running()
        if not entry.entry_id:
            raise ValueError("QueueEntry.entry_id must be non-empty")
        with self._lock:
            if (entry.entry_id not in self._by_id and
                    len(self._by_id) >= self._max_size):
                raise QueueCapacityError(
                    f"Queue registry at capacity ({self._max_size} entries)"
                )
            self._by_id[entry.entry_id] = entry
            if entry.order_id:
                self._by_order[entry.order_id] = entry.entry_id

    def remove(self, entry_id: str) -> bool:
        self._assert_running()
        with self._lock:
            entry = self._by_id.pop(entry_id, None)
            if entry is None:
                return False
            self._by_order.pop(entry.order_id, None)
        return True

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get(self, entry_id: str) -> Optional[QueueEntry]:
        self._assert_running()
        with self._lock:
            return self._by_id.get(entry_id)

    def get_by_order_id(self, order_id: str) -> Optional[QueueEntry]:
        self._assert_running()
        with self._lock:
            eid = self._by_order.get(order_id)
            if eid is None:
                return None
            return self._by_id.get(eid)

    def all(self) -> list[QueueEntry]:
        self._assert_running()
        with self._lock:
            return list(self._by_id.values())

    def by_state(self, state: QueueEntryState) -> list[QueueEntry]:
        self._assert_running()
        with self._lock:
            return [e for e in self._by_id.values() if e.state == state]

    def active_order_ids(self) -> set[str]:
        """Return set of order_ids currently in the registry."""
        self._assert_running()
        with self._lock:
            return set(self._by_order.keys())

    def contains(self, entry_id: str) -> bool:
        with self._lock:
            return entry_id in self._by_id

    def contains_order(self, order_id: str) -> bool:
        with self._lock:
            return order_id in self._by_order

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._by_id)

    def clear(self) -> int:
        """Remove all entries. Returns count removed."""
        self._assert_running()
        with self._lock:
            count = len(self._by_id)
            self._by_id.clear()
            self._by_order.clear()
        return count

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "size":     len(self._by_id),
                "max_size": self._max_size,
            }
