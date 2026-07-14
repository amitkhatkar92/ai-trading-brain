"""iios/investment/decision/confidence/confidence_history.py
ConfidenceHistory — thread-safe, per-subject rolling store of ConfidenceSnapshots.
"""
from __future__ import annotations

import threading
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.decision.confidence.confidence_constants import HISTORY_WINDOW_SIZE
from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot


class ConfidenceHistory:
    """
    Thread-safe rolling history of ConfidenceSnapshots.
    Keyed by subject_id.  Maximum HISTORY_WINDOW_SIZE entries per subject.
    """

    def __init__(self, window: int = HISTORY_WINDOW_SIZE) -> None:
        self._window = window
        self._lock   = threading.RLock()
        # subject_id -> deque[ConfidenceSnapshot]
        self._by_subject: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self._window))
        # snapshot_id -> ConfidenceSnapshot  (fast random access)
        self._by_id: Dict[str, ConfidenceSnapshot] = {}

    # ── write ──────────────────────────────────────────────────────────────

    def record(self, snapshot: ConfidenceSnapshot) -> None:
        with self._lock:
            self._by_subject[snapshot.subject_id].append(snapshot)
            self._by_id[snapshot.snapshot_id] = snapshot

    # ── read ───────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> Optional[ConfidenceSnapshot]:
        with self._lock:
            return self._by_id.get(snapshot_id)

    def for_subject(self, subject_id: str) -> List[ConfidenceSnapshot]:
        with self._lock:
            return list(self._by_subject.get(subject_id, []))

    def for_decision(self, decision_id: str) -> List[ConfidenceSnapshot]:
        with self._lock:
            result = []
            for dq in self._by_subject.values():
                for snap in dq:
                    if snap.decision_id == decision_id:
                        result.append(snap)
            return result

    def latest_for_subject(self, subject_id: str) -> Optional[ConfidenceSnapshot]:
        with self._lock:
            dq = self._by_subject.get(subject_id)
            return dq[-1] if dq else None

    def recent(self, n: int = 20) -> List[ConfidenceSnapshot]:
        with self._lock:
            all_snaps: List[ConfidenceSnapshot] = []
            for dq in self._by_subject.values():
                all_snaps.extend(dq)
            all_snaps.sort(key=lambda s: s.created_at, reverse=True)
            return all_snaps[:n]

    def count(self) -> int:
        with self._lock:
            return sum(len(dq) for dq in self._by_subject.values())

    def known_subjects(self) -> List[str]:
        with self._lock:
            return list(self._by_subject.keys())

    def confidence_series(self, subject_id: str) -> List[float]:
        """Returns the chronological overall_confidence series for a subject."""
        with self._lock:
            return [s.overall_confidence for s in self._by_subject.get(subject_id, [])]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total   = self.count()
            usable  = sum(
                1 for dq in self._by_subject.values() for s in dq if s.is_usable
            )
            return {
                "total_snapshots":  total,
                "usable_snapshots": usable,
                "known_subjects":   len(self._by_subject),
                "window_size":      self._window,
            }
