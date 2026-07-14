"""iios/investment/decision/confidence/contradiction_analysis.py
ContradictionAnalyzer — detects and measures contradiction within reasoning.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.reasoning.reasoning_constants import LogicValidationStatus
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot


@dataclass(frozen=True)
class ContradictionResult:
    contradiction_count:      int
    has_contradictions:       bool
    contradiction_severity:   float   # 0–100  (0 = none, 100 = maximum)
    contradiction_free_score: float   # 0–100  (inverse of severity)
    contradictory_hypotheses: int
    argument_conflicts:       int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contradiction_count":      self.contradiction_count,
            "has_contradictions":       self.has_contradictions,
            "contradiction_severity":   round(self.contradiction_severity, 2),
            "contradiction_free_score": round(self.contradiction_free_score, 2),
            "contradictory_hypotheses": self.contradictory_hypotheses,
            "argument_conflicts":       self.argument_conflicts,
        }


class ContradictionAnalyzer:
    """
    Measures contradiction level in a reasoning snapshot.
    Uses the logic_result and argument_reports from the reasoning engine.
    """

    def analyze(self, snapshot: ReasoningSnapshot) -> ContradictionResult:
        logic = snapshot.logic_result

        contradiction_count = logic.contradiction_count
        hyp_contradictions  = 1 if logic.contradiction_count > 0 else 0

        # Count argument-level conflicts: reports where opposing > supporting score
        arg_conflicts = sum(
            1 for r in snapshot.argument_reports
            if (r.strength_summary.avg_opposing_score > r.strength_summary.avg_supporting_score)
        )

        total_contradictions = contradiction_count + arg_conflicts

        # Severity: 0–100
        if logic.status == LogicValidationStatus.CONTRADICTORY:
            base_severity = 80.0
        elif logic.status == LogicValidationStatus.VALID_WITH_GAPS:
            base_severity = 30.0
        elif logic.status == LogicValidationStatus.INSUFFICIENT:
            base_severity = 50.0
        else:
            base_severity = 0.0

        # Additional penalty per argument conflict
        severity = min(100.0, base_severity + arg_conflicts * 5.0)

        return ContradictionResult(
            contradiction_count=total_contradictions,
            has_contradictions=(total_contradictions > 0),
            contradiction_severity=round(severity, 4),
            contradiction_free_score=round(100.0 - severity, 4),
            contradictory_hypotheses=hyp_contradictions,
            argument_conflicts=arg_conflicts,
        )
