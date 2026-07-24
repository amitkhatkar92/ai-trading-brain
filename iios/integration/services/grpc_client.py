"""
grpc_client.py — iios.integration.services
--------------------------------------------
Provider-independent gRPC client adapter.

MUST NOT import: grpc, grpcio, protobuf, or any gRPC library.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse


# ════════════════════════════════════════════════════════════════════════
# Abstract Interface
# ════════════════════════════════════════════════════════════════════════


class BaseGrpcClient(ABC):
    """Abstract gRPC client — implementors inject the gRPC library."""

    @abstractmethod
    def unary(
        self,
        service:    str,
        method:     str,
        request_pb: Dict[str, Any],
        metadata:   Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        """Execute a unary gRPC call."""

    @abstractmethod
    def server_stream(
        self,
        service:    str,
        method:     str,
        request_pb: Dict[str, Any],
        metadata:   Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> list[Dict[str, Any]]:
        """Execute a server-streaming gRPC call and return all messages."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the gRPC channel is ready."""

    def execute(self, request: ConnectorRequest) -> ConnectorResponse:
        start = time.perf_counter_ns()
        try:
            cfg      = request.connector_config
            service  = cfg.get("grpc_service", "")
            method   = cfg.get("grpc_method", "")
            streaming = cfg.get("grpc_streaming", False)
            if streaming:
                data = {"messages": self.server_stream(
                    service=service, method=method,
                    request_pb=request.payload,
                    timeout_ms=request.timeout_ms,
                )}
            else:
                data = self.unary(
                    service=service, method=method,
                    request_pb=request.payload,
                    timeout_ms=request.timeout_ms,
                )
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.success(
                request.request_id, data=data, latency_ms=latency_ms,
                adapter_id="grpc-client", transport="grpc",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.failure(
                request.request_id, error_message=str(exc), latency_ms=latency_ms,
                adapter_id="grpc-client", transport="grpc",
            )


# ════════════════════════════════════════════════════════════════════════
# Simulated Implementation
# ════════════════════════════════════════════════════════════════════════


class SimulatedGrpcClient(BaseGrpcClient):
    """In-process gRPC simulation — no network I/O."""

    def unary(
        self,
        service:    str,
        method:     str,
        request_pb: Dict[str, Any],
        metadata:   Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        return {"service": service, "method": method, "response": {}, "simulated": True}

    def server_stream(
        self,
        service:    str,
        method:     str,
        request_pb: Dict[str, Any],
        metadata:   Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> list[Dict[str, Any]]:
        return [{"service": service, "method": method, "index": 0, "simulated": True}]

    def health_check(self) -> bool:
        return True
