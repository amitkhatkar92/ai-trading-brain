"""iios/investment/portfolio/performance/performance_snapshot.py

Lightweight performance snapshot and bounded history.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.performance.performance_types import (
    PerformanceGrade, PerformanceLevel,
)


@dataclass(frozen=True)
class PerformanceRecord:
    """Lightweight snapshot of a single performance evaluation."""

    record_id:       str                = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str                = ""
    timestamp:       str                = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Key metrics
    portfolio_return:float              = 0.0
    sharpe_ratio:    float              = 0.0
    alpha:           float              = 0.0
    overall_score:   float              = 0.0
    grade:           PerformanceGrade   = PerformanceGrade.F
    level:           PerformanceLevel   = PerformanceLevel.POOR
    is_acceptable:   bool               = False
    n_positions:     int                = 0
    benchmark_id:    str                = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":       self.record_id,
            "portfolio_id":    self.portfolio_id,
            "timestamp":       self.timestamp,
            "overall_score":   round(self.overall_score, 4),
            "grade":           self.grade.value,
            "sharpe_ratio":    round(self.sharpe_ratio, 4),
            "alpha":           round(self.alpha, 4),
            "is_acceptable":   self.is_acceptable,
        }


class PerformanceHistory:
    """Thread-safe bounded history of PerformanceRecord snapshots."""

    def __init__(self, portfolio_id: str, max_snapshots: int = 200) -> None:
        self.portfolio_id   = portfolio_id
        self._max           = max_snapshots
        self._lock          = threading.RLock()
        self._records:      List[PerformanceRecord] = []

    def add(self, record: PerformanceRecord) -> None:
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max:
                self._records = self._records[-self._max:]

    def latest(self) -> Optional[PerformanceRecord]:
        with self._lock:
            return self._records[-1] if self._records else None

    def recent(self, n: int) -> List[PerformanceRecord]:
        with self._lock:
            return list(self._records[-n:])

    def best(self) -> Optional[PerformanceRecord]:
        with self._lock:
            if not self._records:
                return None
            return max(self._records, key=lambda r: r.overall_score)

    def count(self) -> int:
        with self._lock:
            return len(self._records)
