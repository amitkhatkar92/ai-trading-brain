"""
knowledge_integration_history.py — iios.knowledge.integration
-------------------------------------------------------------
Bounded history of KnowledgeIntegrationResponse records.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .knowledge_integration_response import KnowledgeIntegrationResponse


class KnowledgeIntegrationHistory:
    """
    Thread-safe bounded history of integration responses.

    Global buffer bounded by max_history.
    Per-session index provides fast lookup by session_id.
    """

    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY) -> None:
        self._max_history = max_history
        self._buffer:     Deque[KnowledgeIntegrationResponse] = deque(maxlen=max_history)
        self._by_id:      Dict[str, KnowledgeIntegrationResponse] = {}
        self._by_session: Dict[str, List[str]] = {}
        self._lock        = threading.Lock()

    def record(self, response: KnowledgeIntegrationResponse) -> None:
        with self._lock:
            # Remove evicted entry from indexes when buffer is at capacity
            if len(self._buffer) == self._max_history:
                oldest = self._buffer[0]
                self._by_id.pop(oldest.response_id, None)
                session_list = self._by_session.get(oldest.session_id, [])
                if oldest.response_id in session_list:
                    session_list.remove(oldest.response_id)
            self._buffer.append(response)
            self._by_id[response.response_id] = response
            self._by_session.setdefault(
                response.session_id, []
            ).append(response.response_id)

    def recent(self, n: int = 20) -> List[KnowledgeIntegrationResponse]:
        with self._lock:
            return list(self._buffer)[-n:]

    def all(self) -> List[KnowledgeIntegrationResponse]:
        with self._lock:
            return list(self._buffer)

    def get(self, response_id: str) -> Optional[KnowledgeIntegrationResponse]:
        with self._lock:
            return self._by_id.get(response_id)

    def by_session(self, session_id: str) -> List[KnowledgeIntegrationResponse]:
        with self._lock:
            ids = list(self._by_session.get(session_id, []))
        return [r for rid in ids if (r := self._by_id.get(rid))]

    def latest_for_session(
        self, session_id: str
    ) -> Optional[KnowledgeIntegrationResponse]:
        records = self.by_session(session_id)
        return records[-1] if records else None

    def count(self) -> int:
        with self._lock:
            return len(self._buffer)

    def session_count(self) -> int:
        with self._lock:
            return len(self._by_session)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()
            self._by_id.clear()
            self._by_session.clear()
