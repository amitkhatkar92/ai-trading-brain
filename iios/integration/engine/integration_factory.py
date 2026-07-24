"""
integration_factory.py — iios.integration.engine
--------------------------------------------------
IntegrationEngineFactory — creates engine data objects with defaults.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .adapter_manager import AdapterDescriptor
from .connector_manager import ConnectorDescriptor
from .constants import (
    AdapterType,
    ConnectorType,
    DEFAULT_ENGINE_ID,
    DEFAULT_PRIORITY,
    DispatchMode,
    ProtocolType,
)
from .integration_context import IntegrationEngineContext
from .integration_request import IntegrationRequest
from .integration_response import IntegrationResponse
from .protocol_registry import ProtocolDescriptor

_log = get_logger(__name__)


class IntegrationEngineFactory:
    """Creates Integration Engine data objects with consistent defaults."""

    # ----------------------------------------------------------------
    # Request
    # ----------------------------------------------------------------

    def create_request(
        self,
        connector_type:  ConnectorType,
        adapter_type:    AdapterType    = AdapterType.GENERIC,
        protocol_type:   ProtocolType   = ProtocolType.INTERNAL,
        dispatch_mode:   DispatchMode   = DispatchMode.IMMEDIATE,
        *,
        endpoint:       str                       = "",
        payload:        Optional[Dict[str, Any]]  = None,
        headers:        Optional[Dict[str, str]]  = None,
        auth_config:    Optional[Dict[str, Any]]  = None,
        metadata:       Optional[Dict[str, Any]]  = None,
        priority:       int                       = DEFAULT_PRIORITY,
        request_id:     Optional[str]             = None,
    ) -> IntegrationRequest:
        return IntegrationRequest.create(
            connector_type = connector_type,
            adapter_type   = adapter_type,
            protocol_type  = protocol_type,
            dispatch_mode  = dispatch_mode,
            endpoint       = endpoint,
            payload        = payload,
            headers        = headers,
            auth_config    = auth_config,
            metadata       = metadata,
            priority       = priority,
            request_id     = request_id,
        )

    # ----------------------------------------------------------------
    # Context
    # ----------------------------------------------------------------

    def create_context(
        self,
        request:    IntegrationRequest,
        session_id: str,
        engine_id:  str = DEFAULT_ENGINE_ID,
    ) -> IntegrationEngineContext:
        return IntegrationEngineContext.create(
            request,
            session_id,
            engine_id = engine_id,
        )

    # ----------------------------------------------------------------
    # Response
    # ----------------------------------------------------------------

    def create_success_response(
        self,
        request:    IntegrationRequest,
        session_id: str,
        data:       Optional[Dict[str, Any]] = None,
        latency_ms: float = 0.0,
    ) -> IntegrationResponse:
        return IntegrationResponse.success_for(request, session_id, data, latency_ms)

    def create_failure_response(
        self,
        request:       IntegrationRequest,
        session_id:    str,
        error_message: str,
        latency_ms:    float = 0.0,
    ) -> IntegrationResponse:
        return IntegrationResponse.failure_for(
            request, session_id, error_message, latency_ms
        )

    # ----------------------------------------------------------------
    # Descriptors
    # ----------------------------------------------------------------

    def create_connector_descriptor(
        self,
        connector_type: ConnectorType,
        name:           str,
        *,
        version:      str                       = "1.0.0",
        capabilities: Optional[List[str]]       = None,
        metadata:     Optional[Dict[str, Any]]  = None,
        connector_id: Optional[str]             = None,
    ) -> ConnectorDescriptor:
        return ConnectorDescriptor.create(
            connector_type = connector_type,
            name           = name,
            version        = version,
            capabilities   = capabilities,
            metadata       = metadata,
            connector_id   = connector_id,
        )

    def create_adapter_descriptor(
        self,
        adapter_type:   AdapterType,
        connector_type: ConnectorType,
        name:           str,
        *,
        version:      str                       = "1.0.0",
        capabilities: Optional[List[str]]       = None,
        metadata:     Optional[Dict[str, Any]]  = None,
        adapter_id:   Optional[str]             = None,
    ) -> AdapterDescriptor:
        return AdapterDescriptor.create(
            adapter_type   = adapter_type,
            connector_type = connector_type,
            name           = name,
            version        = version,
            capabilities   = capabilities,
            metadata       = metadata,
            adapter_id     = adapter_id,
        )

    def create_protocol_descriptor(
        self,
        protocol_type: ProtocolType,
        name:          str,
        *,
        version:                  str                             = "1.0.0",
        supported_connector_types: Optional[List[ConnectorType]] = None,
        metadata:                 Optional[Dict[str, Any]]       = None,
        protocol_id:              Optional[str]                  = None,
    ) -> ProtocolDescriptor:
        return ProtocolDescriptor.create(
            protocol_type             = protocol_type,
            name                      = name,
            version                   = version,
            supported_connector_types = supported_connector_types,
            metadata                  = metadata,
            protocol_id               = protocol_id,
        )
