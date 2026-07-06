"""
iios/infrastructure/dependency_injection/service_locator.py
============================================================
Service Locator — static access point for resolving services
without needing a Container reference.

Prefer constructor injection via the Container. Use the locator
only where injection is not feasible (e.g. framework callbacks).
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from .container import Container, get_container
from ..infrastructure_exceptions import ServiceNotFoundError

__all__ = ["ServiceLocator", "get_service"]

_locator_lock = threading.Lock()
_locator: Optional["ServiceLocator"] = None


class ServiceLocator:
    """Thin wrapper around a Container for static-access patterns."""

    def __init__(self, container: Optional[Container] = None) -> None:
        self._container = container or get_container()

    def get(self, key: Any) -> Any:
        """Resolve a service by key or type."""
        return self._container.resolve(key)

    def get_optional(self, key: Any) -> Optional[Any]:
        return self._container.try_resolve(key)

    def get_all(self, tag: str) -> list[Any]:
        """Resolve all services tagged with *tag*."""
        return self._container.resolve_all(tag)

    def has(self, key: Any) -> bool:
        return self._container.is_registered(key)

    def use_container(self, container: Container) -> "ServiceLocator":
        """Swap the underlying container (for testing)."""
        self._container = container
        return self

    @property
    def container(self) -> Container:
        return self._container


def get_service(key: Any) -> Any:
    """Resolve a service from the global locator."""
    global _locator
    with _locator_lock:
        if _locator is None:
            _locator = ServiceLocator()
    return _locator.get(key)


def _reset_service_locator() -> None:
    global _locator
    with _locator_lock:
        _locator = None
