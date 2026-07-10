"""iios/execution/monitoring/monitoring_registry.py"""
from __future__ import annotations

import threading
from typing import Any

from iios.execution.monitoring.monitoring_constants import MONITORING_ENGINE_SYSTEM_ID
from iios.execution.monitoring.monitoring_exceptions import MonitoringRegistryError


class MonitoringRegistry:
    """
    Lightweight registry that maps execution_id → component metadata.

    Used for cross-component lookups without circular imports.
    """

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}
        self._lock     = threading.RLock()

    def register(self, execution_id: str, metadata: dict[str, Any]) -> None:
        with self._lock:
            self._entries[execution_id] = metadata

    def get(self, execution_id: str) -> dict[str, Any]:
        with self._lock:
            entry = self._entries.get(execution_id)
        if entry is None:
            raise MonitoringRegistryError(
                f"No registry entry for execution_id '{execution_id}'",
                "EM-050",
            )
        return entry

    def has(self, execution_id: str) -> bool:
        with self._lock:
            return execution_id in self._entries

    def unregister(self, execution_id: str) -> None:
        with self._lock:
            self._entries.pop(execution_id, None)

    def all_ids(self) -> list[str]:
        with self._lock:
            return list(self._entries.keys())

    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "registered_executions": len(self._entries),
                "system_id":             MONITORING_ENGINE_SYSTEM_ID,
            }


_registry_instance: MonitoringRegistry | None = None
_registry_lock = threading.Lock()


def get_monitoring_registry() -> MonitoringRegistry:
    global _registry_instance
    if _registry_instance is None:
        with _registry_lock:
            if _registry_instance is None:
                _registry_instance = MonitoringRegistry()
    return _registry_instance


def reset_monitoring_registry() -> None:
    global _registry_instance
    with _registry_lock:
        _registry_instance = None
