"""
iios/decisions/models/decision_statistics.py
=============================================
DecisionStatistics — aggregated metrics over a set of decisions.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..decision_constants import DecisionStatus, DecisionType
from .decision import Decision


@dataclass
class DecisionStatistics:
    """
    Aggregated statistics over a collection of Decision objects.
    """

    stats_id:               str              = field(default_factory=lambda: str(uuid.uuid4()))
    source_id:              str              = "*"
    total:                  int              = 0
    completed:              int              = 0
    failed:                 int              = 0
    cancelled:              int              = 0
    deferred:               int              = 0
    avg_confidence:         float            = 0.0
    avg_risk_score:         float            = 0.0
    avg_elapsed_ms:         float            = 0.0
    min_confidence:         float            = 0.0
    max_confidence:         float            = 0.0
    completion_rate:        float            = 0.0
    by_type:                dict[str, int]   = field(default_factory=dict)
    generated_at:           float            = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stats_id":         self.stats_id,
            "source_id":        self.source_id,
            "total":            self.total,
            "completed":        self.completed,
            "failed":           self.failed,
            "cancelled":        self.cancelled,
            "deferred":         self.deferred,
            "avg_confidence":   round(self.avg_confidence, 4),
            "avg_risk_score":   round(self.avg_risk_score, 4),
            "avg_elapsed_ms":   round(self.avg_elapsed_ms, 2),
            "min_confidence":   round(self.min_confidence, 4),
            "max_confidence":   round(self.max_confidence, 4),
            "completion_rate":  round(self.completion_rate, 4),
            "by_type":          dict(self.by_type),
            "generated_at":     self.generated_at,
        }


def build_statistics(decisions: list[Decision], source_id: str = "*") -> DecisionStatistics:
    if not decisions:
        return DecisionStatistics(source_id=source_id)

    completed  = [d for d in decisions if d.status == DecisionStatus.COMPLETED]
    failed     = [d for d in decisions if d.status == DecisionStatus.FAILED]
    cancelled  = [d for d in decisions if d.status == DecisionStatus.CANCELLED]
    deferred   = [d for d in decisions if d.status == DecisionStatus.DEFERRED]

    confidences = [d.confidence for d in completed] if completed else [0.0]
    risks       = [d.risk_score for d in completed] if completed else [0.0]
    elapsed     = [d.elapsed_ms() for d in completed] if completed else [0.0]

    by_type: dict[str, int] = {}
    for d in decisions:
        by_type[d.decision_type.value] = by_type.get(d.decision_type.value, 0) + 1

    return DecisionStatistics(
        source_id        = source_id,
        total            = len(decisions),
        completed        = len(completed),
        failed           = len(failed),
        cancelled        = len(cancelled),
        deferred         = len(deferred),
        avg_confidence   = sum(confidences) / len(confidences),
        avg_risk_score   = sum(risks) / len(risks),
        avg_elapsed_ms   = sum(elapsed) / len(elapsed),
        min_confidence   = min(confidences),
        max_confidence   = max(confidences),
        completion_rate  = len(completed) / len(decisions),
        by_type          = by_type,
    )
