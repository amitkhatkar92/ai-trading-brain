"""
workflow_gateway_factory.py — iios.workflow.gateway
----------------------------------------------------
WorkflowGatewayFactory — fluent factory for creating standard
gateway objects with sensible defaults.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .constants import DEFAULT_ENTERPRISE_ID, GatewayRequestType
from .workflow_gateway_context import WorkflowGatewayContext
from .workflow_gateway_request import WorkflowGatewayRequest
from .workflow_gateway_response import WorkflowGatewayResponse


class WorkflowGatewayFactory:
    """
    Fluent factory for standard gateway objects.

    All methods are stateless and thread-safe.
    """

    @staticmethod
    def create_submit_request(
        workflow_id:   str,
        workflow_name: str               = "",
        *,
        enterprise_id: str               = DEFAULT_ENTERPRISE_ID,
        correlation_id: str              = "",
        trace_id:      str               = "",
        priority:      int               = 1,
        payload:       Optional[Dict[str, Any]] = None,
        configuration: Optional[Dict[str, Any]] = None,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> WorkflowGatewayRequest:
        return WorkflowGatewayRequest.create(
            workflow_id    = workflow_id,
            workflow_name  = workflow_name or workflow_id,
            request_type   = GatewayRequestType.SUBMIT,
            enterprise_id  = enterprise_id,
            correlation_id = correlation_id,
            trace_id       = trace_id,
            priority       = priority,
            payload        = payload,
            configuration  = configuration,
            metadata       = metadata,
        )

    @staticmethod
    def create_query_request(
        workflow_id:    str,
        *,
        enterprise_id:  str  = DEFAULT_ENTERPRISE_ID,
        correlation_id: str  = "",
    ) -> WorkflowGatewayRequest:
        return WorkflowGatewayRequest.create(
            workflow_id    = workflow_id,
            request_type   = GatewayRequestType.QUERY,
            enterprise_id  = enterprise_id,
            correlation_id = correlation_id,
        )

    @staticmethod
    def create_cancel_request(
        workflow_id:    str,
        *,
        enterprise_id:  str  = DEFAULT_ENTERPRISE_ID,
        correlation_id: str  = "",
    ) -> WorkflowGatewayRequest:
        return WorkflowGatewayRequest.create(
            workflow_id    = workflow_id,
            request_type   = GatewayRequestType.CANCEL,
            enterprise_id  = enterprise_id,
            correlation_id = correlation_id,
        )

    @staticmethod
    def create_retry_request(
        workflow_id:    str,
        *,
        enterprise_id:  str  = DEFAULT_ENTERPRISE_ID,
        correlation_id: str  = "",
        payload:        Optional[Dict[str, Any]] = None,
    ) -> WorkflowGatewayRequest:
        return WorkflowGatewayRequest.create(
            workflow_id    = workflow_id,
            request_type   = GatewayRequestType.RETRY,
            enterprise_id  = enterprise_id,
            correlation_id = correlation_id,
            payload        = payload,
        )

    @staticmethod
    def create_validate_request(
        workflow_id:    str,
        *,
        enterprise_id:  str  = DEFAULT_ENTERPRISE_ID,
        correlation_id: str  = "",
    ) -> WorkflowGatewayRequest:
        return WorkflowGatewayRequest.create(
            workflow_id    = workflow_id,
            request_type   = GatewayRequestType.VALIDATE,
            enterprise_id  = enterprise_id,
            correlation_id = correlation_id,
        )

    @staticmethod
    def create_context(
        request:    WorkflowGatewayRequest,
        gateway_id: str,
        *,
        component_context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowGatewayContext:
        return WorkflowGatewayContext.create(
            request           = request,
            gateway_id        = gateway_id,
            component_context = component_context,
        )

    @staticmethod
    def create_success_response(
        request:            WorkflowGatewayRequest,
        *,
        session_id:         str                    = "",
        snapshot_id:        str                    = "",
        data:               Optional[Dict[str, Any]] = None,
        gateway_latency_ms: float                  = 0.0,
    ) -> WorkflowGatewayResponse:
        return WorkflowGatewayResponse.success_for(
            request,
            session_id         = session_id,
            snapshot_id        = snapshot_id,
            data               = data,
            gateway_latency_ms = gateway_latency_ms,
        )

    @staticmethod
    def create_failure_response(
        request:            WorkflowGatewayRequest,
        error:              str,
        *,
        gateway_latency_ms: float = 0.0,
    ) -> WorkflowGatewayResponse:
        return WorkflowGatewayResponse.failure_for(
            request,
            error,
            gateway_latency_ms = gateway_latency_ms,
        )
