"""
feedback_collector.py -- iios.ai.learning_evaluation.learning
==============================================================
:class:`FeedbackCollector` — thread-safe store for FeedbackRecord objects.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..core.feedback_record import FeedbackRecord, FeedbackType


class FeedbackCollector:
    """
    Thread-safe per-target feedback store.

    All records are kept in insertion order per ``target_id``.
    """

    def __init__(self) -> None:
        self._lock:    threading.Lock          = threading.Lock()
        self._store:   Dict[str, List[FeedbackRecord]] = {}

    # ── collection ────────────────────────────────────────────────────────────

    def collect(self, record: FeedbackRecord) -> None:
        with self._lock:
            self._store.setdefault(record.target_id, []).append(record)

    # ── retrieval ─────────────────────────────────────────────────────────────

    def get_feedback(
        self,
        target_id:     str,
        feedback_type: Optional[FeedbackType] = None,
    ) -> List[FeedbackRecord]:
        with self._lock:
            records = list(self._store.get(target_id, []))
        if feedback_type is not None:
            records = [r for r in records if r.feedback_type == feedback_type]
        return records

    def all_targets(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    # ── statistics ────────────────────────────────────────────────────────────

    def total_count(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._store.values())

    def count_for(self, target_id: str) -> int:
        with self._lock:
            return len(self._store.get(target_id, []))

    def average_rating(self, target_id: str) -> Optional[float]:
        """Return mean rating for a target (None if no rated feedback)."""
        with self._lock:
            records = self._store.get(target_id, [])
        rated = [r.rating for r in records if r.rating is not None]
        return (sum(rated) / len(rated)) if rated else None

    # ── cleanup ───────────────────────────────────────────────────────────────

    def clear(self, target_id: str) -> None:
        with self._lock:
            self._store.pop(target_id, None)

    def clear_all(self) -> None:
        with self._lock:
            self._store.clear()
