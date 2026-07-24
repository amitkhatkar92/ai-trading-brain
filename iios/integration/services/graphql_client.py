"""
graphql_client.py — iios.integration.services
-----------------------------------------------
Provider-independent GraphQL client adapter.

MUST NOT import: gql, graphql-core, requests, httpx, or any HTTP library.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse


# ════════════════════════════════════════════════════════════════════════
# Abstract Interface
# ════════════════════════════════════════════════════════════════════════


class BaseGraphqlClient(ABC):
    """Abstract GraphQL client — implementors inject the actual library."""

    @abstractmethod
    def query(
        self,
        url:        str,
        document:   str,
        variables:  Optional[Dict[str, Any]] = None,
        headers:    Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        """Execute a GraphQL query and return the data dict."""

    @abstractmethod
    def mutate(
        self,
        url:        str,
        document:   str,
        variables:  Optional[Dict[str, Any]] = None,
        headers:    Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        """Execute a GraphQL mutation and return the data dict."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the GraphQL endpoint is reachable."""

    def execute(self, request: ConnectorRequest) -> ConnectorResponse:
        start = time.perf_counter_ns()
        try:
            cfg = request.connector_config
            operation = cfg.get("graphql_operation", "query").lower()
            document  = cfg.get("graphql_document", "{ __typename }")
            variables = cfg.get("graphql_variables", request.payload)
            if operation == "mutate":
                result = self.mutate(
                    url=request.endpoint, document=document,
                    variables=variables, headers=request.headers,
                    timeout_ms=request.timeout_ms,
                )
            else:
                result = self.query(
                    url=request.endpoint, document=document,
                    variables=variables, headers=request.headers,
                    timeout_ms=request.timeout_ms,
                )
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.success(
                request.request_id, data=result, latency_ms=latency_ms,
                adapter_id="graphql-client", transport="http",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.failure(
                request.request_id, error_message=str(exc), latency_ms=latency_ms,
                adapter_id="graphql-client", transport="http",
            )


# ════════════════════════════════════════════════════════════════════════
# Simulated Implementation
# ════════════════════════════════════════════════════════════════════════


class SimulatedGraphqlClient(BaseGraphqlClient):
    """In-process GraphQL simulation — no network I/O."""

    def query(
        self,
        url:        str,
        document:   str,
        variables:  Optional[Dict[str, Any]] = None,
        headers:    Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        return {"data": {}, "errors": None, "simulated": True, "document": document}

    def mutate(
        self,
        url:        str,
        document:   str,
        variables:  Optional[Dict[str, Any]] = None,
        headers:    Optional[Dict[str, str]] = None,
        timeout_ms: int = 30_000,
    ) -> Dict[str, Any]:
        return {"data": {}, "errors": None, "simulated": True, "document": document}

    def health_check(self) -> bool:
        return True
