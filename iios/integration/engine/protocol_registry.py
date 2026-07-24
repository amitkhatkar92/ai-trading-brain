"""
protocol_registry.py — iios.integration.engine
------------------------------------------------
ProtocolDescriptor and ProtocolRegistry.

Manages protocol registrations (metadata only).
Does NOT implement protocol logic — that belongs to M4.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import ConnectorType, DEFAULT_MAX_PROTOCOLS, ProtocolType
from .exceptions import ProtocolNotRegisteredError


@dataclass(frozen=True)
class ProtocolDescriptor:
    """
    Immutable metadata record describing a registered protocol.

    The protocol implementation lives in M4 (Integration Services Framework).
    This descriptor carries the registration metadata only.
    """
    protocol_id:              str
    protocol_type:            ProtocolType
    name:                     str
    version:                  str
    supported_connector_types: tuple   # Tuple[ConnectorType]
    metadata:                 Dict[str, Any]
    registered_at:            str

    @classmethod
    def create(
        cls,
        protocol_type: ProtocolType,
        name:          str,
        *,
        version:                  str                             = "1.0.0",
        supported_connector_types: Optional[List[ConnectorType]] = None,
        metadata:                 Optional[Dict[str, Any]]       = None,
        protocol_id:              Optional[str]                  = None,
    ) -> "ProtocolDescriptor":
        return cls(
            protocol_id               = protocol_id or f"proto-{uuid.uuid4().hex[:12]}",
            protocol_type             = protocol_type,
            name                      = name,
            version                   = version,
            supported_connector_types = tuple(supported_connector_types or []),
            metadata                  = dict(metadata or {}),
            registered_at             = datetime.now(tz=timezone.utc).isoformat(),
        )

    def supports_connector(self, connector_type: ConnectorType) -> bool:
        return (
            not self.supported_connector_types
            or connector_type in self.supported_connector_types
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol_id":               self.protocol_id,
            "protocol_type":             self.protocol_type.value,
            "name":                      self.name,
            "version":                   self.version,
            "supported_connector_types": [c.value for c in self.supported_connector_types],
            "metadata":                  self.metadata,
            "registered_at":             self.registered_at,
        }


class ProtocolRegistry:
    """
    Thread-safe registry of ProtocolDescriptor objects.

    Manages protocol registrations for the Integration Engine.
    Does NOT implement or invoke protocol logic.
    """

    def __init__(self, max_protocols: int = DEFAULT_MAX_PROTOCOLS) -> None:
        self._max      = max_protocols
        self._by_id:   Dict[str, ProtocolDescriptor]         = {}
        self._by_type: Dict[ProtocolType, List[str]]         = {}
        self._lock     = threading.Lock()

    # ----------------------------------------------------------------
    # Registration
    # ----------------------------------------------------------------

    def register(self, descriptor: ProtocolDescriptor) -> None:
        with self._lock:
            if len(self._by_id) >= self._max and descriptor.protocol_id not in self._by_id:
                raise ProtocolNotRegisteredError(
                    f"Protocol registry capacity exceeded: {self._max}"
                )
            self._by_id[descriptor.protocol_id] = descriptor
            self._by_type.setdefault(descriptor.protocol_type, []).append(
                descriptor.protocol_id
            )

    def deregister(self, protocol_id: str) -> bool:
        with self._lock:
            d = self._by_id.pop(protocol_id, None)
            if d is None:
                return False
            ids = self._by_type.get(d.protocol_type, [])
            if protocol_id in ids:
                ids.remove(protocol_id)
            return True

    # ----------------------------------------------------------------
    # Lookup
    # ----------------------------------------------------------------

    def get(self, protocol_id: str) -> Optional[ProtocolDescriptor]:
        with self._lock:
            return self._by_id.get(protocol_id)

    def get_or_raise(self, protocol_id: str) -> ProtocolDescriptor:
        d = self.get(protocol_id)
        if d is None:
            raise ProtocolNotRegisteredError(protocol_id)
        return d

    def first_by_type(
        self, protocol_type: ProtocolType
    ) -> Optional[ProtocolDescriptor]:
        with self._lock:
            ids = self._by_type.get(protocol_type, [])
            if not ids:
                return None
            return self._by_id.get(ids[0])

    def by_type(self, protocol_type: ProtocolType) -> List[ProtocolDescriptor]:
        with self._lock:
            ids = list(self._by_type.get(protocol_type, []))
        return [d for pid in ids if (d := self._by_id.get(pid))]

    def is_registered(self, protocol_type: ProtocolType) -> bool:
        with self._lock:
            return bool(self._by_type.get(protocol_type))

    def supports_connector(
        self, protocol_type: ProtocolType, connector_type: ConnectorType
    ) -> bool:
        with self._lock:
            ids = self._by_type.get(protocol_type, [])
        for pid in ids:
            d = self._by_id.get(pid)
            if d and d.supports_connector(connector_type):
                return True
        return False

    def all_protocols(self) -> List[ProtocolDescriptor]:
        with self._lock:
            return list(self._by_id.values())

    def count(self) -> int:
        with self._lock:
            return len(self._by_id)

    def clear(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._by_type.clear()
