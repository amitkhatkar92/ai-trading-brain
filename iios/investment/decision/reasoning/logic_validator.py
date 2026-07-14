"""iios/investment/decision/reasoning/logic_validator.py
LogicValidator — validates the logical consistency of the reasoning before finalisation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.reasoning.argument_engine import ArgumentReport
from iios.investment.decision.reasoning.hypothesis_engine import Hypothesis
from iios.investment.decision.reasoning.hypothesis_validator import HypothesisValidator
from iios.investment.decision.reasoning.reasoning_constants import (
    LogicValidationStatus,
    ReasoningStepType,
)
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep, make_step


@dataclass(frozen=True)
class LogicValidationResult:
    status:             LogicValidationStatus
    hypothesis_issues:  int
    argument_gaps:      int
    contradiction_count: int
    consistency_score:  float        # 0–100
    issues:             Tuple[str, ...]

    @property
    def is_usable(self) -> bool:
        return self.status.is_usable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status":             self.status.value,
            "hypothesis_issues":  self.hypothesis_issues,
            "argument_gaps":      self.argument_gaps,
            "contradiction_count": self.contradiction_count,
            "consistency_score":  round(self.consistency_score, 2),
            "is_usable":          self.is_usable,
            "issues":             list(self.issues),
        }


class LogicValidator:
    """Validates hypothesis consistency and argument completeness."""

    def __init__(self, hypothesis_validator: HypothesisValidator | None = None) -> None:
        self._hval = hypothesis_validator or HypothesisValidator()

    def validate(
        self,
        hypotheses: List[Hypothesis],
        reports:    List[ArgumentReport],
        order:      int = 6,
    ) -> Tuple[LogicValidationResult, ReasoningStep]:
        hval_result = self._hval.validate(hypotheses)
        issues: List[str] = list(hval_result.issues)

        # Argument gap check: hypothesis with zero supporting arguments
        arg_gaps = 0
        for report in reports:
            if not report.supporting_arguments:
                arg_gaps += 1
                issues.append(
                    f"Hypothesis {report.hypothesis_type_value!r} has no supporting arguments."
                )

        contradictions = hval_result.contradictions_found

        # Consistency score
        penalty  = 20.0 * hval_result.hypothesis_issues + 10.0 * arg_gaps + 30.0 * (1 if contradictions else 0)
        score    = max(0.0, 100.0 - penalty)

        if hval_result.status == LogicValidationStatus.INSUFFICIENT:
            status = LogicValidationStatus.INSUFFICIENT
        elif contradictions:
            status = LogicValidationStatus.CONTRADICTORY
        elif arg_gaps > 0:
            status = LogicValidationStatus.VALID_WITH_GAPS
        else:
            status = LogicValidationStatus.VALID

        result = LogicValidationResult(
            status=status,
            hypothesis_issues=hval_result.hypothesis_issues if hasattr(hval_result, "hypothesis_issues") else len(hval_result.issues),
            argument_gaps=arg_gaps,
            contradiction_count=1 if contradictions else 0,
            consistency_score=round(score, 2),
            issues=tuple(issues),
        )

        step = make_step(
            step_type=ReasoningStepType.CROSS_VALIDATION,
            description=(
                f"Logic validation of {len(hypotheses)} hypotheses and "
                f"{len(reports)} argument reports."
            ),
            intermediate_conclusion=(
                f"Logic validation: {status.value}. "
                f"Consistency score: {score:.1f}. "
                f"Issues: {len(issues)}."
            ),
            evidence_trace_ids=tuple(
                t for h in hypotheses
                for t in list(h.supporting_trace_ids) + list(h.opposing_trace_ids)
            ),
            confidence=score,
            order=order,
            module_name="LogicValidator",
        )
        return result, step
