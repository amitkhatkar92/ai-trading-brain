"""iios/investment/portfolio/rebalancing/rebalance_snapshot.py

Lightweight historical records for rebalancing runs.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.rebalancing.rebalancing_types import (
    DriftLevel, RebalanceGrade, RebalanceStatus,
    RebalanceTrigger, TradePriority, now_utc,
)


@dataclass(frozen=True)
class RebalanceRecord:
    """Lightweight snapshot of one rebalancing run."""

    record_id:      str             = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:   str             = ""
    plan_id:        str             = ""
    timestamp:      str             = field(default_factory=now_utc)

    trigger:        RebalanceTrigger = RebalanceTrigger.NONE
    status:         RebalanceStatus  = RebalanceStatus.PENDING

    total_turnover: float            = 0.0
    total_cost_pct: float            = 0.0
    pre_drift:      float            = 0.0
    post_drift:     float            = 0.0
    drift_reduction:float            = 0.0
    drift_level:    DriftLevel       = DriftLevel.NONE

    rebalance_score:float            = 0.0
    grade:          RebalanceGrade   = RebalanceGrade.F
    is_recommended: bool             = False
    is_valid:       bool             = True

    n_trades:       int              = 0
    n_buys:         int              = 0
    n_sells:        int              = 0
    overall_priority: TradePriority  = TradePriority.MEDIUM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":      self.record_id,
            "portfolio_id":   self.portfolio_id,
            "timestamp":      self.timestamp,
            "trigger":        self.trigger.value,
            "status":         self.status.value,
            "total_turnover": round(self.total_turnover, 4),
            "total_cost_pct": round(self.total_cost_pct, 5),
            "pre_drift":      round(self.pre_drift, 4),
            "rebalance_score":round(self.rebalance_score, 4),
            "grade":          self.grade.value,
            "is_recommended": self.is_recommended,
            "n_trades":       self.n_trades,
        }


class RebalanceHistory:
    """Thread-safe bounded history of RebalanceRecord for a single portfolio."""

    def __init__(self, portfolio_id: str, max_size: int = 200) -> None:
        self.portfolio_id = portfolio_id
        self._max         = max_size
        self._lock        = threading.RLock()
        self._records:    List[RebalanceRecord] = []

    def add(self, record: RebalanceRecord) -> None:
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max:
                self._records = self._records[-self._max:]

    def latest(self) -> Optional[RebalanceRecord]:
        with self._lock:
            return self._records[-1] if self._records else None

    def recent(self, n: int = 10) -> List[RebalanceRecord]:
        with self._lock:
            return list(self._records[-n:])

    def best(self) -> Optional[RebalanceRecord]:
        with self._lock:
            if not self._records:
                return None
            return max(self._records, key=lambda r: r.rebalance_score)

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def recommended_count(self) -> int:
        with self._lock:
            return sum(1 for r in self._records if r.is_recommended)
