"""iios/investment/decision/confidence/confidence_statistics.py
ConfidenceStatistics — thread-safe accumulator for confidence engine telemetry.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.decision.confidence.confidence_constants import ConfidenceQualityGrade


@dataclass(frozen=True)
class ConfidenceStatistics:
    total_estimations:   int
    successful:          int
    failed:              int
    avg_confidence:      float   # 0–100
    avg_duration_ms:     float
    avg_evidence_conf:   float
    avg_reasoning_conf:  float
    high_confidence_pct: float   # fraction >= 70
    computed_at:         datetime

    @property
    def success_rate(self) -> float:
        return self.successful / max(1, self.total_estimations)

    @property
    def grade(self) -> str:
        return ConfidenceQualityGrade.from_score(self.avg_confidence).value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_estimations":   self.total_estimations,
            "successful":          self.successful,
            "failed":              self.failed,
            "success_rate":        round(self.success_rate, 4),
            "avg_confidence":      round(self.avg_confidence, 2),
            "avg_duration_ms":     round(self.avg_duration_ms, 2),
            "avg_evidence_conf":   round(self.avg_evidence_conf, 2),
            "avg_reasoning_conf":  round(self.avg_reasoning_conf, 2),
            "high_confidence_pct": round(self.high_confidence_pct, 4),
            "grade":               self.grade,
            "computed_at":         self.computed_at.isoformat(),
        }


class ConfidenceStatisticsTracker:
    """Thread-safe accumulator for ConfidenceStatistics."""

    def __init__(self) -> None:
        self._lock            = threading.RLock()
        self._total           = 0
        self._successful      = 0
        self._failed          = 0
        self._sum_confidence  = 0.0
        self._sum_duration    = 0.0
        self._sum_ev_conf     = 0.0
        self._sum_re_conf     = 0.0
        self._high_conf_count = 0

    def record_success(
        self,
        overall_confidence:    float,
        duration_ms:           float,
        evidence_confidence:   float,
        reasoning_confidence:  float,
    ) -> None:
        with self._lock:
            self._total          += 1
            self._successful     += 1
            self._sum_confidence += overall_confidence
            self._sum_duration   += duration_ms
            self._sum_ev_conf    += evidence_confidence
            self._sum_re_conf    += reasoning_confidence
            if overall_confidence >= 70.0:
                self._high_conf_count += 1

    def record_failure(self) -> None:
        with self._lock:
            self._total  += 1
            self._failed += 1

    def summary(self) -> ConfidenceStatistics:
        with self._lock:
            s = max(1, self._successful)
            return ConfidenceStatistics(
                total_estimations=self._total,
                successful=self._successful,
                failed=self._failed,
                avg_confidence=round(self._sum_confidence / s, 4),
                avg_duration_ms=round(self._sum_duration / s, 4),
                avg_evidence_conf=round(self._sum_ev_conf / s, 4),
                avg_reasoning_conf=round(self._sum_re_conf / s, 4),
                high_confidence_pct=round(self._high_conf_count / s, 4),
                computed_at=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = self._successful = self._failed = 0
            self._sum_confidence = self._sum_duration = 0.0
            self._sum_ev_conf = self._sum_re_conf = 0.0
            self._high_conf_count = 0
