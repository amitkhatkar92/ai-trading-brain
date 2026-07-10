"""iios/execution/monitoring/audit/audit_registry.py"""
from __future__ import annotations

import threading
from typing import Any

from iios.execution.monitoring.audit.audit_event import AuditEvent
from iios.execution.monitoring.audit.audit_history import AuditHistory


class AuditRegistry:
    """
    Multi-entity audit registry.

    Maintains separate AuditHistory instances per entity_type,
    plus a global history.  Thread-safe.
    """

    def __init__(self) -> None:
        self._global: AuditHistory = AuditHistory()
        self._by_type: dict[str, AuditHistory] = {}
        self._lock = threading.RLock()

    def record(self, event: AuditEvent) -> None:
        with self._lock:
            self._global.append(event)
            if event.entity_type:
                if event.entity_type not in self._by_type:
                    self._by_type[event.entity_type] = AuditHistory()
                self._by_type[event.entity_type].append(event)

    def for_entity(self, entity_id: str) -> list[AuditEvent]:
        return self._global.for_entity(entity_id)

    def for_entity_type(self, entity_type: str) -> list[AuditEvent]:
        with self._lock:
            h = self._by_type.get(entity_type)
        if h is None:
            return []
        return h.all_events()

    def global_history(self) -> AuditHistory:
        return self._global

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "global_events": self._global.count(),
                "entity_types":  list(self._by_type.keys()),
            }
