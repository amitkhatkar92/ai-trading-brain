"""iios/investment/strategy/migration/migration_statistics.py
Thread-safe migration counters and timing aggregates.
"""
from __future__ import annotations

import statistics
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.migration.migration_status import MigrationStatus


@dataclass
class _StatusCounters:
    not_started:     int = 0
    discovered:      int = 0
    validating:      int = 0
    preparing:       int = 0
    migrating:       int = 0
    verifying:       int = 0
    approval_pending: int = 0
    completed:       int = 0
    failed:          int = 0
    rolled_back:     int = 0
    archived:        int = 0

    def increment(self, status: MigrationStatus) -> None:
        mapping = {
            MigrationStatus.NOT_STARTED:      "not_started",
            MigrationStatus.DISCOVERY:        "discovered",
            MigrationStatus.VALIDATION:       "validating",
            MigrationStatus.PREPARATION:      "preparing",
            MigrationStatus.MIGRATING:        "migrating",
            MigrationStatus.VERIFICATION:     "verifying",
            MigrationStatus.APPROVAL_PENDING: "approval_pending",
            MigrationStatus.COMPLETED:        "completed",
            MigrationStatus.FAILED:           "failed",
            MigrationStatus.ROLLED_BACK:      "rolled_back",
            MigrationStatus.ARCHIVED:         "archived",
        }
        attr = mapping.get(status)
        if attr:
            setattr(self, attr, getattr(self, attr) + 1)

    def to_dict(self) -> Dict[str, int]:
        return {k: v for k, v in self.__dict__.items()}


class MigrationStatistics:
    """
    Thread-safe statistics tracker for the migration pipeline.
    Records per-strategy outcomes and timing information.
    """

    def __init__(self) -> None:
        self._lock         = threading.RLock()
        self._counters     = _StatusCounters()
        self._durations:   List[float] = []   # per-strategy total duration ms
        self._attempts:    int         = 0
        self._errors:      int         = 0
        self._started_at:  datetime    = datetime.now(timezone.utc)

    def record_attempt(self) -> None:
        with self._lock:
            self._attempts += 1

    def record_status(self, status: MigrationStatus) -> None:
        with self._lock:
            self._counters.increment(status)
            if status == MigrationStatus.FAILED:
                self._errors += 1

    def record_duration(self, duration_ms: float) -> None:
        with self._lock:
            self._durations.append(duration_ms)

    @property
    def total_attempts(self) -> int:
        with self._lock:
            return self._attempts

    @property
    def completed(self) -> int:
        with self._lock:
            return self._counters.completed

    @property
    def failed(self) -> int:
        with self._lock:
            return self._counters.failed

    @property
    def rolled_back(self) -> int:
        with self._lock:
            return self._counters.rolled_back

    @property
    def success_rate(self) -> float:
        with self._lock:
            if self._attempts == 0:
                return 0.0
            return round(self._counters.completed / self._attempts * 100, 2)

    @property
    def avg_duration_ms(self) -> float:
        with self._lock:
            if not self._durations:
                return 0.0
            return round(statistics.mean(self._durations), 2)

    @property
    def p95_duration_ms(self) -> float:
        with self._lock:
            if not self._durations:
                return 0.0
            sorted_d = sorted(self._durations)
            idx = max(0, int(len(sorted_d) * 0.95) - 1)
            return round(sorted_d[idx], 2)

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_attempts":  self._attempts,
                "completed":       self._counters.completed,
                "failed":          self._counters.failed,
                "rolled_back":     self._counters.rolled_back,
                "archived":        self._counters.archived,
                "approval_pending": self._counters.approval_pending,
                "success_rate_pct": self.success_rate,
                "avg_duration_ms": self.avg_duration_ms,
                "p95_duration_ms": self.p95_duration_ms,
                "by_status":       self._counters.to_dict(),
                "started_at":      self._started_at.isoformat(),
            }

    def reset(self) -> None:
        with self._lock:
            self._counters   = _StatusCounters()
            self._durations  = []
            self._attempts   = 0
            self._errors     = 0
            self._started_at = datetime.now(timezone.utc)
