"""
http_client.py — iios.integration.services
--------------------------------------------
Provider-independent HTTP client adapter interface.

Defines the abstract contract that HTTP providers must implement.
Includes a SimulatedHttpClient for testing and framework validation.

MUST NOT import: requests, httpx, aiohttp, urllib3 or any HTTP library.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse
from .constants import AdapterProtocol, ServiceResponseStatus


# ════════════════════════════════════════════════════════════════════════
# Abstract Interface
# ════════════════════════════════════════════════════════════════════════


class BaseHttpClient(ABC):
    """
    Provider-independent HTTP client interface.

    Implementors inject vendor-specific HTTP libraries at deployment.
    The framework only depends on this contract.
    """

    @abstractmethod
    def get(
        self,
        url:     str,
        headers: Optional[Dict[str, str]] = None,
        params:  Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        """Perform an HTTP GET and return a normalised response dict."""

    @abstractmethod
    def post(
        self,
        url:     str,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        """Perform an HTTP POST and return a normalised response dict."""

    @abstractmethod
    def put(
        self,
        url:     str,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        """Perform an HTTP PUT and return a normalised response dict."""

    @abstractmethod
    def delete(
        self,
        url:     str,
        headers: Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        """Perform an HTTP DELETE and return a normalised response dict."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the HTTP transport is available."""

    def execute(
        self,
        request:   ConnectorRequest,
        operation: str = "post",
    ) -> ConnectorResponse:
        """
        Dispatch a ConnectorRequest to the appropriate HTTP method.
        Returns a ConnectorResponse.
        """
        start = time.perf_counter_ns()
        try:
            method = operation.lower()
            if method == "get":
                data = self.get(
                    request.endpoint,
                    headers    = request.headers,
                    timeout_ms = request.timeout_ms,
                )
            elif method == "put":
                data = self.put(
                    request.endpoint,
                    payload    = request.payload,
                    headers    = request.headers,
                    timeout_ms = request.timeout_ms,
                )
            elif method == "delete":
                data = self.delete(
                    request.endpoint,
                    headers    = request.headers,
                    timeout_ms = request.timeout_ms,
                )
            else:  # post (default)
                data = self.post(
                    request.endpoint,
                    payload    = request.payload,
                    headers    = request.headers,
                    timeout_ms = request.timeout_ms,
                )
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.success(
                request.request_id, data=data, latency_ms=latency_ms,
                adapter_id="http-client", transport="http",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.failure(
                request.request_id, error_message=str(exc), latency_ms=latency_ms,
                adapter_id="http-client", transport="http",
            )


# ════════════════════════════════════════════════════════════════════════
# Simulated Implementation (for framework validation — no network I/O)
# ════════════════════════════════════════════════════════════════════════


class SimulatedHttpClient(BaseHttpClient):
    """
    In-process simulation of an HTTP client.

    Returns structured mock responses so the full integration workflow
    can be validated without any network dependency.
    """

    def get(
        self,
        url:        str,
        headers:    Optional[Dict[str, str]] = None,
        params:     Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        return {
            "status_code": 200,
            "method":      "GET",
            "url":         url,
            "body":        {},
            "headers":     {},
            "simulated":   True,
        }

    def post(
        self,
        url:        str,
        payload:    Optional[Dict[str, Any]] = None,
        headers:    Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        return {
            "status_code": 200,
            "method":      "POST",
            "url":         url,
            "body":        payload or {},
            "headers":     {},
            "simulated":   True,
        }

    def put(
        self,
        url:        str,
        payload:    Optional[Dict[str, Any]] = None,
        headers:    Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        return {
            "status_code": 200,
            "method":      "PUT",
            "url":         url,
            "body":        payload or {},
            "headers":     {},
            "simulated":   True,
        }

    def delete(
        self,
        url:        str,
        headers:    Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        return {
            "status_code": 200,
            "method":      "DELETE",
            "url":         url,
            "body":        {},
            "headers":     {},
            "simulated":   True,
        }

    def health_check(self) -> bool:
        return True
