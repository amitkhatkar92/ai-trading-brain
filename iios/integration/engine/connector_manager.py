"""
connector_manager.py — iios.integration.engine
------------------------------------------------
ConnectorDescriptor and ConnectorManager.

Manages connector registrations (metadata only).
Does NOT implement connector logic — that belongs to M4.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import ConnectorType, DEFAULT_MAX_CONNECTORS
from .exceptions import ConnectorNotFoundError, ConnectorRegistrationError


@dataclass(frozen=True)
class ConnectorDescriptor:
    """
    Immutable metadata record describing a registered connector.

    The connector itself is implemented in M4 (Integration Services Framework).
    This descriptor carries the registration metadata only.
    """
    connector_id:   str
    connector_type: ConnectorType
    name:           str
    version:        str
    capabilities:   tuple   # Tuple[str]
    metadata:       Dict[str, Any]
    registered_at:  str

    @classmethod
    def create(
        cls,
        connector_type: ConnectorType,
        name:           str,
        *,
        version:        str                       = "1.0.0",
        capabilities:   Optional[List[str]]       = None,
        metadata:       Optional[Dict[str, Any]]  = None,
        connector_id:   Optional[str]             = None,
    ) -> "ConnectorDescriptor":
        return cls(
            connector_id   = connector_id or f"conn-{uuid.uuid4().hex[:12]}",
            connector_type = connector_type,
            name           = name,
            version        = version,
            capabilities   = tuple(capabilities or []),
            metadata       = dict(metadata or {}),
            registered_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connector_id":   self.connector_id,
            "connector_type": self.connector_type.value,
            "name":           self.name,
            "version":        self.version,
            "capabilities":   list(self.capabilities),
            "metadata":       self.metadata,
            "registered_at":  self.registered_at,
        }


class ConnectorManager:
    """
    Thread-safe registry of ConnectorDescriptor objects.

    Manages connector registrations for the Integration Engine.
    Does NOT implement or invoke connector logic.
    """

    def __init__(self, max_connectors: int = DEFAULT_MAX_CONNECTORS) -> None:
        self._max   = max_connectors
        self._by_id: Dict[str, ConnectorDescriptor] = {}
        self._by_type: Dict[ConnectorType, List[str]] = {}
        self._lock  = threading.Lock()

    # ----------------------------------------------------------------
    # Registration
    # ----------------------------------------------------------------

    def register(self, descriptor: ConnectorDescriptor) -> None:
        with self._lock:
            if len(self._by_id) >= self._max and descriptor.connector_id not in self._by_id:
                raise ConnectorRegistrationError(
                    f"Connector registry capacity exceeded: {self._max}"
                )
            self._by_id[descriptor.connector_id] = descriptor
            self._by_type.setdefault(descriptor.connector_type, []).append(
                descriptor.connector_id
            )

    def deregister(self, connector_id: str) -> bool:
        with self._lock:
            d = self._by_id.pop(connector_id, None)
            if d is None:
                return False
            ids = self._by_type.get(d.connector_type, [])
            if connector_id in ids:
                ids.remove(connector_id)
            return True

    # ----------------------------------------------------------------
    # Lookup
    # ----------------------------------------------------------------

    def get(self, connector_id: str) -> Optional[ConnectorDescriptor]:
        with self._lock:
            return self._by_id.get(connector_id)

    def get_or_raise(self, connector_id: str) -> ConnectorDescriptor:
        d = self.get(connector_id)
        if d is None:
            raise ConnectorNotFoundError(connector_id)
        return d

    def first_by_type(
        self, connector_type: ConnectorType
    ) -> Optional[ConnectorDescriptor]:
        with self._lock:
            ids = self._by_type.get(connector_type, [])
            if not ids:
                return None
            return self._by_id.get(ids[0])

    def by_type(self, connector_type: ConnectorType) -> List[ConnectorDescriptor]:
        with self._lock:
            ids = list(self._by_type.get(connector_type, []))
        return [d for cid in ids if (d := self._by_id.get(cid))]

    def supports(self, connector_type: ConnectorType) -> bool:
        with self._lock:
            return bool(self._by_type.get(connector_type))

    def all_connectors(self) -> List[ConnectorDescriptor]:
        with self._lock:
            return list(self._by_id.values())

    def count(self) -> int:
        with self._lock:
            return len(self._by_id)

    def clear(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._by_type.clear()
