"""
integration_registry.py — iios.integration.engine
---------------------------------------------------
IntegrationEngineRegistry — unified facade over ConnectorManager,
AdapterManager, and ProtocolRegistry.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .adapter_manager import AdapterDescriptor, AdapterManager
from .connector_manager import ConnectorDescriptor, ConnectorManager
from .constants import (
    AdapterType,
    ConnectorType,
    DEFAULT_MAX_ADAPTERS,
    DEFAULT_MAX_CONNECTORS,
    DEFAULT_MAX_PROTOCOLS,
    ProtocolType,
)
from .protocol_registry import ProtocolDescriptor, ProtocolRegistry


class IntegrationEngineRegistry:
    """
    Unified registry facade for the Integration Engine.

    Provides a single entry-point for registering and querying
    connectors, adapters, and protocols.
    """

    def __init__(
        self,
        connector_manager: Optional[ConnectorManager] = None,
        adapter_manager:   Optional[AdapterManager]   = None,
        protocol_registry: Optional[ProtocolRegistry] = None,
        *,
        max_connectors: int = DEFAULT_MAX_CONNECTORS,
        max_adapters:   int = DEFAULT_MAX_ADAPTERS,
        max_protocols:  int = DEFAULT_MAX_PROTOCOLS,
    ) -> None:
        self._connectors = connector_manager or ConnectorManager(max_connectors)
        self._adapters   = adapter_manager   or AdapterManager(max_adapters)
        self._protocols  = protocol_registry or ProtocolRegistry(max_protocols)

    # ----------------------------------------------------------------
    # Convenience properties
    # ----------------------------------------------------------------

    @property
    def connector_manager(self) -> ConnectorManager:
        return self._connectors

    @property
    def adapter_manager(self) -> AdapterManager:
        return self._adapters

    @property
    def protocol_registry(self) -> ProtocolRegistry:
        return self._protocols

    # ----------------------------------------------------------------
    # Registration
    # ----------------------------------------------------------------

    def register_connector(self, descriptor: ConnectorDescriptor) -> None:
        self._connectors.register(descriptor)

    def register_adapter(self, descriptor: AdapterDescriptor) -> None:
        self._adapters.register(descriptor)

    def register_protocol(self, descriptor: ProtocolDescriptor) -> None:
        self._protocols.register(descriptor)

    # ----------------------------------------------------------------
    # Lookup
    # ----------------------------------------------------------------

    def get_connector(
        self, connector_type: ConnectorType
    ) -> Optional[ConnectorDescriptor]:
        return self._connectors.first_by_type(connector_type)

    def get_adapter_for(
        self, connector_type: ConnectorType
    ) -> Optional[AdapterDescriptor]:
        return self._adapters.first_for_connector(connector_type)

    def get_protocol(
        self, protocol_type: ProtocolType
    ) -> Optional[ProtocolDescriptor]:
        return self._protocols.first_by_type(protocol_type)

    def has_connector(self, connector_type: ConnectorType) -> bool:
        return self._connectors.supports(connector_type)

    def has_adapter_for(self, connector_type: ConnectorType) -> bool:
        return self._adapters.supports_connector(connector_type)

    def has_protocol(self, protocol_type: ProtocolType) -> bool:
        return self._protocols.is_registered(protocol_type)

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        return {
            "connector_count": self._connectors.count(),
            "adapter_count":   self._adapters.count(),
            "protocol_count":  self._protocols.count(),
        }

    def clear(self) -> None:
        self._connectors.clear()
        self._adapters.clear()
        self._protocols.clear()
