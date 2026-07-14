"""iios/investment/decision/confidence/reasoning_consistency.py
ReasoningConsistencyAnalyzer — evaluates internal consistency of a reasoning chain.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot


@dataclass(frozen=True)
class ConsistencyResult:
    step_count:              int
    confidence_std_dev:      float   # low = consistent
    step_confidence_trend:   float   # >0 means confidence grows through chain
    logic_status_score:      float   # 0–100 from logic_result.consistency_score
    inter_step_consistency:  float   # 0–100
    consistency_score:       float   # 0–100 overall

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_count":             self.step_count,
            "confidence_std_dev":     round(self.confidence_std_dev, 4),
            "step_confidence_trend":  round(self.step_confidence_trend, 4),
            "logic_status_score":     round(self.logic_status_score, 2),
            "inter_step_consistency": round(self.inter_step_consistency, 2),
            "consistency_score":      round(self.consistency_score, 2),
        }


class ReasoningConsistencyAnalyzer:
    """Computes consistency of a reasoning chain from a ReasoningSnapshot."""

    def analyze(self, snapshot: ReasoningSnapshot) -> ConsistencyResult:
        chain = snapshot.reasoning_chain
        steps = list(chain.steps)

        if not steps:
            return ConsistencyResult(
                step_count=0,
                confidence_std_dev=0.0,
                step_confidence_trend=0.0,
                logic_status_score=snapshot.logic_result.consistency_score,
                inter_step_consistency=0.0,
                consistency_score=0.0,
            )

        confidences: List[float] = [s.confidence for s in steps]

        # Standard deviation of step confidences (lower = more consistent)
        std_dev = statistics.stdev(confidences) if len(confidences) > 1 else 0.0

        # Trend: is confidence growing or declining through the chain?
        if len(confidences) > 1:
            first_half = statistics.mean(confidences[:len(confidences)//2])
            second_half = statistics.mean(confidences[len(confidences)//2:])
            trend = second_half - first_half
        else:
            trend = 0.0

        logic_score = snapshot.logic_result.consistency_score   # 0–100

        # Inter-step consistency: penalise high std_dev
        inter_step = max(0.0, 100.0 - std_dev * 2.0)

        # Composite
        overall = (
            logic_score      * 0.50
            + inter_step     * 0.30
            + min(100.0, max(0.0, 50.0 + trend)) * 0.20
        )
        overall = max(0.0, min(100.0, overall))

        return ConsistencyResult(
            step_count=len(steps),
            confidence_std_dev=round(std_dev, 4),
            step_confidence_trend=round(trend, 4),
            logic_status_score=round(logic_score, 4),
            inter_step_consistency=round(inter_step, 4),
            consistency_score=round(overall, 4),
        )
