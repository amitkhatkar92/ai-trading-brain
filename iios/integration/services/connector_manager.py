"""
connector_manager.py — iios.integration.services
--------------------------------------------------
ConnectorManager — manages connector lifecycle and execution delegation.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from .connector_context import ConnectorContext
from .connector_registry import ConnectorDescriptor, ConnectorRegistry
from .connector_response import ConnectorResponse
from .constants import ServiceType
from .exceptions import ConnectorNotFoundError


class ConnectorManager:
    """
    Manages connector lifecycle: loading, activation, and execution delegation.

    Thread-safe.  Delegates actual protocol execution to the adapter layer.
    """

    def __init__(self, registry: Optional[ConnectorRegistry] = None) -> None:
        self._registry = registry or ConnectorRegistry()
        self._active:   Dict[str, ConnectorDescriptor] = {}
        self._lock      = threading.Lock()

    @property
    def registry(self) -> ConnectorRegistry:
        return self._registry

    def register(self, descriptor: ConnectorDescriptor) -> None:
        """Register a connector descriptor."""
        self._registry.register(descriptor)

    def load(self, service_type: ServiceType) -> ConnectorDescriptor:
        """Load the first available connector for the given service type."""
        desc = self._registry.first_by_type(service_type)
        if desc is None:
            raise ConnectorNotFoundError(service_type.value)
        with self._lock:
            self._active[desc.connector_id] = desc
        return desc

    def unload(self, connector_id: str) -> None:
        with self._lock:
            self._active.pop(connector_id, None)

    def is_loaded(self, connector_id: str) -> bool:
        with self._lock:
            return connector_id in self._active

    def active_connectors(self) -> List[ConnectorDescriptor]:
        with self._lock:
            return list(self._active.values())

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def get(self, connector_id: str) -> Optional[ConnectorDescriptor]:
        return self._registry.get(connector_id)

    def all_connectors(self) -> List[ConnectorDescriptor]:
        return self._registry.all_connectors()

    def supports_type(self, service_type: ServiceType) -> bool:
        return self._registry.supports_type(service_type)

    def count(self) -> int:
        return self._registry.count()
