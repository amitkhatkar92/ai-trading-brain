"""
integration_component_registry.py — iios.integration.gateway
--------------------------------------------------------------
IntegrationComponentRegistry — stores and exposes the 5 integrated
subsystem components (Lifecycle, Engine, Policies, Services, Snapshot).

Thread-safe.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import COMPONENT_ID_PREFIX, GatewayComponentType
from .exceptions import GatewayComponentError


@dataclass(frozen=True)
class GatewayComponent:
    """Metadata record for a registered gateway component."""

    component_type: GatewayComponentType
    component_id:   str
    is_available:   bool
    registered_at:  str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_type": self.component_type.value,
            "component_id":   self.component_id,
            "is_available":   self.is_available,
            "registered_at":  self.registered_at,
        }


class IntegrationComponentRegistry:
    """
    Registry for the 5 integrated subsystem component instances.

    Stores a live Python object reference for each component type
    together with a metadata record (GatewayComponent).
    Thread-safe.
    """

    def __init__(self) -> None:
        self._components:  Dict[GatewayComponentType, Any]              = {}
        self._metadata:    Dict[GatewayComponentType, GatewayComponent] = {}
        self._lock         = threading.Lock()

    # ─── registration ─────────────────────────────────────────────────

    def register(
        self,
        component_type: GatewayComponentType,
        component:      Any,
        component_id:   Optional[str] = None,
    ) -> bool:
        """
        Register *component* under *component_type*.

        Overwrites any existing registration for the same type.
        Returns True.
        """
        cid = component_id or f"{COMPONENT_ID_PREFIX}{uuid.uuid4().hex[:8]}"
        meta = GatewayComponent(
            component_type = component_type,
            component_id   = cid,
            is_available   = True,
            registered_at  = datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._components[component_type] = component
            self._metadata[component_type]   = meta
        return True

    def deregister(self, component_type: GatewayComponentType) -> bool:
        """Remove *component_type*. Returns True if it existed."""
        with self._lock:
            found = component_type in self._components
            self._components.pop(component_type, None)
            self._metadata.pop(component_type, None)
        return found

    # ─── retrieval ────────────────────────────────────────────────────

    def get(self, component_type: GatewayComponentType) -> Optional[Any]:
        """Return the component instance, or None if not registered."""
        with self._lock:
            return self._components.get(component_type)

    def get_or_raise(self, component_type: GatewayComponentType) -> Any:
        """Return the component instance or raise GatewayComponentError."""
        with self._lock:
            comp = self._components.get(component_type)
        if comp is None:
            raise GatewayComponentError(
                component = component_type.value,
                message   = f"Component {component_type.value!r} is not registered",
            )
        return comp

    # ─── availability ─────────────────────────────────────────────────

    def is_available(self, component_type: GatewayComponentType) -> bool:
        with self._lock:
            return component_type in self._components

    def all_available(self) -> bool:
        """Return True if all 5 component types are registered."""
        with self._lock:
            return all(ct in self._components for ct in GatewayComponentType)

    def available_types(self) -> List[GatewayComponentType]:
        with self._lock:
            return list(self._components.keys())

    # ─── metadata ─────────────────────────────────────────────────────

    def list_registered(self) -> List[GatewayComponent]:
        with self._lock:
            return list(self._metadata.values())

    def get_metadata(
        self,
        component_type: GatewayComponentType,
    ) -> Optional[GatewayComponent]:
        with self._lock:
            return self._metadata.get(component_type)

    # ─── management ───────────────────────────────────────────────────

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._components)

    def clear(self) -> int:
        with self._lock:
            n = len(self._components)
            self._components.clear()
            self._metadata.clear()
        return n
