"""
protocol_engine.py — iios.integration.services
------------------------------------------------
ProtocolEngine — coordinates protocol selection and execution.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .connector_context import ConnectorContext
from .protocol_registry import ProtocolDescriptor, ProtocolRegistry
from .constants import AdapterProtocol, TransportType


class ProtocolEngine:
    """
    Coordinates protocol selection and execution routing.

    Provider-independent.  Routes protocol invocations to registered
    protocol handlers.  Does not implement any vendor-specific protocol.
    """

    def __init__(self, registry: Optional[ProtocolRegistry] = None) -> None:
        self._registry = registry or ProtocolRegistry()

    @property
    def registry(self) -> ProtocolRegistry:
        return self._registry

    def register(self, descriptor: ProtocolDescriptor) -> None:
        self._registry.register(descriptor)

    def resolve(self, protocol: AdapterProtocol) -> Optional[ProtocolDescriptor]:
        return self._registry.first_by_protocol(protocol)

    def is_supported(self, protocol: AdapterProtocol) -> bool:
        return self._registry.is_registered(protocol)

    def execute(
        self,
        descriptor: ProtocolDescriptor,
        context:    ConnectorContext,
        payload:    Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a protocol operation through the registered handler.

        Returns a result dict.  Actual protocol implementation is
        plugged in at the infrastructure layer.
        """
        return {
            "protocol_id":    descriptor.protocol_id,
            "protocol":       descriptor.protocol.value,
            "transport":      descriptor.transport_type.value,
            "endpoint":       context.endpoint,
            "status":         "executed",
            "payload_keys":   list(payload.keys()),
        }

    def count(self) -> int:
        return self._registry.count()
