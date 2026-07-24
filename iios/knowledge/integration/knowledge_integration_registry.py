"""
knowledge_integration_registry.py — iios.knowledge.integration
---------------------------------------------------------------
Thread-safe registry of active KnowledgeIntegrationResponse records,
keyed by response_id.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_REQUESTS
from .exceptions import IntegrationCapacityError
from .knowledge_integration_response import KnowledgeIntegrationResponse


class KnowledgeIntegrationRegistry:
    """
    Thread-safe registry of KnowledgeIntegrationResponse objects.

    Keyed by response_id.
    Raises IntegrationCapacityError if max_requests is exceeded.
    """

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS) -> None:
        self._max  = max_requests
        self._store: Dict[str, KnowledgeIntegrationResponse] = {}
        self._lock  = threading.Lock()

    def register(self, response: KnowledgeIntegrationResponse) -> None:
        with self._lock:
            if (
                len(self._store) >= self._max
                and response.response_id not in self._store
            ):
                raise IntegrationCapacityError(limit=self._max)
            self._store[response.response_id] = response

    def get(
        self, response_id: str
    ) -> Optional[KnowledgeIntegrationResponse]:
        with self._lock:
            return self._store.get(response_id)

    def remove(self, response_id: str) -> bool:
        with self._lock:
            if response_id in self._store:
                del self._store[response_id]
                return True
            return False

    def by_session(self, session_id: str) -> List[KnowledgeIntegrationResponse]:
        with self._lock:
            return [
                r for r in self._store.values()
                if r.session_id == session_id
            ]

    def all_responses(self) -> List[KnowledgeIntegrationResponse]:
        with self._lock:
            return list(self._store.values())

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
