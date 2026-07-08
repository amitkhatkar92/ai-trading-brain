"""iios/decision_governance/audit/audit_registry.py

Per-decision registry of AuditEvent IDs (lightweight index).
"""
from __future__ import annotations

import threading

from iios.decision_governance.governance_exceptions import (
    AuditNotFoundError,
    RegistryOverflowError,
)
from iios.decision_governance.governance_constants import MAX_REGISTRY_SIZE
from iios.decision_governance.audit.audit_event import AuditEvent


class AuditRegistry:
    """
    Thread-safe registry mapping decision_id → list[AuditEvent].
    Provides O(1) lookup by decision_id.
    """

    def __init__(self, max_size: int = MAX_REGISTRY_SIZE) -> None:
        self._lock:   threading.RLock             = threading.RLock()
        self._index:  dict[str, list[AuditEvent]] = {}
        self._max:    int                         = max_size

    def register(self, event: AuditEvent) -> None:
        with self._lock:
            if event.decision_id not in self._index:
                if len(self._index) >= self._max:
                    raise RegistryOverflowError(self._max)
                self._index[event.decision_id] = []
            self._index[event.decision_id].append(event)

    def get(self, decision_id: str) -> list[AuditEvent]:
        with self._lock:
            events = self._index.get(decision_id)
        if events is None:
            raise AuditNotFoundError(decision_id)
        return list(events)

    def has(self, decision_id: str) -> bool:
        with self._lock:
            return decision_id in self._index

    def all_decision_ids(self) -> list[str]:
        with self._lock:
            return list(self._index.keys())

    def size(self) -> int:
        with self._lock:
            return len(self._index)


# ── singleton ─────────────────────────────────────────────────────────────────

_singleton_lock: threading.Lock     = threading.Lock()
_instance:       AuditRegistry | None = None


def get_audit_registry() -> AuditRegistry:
    global _instance  # noqa: PLW0603
    if _instance is None:
        with _singleton_lock:
            if _instance is None:
                _instance = AuditRegistry()
    return _instance


def reset_audit_registry() -> None:
    global _instance  # noqa: PLW0603
    with _singleton_lock:
        _instance = None
