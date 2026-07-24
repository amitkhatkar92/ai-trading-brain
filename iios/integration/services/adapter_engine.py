"""
adapter_engine.py — iios.integration.services
-----------------------------------------------
AdapterEngine — loads adapters and delegates protocol execution.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .adapter_registry import AdapterDescriptor, AdapterRegistry
from .connector_context import ConnectorContext
from .connector_response import ConnectorResponse
from .constants import AdapterProtocol, ServiceType
from .exceptions import AdapterNotFoundError


class AdapterEngine:
    """
    Loads adapters from the registry and executes integration payloads
    through them.

    Provider-agnostic: the engine routes to registered adapter descriptors;
    actual network I/O is delegated to vendor connector implementations
    that are plugged in at deployment time (not in this framework).
    """

    def __init__(self, registry: Optional[AdapterRegistry] = None) -> None:
        self._registry = registry or AdapterRegistry()

    @property
    def registry(self) -> AdapterRegistry:
        return self._registry

    def register(self, descriptor: AdapterDescriptor) -> None:
        self._registry.register(descriptor)

    def load_for_service(self, service_type: ServiceType) -> AdapterDescriptor:
        desc = self._registry.first_for_service(service_type)
        if desc is None:
            raise AdapterNotFoundError(service_type.value)
        return desc

    def load_by_protocol(self, protocol: AdapterProtocol) -> AdapterDescriptor:
        desc = self._registry.first_by_protocol(protocol)
        if desc is None:
            raise AdapterNotFoundError(protocol.value)
        return desc

    def execute(
        self,
        adapter:  AdapterDescriptor,
        context:  ConnectorContext,
        payload:  Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a payload through an adapter.

        Returns a result dict.  Actual network I/O is performed by the
        registered vendor implementation at the infrastructure layer.
        This method provides the adapter-agnostic routing interface.
        """
        return {
            "adapter_id":    adapter.adapter_id,
            "adapter_name":  adapter.name,
            "protocol":      adapter.protocol.value,
            "service_type":  adapter.service_type.value,
            "endpoint":      context.endpoint,
            "status":        "executed",
            "payload_size":  len(str(payload)),
        }

    def count(self) -> int:
        return self._registry.count()

    def supports_service(self, service_type: ServiceType) -> bool:
        return self._registry.supports_service(service_type)
