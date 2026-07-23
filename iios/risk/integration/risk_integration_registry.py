"""
risk_integration_registry.py — iios.risk.integration
======================================================
Thread-safe registry for integration requests and responses.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_REQUESTS, IntegrationStatus
from .exceptions import (
    RiskIntegrationCapacityError,
    RiskIntegrationRequestError,
)
from .risk_integration_request import RiskIntegrationRequest
from .risk_integration_response import RiskIntegrationResponse


class RiskIntegrationRegistry:
    """
    Thread-safe registry for integration requests and responses.

    Supports:
    - Request registration and retrieval
    - Response association per request
    - Latest response per portfolio
    - Capacity enforcement

    Parameters
    ----------
    max_requests :
        Maximum entries retained.
    """

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS) -> None:
        self._max       = max_requests
        self._lock      = threading.RLock()
        self._requests:  Dict[str, RiskIntegrationRequest]  = {}
        self._responses: Dict[str, RiskIntegrationResponse] = {}
        # portfolio_id → latest request_id
        self._latest_by_portfolio: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_request(self, request: RiskIntegrationRequest) -> None:
        with self._lock:
            if len(self._requests) >= self._max:
                raise RiskIntegrationCapacityError(
                    f"Integration registry capacity exceeded ({self._max})"
                )
            if request.request_id in self._requests:
                raise RiskIntegrationRequestError(
                    f"Request already registered: {request.request_id}"
                )
            self._requests[request.request_id] = request
            self._latest_by_portfolio[request.portfolio_id] = request.request_id

    def register_response(self, response: RiskIntegrationResponse) -> None:
        with self._lock:
            self._responses[response.request_id] = response

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_request(self, request_id: str) -> Optional[RiskIntegrationRequest]:
        with self._lock:
            return self._requests.get(request_id)

    def get_response(self, request_id: str) -> Optional[RiskIntegrationResponse]:
        with self._lock:
            return self._responses.get(request_id)

    def latest_for_portfolio(
        self, portfolio_id: str
    ) -> Optional[RiskIntegrationResponse]:
        with self._lock:
            rid = self._latest_by_portfolio.get(portfolio_id)
            if rid is None:
                return None
            return self._responses.get(rid)

    def requests_for_portfolio(
        self, portfolio_id: str, *, limit: int = 50
    ) -> List[RiskIntegrationRequest]:
        with self._lock:
            results = [
                r for r in reversed(list(self._requests.values()))
                if r.portfolio_id == portfolio_id
            ]
        return results[:limit]

    def responses_by_status(
        self, status: IntegrationStatus
    ) -> List[RiskIntegrationResponse]:
        with self._lock:
            return [r for r in self._responses.values() if r.status == status]

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._requests) == 0

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._responses.clear()
            self._latest_by_portfolio.clear()
