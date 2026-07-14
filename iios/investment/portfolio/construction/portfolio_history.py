"""iios/investment/portfolio/construction/portfolio_history.py

Versioned history of portfolio construction snapshots and blueprints.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.construction.portfolio_snapshot import (
    PortfolioConstructionSnapshot,
)


@dataclass(frozen=True)
class BlueprintRecord:
    """
    Lightweight record of a blueprint version stored in the history.

    Carries the full blueprint_id, version, status, and quality score
    so the history can answer queries without deserialising every blueprint.
    """

    record_id:            str   = ""
    portfolio_id:         str   = ""
    blueprint_id:         str   = ""
    blueprint_version:    int   = 1
    result_id:            str   = ""
    status:               str   = "unknown"
    construction_type:    str   = "unknown"
    weighting_method:     str   = "unknown"
    long_count:           int   = 0
    short_count:          int   = 0
    quality_score:        float = 0.0
    is_valid:             bool  = False
    is_ready:             bool  = False
    created_at:           float = 0.0
    recorded_at:          float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":         self.record_id,
            "portfolio_id":      self.portfolio_id,
            "blueprint_id":      self.blueprint_id,
            "blueprint_version": self.blueprint_version,
            "result_id":         self.result_id,
            "status":            self.status,
            "construction_type": self.construction_type,
            "weighting_method":  self.weighting_method,
            "long_count":        self.long_count,
            "short_count":       self.short_count,
            "quality_score":     round(self.quality_score, 4),
            "is_valid":          self.is_valid,
            "is_ready":          self.is_ready,
            "created_at":        self.created_at,
            "recorded_at":       self.recorded_at,
        }


class PortfolioConstructionHistory:
    """
    Thread-safe, bounded store of construction snapshots and blueprint records
    for a single portfolio.

    Supports retrieval by version, recency, and date range.  The history cap
    ensures bounded memory even for portfolios reconstructed frequently.
    """

    __slots__ = (
        "_portfolio_id",
        "_max_snapshots",
        "_snapshots",
        "_records",
        "_lock",
    )

    def __init__(self, portfolio_id: str, max_snapshots: int = 200) -> None:
        if max_snapshots < 1:
            raise ValueError("max_snapshots must be >= 1")
        self._portfolio_id  = portfolio_id
        self._max_snapshots = max_snapshots
        self._snapshots: List[PortfolioConstructionSnapshot] = []
        self._records:   List[BlueprintRecord]               = []
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(
        self,
        snapshot: PortfolioConstructionSnapshot,
        *,
        status: str = "completed",
        construction_type: str = "unknown",
        weighting_method: str = "unknown",
        quality_score: float = 0.0,
    ) -> BlueprintRecord:
        """Add a snapshot and its lightweight record.  Oldest evicted if at cap."""
        import uuid as _uuid
        record = BlueprintRecord(
            record_id=str(_uuid.uuid4()),
            portfolio_id=snapshot.portfolio_id,
            blueprint_id=snapshot.blueprint_id,
            blueprint_version=snapshot.blueprint_version,
            result_id=snapshot.result_id,
            status=status,
            construction_type=construction_type,
            weighting_method=weighting_method,
            long_count=snapshot.long_count,
            short_count=snapshot.short_count,
            quality_score=quality_score,
            is_valid=snapshot.is_valid,
            is_ready=snapshot.is_ready,
            created_at=snapshot.snapshotted_at,
        )
        with self._lock:
            self._snapshots.append(snapshot)
            self._records.append(record)
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots.pop(0)
                self._records.pop(0)
        return record

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    def count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    def all_records(self) -> List[BlueprintRecord]:
        with self._lock:
            return list(self._records)

    def all_snapshots(self) -> List[PortfolioConstructionSnapshot]:
        with self._lock:
            return list(self._snapshots)

    def latest(self) -> Optional[PortfolioConstructionSnapshot]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def latest_record(self) -> Optional[BlueprintRecord]:
        with self._lock:
            return self._records[-1] if self._records else None

    def by_version(self, version: int) -> Optional[PortfolioConstructionSnapshot]:
        with self._lock:
            for snap in reversed(self._snapshots):
                if snap.blueprint_version == version:
                    return snap
        return None

    def since(self, ts: float) -> List[PortfolioConstructionSnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.snapshotted_at >= ts]

    def recent(self, n: int) -> List[PortfolioConstructionSnapshot]:
        with self._lock:
            return list(self._snapshots[-n:])

    def valid_snapshots(self) -> List[PortfolioConstructionSnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.is_valid]

    def ready_snapshots(self) -> List[PortfolioConstructionSnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.is_ready]

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
