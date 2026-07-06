"""
iios/infrastructure/dependency_injection/service_registry.py
=============================================================
Low-level registry that stores ServiceDescriptors keyed by service key.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional, Type

from ..infrastructure_constants import LifecycleScope
from ..infrastructure_exceptions import ServiceNotFoundError, ServiceAlreadyRegisteredError
from ..infrastructure_models import ServiceDescriptor

__all__ = ["ServiceRegistry"]


class ServiceRegistry:
    """Thread-safe store of service descriptors.

    The registry is separate from the container so it can be inspected
    and tested independently.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._descriptors: dict[str, ServiceDescriptor] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        key: str,
        implementation: Any,
        scope: str = LifecycleScope.SINGLETON.value,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        allow_override: bool = False,
    ) -> ServiceDescriptor:
        """Register a service binding.

        Args:
            key:             Unique service key (usually the interface name or type).
            implementation:  The class, factory callable, or instance to bind.
            scope:           LifecycleScope value.
            tags:            Optional categorisation tags.
            metadata:        Arbitrary metadata attached to the descriptor.
            allow_override:  If True, silently replaces an existing binding.

        Returns:
            The created ``ServiceDescriptor``.
        """
        with self._lock:
            if key in self._descriptors and not allow_override:
                raise ServiceAlreadyRegisteredError(
                    f"Service '{key}' is already registered. Use allow_override=True to replace.",
                    code="INF-DI-003",
                    context={"key": key},
                )
            descriptor = ServiceDescriptor(
                service_key=key,
                implementation=implementation,
                scope=scope,
                tags=tags or [],
                metadata=metadata or {},
            )
            self._descriptors[key] = descriptor
            return descriptor

    def register_instance(
        self,
        key: str,
        instance: Any,
        tags: Optional[list[str]] = None,
        allow_override: bool = False,
    ) -> ServiceDescriptor:
        """Register a pre-built singleton instance."""
        descriptor = self.register(
            key,
            implementation=type(instance),
            scope=LifecycleScope.SINGLETON.value,
            tags=tags,
            allow_override=allow_override,
        )
        descriptor.singleton_instance = instance
        return descriptor

    def unregister(self, key: str) -> bool:
        """Remove a registration. Returns True if it existed."""
        with self._lock:
            return self._descriptors.pop(key, None) is not None

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, key: str) -> ServiceDescriptor:
        """Return descriptor for *key*.

        Raises:
            ServiceNotFoundError: If no binding for *key* exists.
        """
        with self._lock:
            descriptor = self._descriptors.get(key)
        if descriptor is None:
            raise ServiceNotFoundError(
                f"No service registered for key '{key}'",
                code="INF-DI-004",
                context={"key": key},
            )
        return descriptor

    def get_optional(self, key: str) -> Optional[ServiceDescriptor]:
        with self._lock:
            return self._descriptors.get(key)

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._descriptors

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._descriptors.keys())

    def by_tag(self, tag: str) -> list[ServiceDescriptor]:
        """Return all descriptors that have the given tag."""
        with self._lock:
            return [d for d in self._descriptors.values() if tag in d.tags]

    def all(self) -> list[ServiceDescriptor]:
        with self._lock:
            return list(self._descriptors.values())

    def clear(self) -> None:
        with self._lock:
            self._descriptors.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._descriptors)

    def __contains__(self, key: str) -> bool:
        return self.has(key)
