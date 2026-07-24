"""
protocol_registry.py — iios.integration.services
--------------------------------------------------
ProtocolRegistry — registry of protocol handler descriptors.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import AdapterProtocol, DEFAULT_MAX_PROTOCOLS, TransportType


@dataclass(frozen=True)
class ProtocolDescriptor:
    """Immutable descriptor for a registered protocol handler."""

    protocol_id:     str
    name:            str
    protocol:        AdapterProtocol
    transport_type:  TransportType
    version:         str
    features:        tuple       # e.g. ("streaming", "bidirectional")
    metadata:        Dict[str, Any]
    registered_at:   str

    @classmethod
    def create(
        cls,
        name:           str,
        protocol:       AdapterProtocol,
        transport_type: TransportType    = TransportType.HTTP,
        *,
        version:        str                      = "1.0.0",
        features:       Optional[List[str]]      = None,
        metadata:       Optional[Dict[str, Any]] = None,
        protocol_id:    Optional[str]            = None,
    ) -> "ProtocolDescriptor":
        return cls(
            protocol_id   = protocol_id or f"proto-{uuid.uuid4().hex[:12]}",
            name          = name,
            protocol      = protocol,
            transport_type= transport_type,
            version       = version,
            features      = tuple(features or []),
            metadata      = dict(metadata or {}),
            registered_at = datetime.now(timezone.utc).isoformat(),
        )

    def has_feature(self, feature: str) -> bool:
        return feature in self.features

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol_id":   self.protocol_id,
            "name":          self.name,
            "protocol":      self.protocol.value,
            "transport_type":self.transport_type.value,
            "version":       self.version,
            "features":      list(self.features),
            "metadata":      self.metadata,
            "registered_at": self.registered_at,
        }


class ProtocolRegistry:
    """Thread-safe registry for protocol handler descriptors."""

    def __init__(self, max_protocols: int = DEFAULT_MAX_PROTOCOLS) -> None:
        self._max   = max_protocols
        self._store: Dict[str, ProtocolDescriptor] = {}
        self._lock  = threading.Lock()

    def register(self, descriptor: ProtocolDescriptor) -> None:
        with self._lock:
            self._store[descriptor.protocol_id] = descriptor

    def deregister(self, protocol_id: str) -> bool:
        with self._lock:
            if protocol_id in self._store:
                del self._store[protocol_id]
                return True
        return False

    def get(self, protocol_id: str) -> Optional[ProtocolDescriptor]:
        with self._lock:
            return self._store.get(protocol_id)

    def first_by_protocol(self, protocol: AdapterProtocol) -> Optional[ProtocolDescriptor]:
        with self._lock:
            for d in self._store.values():
                if d.protocol == protocol:
                    return d
        return None

    def by_protocol(self, protocol: AdapterProtocol) -> List[ProtocolDescriptor]:
        with self._lock:
            return [d for d in self._store.values() if d.protocol == protocol]

    def is_registered(self, protocol: AdapterProtocol) -> bool:
        return self.first_by_protocol(protocol) is not None

    def all_protocols(self) -> List[ProtocolDescriptor]:
        with self._lock:
            return list(self._store.values())

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
