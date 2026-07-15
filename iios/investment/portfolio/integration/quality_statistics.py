"""iios/investment/portfolio/integration/quality_statistics.py

Quality assessment run-level metrics and statistics.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class QualityRunMetric:
    metric_id:      str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:   str   = ""
    overall_score:  float = 0.0
    completeness:   float = 0.0
    consistency:    float = 0.0
    freshness:      float = 0.0
    confidence:     float = 0.0
    coverage:       float = 0.0
    is_publishable: bool  = False


class QualityStatistics:
    """Thread-safe statistics over quality assessment runs."""

    def __init__(self, max_runs: int = 200) -> None:
        self._max  = max_runs
        self._lock = threading.RLock()
        self._runs: List[QualityRunMetric] = []

    def record(self, metric: QualityRunMetric) -> None:
        with self._lock:
            self._runs.append(metric)
            if len(self._runs) > self._max:
                self._runs = self._runs[-self._max:]

    def average_quality(self) -> float:
        with self._lock:
            if not self._runs:
                return 0.0
            return sum(r.overall_score for r in self._runs) / len(self._runs)

    def publishable_rate(self) -> float:
        with self._lock:
            if not self._runs:
                return 0.0
            return sum(1 for r in self._runs if r.is_publishable) / len(self._runs)

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            n = len(self._runs)
            if n == 0:
                return {"total_runs": 0}
            return {
                "total_runs":       n,
                "avg_quality":      round(sum(r.overall_score for r in self._runs) / n, 4),
                "avg_completeness": round(sum(r.completeness  for r in self._runs) / n, 4),
                "publishable_rate": round(self.publishable_rate(), 4),
            }
