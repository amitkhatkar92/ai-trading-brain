"""iios/investment/decision/risk/execution_risk.py
ExecutionRiskEvaluator — derives execution risk from reasoning and confidence quality.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.risk_constants import EXECUTION_RISK_CONF_FLOOR


@dataclass(frozen=True)
class ExecutionRiskResult:
    confidence_score:     float   # 0–100 from confidence engine
    reasoning_quality:    float   # 0–100 from reasoning engine
    logic_consistency:    float   # 0–100
    timing_risk:          float   # 0–100 (proxy: stale reasoning)
    execution_risk:       float   # 0–100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_score":  round(self.confidence_score, 2),
            "reasoning_quality": round(self.reasoning_quality, 2),
            "logic_consistency": round(self.logic_consistency, 2),
            "timing_risk":       round(self.timing_risk, 2),
            "execution_risk":    round(self.execution_risk, 2),
        }


class ExecutionRiskEvaluator:
    """
    Derives execution dimension risk from ReasoningSnapshot + ConfidenceSnapshot.
    Consumes ONLY upstream engine outputs.
    """

    def evaluate(
        self,
        reasoning_snapshot:  ReasoningSnapshot,
        confidence_snapshot: ConfidenceSnapshot,
    ) -> ExecutionRiskResult:
        conf  = confidence_snapshot.overall_confidence
        rq    = reasoning_snapshot.quality_score.overall     # 0–100
        logic = reasoning_snapshot.logic_result.consistency_score  # 0–100

        # Confidence risk component
        if conf >= 70.0:
            conf_risk = 0.0
        elif conf >= EXECUTION_RISK_CONF_FLOOR:
            conf_risk = (70.0 - conf) / (70.0 - EXECUTION_RISK_CONF_FLOOR) * 40.0
        else:
            conf_risk = 40.0 + (EXECUTION_RISK_CONF_FLOOR - conf) * 1.5
        conf_risk = min(100.0, max(0.0, conf_risk))

        # Reasoning quality risk (inverse)
        rq_risk    = max(0.0, 100.0 - rq)
        logic_risk = max(0.0, 100.0 - logic)

        # Timing risk: how long ago was reasoning done? (proxy: use duration_ms as completeness indicator)
        duration_ms = reasoning_snapshot.reasoning_duration_ms
        timing_risk = 0.0 if duration_ms < 5000 else min(30.0, duration_ms / 1000.0)

        execution_risk = (
            conf_risk  * 0.40
            + rq_risk  * 0.30
            + logic_risk * 0.20
            + timing_risk * 0.10
        )
        execution_risk = max(0.0, min(100.0, execution_risk))

        return ExecutionRiskResult(
            confidence_score=round(conf, 4),
            reasoning_quality=round(rq, 4),
            logic_consistency=round(logic, 4),
            timing_risk=round(timing_risk, 4),
            execution_risk=round(execution_risk, 4),
        )
