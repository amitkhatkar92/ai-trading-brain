"""
portfolio_integration_registry.py — iios.portfolio.integration
===============================================================
PortfolioIntegrationRegistry — thread-safe storage for all integration
requests and responses with secondary indexes.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .constants import DEFAULT_MAX_REQUESTS, IntegrationServiceType
from .exceptions import IntegrationCapacityError

if TYPE_CHECKING:
    from .portfolio_integration_request import PortfolioIntegrationRequest
    from .portfolio_integration_response import PortfolioIntegrationResponse


class PortfolioIntegrationRegistry:
    """
    Thread-safe in-memory registry of integration requests and responses.

    Indexes maintained:
    - primary requests  : request_id  → PortfolioIntegrationRequest
    - primary responses : request_id  → PortfolioIntegrationResponse
    - by_portfolio      : portfolio_id → List[request_id]
    - by_service_type   : service_type → List[request_id]
    """

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS) -> None:
        if max_requests < 1:
            max_requests = 1
        self._max_requests   = max_requests
        self._lock           = threading.Lock()
        self._requests:      Dict[str, Any] = {}
        self._responses:     Dict[str, Any] = {}
        self._by_portfolio:  Dict[str, List[str]] = {}
        self._by_service:    Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def register_request(self, request: "PortfolioIntegrationRequest") -> None:
        rid = request.request_id
        with self._lock:
            if rid not in self._requests:
                if len(self._requests) >= self._max_requests:
                    raise IntegrationCapacityError(self._max_requests)
                self._requests[rid] = request
                _idx_append(self._by_portfolio, request.portfolio_id, rid)
                _idx_append(self._by_service, request.service_type, rid)

    def register_response(self, response: "PortfolioIntegrationResponse") -> None:
        with self._lock:
            self._responses[response.request_id] = response

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_request(self, request_id: str) -> Optional[Any]:
        with self._lock:
            return self._requests.get(request_id)

    def get_response(self, request_id: str) -> Optional[Any]:
        with self._lock:
            return self._responses.get(request_id)

    def find_by_portfolio(self, portfolio_id: str) -> List[Any]:
        with self._lock:
            rids = self._by_portfolio.get(portfolio_id, [])
            return [self._requests[r] for r in rids if r in self._requests]

    def find_responses_by_portfolio(self, portfolio_id: str) -> List[Any]:
        with self._lock:
            rids = self._by_portfolio.get(portfolio_id, [])
            return [self._responses[r] for r in rids if r in self._responses]

    def find_by_service(self, service_type: str) -> List[Any]:
        with self._lock:
            rids = self._by_service.get(service_type, [])
            return [self._requests[r] for r in rids if r in self._requests]

    def all_requests(self) -> List[Any]:
        with self._lock:
            return list(self._requests.values())

    def all_responses(self) -> List[Any]:
        with self._lock:
            return list(self._responses.values())

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    def contains_request(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._requests

    def contains_response(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._responses

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._responses.clear()
            self._by_portfolio.clear()
            self._by_service.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _idx_append(idx: Dict[str, List[str]], key: str, value: str) -> None:
    if key not in idx:
        idx[key] = []
    if value not in idx[key]:
        idx[key].append(value)
