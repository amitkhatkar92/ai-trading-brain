"""iios/investment/portfolio/recommendation/recommendation_snapshot.py

Lightweight historical records per recommendation run.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.recommendation.recommendation_types import (
    LifecycleState, RecommendationAction, RecommendationGrade,
    RecommendationPriority, RecommendationStatus, now_utc,
)


@dataclass(frozen=True)
class RecommendationRecord:
    """Lightweight snapshot of one published recommendation."""

    record_id:          str                    = field(default_factory=lambda: str(uuid.uuid4()))
    recommendation_id:  str                    = ""
    portfolio_id:       str                    = ""
    timestamp:          str                    = field(default_factory=now_utc)

    action:             RecommendationAction   = RecommendationAction.NO_ACTION
    priority:           RecommendationPriority = RecommendationPriority.INFORMATIONAL
    status:             RecommendationStatus   = RecommendationStatus.DRAFT
    lifecycle_state:    LifecycleState         = LifecycleState.CREATED

    confidence:         float                  = 0.5
    recommendation_score: float               = 0.5
    grade:              RecommendationGrade    = RecommendationGrade.C
    is_actionable:      bool                   = True
    requires_approval:  bool                   = False
    category:           str                    = ""
    policy_id:          str                    = ""
    expires_at:         str                    = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":           self.record_id,
            "recommendation_id":   self.recommendation_id,
            "portfolio_id":        self.portfolio_id,
            "timestamp":           self.timestamp,
            "action":              self.action.value,
            "priority":            self.priority.value,
            "status":              self.status.value,
            "confidence":          round(self.confidence, 4),
            "recommendation_score":round(self.recommendation_score, 4),
            "grade":               self.grade.value,
            "is_actionable":       self.is_actionable,
            "category":            self.category,
        }


class RecommendationHistory:
    """Thread-safe bounded history of RecommendationRecord for a single portfolio."""

    def __init__(self, portfolio_id: str, max_size: int = 200) -> None:
        self.portfolio_id = portfolio_id
        self._max         = max_size
        self._lock        = threading.RLock()
        self._records:    List[RecommendationRecord] = []

    def add(self, record: RecommendationRecord) -> None:
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max:
                self._records = self._records[-self._max:]

    def latest(self) -> Optional[RecommendationRecord]:
        with self._lock:
            return self._records[-1] if self._records else None

    def recent(self, n: int = 10) -> List[RecommendationRecord]:
        with self._lock:
            return list(self._records[-n:])

    def best(self) -> Optional[RecommendationRecord]:
        with self._lock:
            if not self._records:
                return None
            return max(self._records, key=lambda r: r.recommendation_score)

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def actionable_count(self) -> int:
        with self._lock:
            return sum(1 for r in self._records if r.is_actionable)

    def by_action(self, action: RecommendationAction) -> List[RecommendationRecord]:
        with self._lock:
            return [r for r in self._records if r.action == action]
