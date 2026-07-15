"""iios/investment/portfolio/integration/aggregation_history.py

Bounded per-portfolio history of aggregation run records.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.integration.integration_types import (
    AggregationStatus, now_utc,
)


@dataclass(frozen=True)
class AggregationRecord:
    """Immutable summary of one completed aggregation run."""
    record_id:     str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:  str   = ""
    aggregated_at: str   = field(default_factory=now_utc)
    status:        AggregationStatus = AggregationStatus.INVALID
    n_engines:     int   = 0
    completeness:  float = 0.0
    freshness:     float = 0.0
    duration_ms:   float = 0.0
    snapshot_id:   Optional[str] = None
    error:         Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":    self.record_id,
            "portfolio_id": self.portfolio_id,
            "status":       self.status.value,
            "n_engines":    self.n_engines,
            "completeness": round(self.completeness, 4),
            "freshness":    round(self.freshness, 4),
            "duration_ms":  round(self.duration_ms, 2),
        }


class AggregationHistory:
    """Thread-safe bounded history of aggregation records per portfolio."""

    def __init__(self, max_records: int = 100) -> None:
        self._max  = max_records
        self._lock = threading.RLock()
        self._store: Dict[str, deque] = {}

    def add(self, record: AggregationRecord) -> None:
        with self._lock:
            pid = record.portfolio_id
            if pid not in self._store:
                self._store[pid] = deque(maxlen=self._max)
            self._store[pid].appendleft(record)

    def recent(self, portfolio_id: str, n: int = 10) -> List[AggregationRecord]:
        with self._lock:
            return list(self._store.get(portfolio_id, deque()))[:n]

    def latest(self, portfolio_id: str) -> Optional[AggregationRecord]:
        results = self.recent(portfolio_id, 1)
        return results[0] if results else None

    def all_portfolio_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())
