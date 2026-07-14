"""iios/investment/decision/confidence/reasoning_confidence.py
ReasoningConfidenceEstimator — aggregates consistency, logic strength, and contradiction
analysis into a single reasoning confidence score (0–100).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from iios.investment.decision.confidence.confidence_constants import (
    ReasoningConfidenceFactor,
)
from iios.investment.decision.confidence.contradiction_analysis import (
    ContradictionAnalyzer,
    ContradictionResult,
)
from iios.investment.decision.confidence.logic_strength import (
    LogicStrengthAnalyzer,
    LogicStrengthResult,
)
from iios.investment.decision.confidence.reasoning_consistency import (
    ReasoningConsistencyAnalyzer,
    ConsistencyResult,
)
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot


@dataclass(frozen=True)
class ReasoningConfidenceResult:
    overall:              float   # 0–100
    completeness_score:   float   # 0–100
    consistency_score:    float   # 0–100
    contradiction_free:   float   # 0–100
    hypothesis_strength:  float   # 0–100
    argument_quality:     float   # 0–100
    consistency_detail:   ConsistencyResult
    logic_detail:         LogicStrengthResult
    contradiction_detail: ContradictionResult
    factor_weights:       Tuple[Tuple[str, float], ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":              round(self.overall, 2),
            "completeness_score":   round(self.completeness_score, 2),
            "consistency_score":    round(self.consistency_score, 2),
            "contradiction_free":   round(self.contradiction_free, 2),
            "hypothesis_strength":  round(self.hypothesis_strength, 2),
            "argument_quality":     round(self.argument_quality, 2),
            "consistency_detail":   self.consistency_detail.to_dict(),
            "logic_detail":         self.logic_detail.to_dict(),
            "contradiction_detail": self.contradiction_detail.to_dict(),
        }


class ReasoningConfidenceEstimator:
    """
    Estimates reasoning-dimension confidence from a ReasoningSnapshot.
    Consumes ONLY the Decision Reasoning Engine output.
    """

    def __init__(
        self,
        consistency_analyzer:    Optional[ReasoningConsistencyAnalyzer] = None,
        logic_strength_analyzer:  Optional[LogicStrengthAnalyzer]       = None,
        contradiction_analyzer:   Optional[ContradictionAnalyzer]       = None,
    ) -> None:
        self._cons = consistency_analyzer   or ReasoningConsistencyAnalyzer()
        self._logic = logic_strength_analyzer or LogicStrengthAnalyzer()
        self._cont  = contradiction_analyzer  or ContradictionAnalyzer()

    def estimate(self, snapshot: ReasoningSnapshot) -> ReasoningConfidenceResult:
        cons_result = self._cons.analyze(snapshot)
        logic_result = self._logic.analyze(snapshot)
        cont_result  = self._cont.analyze(snapshot)

        # ── Map to named factors ───────────────────────────────────────────
        completeness_score  = logic_result.step_completeness
        consistency_score   = cons_result.consistency_score
        contradiction_free  = cont_result.contradiction_free_score
        hypothesis_strength = min(100.0, logic_result.primary_support * 100.0)
        argument_quality    = min(100.0, logic_result.argument_ratio * 100.0)

        # ── Weights ────────────────────────────────────────────────────────
        cw  = ReasoningConfidenceFactor.COMPLETENESS.default_weight
        csw = ReasoningConfidenceFactor.CONSISTENCY.default_weight
        cfw = ReasoningConfidenceFactor.CONTRADICTION_FREE.default_weight
        hw  = ReasoningConfidenceFactor.HYPOTHESIS_STRENGTH.default_weight
        aw  = ReasoningConfidenceFactor.ARGUMENT_QUALITY.default_weight

        overall = (
            completeness_score  * cw
            + consistency_score * csw
            + contradiction_free * cfw
            + hypothesis_strength * hw
            + argument_quality  * aw
        )
        overall = max(0.0, min(100.0, overall))

        factor_weights: Tuple[Tuple[str, float], ...] = (
            (ReasoningConfidenceFactor.COMPLETENESS.value,        cw),
            (ReasoningConfidenceFactor.CONSISTENCY.value,         csw),
            (ReasoningConfidenceFactor.CONTRADICTION_FREE.value,  cfw),
            (ReasoningConfidenceFactor.HYPOTHESIS_STRENGTH.value, hw),
            (ReasoningConfidenceFactor.ARGUMENT_QUALITY.value,    aw),
        )

        return ReasoningConfidenceResult(
            overall=round(overall, 4),
            completeness_score=round(completeness_score, 4),
            consistency_score=round(consistency_score, 4),
            contradiction_free=round(contradiction_free, 4),
            hypothesis_strength=round(hypothesis_strength, 4),
            argument_quality=round(argument_quality, 4),
            consistency_detail=cons_result,
            logic_detail=logic_result,
            contradiction_detail=cont_result,
            factor_weights=factor_weights,
        )
