"""
supervisor_integration_registry.py — iios.supervisor.integration
-----------------------------------------------------------------
Thread-safe registry of active and completed integration requests/responses.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_REQUESTS
from .exceptions import (
    SupervisorIntegrationCapacityError,
    SupervisorIntegrationRegistryError,
)
from .supervisor_integration_request import SupervisorIntegrationRequest
from .supervisor_integration_response import SupervisorIntegrationResponse


class SupervisorIntegrationRegistry:
    """
    Thread-safe registry mapping ``request_id → (request, response)`` pairs.

    Tracks both in-flight requests (response == None) and completed
    request-response pairs.  Oldest entries are evicted when the registry
    reaches its capacity limit.

    Parameters
    ----------
    max_requests : Maximum number of entries (active + completed).
    """

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS) -> None:
        self._max  = max(1, max_requests)
        self._lock = threading.Lock()
        # request_id → (request, Optional[response])
        self._store: Dict[str, tuple] = {}
        # Insertion order for eviction
        self._order: List[str] = []

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def register_request(self, request: SupervisorIntegrationRequest) -> None:
        """Register an in-flight request (before response is available)."""
        with self._lock:
            if request.request_id in self._store:
                return  # idempotent
            self._evict_if_needed()
            self._store[request.request_id] = (request, None)
            self._order.append(request.request_id)

    def register_response(self, response: SupervisorIntegrationResponse) -> None:
        """Attach a completed response to its registered request."""
        with self._lock:
            entry = self._store.get(response.request_id)
            if entry is None:
                raise SupervisorIntegrationRegistryError(
                    f"Request {response.request_id!r} not found in registry"
                )
            req, _ = entry
            self._store[response.request_id] = (req, response)

    def unregister(self, request_id: str) -> None:
        """Remove a request-response pair from the registry."""
        with self._lock:
            self._store.pop(request_id, None)
            try:
                self._order.remove(request_id)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_request(self, request_id: str) -> Optional[SupervisorIntegrationRequest]:
        with self._lock:
            entry = self._store.get(request_id)
            return entry[0] if entry else None

    def get_response(self, request_id: str) -> Optional[SupervisorIntegrationResponse]:
        with self._lock:
            entry = self._store.get(request_id)
            return entry[1] if entry else None

    def is_registered(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._store

    def is_complete(self, request_id: str) -> bool:
        with self._lock:
            entry = self._store.get(request_id)
            return entry is not None and entry[1] is not None

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._store)

    @property
    def active_count(self) -> int:
        """Number of requests without a response yet."""
        with self._lock:
            return sum(1 for _, resp in self._store.values() if resp is None)

    @property
    def completed_count(self) -> int:
        with self._lock:
            return sum(1 for _, resp in self._store.values() if resp is not None)

    def all_request_ids(self) -> List[str]:
        with self._lock:
            return list(self._order)

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._order.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evict_if_needed(self) -> None:
        """Evict oldest entry when at capacity (caller must hold lock)."""
        while len(self._store) >= self._max:
            if not self._order:
                break
            oldest = self._order.pop(0)
            self._store.pop(oldest, None)
