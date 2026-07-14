"""iios/investment/portfolio/allocation/allocation_history.py

Versioned history of allocation plans and snapshots for a single portfolio.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.allocation.allocation_snapshot import AllocationSnapshot


@dataclass(frozen=True)
class AllocationRecord:
    """
    Lightweight audit record stored alongside each snapshot.
    Answers history queries without deserialising full snapshots.
    """

    record_id:         str   = ""
    portfolio_id:      str   = ""
    plan_id:           str   = ""
    blueprint_id:      str   = ""
    plan_version:      int   = 1
    result_id:         str   = ""
    status:            str   = "completed"
    method:            str   = "blueprint_weight"
    total_capital:     float = 0.0
    invested_capital:  float = 0.0
    cash_capital:      float = 0.0
    utilisation_rate:  float = 0.0
    positions_count:   int   = 0
    quality_score:     float = 0.0
    is_valid:          bool  = False
    is_ready:          bool  = False
    created_at:        float = 0.0
    recorded_at:       float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":        self.record_id,
            "portfolio_id":     self.portfolio_id,
            "plan_id":          self.plan_id,
            "blueprint_id":     self.blueprint_id,
            "plan_version":     self.plan_version,
            "status":           self.status,
            "method":           self.method,
            "total_capital":    round(self.total_capital, 2),
            "invested_capital": round(self.invested_capital, 2),
            "cash_capital":     round(self.cash_capital, 2),
            "utilisation_rate": round(self.utilisation_rate, 4),
            "positions_count":  self.positions_count,
            "quality_score":    round(self.quality_score, 4),
            "is_valid":         self.is_valid,
            "is_ready":         self.is_ready,
            "created_at":       self.created_at,
            "recorded_at":      self.recorded_at,
        }


class AllocationHistory:
    """
    Thread-safe, bounded history of AllocationSnapshots for one portfolio.
    """

    __slots__ = ("_portfolio_id", "_max_snapshots", "_snapshots", "_records", "_lock")

    def __init__(self, portfolio_id: str, max_snapshots: int = 200) -> None:
        self._portfolio_id  = portfolio_id
        self._max_snapshots = max(1, max_snapshots)
        self._snapshots: List[AllocationSnapshot] = []
        self._records:   List[AllocationRecord]   = []
        self._lock = threading.RLock()

    def record(
        self,
        snapshot:    AllocationSnapshot,
        *,
        status:      str   = "completed",
        quality_score:float= 0.0,
    ) -> AllocationRecord:
        record = AllocationRecord(
            record_id        = str(uuid.uuid4()),
            portfolio_id     = snapshot.portfolio_id,
            plan_id          = snapshot.plan_id,
            blueprint_id     = snapshot.blueprint_id,
            plan_version     = snapshot.plan_version,
            result_id        = snapshot.result_id,
            status           = status,
            method           = snapshot.method.value,
            total_capital    = snapshot.total_capital,
            invested_capital = snapshot.invested_capital,
            cash_capital     = snapshot.cash_capital,
            utilisation_rate = snapshot.utilisation_rate,
            positions_count  = snapshot.total_holdings,
            quality_score    = quality_score,
            is_valid         = snapshot.is_valid,
            is_ready         = snapshot.is_ready,
            created_at       = snapshot.snapshotted_at,
        )
        with self._lock:
            self._snapshots.append(snapshot)
            self._records.append(record)
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots.pop(0)
                self._records.pop(0)
        return record

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    def count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    def latest(self) -> Optional[AllocationSnapshot]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def latest_record(self) -> Optional[AllocationRecord]:
        with self._lock:
            return self._records[-1] if self._records else None

    def all_snapshots(self) -> List[AllocationSnapshot]:
        with self._lock:
            return list(self._snapshots)

    def all_records(self) -> List[AllocationRecord]:
        with self._lock:
            return list(self._records)

    def recent(self, n: int) -> List[AllocationSnapshot]:
        with self._lock:
            return list(self._snapshots[-n:])

    def by_version(self, version: int) -> Optional[AllocationSnapshot]:
        with self._lock:
            for snap in reversed(self._snapshots):
                if snap.plan_version == version:
                    return snap
        return None

    def valid_snapshots(self) -> List[AllocationSnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.is_valid]

    def reset(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._records.clear()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "portfolio_id":  self._portfolio_id,
                "max_snapshots": self._max_snapshots,
                "count":         len(self._snapshots),
                "records":       [r.to_dict() for r in self._records],
            }
