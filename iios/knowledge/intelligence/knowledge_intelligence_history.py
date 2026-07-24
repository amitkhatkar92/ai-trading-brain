"""
knowledge_intelligence_history.py — iios.knowledge.intelligence
----------------------------------------------------------------
Bounded circular history of KnowledgeIntelligenceResponse records.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, List

from .constants import DEFAULT_MAX_HISTORY
from .knowledge_intelligence_response import KnowledgeIntelligenceResponse


class KnowledgeIntelligenceHistory:
    """
    Thread-safe bounded history of intelligence responses.

    Oldest records are evicted when the buffer is full.
    """

    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY) -> None:
        self._max_history = max_history
        self._buffer: Deque[KnowledgeIntelligenceResponse] = deque(
            maxlen=max_history
        )
        self._lock = threading.Lock()

    def record(self, response: KnowledgeIntelligenceResponse) -> None:
        with self._lock:
            self._buffer.append(response)

    def recent(self, n: int = 20) -> List[KnowledgeIntelligenceResponse]:
        with self._lock:
            items = list(self._buffer)
        return items[-n:]

    def all(self) -> List[KnowledgeIntelligenceResponse]:
        with self._lock:
            return list(self._buffer)

    def count(self) -> int:
        with self._lock:
            return len(self._buffer)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()
