"""
risk_component_registry.py — iios.risk.integration
====================================================
Registry for Risk Intelligence subsystem components.

Tracks availability and holds references to M1-M5 subsystem components.
The integration engine uses this registry to discover and invoke each
subsystem in the workflow.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from .constants import (
    COMPONENT_ASSESSMENT,
    COMPONENT_ENGINE,
    COMPONENT_LIFECYCLE,
    COMPONENT_POLICIES,
    COMPONENT_SNAPSHOT,
    ComponentStatus,
    REQUIRED_COMPONENTS,
)
from .exceptions import RiskIntegrationComponentError


class RiskComponentRegistry:
    """
    Thread-safe registry for Risk Intelligence subsystem components.

    Each component is stored under its key (e.g. ``"risk_lifecycle"``) and
    has an associated :class:`~.constants.ComponentStatus`.

    Usage::

        registry = RiskComponentRegistry()
        registry.register("risk_lifecycle",   lifecycle_instance)
        registry.register("risk_engine",      engine_instance)
        registry.register("risk_policies",    policy_engine_instance)
        registry.register("risk_assessment",  assessment_engine_instance)
        registry.register("risk_snapshot",    snapshot_factory_instance)

        engine = registry.get("risk_assessment")
    """

    def __init__(self) -> None:
        self._lock:       threading.RLock              = threading.RLock()
        self._components: Dict[str, Any]               = {}
        self._status:     Dict[str, ComponentStatus]   = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        key:       str,
        component: Any,
        *,
        status: ComponentStatus = ComponentStatus.AVAILABLE,
    ) -> None:
        """Register a component under *key* with the given *status*."""
        with self._lock:
            self._components[key] = component
            self._status[key]     = status

    def set_status(self, key: str, status: ComponentStatus) -> None:
        """Update the availability status of a registered component."""
        with self._lock:
            if key not in self._components:
                raise RiskIntegrationComponentError(
                    f"Component not registered: {key}"
                )
            self._status[key] = status

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any:
        """
        Retrieve a component by key.

        Raises
        ------
        RiskIntegrationComponentError
            If the component is not registered or is unavailable.
        """
        with self._lock:
            component = self._components.get(key)
            if component is None:
                raise RiskIntegrationComponentError(
                    f"Component not registered: {key}"
                )
            status = self._status.get(key, ComponentStatus.UNKNOWN)
            if status == ComponentStatus.UNAVAILABLE:
                raise RiskIntegrationComponentError(
                    f"Component unavailable: {key}"
                )
            return component

    def get_or_none(self, key: str) -> Optional[Any]:
        """Return component or None if not registered / unavailable."""
        with self._lock:
            return self._components.get(key)

    def get_status(self, key: str) -> ComponentStatus:
        with self._lock:
            return self._status.get(key, ComponentStatus.UNKNOWN)

    # ------------------------------------------------------------------
    # Availability checks
    # ------------------------------------------------------------------

    def is_available(self, key: str) -> bool:
        with self._lock:
            return self._status.get(key) == ComponentStatus.AVAILABLE

    def all_available(self) -> bool:
        """Return True only if all required components are available."""
        with self._lock:
            for key in REQUIRED_COMPONENTS:
                if self._status.get(key) != ComponentStatus.AVAILABLE:
                    return False
            return True

    def available_components(self) -> Dict[str, ComponentStatus]:
        with self._lock:
            return dict(self._status)

    def missing_required(self) -> list:
        """Return list of required component keys that are not registered."""
        with self._lock:
            return [k for k in REQUIRED_COMPONENTS if k not in self._components]

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    def unregister(self, key: str) -> bool:
        with self._lock:
            if key not in self._components:
                return False
            del self._components[key]
            self._status.pop(key, None)
            return True

    def clear(self) -> None:
        with self._lock:
            self._components.clear()
            self._status.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._components)

    def keys(self) -> list:
        with self._lock:
            return list(self._components.keys())

    def health_summary(self) -> Dict[str, str]:
        with self._lock:
            return {k: v.value for k, v in self._status.items()}
