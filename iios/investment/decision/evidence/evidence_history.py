"""iios/investment/decision/evidence/evidence_history.py
EvidenceHistory — thread-safe rolling store of EvidenceSnapshots.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot


class EvidenceHistory:
    """Thread-safe append-only store of EvidenceSnapshots."""

    def __init__(self, max_size: int = 100_000) -> None:
        self._lock:  threading.RLock         = threading.RLock()
        self._store: List[EvidenceSnapshot]  = []
        self._max    = max_size

    def record(self, snapshot: EvidenceSnapshot) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                self._store.pop(0)
            self._store.append(snapshot)

    def get(self, snapshot_id: str) -> Optional[EvidenceSnapshot]:
        with self._lock:
            for s in reversed(self._store):
                if s.snapshot_id == snapshot_id:
                    return s
            return None

    def for_decision(self, decision_id: str) -> List[EvidenceSnapshot]:
        with self._lock:
            return [s for s in self._store if s.decision_id == decision_id]

    def for_subject(self, subject_id: str) -> List[EvidenceSnapshot]:
        with self._lock:
            return [s for s in self._store if s.subject_id == subject_id]

    def latest_for_subject(self, subject_id: str) -> Optional[EvidenceSnapshot]:
        snapshots = self.for_subject(subject_id)
        return snapshots[-1] if snapshots else None

    def recent(self, n: int = 50) -> List[EvidenceSnapshot]:
        with self._lock:
            return self._store[-n:]

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def known_subjects(self) -> List[str]:
        with self._lock:
            return list({s.subject_id for s in self._store})

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._store)
            if not total:
                return {"total": 0}
            avg_q  = sum(s.quality_score for s in self._store) / total
            avg_c  = sum(s.overall_confidence for s in self._store) / total
            return {
                "total":           total,
                "avg_quality":     round(avg_q, 2),
                "avg_confidence":  round(avg_c, 2),
                "known_subjects":  len({s.subject_id for s in self._store}),
            }
