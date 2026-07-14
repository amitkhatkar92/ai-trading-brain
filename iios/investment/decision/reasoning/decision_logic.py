"""iios/investment/decision/reasoning/decision_logic.py
DecisionLogic — extracts the logical structure of the reasoning from context.
Produces the final_conclusion that seals the ReasoningChain.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from iios.investment.decision.reasoning.argument_engine import ArgumentReport
from iios.investment.decision.reasoning.context_analyzer import ContextProfile
from iios.investment.decision.reasoning.hypothesis_engine import Hypothesis
from iios.investment.decision.reasoning.reasoning_constants import (
    HypothesisStatus,
    HypothesisType,
    ReasoningStepType,
    SignalDirection,
)
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep, make_step


class DecisionLogic:
    """
    Extracts the logical conclusion structure:
    - Identifies the dominant hypothesis
    - Summarises supporting vs. opposing evidence
    - Generates the human-readable final_conclusion
    - Produces the INTERMEDIATE_CONCLUSION and FINAL_REASONING steps
    """

    def extract(
        self,
        subject_id:      str,
        subject_type:    str,
        context_profile: ContextProfile,
        hypotheses:      List[Hypothesis],
        reports:         List[ArgumentReport],
        base_order:      int = 6,
    ) -> Tuple[Optional[Hypothesis], List[ReasoningStep], str]:
        """
        Returns: (primary_hypothesis, extra_steps, final_conclusion_text)
        """
        steps: List[ReasoningStep] = []

        # Determine primary hypothesis
        supported = [h for h in hypotheses if h.status == HypothesisStatus.SUPPORTED]
        primary   = max(supported, key=lambda h: h.support_score) if supported else None

        # Determine net-supported hypothesis by argument analysis
        best_by_args: Optional[Hypothesis] = None
        best_net     = float("-inf")
        for report in reports:
            if report.strength_summary.net_strength > best_net:
                best_net     = report.strength_summary.net_strength
                # find matching hypothesis
                for h in hypotheses:
                    if h.hypothesis_id == report.hypothesis_id:
                        best_by_args = h
                        break

        primary = primary or best_by_args

        # Intermediate conclusions step
        if primary:
            intermediate = (
                f"Primary hypothesis: {primary.hypothesis_type.value.upper()} "
                f"(support={primary.support_score:.0%}). "
                f"Context: {context_profile.positive_signals} positive, "
                f"{context_profile.negative_signals} negative, "
                f"{context_profile.neutral_signals} neutral signals."
            )
        else:
            intermediate = (
                f"No dominant hypothesis identified. "
                f"Evidence context: {context_profile.dominant_direction.value} "
                f"dominant direction, {context_profile.total_signals} signals."
            )

        steps.append(make_step(
            step_type=ReasoningStepType.INTERMEDIATE_CONCLUSION,
            description="Drawing intermediate conclusions from hypothesis and argument analysis.",
            intermediate_conclusion=intermediate,
            evidence_trace_ids=tuple(
                t for h in hypotheses for t in h.supporting_trace_ids
            ),
            confidence=70.0,
            order=base_order,
            module_name="DecisionLogic",
        ))

        # Final reasoning step
        final = self._compose_final(subject_id, subject_type, primary, context_profile, reports)
        steps.append(make_step(
            step_type=ReasoningStepType.FINAL_REASONING,
            description="Synthesising all evidence, hypotheses, and arguments into final reasoning.",
            intermediate_conclusion=final,
            evidence_trace_ids=tuple(
                t for h in hypotheses for t in list(h.supporting_trace_ids) + list(h.opposing_trace_ids)
            ),
            confidence=min(100.0, 60.0 + (primary.support_score * 30.0 if primary else 0.0)),
            order=base_order + 1,
            module_name="DecisionLogic",
        ))
        return primary, steps, final

    @staticmethod
    def _compose_final(
        subject_id:      str,
        subject_type:    str,
        primary:         Optional[Hypothesis],
        ctx:             ContextProfile,
        reports:         List[ArgumentReport],
    ) -> str:
        parts = []
        if primary:
            parts.append(
                f"For {subject_type} '{subject_id}', the dominant hypothesis is "
                f"{primary.hypothesis_type.value.upper()} with "
                f"{primary.support_score:.0%} signal support."
            )
        else:
            parts.append(
                f"For {subject_type} '{subject_id}', evidence is inconclusive "
                f"(dominant direction: {ctx.dominant_direction.value})."
            )

        parts.append(
            f"Evidence context: {ctx.positive_signals}+ / {ctx.negative_signals}- / "
            f"{ctx.neutral_signals}~ signals across {len(ctx.source_types_present)} source types."
        )

        net_supported = sum(1 for r in reports if r.is_net_supported)
        parts.append(
            f"Argument analysis: {net_supported}/{len(reports)} hypotheses "
            f"have net-positive argument support."
        )
        return " ".join(parts)
