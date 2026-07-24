"""
adapter_registry.py — iios.integration.services
-------------------------------------------------
AdapterRegistry — thread-safe registry of adapter descriptors.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import AdapterProtocol, DEFAULT_MAX_ADAPTERS, ServiceType
from .exceptions import AdapterNotFoundError, AdapterExecutionError


@dataclass(frozen=True)
class AdapterDescriptor:
    """Immutable descriptor for a registered adapter."""

    adapter_id:     str
    name:           str
    protocol:       AdapterProtocol
    service_type:   ServiceType
    version:        str
    capabilities:   tuple
    enabled:        bool
    metadata:       Dict[str, Any]
    registered_at:  str

    @classmethod
    def create(
        cls,
        name:         str,
        protocol:     AdapterProtocol,
        service_type: ServiceType,
        *,
        version:      str                      = "1.0.0",
        capabilities: Optional[List[str]]      = None,
        enabled:      bool                     = True,
        metadata:     Optional[Dict[str, Any]] = None,
        adapter_id:   Optional[str]            = None,
    ) -> "AdapterDescriptor":
        return cls(
            adapter_id    = adapter_id or f"adpt-{uuid.uuid4().hex[:12]}",
            name          = name,
            protocol      = protocol,
            service_type  = service_type,
            version       = version,
            capabilities  = tuple(capabilities or []),
            enabled       = enabled,
            metadata      = dict(metadata or {}),
            registered_at = datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id":    self.adapter_id,
            "name":          self.name,
            "protocol":      self.protocol.value,
            "service_type":  self.service_type.value,
            "version":       self.version,
            "capabilities":  list(self.capabilities),
            "enabled":       self.enabled,
            "metadata":      self.metadata,
            "registered_at": self.registered_at,
        }


class AdapterRegistry:
    """Thread-safe registry for adapter descriptors."""

    def __init__(self, max_adapters: int = DEFAULT_MAX_ADAPTERS) -> None:
        self._max   = max_adapters
        self._store: Dict[str, AdapterDescriptor] = {}
        self._lock  = threading.Lock()

    def register(self, descriptor: AdapterDescriptor) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                raise AdapterExecutionError(
                    f"Adapter registry at capacity ({self._max})"
                )
            self._store[descriptor.adapter_id] = descriptor

    def deregister(self, adapter_id: str) -> bool:
        with self._lock:
            if adapter_id in self._store:
                del self._store[adapter_id]
                return True
        return False

    def get(self, adapter_id: str) -> Optional[AdapterDescriptor]:
        with self._lock:
            return self._store.get(adapter_id)

    def get_or_raise(self, adapter_id: str) -> AdapterDescriptor:
        desc = self.get(adapter_id)
        if desc is None:
            raise AdapterNotFoundError(adapter_id)
        return desc

    def first_by_protocol(self, protocol: AdapterProtocol) -> Optional[AdapterDescriptor]:
        with self._lock:
            for d in self._store.values():
                if d.protocol == protocol and d.enabled:
                    return d
        return None

    def first_for_service(self, service_type: ServiceType) -> Optional[AdapterDescriptor]:
        with self._lock:
            for d in self._store.values():
                if d.service_type == service_type and d.enabled:
                    return d
        return None

    def by_protocol(self, protocol: AdapterProtocol) -> List[AdapterDescriptor]:
        with self._lock:
            return [d for d in self._store.values() if d.protocol == protocol]

    def by_service(self, service_type: ServiceType) -> List[AdapterDescriptor]:
        with self._lock:
            return [d for d in self._store.values() if d.service_type == service_type]

    def all_enabled(self) -> List[AdapterDescriptor]:
        with self._lock:
            return [d for d in self._store.values() if d.enabled]

    def all_adapters(self) -> List[AdapterDescriptor]:
        with self._lock:
            return list(self._store.values())

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def supports_service(self, service_type: ServiceType) -> bool:
        return self.first_for_service(service_type) is not None

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
