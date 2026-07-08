"""
iios/intelligence/agents/consensus/confidence_aggregator.py
===========================================================
ConfidenceAggregator — aggregates per-agent confidence scores
into a single system-level confidence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from ..core.base_agent import AgentDecision

__all__ = ["AggregatedConfidence", "ConfidenceAggregator"]


@dataclass
class AggregatedConfidence:
    """Aggregated confidence metrics."""
    mean:       float
    median:     float
    weighted:   float
    min_val:    float
    max_val:    float
    std_dev:    float
    count:      int
    explanation: str

    def to_dict(self) -> dict:
        return {
            "mean":     round(self.mean,     4),
            "median":   round(self.median,   4),
            "weighted": round(self.weighted, 4),
            "min":      round(self.min_val,  4),
            "max":      round(self.max_val,  4),
            "std_dev":  round(self.std_dev,  4),
            "count":    self.count,
        }


class ConfidenceAggregator:
    """Computes ensemble confidence statistics over multiple agent decisions."""

    def aggregate(self, decisions: list[AgentDecision]) -> AggregatedConfidence:
        """Full aggregation with all statistics."""
        if not decisions:
            return AggregatedConfidence(
                mean=0.0, median=0.0, weighted=0.0,
                min_val=0.0, max_val=0.0, std_dev=0.0,
                count=0, explanation="No decisions"
            )

        confs  = [d.confidence for d in decisions]
        n      = len(confs)
        mean   = sum(confs) / n
        median = self._median(confs)

        total_w = sum(d.weight for d in decisions)
        weighted = (
            sum(d.confidence * d.weight for d in decisions) / total_w
            if total_w > 0 else mean
        )

        variance = sum((c - mean) ** 2 for c in confs) / n
        std_dev  = math.sqrt(variance)

        return AggregatedConfidence(
            mean        = mean,
            median      = median,
            weighted    = weighted,
            min_val     = min(confs),
            max_val     = max(confs),
            std_dev     = std_dev,
            count       = n,
            explanation = (
                f"Aggregated {n} decisions: "
                f"mean={mean:.2%}, weighted={weighted:.2%}, "
                f"std={std_dev:.2%}"
            ),
        )

    def mean_confidence(self, decisions: list[AgentDecision]) -> float:
        if not decisions:
            return 0.0
        return sum(d.confidence for d in decisions) / len(decisions)

    def weighted_confidence(self, decisions: list[AgentDecision]) -> float:
        if not decisions:
            return 0.0
        total_w = sum(d.weight for d in decisions)
        if total_w == 0:
            return self.mean_confidence(decisions)
        return sum(d.confidence * d.weight for d in decisions) / total_w

    def is_high_confidence(
        self,
        decisions:  list[AgentDecision],
        threshold:  float = 0.7,
    ) -> bool:
        return self.weighted_confidence(decisions) >= threshold

    @staticmethod
    def _median(values: list[float]) -> float:
        s = sorted(values)
        n = len(s)
        mid = n // 2
        return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2
