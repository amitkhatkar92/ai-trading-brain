"""
knowledge_snapshot_history.py — iios.knowledge.snapshot
---------------------------------------------------------
Bounded versioned history of KnowledgeSnapshot records.

Tracks all snapshot versions per knowledge_session_id and provides
point-in-time lookup.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .knowledge_snapshot import KnowledgeSnapshot


class KnowledgeSnapshotHistory:
    """
    Thread-safe bounded history of KnowledgeSnapshot records.

    Global buffer bounded by max_history.
    Per-session index provides fast lookup by knowledge_session_id.
    """

    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY) -> None:
        self._max_history  = max_history
        self._buffer:  Deque[KnowledgeSnapshot] = deque(maxlen=max_history)
        # session_id → ordered list of snapshot_ids
        self._by_session: Dict[str, List[str]] = {}
        self._by_id:      Dict[str, KnowledgeSnapshot] = {}
        self._lock        = threading.Lock()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(self, snapshot: KnowledgeSnapshot) -> None:
        with self._lock:
            # If buffer is about to evict the oldest, remove from indexes
            if len(self._buffer) == self._max_history:
                oldest = self._buffer[0]
                self._by_id.pop(oldest.snapshot_id, None)
                session_list = self._by_session.get(oldest.knowledge_session_id, [])
                if oldest.snapshot_id in session_list:
                    session_list.remove(oldest.snapshot_id)

            self._buffer.append(snapshot)
            self._by_id[snapshot.snapshot_id] = snapshot
            self._by_session.setdefault(
                snapshot.knowledge_session_id, []
            ).append(snapshot.snapshot_id)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def recent(self, n: int = 20) -> List[KnowledgeSnapshot]:
        with self._lock:
            return list(self._buffer)[-n:]

    def all(self) -> List[KnowledgeSnapshot]:
        with self._lock:
            return list(self._buffer)

    def get(self, snapshot_id: str) -> Optional[KnowledgeSnapshot]:
        with self._lock:
            return self._by_id.get(snapshot_id)

    def by_session(self, knowledge_session_id: str) -> List[KnowledgeSnapshot]:
        with self._lock:
            ids = list(self._by_session.get(knowledge_session_id, []))
        return [s for sid in ids if (s := self._by_id.get(sid))]

    def latest_for_session(
        self, knowledge_session_id: str,
    ) -> Optional[KnowledgeSnapshot]:
        snaps = self.by_session(knowledge_session_id)
        return snaps[-1] if snaps else None

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def count(self) -> int:
        with self._lock:
            return len(self._buffer)

    def session_count(self) -> int:
        with self._lock:
            return len(self._by_session)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()
            self._by_session.clear()
            self._by_id.clear()
