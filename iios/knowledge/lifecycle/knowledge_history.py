"""
knowledge_history.py — iios.knowledge.lifecycle
-------------------------------------------------
Ordered, bounded history log for knowledge lifecycle transitions.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY, KnowledgeLifecycleState
from .exceptions import KnowledgeHistoryError
from .knowledge_transition import KnowledgeTransition


class KnowledgeHistory:
    """
    Thread-safe, bounded log of :class:`KnowledgeTransition` records.

    Transitions are stored in insertion order (chronological).  When
    ``max_entries`` is reached the oldest entry is evicted.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        self._max_entries = max(1, max_entries)
        self._log:  List[KnowledgeTransition]        = []
        self._by_session: Dict[str, List[int]]        = {}  # session_id → index list
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def record(self, transition: KnowledgeTransition) -> None:
        """Append a transition to the history."""
        with self._lock:
            if len(self._log) >= self._max_entries:
                evicted = self._log.pop(0)
                idxs = self._by_session.get(evicted.session_id, [])
                if idxs:
                    idxs.pop(0)
                # Recompute indices after pop
                self._by_session = {}
                for idx, t in enumerate(self._log):
                    self._by_session.setdefault(t.session_id, []).append(idx)

            idx = len(self._log)
            self._log.append(transition)
            self._by_session.setdefault(transition.session_id, []).append(idx)

    def clear(self) -> None:
        """Remove all entries (used in tests / teardown)."""
        with self._lock:
            self._log.clear()
            self._by_session.clear()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def all(self) -> List[KnowledgeTransition]:
        """Return all transitions in chronological order."""
        with self._lock:
            return list(self._log)

    def for_session(self, session_id: str) -> List[KnowledgeTransition]:
        """Return all transitions for a given session in chronological order."""
        with self._lock:
            return [self._log[i] for i in self._by_session.get(session_id, [])]

    def recent(self, n: int = 20) -> List[KnowledgeTransition]:
        """Return up to *n* most recent transitions."""
        with self._lock:
            return list(self._log[-n:])

    def count(self) -> int:
        """Total number of recorded transitions."""
        with self._lock:
            return len(self._log)

    def session_count(self) -> int:
        """Number of distinct sessions that have entries in the history."""
        with self._lock:
            return len(self._by_session)

    @property
    def max_entries(self) -> int:
        return self._max_entries
