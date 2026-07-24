"""
integration_gateway_registry.py — iios.integration.gateway
------------------------------------------------------------
IntegrationGatewayRegistry — tracks active gateway requests and
their corresponding responses.

Thread-safe.  Supports bounded capacity.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_REGISTRY_SIZE
from .exceptions import GatewayCapacityError
from .integration_gateway_request import IntegrationGatewayRequest
from .integration_gateway_response import IntegrationGatewayResponse


class IntegrationGatewayRegistry:
    """
    Thread-safe registry of in-flight and recently-completed gateway
    requests.

    ``register``   — marks a request as active
    ``set_response`` — attaches the completed response
    ``deregister`` — removes the entry
    ``get``        — retrieves the request by ID
    ``get_response`` — retrieves the response by request ID
    """

    def __init__(self, max_size: int = DEFAULT_MAX_REGISTRY_SIZE) -> None:
        self._requests:  Dict[str, IntegrationGatewayRequest]  = {}
        self._responses: Dict[str, IntegrationGatewayResponse] = {}
        self._max_size   = max_size
        self._lock       = threading.Lock()

    # ─── registration ─────────────────────────────────────────────────

    def register(self, request: IntegrationGatewayRequest) -> str:
        """
        Register an active request.

        Returns the request_id.
        Raises GatewayCapacityError if max_size is reached.
        """
        with self._lock:
            if len(self._requests) >= self._max_size:
                raise GatewayCapacityError(
                    f"Registry capacity ({self._max_size}) exceeded"
                )
            self._requests[request.request_id] = request
        return request.request_id

    def set_response(
        self,
        request_id: str,
        response:   IntegrationGatewayResponse,
    ) -> None:
        """Attach a completed response to an existing request entry."""
        with self._lock:
            self._responses[request_id] = response

    def deregister(self, request_id: str) -> bool:
        """Remove request and response for *request_id*. Returns True if found."""
        with self._lock:
            found = request_id in self._requests
            self._requests.pop(request_id, None)
            self._responses.pop(request_id, None)
        return found

    # ─── lookup ───────────────────────────────────────────────────────

    def get(self, request_id: str) -> Optional[IntegrationGatewayRequest]:
        with self._lock:
            return self._requests.get(request_id)

    def get_response(self, request_id: str) -> Optional[IntegrationGatewayResponse]:
        with self._lock:
            return self._responses.get(request_id)

    def exists(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._requests

    def has_response(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._responses

    def list_active(self) -> List[str]:
        """Return IDs of requests without a completed response."""
        with self._lock:
            return [
                rid for rid in self._requests
                if rid not in self._responses
            ]

    def list_all(self) -> List[str]:
        with self._lock:
            return list(self._requests.keys())

    # ─── management ───────────────────────────────────────────────────

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._requests)

    @property
    def active_count(self) -> int:
        with self._lock:
            return sum(1 for rid in self._requests if rid not in self._responses)

    def clear(self) -> int:
        with self._lock:
            n = len(self._requests)
            self._requests.clear()
            self._responses.clear()
        return n

    @property
    def max_size(self) -> int:
        return self._max_size
