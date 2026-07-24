"""
rest_client.py — iios.integration.services
--------------------------------------------
Provider-independent REST API client adapter.

MUST NOT import: requests, httpx, aiohttp, or any HTTP library.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse
from .constants import AdapterProtocol


# ════════════════════════════════════════════════════════════════════════
# Abstract Interface
# ════════════════════════════════════════════════════════════════════════


class BaseRestClient(ABC):
    """Abstract REST client — implementors inject HTTP libraries."""

    @abstractmethod
    def call(
        self,
        method:     str,
        url:        str,
        payload:    Optional[Dict[str, Any]] = None,
        headers:    Optional[Dict[str, str]] = None,
        params:     Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        """Execute a REST call and return a normalised dict."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the REST transport is reachable."""

    def execute(self, request: ConnectorRequest) -> ConnectorResponse:
        start = time.perf_counter_ns()
        try:
            method = request.connector_config.get("http_method", "POST").upper()
            result = self.call(
                method     = method,
                url        = request.endpoint,
                payload    = request.payload,
                headers    = request.headers,
                timeout_ms = request.timeout_ms,
            )
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.success(
                request.request_id, data=result, latency_ms=latency_ms,
                adapter_id="rest-client", transport="http",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.failure(
                request.request_id, error_message=str(exc), latency_ms=latency_ms,
                adapter_id="rest-client", transport="http",
            )


# ════════════════════════════════════════════════════════════════════════
# Simulated Implementation
# ════════════════════════════════════════════════════════════════════════


class SimulatedRestClient(BaseRestClient):
    """In-process REST simulation — no network I/O."""

    def call(
        self,
        method:     str,
        url:        str,
        payload:    Optional[Dict[str, Any]] = None,
        headers:    Optional[Dict[str, str]] = None,
        params:     Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        return {
            "status_code": 200,
            "method":      method,
            "url":         url,
            "body":        payload or {},
            "simulated":   True,
        }

    def health_check(self) -> bool:
        return True
