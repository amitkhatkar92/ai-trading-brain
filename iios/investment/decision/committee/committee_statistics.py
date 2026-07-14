"""iios/investment/decision/committee/committee_statistics.py
CommitteeStatisticsTracker — thread-safe stats for the engine lifetime.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.committee.committee_constants import CommitteePosition


@dataclass(frozen=True)
class CommitteeStatistics:
    total_sessions:     int
    successful:         int
    failed:             int
    proceed_count:      int
    defer_count:        int
    insufficient_count: int
    blocked_count:      int
    avg_score:          float
    avg_duration_ms:    float

    @property
    def success_rate(self) -> float:
        return self.successful / max(1, self.total_sessions)

    @property
    def block_rate(self) -> float:
        return self.blocked_count / max(1, self.total_sessions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_sessions":     self.total_sessions,
            "successful":         self.successful,
            "failed":             self.failed,
            "proceed_count":      self.proceed_count,
            "defer_count":        self.defer_count,
            "insufficient_count": self.insufficient_count,
            "blocked_count":      self.blocked_count,
            "avg_score":          round(self.avg_score, 2),
            "avg_duration_ms":    round(self.avg_duration_ms, 2),
            "success_rate":       round(self.success_rate, 4),
            "block_rate":         round(self.block_rate, 4),
        }


class CommitteeStatisticsTracker:
    def __init__(self) -> None:
        self._lock  = threading.RLock()
        self._total = self._ok = self._fail = 0
        self._proceed = self._defer = self._insufficient = self._blocked = 0
        self._score_sum = self._dur_sum = 0.0

    def record_success(
        self, position: CommitteePosition, score: float, duration_ms: float,
    ) -> None:
        with self._lock:
            self._total += 1
            self._ok    += 1
            self._score_sum += score
            self._dur_sum   += duration_ms
            if position == CommitteePosition.PROCEED_TO_RECOMMENDATION:
                self._proceed += 1
            elif position == CommitteePosition.DEFER_PENDING_EVIDENCE:
                self._defer += 1
            elif position == CommitteePosition.INSUFFICIENT_EVIDENCE:
                self._insufficient += 1
            elif position == CommitteePosition.BLOCKED:
                self._blocked += 1

    def record_failure(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._total += 1
            self._fail  += 1
            self._dur_sum += duration_ms

    def summary(self) -> CommitteeStatistics:
        with self._lock:
            return CommitteeStatistics(
                total_sessions     = self._total,
                successful         = self._ok,
                failed             = self._fail,
                proceed_count      = self._proceed,
                defer_count        = self._defer,
                insufficient_count = self._insufficient,
                blocked_count      = self._blocked,
                avg_score          = round(self._score_sum / max(1, self._ok), 2),
                avg_duration_ms    = round(self._dur_sum   / max(1, self._total), 2),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = self._ok = self._fail = 0
            self._proceed = self._defer = self._insufficient = self._blocked = 0
            self._score_sum = self._dur_sum = 0.0
