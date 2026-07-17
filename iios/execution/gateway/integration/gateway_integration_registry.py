"""iios/execution/gateway/integration/gateway_integration_registry.py
==================================================
GatewayIntegrationRegistry — thread-safe store for integration
requests and their corresponding responses.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import (
    DEFAULT_MAX_REQUESTS,
    IntegrationRequestStatus,
    TERMINAL_REQUEST_STATUSES,
)
from .exceptions import (
    IntegrationCapacityError,
    IntegrationRequestNotFoundError,
)
from .gateway_integration_request import GatewayIntegrationRequest
from .gateway_integration_response import GatewayIntegrationResponse


class GatewayIntegrationRegistry:
    """
    Thread-safe registry for integration requests and responses.

    Write operations are permitted regardless of lifecycle state
    (the engine guards state before calling into the registry).
    """

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS) -> None:
        self._max_requests = max(1, max_requests)
        self._requests:  Dict[str, GatewayIntegrationRequest]  = {}
        self._responses: Dict[str, GatewayIntegrationResponse] = {}
        self._lock = threading.RLock()

    # ── Requests ──────────────────────────────────────────────────────────────

    def store_request(self, request: GatewayIntegrationRequest) -> None:
        with self._lock:
            if len(self._requests) >= self._max_requests:
                raise IntegrationCapacityError(self._max_requests)
            self._requests[request.request_id] = request

    def get_request(self, request_id: str) -> GatewayIntegrationRequest:
        with self._lock:
            if request_id not in self._requests:
                raise IntegrationRequestNotFoundError(request_id)
            return self._requests[request_id]

    def get_request_optional(
        self, request_id: str
    ) -> Optional[GatewayIntegrationRequest]:
        with self._lock:
            return self._requests.get(request_id)

    def all_requests(self) -> List[GatewayIntegrationRequest]:
        with self._lock:
            return list(self._requests.values())

    def requests_by_execution_id(
        self, execution_id: str
    ) -> List[GatewayIntegrationRequest]:
        with self._lock:
            return [r for r in self._requests.values()
                    if r.execution_id == execution_id]

    def pending_requests(self) -> List[GatewayIntegrationRequest]:
        with self._lock:
            return [r for r in self._requests.values()
                    if r.status not in TERMINAL_REQUEST_STATUSES]

    # ── Responses ─────────────────────────────────────────────────────────────

    def store_response(self, response: GatewayIntegrationResponse) -> None:
        with self._lock:
            self._responses[response.request_id] = response

    def get_response(
        self, request_id: str
    ) -> Optional[GatewayIntegrationResponse]:
        with self._lock:
            return self._responses.get(request_id)

    def all_responses(self) -> List[GatewayIntegrationResponse]:
        with self._lock:
            return list(self._responses.values())

    def completed_responses(self) -> List[GatewayIntegrationResponse]:
        with self._lock:
            return [
                r for r in self._responses.values()
                if r.status == IntegrationRequestStatus.COMPLETED
            ]

    def failed_responses(self) -> List[GatewayIntegrationResponse]:
        with self._lock:
            return [
                r for r in self._responses.values()
                if r.status == IntegrationRequestStatus.FAILED
            ]

    def responses_for_execution(
        self, execution_id: str
    ) -> List[GatewayIntegrationResponse]:
        with self._lock:
            return [r for r in self._responses.values()
                    if r.execution_id == execution_id]

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    @property
    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    @property
    def pending_count(self) -> int:
        with self._lock:
            return sum(
                1 for r in self._requests.values()
                if r.status not in TERMINAL_REQUEST_STATUSES
            )

    @property
    def completed_count(self) -> int:
        with self._lock:
            return sum(
                1 for r in self._responses.values()
                if r.status == IntegrationRequestStatus.COMPLETED
            )

    @property
    def failed_count(self) -> int:
        with self._lock:
            return sum(
                1 for r in self._responses.values()
                if r.status == IntegrationRequestStatus.FAILED
            )
