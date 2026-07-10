"""iios/integration/integration_registry.py

Module-level singleton registry for the integration engine.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.integration.integration_exceptions import RegistryError


class IntegrationRegistry:
    """
    Central registry for named integration components (engines, configs, etc.).
    Intentionally generic; concrete component managers live elsewhere.
    """

    def __init__(self) -> None:
        self._entries: dict[str, Any] = {}
        self._lock     = threading.RLock()

    def register(self, name: str, obj: Any) -> None:
        with self._lock:
            self._entries[name] = obj

    def get(self, name: str) -> Any:
        with self._lock:
            val = self._entries.get(name)
        if val is None:
            raise RegistryError(f"No entry for '{name}' in IntegrationRegistry", "DI-060")
        return val

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._entries

    def unregister(self, name: str) -> None:
        with self._lock:
            self._entries.pop(name, None)

    def all_names(self) -> list[str]:
        with self._lock:
            return list(self._entries.keys())

    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {"registered": len(self._entries), "names": list(self._entries.keys())}


_registry_instance: IntegrationRegistry | None = None
_registry_lock = threading.Lock()


def get_integration_registry() -> IntegrationRegistry:
    global _registry_instance
    if _registry_instance is None:
        with _registry_lock:
            if _registry_instance is None:
                _registry_instance = IntegrationRegistry()
    return _registry_instance


def reset_integration_registry() -> None:
    global _registry_instance
    with _registry_lock:
        _registry_instance = None
