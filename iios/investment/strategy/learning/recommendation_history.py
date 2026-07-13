"""iios/investment/strategy/learning/recommendation_history.py
RecommendationHistory — versioned, auditable recommendation log.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional


@dataclass(frozen=True)
class RecommendationRecord:
    """Immutable recommendation record for audit trail."""
    record_id:      str
    strategy_id:    str
    rec_type:       str
    priority:       str
    title:          str
    rationale:      str
    evidence:       List[str]
    priority_score: float
    is_reversible:  bool
    created_at:     datetime
    status:         str = "active"   # active | acknowledged | superseded

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":     self.record_id,
            "strategy_id":   self.strategy_id,
            "rec_type":      self.rec_type,
            "priority":      self.priority,
            "title":         self.title,
            "rationale":     self.rationale,
            "evidence":      self.evidence,
            "priority_score": round(self.priority_score, 2),
            "is_reversible": self.is_reversible,
            "created_at":    self.created_at.isoformat(),
            "status":        self.status,
        }


class RecommendationHistory:
    """
    Thread-safe ring buffer of recommendation records per strategy.
    Supports version history and audit trail. Never deletes records.
    """

    def __init__(self, max_per_strategy: int = 500) -> None:
        self._max   = max_per_strategy
        self._store: Dict[str, Deque[RecommendationRecord]] = {}
        self._lock  = threading.RLock()

    def add(self, record: RecommendationRecord) -> None:
        with self._lock:
            sid = record.strategy_id
            if sid not in self._store:
                self._store[sid] = deque(maxlen=self._max)
            self._store[sid].append(record)

    def add_all(self, records: List[RecommendationRecord]) -> None:
        with self._lock:
            for r in records:
                self._store.setdefault(r.strategy_id, deque(maxlen=self._max)).append(r)

    def get_recent(self, strategy_id: str, n: int = 20) -> List[RecommendationRecord]:
        with self._lock:
            return list(self._store.get(strategy_id, []))[-n:]

    def get_active(self, strategy_id: str) -> List[RecommendationRecord]:
        with self._lock:
            return [r for r in self._store.get(strategy_id, []) if r.status == "active"]

    def count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._store.get(strategy_id, []))

    def was_recent_type(
        self, strategy_id: str, rec_type: str, within_n_obs: int = 5
    ) -> bool:
        """Check if a recommendation of this type was created recently."""
        with self._lock:
            recent = list(self._store.get(strategy_id, []))[-within_n_obs:]
            return any(r.rec_type == rec_type for r in recent)

    def all_strategy_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())
