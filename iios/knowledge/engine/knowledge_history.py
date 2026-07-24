"""
knowledge_history.py — iios.knowledge.engine
----------------------------------------------
Thread-safe bounded history log for knowledge engine pipelines.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .knowledge_pipeline import KnowledgePipeline


class KnowledgeEngineHistory:
    """
    Thread-safe, bounded history of completed :class:`KnowledgePipeline` records.

    Pipelines are stored in insertion order (chronological).
    When ``max_entries`` is reached the oldest entry is evicted.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        self._max_entries = max(1, max_entries)
        self._log:        List[KnowledgePipeline]        = []
        self._by_session: Dict[str, List[int]]            = {}
        self._lock        = threading.Lock()

    def record(self, pipeline: KnowledgePipeline) -> None:
        """Append a completed pipeline to the history."""
        with self._lock:
            if len(self._log) >= self._max_entries:
                self._log.pop(0)
                # Rebuild index after eviction
                self._by_session = {}
                for idx, p in enumerate(self._log):
                    self._by_session.setdefault(p.knowledge_id, []).append(idx)

            idx = len(self._log)
            self._log.append(pipeline)
            self._by_session.setdefault(pipeline.knowledge_id, []).append(idx)

    def all(self) -> List[KnowledgePipeline]:
        with self._lock:
            return list(self._log)

    def recent(self, n: int = 20) -> List[KnowledgePipeline]:
        with self._lock:
            return list(self._log[-n:])

    def for_knowledge_id(self, knowledge_id: str) -> List[KnowledgePipeline]:
        with self._lock:
            return [self._log[i] for i in self._by_session.get(knowledge_id, [])]

    def count(self) -> int:
        with self._lock:
            return len(self._log)

    def clear(self) -> None:
        with self._lock:
            self._log.clear()
            self._by_session.clear()

    @property
    def max_entries(self) -> int:
        return self._max_entries
