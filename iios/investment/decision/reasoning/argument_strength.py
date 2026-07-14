"""iios/investment/decision/reasoning/argument_strength.py
ArgumentStrength — evaluates and summarises the net strength of arguments for a hypothesis.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.reasoning.reasoning_constants import ArgumentStrengthLevel, ArgumentType
from iios.investment.decision.reasoning.supporting_arguments import Argument


@dataclass(frozen=True)
class ArgumentStrengthSummary:
    hypothesis_id:        str
    supporting_count:     int
    opposing_count:       int
    avg_supporting_score: float    # 0–1
    avg_opposing_score:   float    # 0–1
    net_strength:         float    # -1 to +1  (>0 = net supporting)
    strength_level:       ArgumentStrengthLevel
    missing_evidence:     bool     # True if either side has zero evidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id":        self.hypothesis_id,
            "supporting_count":     self.supporting_count,
            "opposing_count":       self.opposing_count,
            "avg_supporting_score": round(self.avg_supporting_score, 3),
            "avg_opposing_score":   round(self.avg_opposing_score, 3),
            "net_strength":         round(self.net_strength, 3),
            "strength_level":       self.strength_level.value,
            "missing_evidence":     self.missing_evidence,
        }


class ArgumentStrength:
    """Computes net argument strength from supporting and opposing argument lists."""

    def evaluate(
        self,
        hypothesis_id: str,
        arguments:     List[Argument],
    ) -> ArgumentStrengthSummary:
        supporting = [a for a in arguments if a.argument_type == ArgumentType.SUPPORTING]
        opposing   = [a for a in arguments if a.argument_type == ArgumentType.OPPOSING]

        avg_sup = sum(a.strength_score for a in supporting) / len(supporting) if supporting else 0.0
        avg_opp = sum(a.strength_score for a in opposing)   / len(opposing)   if opposing   else 0.0
        net     = round(avg_sup - avg_opp, 4)

        if net >= 0.50:
            level = ArgumentStrengthLevel.STRONG
        elif net >= 0.25:
            level = ArgumentStrengthLevel.MODERATE
        elif net >= 0.0:
            level = ArgumentStrengthLevel.WEAK
        else:
            level = ArgumentStrengthLevel.NEGLIGIBLE

        missing = not supporting or not opposing

        return ArgumentStrengthSummary(
            hypothesis_id=hypothesis_id,
            supporting_count=len(supporting),
            opposing_count=len(opposing),
            avg_supporting_score=round(avg_sup, 4),
            avg_opposing_score=round(avg_opp, 4),
            net_strength=net,
            strength_level=level,
            missing_evidence=missing,
        )
