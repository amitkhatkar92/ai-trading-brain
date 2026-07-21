"""
decision_component_registry.py — iios.decision.integration
===========================================================
Registry of integrated M1-M5 decision subsystem components.

The component registry holds live instances of the five decision subsystems.
The integration engine queries this registry to determine which components
are available and running before invoking each workflow phase.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from .constants import ComponentHealth, ComponentType, INTEGRATION_SYSTEM_ID, VERSION
from .exceptions import ComponentNotFoundError


class ComponentRecord:
    """Holds one registered component instance with its metadata."""

    __slots__ = ("component_type", "component", "is_optional", "description")

    def __init__(
        self,
        component_type: ComponentType,
        component:      Any,
        is_optional:    bool = False,
        description:    str  = "",
    ) -> None:
        self.component_type: ComponentType = component_type
        self.component:      Any           = component
        self.is_optional:    bool          = is_optional
        self.description:    str           = description


class DecisionComponentRegistry:
    """
    Thread-safe registry of M1-M5 component instances.

    Usage
    -----
    ::

        registry = DecisionComponentRegistry()
        registry.register(ComponentType.LIFECYCLE, lifecycle_instance)
        registry.register(ComponentType.ENGINE, engine_instance, is_optional=True)

        lc = registry.get(ComponentType.LIFECYCLE)
        if registry.is_available(ComponentType.ENGINE):
            ...

    The ``is_ready()`` check inspects the component's :attr:`lifecycle_state`
    (if present via :class:`LifecycleAwareMixin`) and falls back to a
    ``is_running()`` method, then treats any registered component without
    either attribute as *ready*.
    """

    def __init__(self) -> None:
        self._lock:    threading.RLock                      = threading.RLock()
        self._records: Dict[ComponentType, ComponentRecord] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        component_type: ComponentType,
        component:      Any,
        *,
        is_optional:    bool = False,
        description:    str  = "",
    ) -> None:
        """Register a component instance.  Overwrites any prior registration."""
        with self._lock:
            self._records[component_type] = ComponentRecord(
                component_type = component_type,
                component      = component,
                is_optional    = is_optional,
                description    = description,
            )

    def deregister(self, component_type: ComponentType) -> bool:
        """Remove a component.  Returns True if it existed."""
        with self._lock:
            if component_type in self._records:
                del self._records[component_type]
                return True
            return False

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get(self, component_type: ComponentType) -> Any:
        """
        Return the component instance.

        Raises
        ------
        ComponentNotFoundError
            When the component type is not registered.
        """
        with self._lock:
            record = self._records.get(component_type)
        if record is None:
            raise ComponentNotFoundError(component_type.value)
        return record.component

    def find(self, component_type: ComponentType) -> Optional[Any]:
        """Return the component instance or ``None`` if not registered."""
        with self._lock:
            record = self._records.get(component_type)
        return record.component if record is not None else None

    def is_available(self, component_type: ComponentType) -> bool:
        """Return True if the component type is registered."""
        with self._lock:
            return component_type in self._records

    def is_ready(self, component_type: ComponentType) -> bool:
        """
        Return True if the component is registered AND appears to be running.

        Readiness checks (in order):
        1. `component.lifecycle_state()` == "running"  (LifecycleAwareMixin)
        2. `component.is_running()` returns True
        3. Attribute ``_state`` has ``.value == "running"``
        4. Fallback: True (component is present, no lifecycle introspection)
        """
        with self._lock:
            record = self._records.get(component_type)
        if record is None:
            return False
        comp = record.component
        # LifecycleAwareMixin
        if hasattr(comp, "lifecycle_state"):
            try:
                state = comp.lifecycle_state()
                if hasattr(state, "value"):
                    return state.value == "running"
                return str(state).lower() == "running"
            except Exception:
                pass
        if hasattr(comp, "is_running"):
            try:
                return bool(comp.is_running())
            except Exception:
                pass
        if hasattr(comp, "_state"):
            try:
                s = comp._state
                if hasattr(s, "value"):
                    return s.value == "running"
            except Exception:
                pass
        return True  # no lifecycle introspection available — assume ready

    def health(self, component_type: ComponentType) -> ComponentHealth:
        """Return the health level of a component."""
        if not self.is_available(component_type):
            return ComponentHealth.UNAVAILABLE
        if not self.is_ready(component_type):
            return ComponentHealth.CRITICAL
        comp = self.find(component_type)
        # Try component.health() → dict with "health" key
        if hasattr(comp, "health"):
            try:
                h = comp.health()
                if isinstance(h, dict):
                    raw = str(h.get("health", "")).lower()
                    return _parse_component_health(raw)
                if isinstance(h, str):
                    return _parse_component_health(h.lower())
            except Exception:
                pass
        return ComponentHealth.HEALTHY

    # ------------------------------------------------------------------
    # Bulk access
    # ------------------------------------------------------------------

    def all_components(self) -> Dict[ComponentType, Any]:
        with self._lock:
            return {ct: r.component for ct, r in self._records.items()}

    def registered_types(self) -> List[ComponentType]:
        with self._lock:
            return list(self._records.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        with self._lock:
            types = [ct.value for ct in self._records]
        return f"DecisionComponentRegistry(components={types})"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_component_health(raw: str) -> ComponentHealth:
    mapping = {
        "healthy":     ComponentHealth.HEALTHY,
        "degraded":    ComponentHealth.DEGRADED,
        "critical":    ComponentHealth.CRITICAL,
        "unavailable": ComponentHealth.UNAVAILABLE,
    }
    return mapping.get(raw, ComponentHealth.UNKNOWN)
