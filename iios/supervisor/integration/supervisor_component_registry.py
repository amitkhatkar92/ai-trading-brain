"""
supervisor_component_registry.py — iios.supervisor.integration
---------------------------------------------------------------
Thread-safe registry of all M1-M5 component instances managed by the
AI Supervisor Integration layer.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from .constants import ComponentType
from .exceptions import (
    SupervisorIntegrationComponentError,
    SupervisorIntegrationRegistryError,
)


class SupervisorComponentRegistry:
    """
    Thread-safe registry mapping :class:`ComponentType` → component instance.

    The integration engine is the sole owner of all M1-M5 components.
    External code must access them only through the integration engine's
    public API — never directly from this registry.
    """

    def __init__(self) -> None:
        self._lock:  threading.Lock             = threading.Lock()
        self._store: Dict[ComponentType, Any]   = {}

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def register(
        self,
        component_type: ComponentType,
        component:      Any,
    ) -> None:
        """Register (or overwrite) a component instance."""
        with self._lock:
            self._store[component_type] = component

    def unregister(self, component_type: ComponentType) -> None:
        """Remove a component from the registry (idempotent)."""
        with self._lock:
            self._store.pop(component_type, None)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, component_type: ComponentType) -> Any:
        """Return the registered component or raise if absent."""
        with self._lock:
            comp = self._store.get(component_type)
        if comp is None:
            raise SupervisorIntegrationComponentError(
                f"Component {component_type.value!r} is not registered",
                component=component_type.value,
            )
        return comp

    def get_optional(self, component_type: ComponentType) -> Optional[Any]:
        """Return the registered component or None if absent."""
        with self._lock:
            return self._store.get(component_type)

    def is_registered(self, component_type: ComponentType) -> bool:
        with self._lock:
            return component_type in self._store

    def all_components(self) -> Dict[str, Any]:
        """Return a snapshot dict of ``{component_type.value: component}``."""
        with self._lock:
            return {k.value: v for k, v in self._store.items()}

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._store)

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
