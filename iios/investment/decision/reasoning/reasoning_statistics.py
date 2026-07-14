"""iios/investment/decision/reasoning/reasoning_statistics.py
ReasoningStatistics — rolling aggregate statistics across reasoning runs.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot


@dataclass(frozen=True)
class ReasoningStatistics:
    total_snapshots:     int
    successful:          int
    failed:              int
    avg_quality:         float
    avg_step_count:      float
    avg_duration_ms:     float
    avg_hypothesis_count: float
    computed_at:         datetime

    @property
    def success_rate(self) -> float:
        return round(self.successful / self.total_snapshots, 3) if self.total_snapshots else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_snapshots":    self.total_snapshots,
            "successful":         self.successful,
            "failed":             self.failed,
            "success_rate":       self.success_rate,
            "avg_quality":        round(self.avg_quality, 2),
            "avg_step_count":     round(self.avg_step_count, 1),
            "avg_duration_ms":    round(self.avg_duration_ms, 1),
            "avg_hypothesis_count": round(self.avg_hypothesis_count, 1),
            "computed_at":        self.computed_at.isoformat(),
        }


class ReasoningStatisticsTracker:
    """Thread-safe rolling accumulator for ReasoningSnapshot stats."""

    def __init__(self) -> None:
        self._lock           = threading.RLock()
        self._total          = 0
        self._success        = 0
        self._fail           = 0
        self._quality_sum    = 0.0
        self._step_sum       = 0.0
        self._duration_sum   = 0.0
        self._hyp_sum        = 0.0

    def record(self, snapshot: ReasoningSnapshot) -> None:
        with self._lock:
            self._total        += 1
            if snapshot.is_complete:
                self._success  += 1
            else:
                self._fail     += 1
            self._quality_sum  += snapshot.quality_score.overall
            self._step_sum     += snapshot.reasoning_chain.step_count
            self._duration_sum += snapshot.reasoning_duration_ms
            self._hyp_sum      += len(snapshot.hypotheses)

    def summary(self) -> ReasoningStatistics:
        with self._lock:
            n = self._total or 1
            return ReasoningStatistics(
                total_snapshots=self._total,
                successful=self._success,
                failed=self._fail,
                avg_quality=round(self._quality_sum / n, 2),
                avg_step_count=round(self._step_sum / n, 1),
                avg_duration_ms=round(self._duration_sum / n, 1),
                avg_hypothesis_count=round(self._hyp_sum / n, 1),
                computed_at=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = self._success = self._fail = 0
            self._quality_sum = self._step_sum = self._duration_sum = self._hyp_sum = 0.0
