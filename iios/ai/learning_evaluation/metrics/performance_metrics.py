"""
performance_metrics.py -- iios.ai.learning_evaluation.metrics
===============================================================
:class:`PerformanceMetrics` — aggregate container for all metric types.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Optional

from .accuracy_metrics    import AccuracyMetrics
from .confidence_metrics  import ConfidenceMetrics
from .cost_metrics        import CostMetrics
from .latency_metrics     import LatencyMetrics
from .reliability_metrics import ReliabilityMetrics


@dataclass(frozen=True)
class PerformanceMetrics:
    """
    Aggregate container for all five metric categories.

    Individual metric objects are optional — only the categories computed
    for a given evaluation run are populated.
    """

    metrics_id:   str
    session_id:   str
    accuracy:     Optional[AccuracyMetrics]
    latency:      Optional[LatencyMetrics]
    cost:         Optional[CostMetrics]
    reliability:  Optional[ReliabilityMetrics]
    confidence:   Optional[ConfidenceMetrics]
    captured_at:  float

    @classmethod
    def build(
        cls,
        session_id:  str,
        accuracy:    Optional[AccuracyMetrics]    = None,
        latency:     Optional[LatencyMetrics]     = None,
        cost:        Optional[CostMetrics]        = None,
        reliability: Optional[ReliabilityMetrics] = None,
        confidence:  Optional[ConfidenceMetrics]  = None,
    ) -> "PerformanceMetrics":
        return cls(
            metrics_id  = str(uuid.uuid4()),
            session_id  = session_id,
            accuracy    = accuracy,
            latency     = latency,
            cost        = cost,
            reliability = reliability,
            confidence  = confidence,
            captured_at = time.time(),
        )

    def overall_score(self) -> float:
        """
        Compute a simple aggregate 0.0–1.0 score from available metrics.

        Weights: accuracy.f1 40%, confidence (1-ECE) 20%, reliability.success_rate 20%,
        latency (inverse normalised) 10%, cost (inverse normalised) 10%.
        Only metrics that are present contribute.
        """
        scores = []
        if self.accuracy:
            scores.append(("accuracy", self.accuracy.f1, 0.40))
        if self.confidence:
            scores.append(("confidence", max(0.0, 1.0 - self.confidence.calibration_error), 0.20))
        if self.reliability:
            scores.append(("reliability", self.reliability.success_rate, 0.20))
        # latency and cost don't contribute to overall if none present
        if not scores:
            return 0.0
        total_weight = sum(w for _, _, w in scores)
        weighted     = sum(s * w for _, s, w in scores)
        return round(weighted / total_weight, 6) if total_weight else 0.0
