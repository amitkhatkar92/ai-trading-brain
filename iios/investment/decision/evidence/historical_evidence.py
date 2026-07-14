"""iios/investment/decision/evidence/historical_evidence.py
HistoricalEvidence — per-subject rolling store of historical evidence items.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_item import EvidenceItem


class HistoricalEvidence:
    """Thread-safe rolling per-subject evidence store."""

    def __init__(self, max_per_subject: int = 1_000) -> None:
        self._lock:    threading.RLock              = threading.RLock()
        self._store:   Dict[str, List[EvidenceItem]] = {}
        self._max      = max_per_subject

    def record(self, item: EvidenceItem) -> None:
        with self._lock:
            bucket = self._store.setdefault(item.subject_id, [])
            if len(bucket) >= self._max:
                bucket.pop(0)
            bucket.append(item)

    def record_all(self, items: List[EvidenceItem]) -> None:
        for item in items:
            self.record(item)

    def get_history(
        self,
        subject_id: str,
        key:        Optional[str] = None,
        last_n:     int           = 100,
    ) -> List[EvidenceItem]:
        with self._lock:
            bucket = self._store.get(subject_id, [])
            if key is not None:
                bucket = [i for i in bucket if i.key == key]
            return bucket[-last_n:]

    def known_subjects(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def total_items(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._store.values())

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "subjects":    len(self._store),
                "total_items": self.total_items(),
            }
