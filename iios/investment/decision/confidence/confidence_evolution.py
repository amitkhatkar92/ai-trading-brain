"""iios/investment/decision/confidence/confidence_evolution.py
ConfidenceEvolutionTracker — records per-version confidence evolution for a subject.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.decision.confidence.confidence_constants import HISTORY_WINDOW_SIZE


@dataclass(frozen=True)
class EvolutionRecord:
    subject_id:    str
    version:       int
    confidence:    float
    recorded_at:   datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_id":  self.subject_id,
            "version":     self.version,
            "confidence":  round(self.confidence, 2),
            "recorded_at": self.recorded_at.isoformat(),
        }


@dataclass(frozen=True)
class EvolutionResult:
    subject_id:     str
    record_count:   int
    first_version:  int
    last_version:   int
    first_conf:     float
    last_conf:      float
    delta:          float    # last - first
    versions:       Tuple[int, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_id":    self.subject_id,
            "record_count":  self.record_count,
            "first_version": self.first_version,
            "last_version":  self.last_version,
            "first_conf":    round(self.first_conf, 2),
            "last_conf":     round(self.last_conf, 2),
            "delta":         round(self.delta, 2),
        }


from typing import Tuple  # noqa: E402


class ConfidenceEvolutionTracker:
    """Thread-safe per-subject version-over-version confidence tracker."""

    def __init__(self, max_records: int = HISTORY_WINDOW_SIZE) -> None:
        self._max    = max_records
        self._lock   = threading.RLock()
        self._records: Dict[str, List[EvolutionRecord]] = {}

    def record(self, subject_id: str, version: int, confidence: float) -> None:
        with self._lock:
            recs = self._records.setdefault(subject_id, [])
            recs.append(EvolutionRecord(
                subject_id=subject_id,
                version=version,
                confidence=confidence,
                recorded_at=datetime.now(timezone.utc),
            ))
            if len(recs) > self._max:
                self._records[subject_id] = recs[-self._max:]

    def evolution(self, subject_id: str) -> Optional[EvolutionResult]:
        with self._lock:
            recs = self._records.get(subject_id, [])
            if not recs:
                return None
            sorted_recs = sorted(recs, key=lambda r: r.version)
            return EvolutionResult(
                subject_id=subject_id,
                record_count=len(sorted_recs),
                first_version=sorted_recs[0].version,
                last_version=sorted_recs[-1].version,
                first_conf=sorted_recs[0].confidence,
                last_conf=sorted_recs[-1].confidence,
                delta=sorted_recs[-1].confidence - sorted_recs[0].confidence,
                versions=tuple(r.version for r in sorted_recs),
            )

    def confidence_series(self, subject_id: str) -> List[float]:
        with self._lock:
            recs = self._records.get(subject_id, [])
            return [r.confidence for r in sorted(recs, key=lambda r: r.version)]

    def known_subjects(self) -> List[str]:
        with self._lock:
            return list(self._records.keys())
