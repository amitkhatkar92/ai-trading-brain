"""
learning_history.py -- iios.ai.learning_evaluation.learning
=============================================================
:class:`LearningHistory` — thread-safe ordered log of LearningRecord objects.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..core.learning_record import LearningCategory, LearningRecord


class LearningHistory:
    """
    Thread-safe per-source ordered store for :class:`LearningRecord` objects.

    Records are stored in insertion order per ``source_id``.
    """

    def __init__(self, max_per_source: int = 10_000) -> None:
        self._lock:   threading.Lock            = threading.Lock()
        self._store:  Dict[str, List[LearningRecord]] = {}
        self._max:    int                       = max_per_source

    # ── write ─────────────────────────────────────────────────────────────────

    def add(self, record: LearningRecord) -> None:
        with self._lock:
            bucket = self._store.setdefault(record.source_id, [])
            bucket.append(record)
            # Evict oldest if over limit
            if len(bucket) > self._max:
                self._store[record.source_id] = bucket[-self._max:]

    # ── read ──────────────────────────────────────────────────────────────────

    def get(
        self,
        source_id: str,
        category:  Optional[LearningCategory] = None,
        limit:     Optional[int]              = None,
    ) -> List[LearningRecord]:
        with self._lock:
            records = list(self._store.get(source_id, []))
        if category is not None:
            records = [r for r in records if r.category == category]
        if limit is not None:
            records = records[-limit:]
        return records

    def all_sources(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    # ── statistics ────────────────────────────────────────────────────────────

    def total_count(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._store.values())

    def count_for(self, source_id: str) -> int:
        with self._lock:
            return len(self._store.get(source_id, []))

    def average_signal(self, source_id: str) -> Optional[float]:
        with self._lock:
            records = self._store.get(source_id, [])
        if not records:
            return None
        return sum(r.signal for r in records) / len(records)

    # ── cleanup ───────────────────────────────────────────────────────────────

    def clear(self, source_id: str) -> None:
        with self._lock:
            self._store.pop(source_id, None)

    def clear_all(self) -> None:
        with self._lock:
            self._store.clear()
