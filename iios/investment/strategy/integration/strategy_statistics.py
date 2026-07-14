"""iios/investment/strategy/integration/strategy_statistics.py
Tracks rolling statistics per strategy across updates and snapshots.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.integration.aggregation_state import IntelligenceUpdate
from iios.investment.strategy.integration.integration_constants import IntelligenceSource


@dataclass
class _StrategyStats:
    strategy_id:       str
    total_updates:     int                      = 0
    updates_by_source: Dict[str, int]           = None  # type: ignore[assignment]
    confidence_sum:    float                    = 0.0
    conflict_count:    int                      = 0
    snapshot_count:    int                      = 0
    last_snapshot_at:  Optional[datetime]       = None

    def __post_init__(self) -> None:
        if self.updates_by_source is None:
            self.updates_by_source = {}

    @property
    def avg_confidence(self) -> float:
        if self.total_updates == 0:
            return 0.0
        return round(self.confidence_sum / self.total_updates, 2)

    @property
    def conflict_rate(self) -> float:
        if self.snapshot_count == 0:
            return 0.0
        return round(self.conflict_count / self.snapshot_count, 4)


@dataclass(frozen=True)
class StrategyStatistics:
    strategy_id:       str
    total_updates:     int
    updates_by_source: Dict[str, int]
    avg_confidence:    float
    snapshot_count:    int
    conflict_count:    int
    conflict_rate:     float
    last_snapshot_at:  Optional[datetime]
    computed_at:       datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":       self.strategy_id,
            "total_updates":     self.total_updates,
            "updates_by_source": self.updates_by_source,
            "avg_confidence":    self.avg_confidence,
            "snapshot_count":    self.snapshot_count,
            "conflict_count":    self.conflict_count,
            "conflict_rate":     self.conflict_rate,
            "last_snapshot_at":  self.last_snapshot_at.isoformat() if self.last_snapshot_at else None,
            "computed_at":       self.computed_at.isoformat(),
        }


class StrategyStatisticsTracker:
    """Thread-safe rolling statistics accumulator per strategy."""

    def __init__(self) -> None:
        self._lock:  threading.RLock              = threading.RLock()
        self._data:  Dict[str, _StrategyStats]    = {}

    def _ensure(self, strategy_id: str) -> _StrategyStats:
        if strategy_id not in self._data:
            self._data[strategy_id] = _StrategyStats(strategy_id=strategy_id)
        return self._data[strategy_id]

    def record_update(self, update: IntelligenceUpdate) -> None:
        with self._lock:
            s = self._ensure(update.strategy_id)
            s.total_updates      += 1
            s.confidence_sum     += update.confidence
            src_key               = update.source.value
            s.updates_by_source[src_key] = s.updates_by_source.get(src_key, 0) + 1

    def record_snapshot(
        self,
        strategy_id:      str,
        active_conflicts: int,
    ) -> None:
        with self._lock:
            s = self._ensure(strategy_id)
            s.snapshot_count     += 1
            s.conflict_count     += active_conflicts
            s.last_snapshot_at   = datetime.now(timezone.utc)

    def summary(self, strategy_id: str) -> StrategyStatistics:
        with self._lock:
            s = self._ensure(strategy_id)
            return StrategyStatistics(
                strategy_id=s.strategy_id,
                total_updates=s.total_updates,
                updates_by_source=dict(s.updates_by_source),
                avg_confidence=s.avg_confidence,
                snapshot_count=s.snapshot_count,
                conflict_count=s.conflict_count,
                conflict_rate=s.conflict_rate,
                last_snapshot_at=s.last_snapshot_at,
                computed_at=datetime.now(timezone.utc),
            )

    def all_summaries(self) -> Dict[str, StrategyStatistics]:
        with self._lock:
            return {sid: self.summary(sid) for sid in self._data}

    def known_strategies(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())
