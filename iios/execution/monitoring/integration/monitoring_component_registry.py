"""iios/execution/monitoring/integration/monitoring_component_registry.py
==================================================
ComponentRegistry — registry for tracking sub-component instances and
their lifecycle state.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import ComponentType, HealthStatus

_log = get_logger(__name__)


class ComponentEntry:
    """
    Lightweight wrapper around a sub-component instance.

    Fields
    ------
    component_type:  The enum type label.
    component_name:  Human-readable name.
    instance:        The actual sub-component object.
    """

    __slots__ = ("component_type", "component_name", "instance")

    def __init__(
        self,
        component_type: ComponentType,
        component_name: str,
        instance:       Any,
    ) -> None:
        self.component_type = component_type
        self.component_name = component_name
        self.instance       = instance

    def is_running(self) -> bool:
        """Returns True if the component has a lifecycle_state() == RUNNING."""
        try:
            state = self.instance.lifecycle_state()
            return str(state).lower() in ("running", "enginestate.running")
        except Exception:  # noqa: BLE001
            return False

    def health_status(self) -> HealthStatus:
        if self.is_running():
            return HealthStatus.HEALTHY
        return HealthStatus.UNHEALTHY


class ComponentRegistry:
    """
    Thread-safe registry for the integration sub-components.

    Maintains one entry per ComponentType (lifecycle, metrics_engine,
    alert_manager).  The integration engine queries this registry when
    building health reports and routing workflow steps.
    """

    def __init__(self) -> None:
        self._components: Dict[ComponentType, ComponentEntry] = {}
        self._lock = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        component_type: ComponentType,
        component_name: str,
        instance:       Any,
    ) -> None:
        with self._lock:
            self._components[component_type] = ComponentEntry(
                component_type=component_type,
                component_name=component_name,
                instance=instance,
            )
        _log.info(
            "Component registered.",
            component_type=component_type.value,
            component_name=component_name,
        )

    def unregister(self, component_type: ComponentType) -> None:
        with self._lock:
            self._components.pop(component_type, None)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, component_type: ComponentType) -> Optional[ComponentEntry]:
        with self._lock:
            return self._components.get(component_type)

    def get_instance(self, component_type: ComponentType) -> Optional[Any]:
        entry = self.get(component_type)
        return entry.instance if entry else None

    def is_registered(self, component_type: ComponentType) -> bool:
        with self._lock:
            return component_type in self._components

    # ── State queries ─────────────────────────────────────────────────────────

    def all_running(self) -> bool:
        with self._lock:
            entries = list(self._components.values())
        return bool(entries) and all(e.is_running() for e in entries)

    def any_unhealthy(self) -> bool:
        with self._lock:
            entries = list(self._components.values())
        return any(not e.is_running() for e in entries)

    def all_entries(self) -> List[ComponentEntry]:
        with self._lock:
            return list(self._components.values())

    def component_count(self) -> int:
        with self._lock:
            return len(self._components)

    def clear(self) -> None:
        with self._lock:
            self._components.clear()
