"""iios/investment/decision/core/decision_history.py
DecisionHistory — thread-safe rolling store of completed decision records.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from iios.investment.decision.core.decision_constants import (
    DecisionStatus,
    DecisionType,
    RecommendationType,
)
from iios.investment.decision.core.decision_context import DecisionContext
from iios.investment.decision.core.decision_state import DecisionState


@dataclass(frozen=True)
class DecisionRecord:
    """Immutable snapshot of a completed decision for historical storage."""
    decision_id:      str
    decision_type:    DecisionType
    subject_id:       str
    subject_type:     str
    final_status:     DecisionStatus
    score:            float
    confidence:       float
    recommendation:   Optional[RecommendationType]
    explanation:      str
    started_at:       datetime
    completed_at:     datetime
    duration_seconds: float
    source:           str
    session_id:       Optional[str]
    tags:             tuple

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":      self.decision_id,
            "decision_type":    self.decision_type.value,
            "subject_id":       self.subject_id,
            "subject_type":     self.subject_type,
            "final_status":     self.final_status.value,
            "score":            round(self.score, 2),
            "confidence":       round(self.confidence, 2),
            "recommendation":   self.recommendation.value if self.recommendation else None,
            "explanation":      self.explanation,
            "started_at":       self.started_at.isoformat(),
            "completed_at":     self.completed_at.isoformat(),
            "duration_seconds": round(self.duration_seconds, 3),
            "source":           self.source,
            "session_id":       self.session_id,
            "tags":             list(self.tags),
        }


def _build_record(
    context:      DecisionContext,
    state:        DecisionState,
    started_at:   datetime,
) -> DecisionRecord:
    completed = datetime.now(timezone.utc)
    duration  = (completed - started_at).total_seconds()
    return DecisionRecord(
        decision_id=context.decision_id,
        decision_type=context.decision_type,
        subject_id=context.subject_id,
        subject_type=context.subject_type,
        final_status=state.status,
        score=state.score,
        confidence=state.confidence,
        recommendation=state.recommendation,
        explanation=state.explanation,
        started_at=started_at,
        completed_at=completed,
        duration_seconds=duration,
        source=context.source,
        session_id=context.session_id,
        tags=context.tags,
    )


class DecisionHistory:
    """Thread-safe rolling store of DecisionRecords."""

    def __init__(self, max_size: int = 100_000) -> None:
        self._lock:  threading.RLock        = threading.RLock()
        self._store: List[DecisionRecord]   = []
        self._max    = max_size

    def record(
        self,
        context:    DecisionContext,
        state:      DecisionState,
        started_at: datetime,
    ) -> DecisionRecord:
        rec = _build_record(context, state, started_at)
        with self._lock:
            if len(self._store) >= self._max:
                self._store.pop(0)
            self._store.append(rec)
        return rec

    def for_subject(self, subject_id: str) -> List[DecisionRecord]:
        with self._lock:
            return [r for r in self._store if r.subject_id == subject_id]

    def for_type(self, decision_type: DecisionType) -> List[DecisionRecord]:
        with self._lock:
            return [r for r in self._store if r.decision_type == decision_type]

    def for_session(self, session_id: str) -> List[DecisionRecord]:
        with self._lock:
            return [r for r in self._store if r.session_id == session_id]

    def recent(self, n: int = 50) -> List[DecisionRecord]:
        with self._lock:
            return self._store[-n:]

    def get(self, decision_id: str) -> Optional[DecisionRecord]:
        with self._lock:
            for r in reversed(self._store):
                if r.decision_id == decision_id:
                    return r
            return None

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._store)
            if not total:
                return {"total": 0}
            statuses = {}
            for r in self._store:
                statuses[r.final_status.value] = statuses.get(r.final_status.value, 0) + 1
            avg_score = sum(r.score for r in self._store) / total
            return {
                "total":        total,
                "by_status":    statuses,
                "avg_score":    round(avg_score, 2),
            }
