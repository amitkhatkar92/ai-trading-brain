"""iios/investment/decision/committee/committee_history.py
CommitteeHistory — thread-safe rolling store of CommitteeReports.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Dict, List, Optional

from iios.investment.decision.committee.committee_constants import COMMITTEE_HISTORY_WINDOW
from iios.investment.decision.committee.committee_report import CommitteeReport


class CommitteeHistory:
    """Rolling store of CommitteeReports with lookup by report_id, decision_id, and subject_id."""

    def __init__(self, maxlen: int = COMMITTEE_HISTORY_WINDOW) -> None:
        self._lock     = threading.RLock()
        self._store:   deque[CommitteeReport]    = deque(maxlen=maxlen)
        self._by_id:   Dict[str, CommitteeReport]= {}    # report_id → report
        self._by_dec:  Dict[str, CommitteeReport]= {}    # decision_id → latest report
        self._by_sub:  Dict[str, List[CommitteeReport]] = {}  # subject_id → reports

    def record(self, report: CommitteeReport) -> None:
        with self._lock:
            evicted = None
            if len(self._store) == self._store.maxlen:
                evicted = self._store[0]
            self._store.append(report)

            if evicted:
                self._by_id.pop(evicted.report_id, None)
                if self._by_dec.get(evicted.decision_id) is evicted:
                    self._by_dec.pop(evicted.decision_id, None)

            self._by_id[report.report_id]   = report
            self._by_dec[report.decision_id] = report

            if report.subject_id not in self._by_sub:
                self._by_sub[report.subject_id] = []
            self._by_sub[report.subject_id].append(report)

    def get(self, report_id: str) -> Optional[CommitteeReport]:
        with self._lock:
            return self._by_id.get(report_id)

    def for_decision(self, decision_id: str) -> Optional[CommitteeReport]:
        with self._lock:
            return self._by_dec.get(decision_id)

    def for_subject(self, subject_id: str) -> List[CommitteeReport]:
        with self._lock:
            return list(self._by_sub.get(subject_id, []))

    def latest_for_subject(self, subject_id: str) -> Optional[CommitteeReport]:
        reports = self.for_subject(subject_id)
        return reports[-1] if reports else None

    def recent(self, n: int = 10) -> List[CommitteeReport]:
        with self._lock:
            items = list(self._store)
            return items[-n:] if n < len(items) else items

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def known_subjects(self) -> List[str]:
        with self._lock:
            return list(self._by_sub.keys())

    def position_series(self, subject_id: str) -> List[str]:
        return [r.position.value for r in self.for_subject(subject_id)]

    def score_series(self, subject_id: str) -> List[float]:
        return [r.committee_score for r in self.for_subject(subject_id)]
