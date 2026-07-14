"""iios/investment/decision/reasoning/hypothesis_validator.py
HypothesisValidator — validates structural consistency of generated hypotheses.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.reasoning.hypothesis_engine import Hypothesis
from iios.investment.decision.reasoning.reasoning_constants import (
    HypothesisStatus,
    HypothesisType,
    LogicValidationStatus,
)


@dataclass(frozen=True)
class HypothesisValidationResult:
    total_hypotheses:       int
    valid_hypotheses:       int
    has_primary:            bool
    has_alternative:        bool
    contradictions_found:   bool
    status:                 LogicValidationStatus
    issues:                 Tuple[str, ...]
    hypothesis_issues:      int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_hypotheses":     self.total_hypotheses,
            "valid_hypotheses":     self.valid_hypotheses,
            "has_primary":          self.has_primary,
            "has_alternative":      self.has_alternative,
            "contradictions_found": self.contradictions_found,
            "status":               self.status.value,
            "hypothesis_issues":    self.hypothesis_issues,
            "issues":               list(self.issues),
        }


class HypothesisValidator:
    """Validates that a hypothesis set is structurally coherent."""

    def validate(self, hypotheses: List[Hypothesis]) -> HypothesisValidationResult:
        issues: List[str] = []

        if not hypotheses:
            return HypothesisValidationResult(
                total_hypotheses=0, valid_hypotheses=0, has_primary=False,
                has_alternative=False, contradictions_found=False,
                status=LogicValidationStatus.INSUFFICIENT,
                issues=("No hypotheses provided.",),
            )

        # Check for primary
        supported = [h for h in hypotheses if h.status == HypothesisStatus.SUPPORTED]
        has_primary = len(supported) >= 1

        # Check for alternative
        has_alt = any(h.hypothesis_type == HypothesisType.ALTERNATIVE for h in hypotheses)

        # Check contradictions: BULLISH and BEARISH both SUPPORTED → contradiction
        bullish_sup = any(h.hypothesis_type == HypothesisType.BULLISH and
                          h.status == HypothesisStatus.SUPPORTED for h in hypotheses)
        bearish_sup = any(h.hypothesis_type == HypothesisType.BEARISH and
                          h.status == HypothesisStatus.SUPPORTED for h in hypotheses)
        contradictions = bullish_sup and bearish_sup
        if contradictions:
            issues.append("Both BULLISH and BEARISH hypotheses are SUPPORTED — contradictory evidence.")

        valid = len([h for h in hypotheses if h.status != HypothesisStatus.REJECTED])

        if len(hypotheses) < 2:
            issues.append("Only one hypothesis generated — limited reasoning coverage.")

        if not has_primary:
            issues.append("No hypothesis is sufficiently supported.")

        if contradictions:
            status = LogicValidationStatus.CONTRADICTORY
        elif not has_primary:
            status = LogicValidationStatus.VALID_WITH_GAPS
        else:
            status = LogicValidationStatus.VALID

        return HypothesisValidationResult(
            total_hypotheses=len(hypotheses),
            valid_hypotheses=valid,
            has_primary=has_primary,
            has_alternative=has_alt,
            contradictions_found=contradictions,
            status=status,
            issues=tuple(issues),
            hypothesis_issues=len(issues),
        )
