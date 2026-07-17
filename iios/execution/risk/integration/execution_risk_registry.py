"""iios/execution/risk/integration/execution_risk_registry.py
==================================================
ComponentRegistry — tracks component references for the integration engine.

This is NOT the M1 risk lifecycle registry.  It is the integration
layer's internal component reference store, used solely for health
inspection and lifecycle coordination.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .constants import ComponentType, REQUIRED_COMPONENT_TYPES
from .exceptions import ComponentRegistrationError


class ComponentRegistry:
    """
    Lightweight, non-lifecycle reference store for integration components.

    The integration engine populates this during __init__ and uses it
    to perform health checks across all owned components without holding
    hard references in multiple places.
    """

    def __init__(self) -> None:
        self._components: Dict[ComponentType, Any] = {}

    # ── Write ─────────────────────────────────────────────────────────────────

    def register(self, component_type: ComponentType, component: Any) -> None:
        """Register *component* under *component_type*."""
        self._components[component_type] = component

    def deregister(self, component_type: ComponentType) -> None:
        """Remove the component registered under *component_type*."""
        self._components.pop(component_type, None)

    def clear(self) -> None:
        self._components.clear()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, component_type: ComponentType) -> Optional[Any]:
        return self._components.get(component_type)

    def require(self, component_type: ComponentType) -> Any:
        """Return the component or raise ComponentRegistrationError."""
        c = self._components.get(component_type)
        if c is None:
            raise ComponentRegistrationError(
                f"Component '{component_type.value}' is not registered"
            )
        return c

    def is_registered(self, component_type: ComponentType) -> bool:
        return component_type in self._components

    def all_required_registered(self) -> bool:
        """Return True if all REQUIRED_COMPONENT_TYPES are registered."""
        return all(ct in self._components for ct in REQUIRED_COMPONENT_TYPES)

    def registered_types(self) -> List[ComponentType]:
        return list(self._components.keys())

    def all(self) -> Dict[ComponentType, Any]:
        return dict(self._components)
