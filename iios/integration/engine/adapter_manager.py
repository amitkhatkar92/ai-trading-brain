"""
adapter_manager.py — iios.integration.engine
----------------------------------------------
AdapterDescriptor and AdapterManager.

Manages adapter registrations (metadata only).
Does NOT implement adapter logic — that belongs to M4.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import AdapterType, ConnectorType, DEFAULT_MAX_ADAPTERS
from .exceptions import AdapterNotFoundError, AdapterRegistrationError


@dataclass(frozen=True)
class AdapterDescriptor:
    """
    Immutable metadata record describing a registered adapter.

    The adapter itself is implemented in M4 (Integration Services Framework).
    This descriptor carries the registration metadata only.
    """
    adapter_id:      str
    adapter_type:    AdapterType
    connector_type:  ConnectorType   # which connector type this adapter serves
    name:            str
    version:         str
    capabilities:    tuple   # Tuple[str]
    metadata:        Dict[str, Any]
    registered_at:   str

    @classmethod
    def create(
        cls,
        adapter_type:   AdapterType,
        connector_type: ConnectorType,
        name:           str,
        *,
        version:       str                       = "1.0.0",
        capabilities:  Optional[List[str]]       = None,
        metadata:      Optional[Dict[str, Any]]  = None,
        adapter_id:    Optional[str]             = None,
    ) -> "AdapterDescriptor":
        return cls(
            adapter_id     = adapter_id or f"adap-{uuid.uuid4().hex[:12]}",
            adapter_type   = adapter_type,
            connector_type = connector_type,
            name           = name,
            version        = version,
            capabilities   = tuple(capabilities or []),
            metadata       = dict(metadata or {}),
            registered_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id":     self.adapter_id,
            "adapter_type":   self.adapter_type.value,
            "connector_type": self.connector_type.value,
            "name":           self.name,
            "version":        self.version,
            "capabilities":   list(self.capabilities),
            "metadata":       self.metadata,
            "registered_at":  self.registered_at,
        }


class AdapterManager:
    """
    Thread-safe registry of AdapterDescriptor objects.

    Manages adapter registrations for the Integration Engine.
    Does NOT implement or invoke adapter logic.
    """

    def __init__(self, max_adapters: int = DEFAULT_MAX_ADAPTERS) -> None:
        self._max    = max_adapters
        self._by_id: Dict[str, AdapterDescriptor] = {}
        self._by_type: Dict[AdapterType, List[str]] = {}
        self._by_connector: Dict[ConnectorType, List[str]] = {}
        self._lock   = threading.Lock()

    # ----------------------------------------------------------------
    # Registration
    # ----------------------------------------------------------------

    def register(self, descriptor: AdapterDescriptor) -> None:
        with self._lock:
            if len(self._by_id) >= self._max and descriptor.adapter_id not in self._by_id:
                raise AdapterRegistrationError(
                    f"Adapter registry capacity exceeded: {self._max}"
                )
            self._by_id[descriptor.adapter_id] = descriptor
            self._by_type.setdefault(descriptor.adapter_type, []).append(
                descriptor.adapter_id
            )
            self._by_connector.setdefault(descriptor.connector_type, []).append(
                descriptor.adapter_id
            )

    def deregister(self, adapter_id: str) -> bool:
        with self._lock:
            d = self._by_id.pop(adapter_id, None)
            if d is None:
                return False
            for lst in (
                self._by_type.get(d.adapter_type, []),
                self._by_connector.get(d.connector_type, []),
            ):
                if adapter_id in lst:
                    lst.remove(adapter_id)
            return True

    # ----------------------------------------------------------------
    # Lookup
    # ----------------------------------------------------------------

    def get(self, adapter_id: str) -> Optional[AdapterDescriptor]:
        with self._lock:
            return self._by_id.get(adapter_id)

    def get_or_raise(self, adapter_id: str) -> AdapterDescriptor:
        d = self.get(adapter_id)
        if d is None:
            raise AdapterNotFoundError(adapter_id)
        return d

    def first_for_connector(
        self, connector_type: ConnectorType
    ) -> Optional[AdapterDescriptor]:
        with self._lock:
            ids = self._by_connector.get(connector_type, [])
            if not ids:
                return None
            return self._by_id.get(ids[0])

    def for_connector(
        self, connector_type: ConnectorType
    ) -> List[AdapterDescriptor]:
        with self._lock:
            ids = list(self._by_connector.get(connector_type, []))
        return [d for aid in ids if (d := self._by_id.get(aid))]

    def by_type(self, adapter_type: AdapterType) -> List[AdapterDescriptor]:
        with self._lock:
            ids = list(self._by_type.get(adapter_type, []))
        return [d for aid in ids if (d := self._by_id.get(aid))]

    def supports_connector(self, connector_type: ConnectorType) -> bool:
        with self._lock:
            return bool(self._by_connector.get(connector_type))

    def all_adapters(self) -> List[AdapterDescriptor]:
        with self._lock:
            return list(self._by_id.values())

    def count(self) -> int:
        with self._lock:
            return len(self._by_id)

    def clear(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._by_type.clear()
            self._by_connector.clear()
