"""iios/investment/decision/reasoning/reasoning_confidence.py
ReasoningConfidence — measures confidence in the reasoning process itself.
Does NOT estimate investment confidence — only structural reasoning confidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.decision.reasoning.reasoning_chain import ReasoningChain
from iios.investment.decision.reasoning.reasoning_constants import LogicValidationStatus
from iios.investment.decision.reasoning.logic_validator import LogicValidationResult


@dataclass(frozen=True)
class ReasoningConfidenceScore:
    """Structural confidence in the reasoning process (not investment confidence)."""
    overall:          float   # 0–100
    step_confidence:  float   # 0–100 avg confidence across steps
    logic_confidence: float   # 0–100 based on logic validation status
    evidence_depth:   float   # 0–100 normalised evidence references
    chain_completeness: float  # 0–100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":           round(self.overall, 2),
            "step_confidence":   round(self.step_confidence, 2),
            "logic_confidence":  round(self.logic_confidence, 2),
            "evidence_depth":    round(self.evidence_depth, 2),
            "chain_completeness": round(self.chain_completeness, 2),
        }


_LOGIC_STATUS_CONFIDENCE: Dict[str, float] = {
    LogicValidationStatus.VALID.value:           100.0,
    LogicValidationStatus.VALID_WITH_GAPS.value:  70.0,
    LogicValidationStatus.CONTRADICTORY.value:    30.0,
    LogicValidationStatus.INSUFFICIENT.value:     10.0,
}

_EXPECTED_STEP_COUNT = 9  # one per ReasoningStepType


class ReasoningConfidence:
    """Computes structural reasoning confidence from chain and validation result."""

    def compute(
        self,
        chain:        ReasoningChain,
        logic_result: LogicValidationResult,
        total_evidence_items: int,
    ) -> ReasoningConfidenceScore:
        step_conf = chain.avg_step_confidence
        logic_conf = _LOGIC_STATUS_CONFIDENCE.get(logic_result.status.value, 50.0)
        evidence_depth = min(100.0, chain.total_evidence_refs / max(1, total_evidence_items) * 100.0)
        chain_completeness = min(100.0, chain.step_count / _EXPECTED_STEP_COUNT * 100.0)
        overall = (
            step_conf       * 0.35
            + logic_conf    * 0.30
            + evidence_depth * 0.20
            + chain_completeness * 0.15
        )
        return ReasoningConfidenceScore(
            overall=round(min(100.0, overall), 2),
            step_confidence=round(step_conf, 2),
            logic_confidence=round(logic_conf, 2),
            evidence_depth=round(evidence_depth, 2),
            chain_completeness=round(chain_completeness, 2),
        )
