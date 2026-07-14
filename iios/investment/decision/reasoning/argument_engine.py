"""iios/investment/decision/reasoning/argument_engine.py
ArgumentEngine — orchestrates argument construction and evaluation per hypothesis.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.reasoning.argument_strength import ArgumentStrength, ArgumentStrengthSummary
from iios.investment.decision.reasoning.evidence_interpreter import InterpretedSignal
from iios.investment.decision.reasoning.hypothesis_engine import Hypothesis
from iios.investment.decision.reasoning.opposing_arguments import OpposingArguments
from iios.investment.decision.reasoning.reasoning_constants import (
    ReasoningStepType,
    SignalDirection,
)
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep, make_step
from iios.investment.decision.reasoning.supporting_arguments import Argument, SupportingArguments


@dataclass(frozen=True)
class ArgumentReport:
    """Full argument analysis for one hypothesis."""
    hypothesis_id:         str
    hypothesis_type_value: str
    supporting_arguments:  Tuple[Argument, ...]
    opposing_arguments:    Tuple[Argument, ...]
    strength_summary:      ArgumentStrengthSummary

    @property
    def is_net_supported(self) -> bool:
        return self.strength_summary.net_strength > 0

    def all_arguments(self) -> List[Argument]:
        return list(self.supporting_arguments) + list(self.opposing_arguments)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id":     self.hypothesis_id,
            "hypothesis_type":   self.hypothesis_type_value,
            "supporting_count":  len(self.supporting_arguments),
            "opposing_count":    len(self.opposing_arguments),
            "is_net_supported":  self.is_net_supported,
            "strength_summary":  self.strength_summary.to_dict(),
        }


class ArgumentEngine:
    """
    For each hypothesis:
    1. Determines which signals support vs. oppose it
    2. Builds SupportingArguments and OpposingArguments
    3. Evaluates net ArgumentStrength
    4. Returns ArgumentReport
    """

    def __init__(
        self,
        supporting: SupportingArguments | None = None,
        opposing:   OpposingArguments   | None = None,
        strength:   ArgumentStrength    | None = None,
    ) -> None:
        self._sup = supporting or SupportingArguments()
        self._opp = opposing   or OpposingArguments()
        self._str = strength   or ArgumentStrength()

    def evaluate_hypothesis(
        self,
        hypothesis: Hypothesis,
        signals:    List[InterpretedSignal],
    ) -> ArgumentReport:
        # Supporting: signals whose direction matches the hypothesis direction
        if hypothesis.hypothesis_type.value == "bullish":
            pos_signals  = [s for s in signals if s.direction == SignalDirection.POSITIVE]
            neg_signals  = [s for s in signals if s.direction == SignalDirection.NEGATIVE]
        elif hypothesis.hypothesis_type.value == "bearish":
            pos_signals  = [s for s in signals if s.direction == SignalDirection.NEGATIVE]
            neg_signals  = [s for s in signals if s.direction == SignalDirection.POSITIVE]
        else:
            # Neutral / Alternative: mixed
            pos_signals  = [s for s in signals if s.direction != SignalDirection.NEUTRAL]
            neg_signals  = []

        sup_args  = self._sup.build(hypothesis.hypothesis_id, hypothesis.statement, pos_signals)
        opp_args  = self._opp.build(hypothesis.hypothesis_id, hypothesis.statement, neg_signals)
        all_args  = sup_args + opp_args
        strength  = self._str.evaluate(hypothesis.hypothesis_id, all_args)

        return ArgumentReport(
            hypothesis_id=hypothesis.hypothesis_id,
            hypothesis_type_value=hypothesis.hypothesis_type.value,
            supporting_arguments=tuple(sup_args),
            opposing_arguments=tuple(opp_args),
            strength_summary=strength,
        )

    def evaluate_all(
        self,
        hypotheses: List[Hypothesis],
        signals:    List[InterpretedSignal],
        order:      int = 5,
    ) -> Tuple[List[ArgumentReport], ReasoningStep]:
        reports = [self.evaluate_hypothesis(h, signals) for h in hypotheses]
        net_supported = sum(1 for r in reports if r.is_net_supported)
        step = make_step(
            step_type=ReasoningStepType.ARGUMENT_EVALUATION,
            description=(
                f"Evaluated arguments for {len(hypotheses)} hypotheses."
            ),
            intermediate_conclusion=(
                f"Argument evaluation complete: {net_supported}/{len(hypotheses)} "
                f"hypotheses have net-positive argument support."
            ),
            evidence_trace_ids=tuple(
                tid for s in signals for tid in [s.trace_id]
            ),
            confidence=70.0,
            order=order,
            module_name="ArgumentEngine",
        )
        return reports, step
