"""
connector_registry.py — iios.integration.services
---------------------------------------------------
ConnectorRegistry — thread-safe registry of connector descriptors.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import DEFAULT_MAX_CONNECTORS, ServiceType
from .exceptions import ConnectorNotFoundError, ConnectorExecutionError


@dataclass(frozen=True)
class ConnectorDescriptor:
    """Immutable descriptor for a registered connector."""

    connector_id:   str
    name:           str
    service_type:   ServiceType
    version:        str
    capabilities:   tuple        # tuple of str
    enabled:        bool
    metadata:       Dict[str, Any]
    registered_at:  str

    @classmethod
    def create(
        cls,
        name:          str,
        service_type:  ServiceType,
        *,
        version:       str                       = "1.0.0",
        capabilities:  Optional[List[str]]       = None,
        enabled:       bool                      = True,
        metadata:      Optional[Dict[str, Any]]  = None,
        connector_id:  Optional[str]             = None,
    ) -> "ConnectorDescriptor":
        return cls(
            connector_id  = connector_id or f"conn-{uuid.uuid4().hex[:12]}",
            name          = name,
            service_type  = service_type,
            version       = version,
            capabilities  = tuple(capabilities or []),
            enabled       = enabled,
            metadata      = dict(metadata or {}),
            registered_at = datetime.now(timezone.utc).isoformat(),
        )

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connector_id":  self.connector_id,
            "name":          self.name,
            "service_type":  self.service_type.value,
            "version":       self.version,
            "capabilities":  list(self.capabilities),
            "enabled":       self.enabled,
            "metadata":      self.metadata,
            "registered_at": self.registered_at,
        }


class ConnectorRegistry:
    """Thread-safe registry for connector descriptors."""

    def __init__(self, max_connectors: int = DEFAULT_MAX_CONNECTORS) -> None:
        self._max       = max_connectors
        self._store:    Dict[str, ConnectorDescriptor] = {}
        self._lock      = threading.Lock()

    def register(self, descriptor: ConnectorDescriptor) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                raise ConnectorExecutionError(
                    f"Connector registry at capacity ({self._max})"
                )
            self._store[descriptor.connector_id] = descriptor

    def deregister(self, connector_id: str) -> bool:
        with self._lock:
            if connector_id in self._store:
                del self._store[connector_id]
                return True
        return False

    def get(self, connector_id: str) -> Optional[ConnectorDescriptor]:
        with self._lock:
            return self._store.get(connector_id)

    def get_or_raise(self, connector_id: str) -> ConnectorDescriptor:
        desc = self.get(connector_id)
        if desc is None:
            raise ConnectorNotFoundError(connector_id)
        return desc

    def first_by_type(self, service_type: ServiceType) -> Optional[ConnectorDescriptor]:
        with self._lock:
            for d in self._store.values():
                if d.service_type == service_type and d.enabled:
                    return d
        return None

    def by_type(self, service_type: ServiceType) -> List[ConnectorDescriptor]:
        with self._lock:
            return [d for d in self._store.values() if d.service_type == service_type]

    def all_enabled(self) -> List[ConnectorDescriptor]:
        with self._lock:
            return [d for d in self._store.values() if d.enabled]

    def all_connectors(self) -> List[ConnectorDescriptor]:
        with self._lock:
            return list(self._store.values())

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def has(self, connector_id: str) -> bool:
        with self._lock:
            return connector_id in self._store

    def supports_type(self, service_type: ServiceType) -> bool:
        return self.first_by_type(service_type) is not None

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
