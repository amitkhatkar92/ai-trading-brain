"""iios/investment/decision/reasoning/hypothesis_engine.py
HypothesisEngine — proposes structural hypotheses from interpreted signals.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.reasoning.evidence_interpreter import InterpretedSignal
from iios.investment.decision.reasoning.reasoning_constants import (
    BEARISH_SIGNAL_THRESHOLD,
    BULLISH_SIGNAL_THRESHOLD,
    HypothesisStatus,
    HypothesisType,
    ReasoningStepType,
    SignalDirection,
)
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep, make_step


@dataclass(frozen=True)
class Hypothesis:
    """One proposed explanation for the evidence pattern."""
    hypothesis_id:       str
    hypothesis_type:     HypothesisType
    statement:           str
    supporting_trace_ids: Tuple[str, ...]   # trace_ids of supporting evidence
    opposing_trace_ids:   Tuple[str, ...]   # trace_ids of opposing evidence
    support_score:        float             # 0–1 (fraction of supporting signals)
    opposition_score:     float             # 0–1 (fraction of opposing signals)
    status:               HypothesisStatus
    version:              str
    created_at:           datetime

    @property
    def net_support(self) -> float:
        return round(self.support_score - self.opposition_score, 4)

    @property
    def is_primary(self) -> bool:
        return self.status == HypothesisStatus.SUPPORTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id":     self.hypothesis_id,
            "hypothesis_type":   self.hypothesis_type.value,
            "statement":         self.statement,
            "support_score":     round(self.support_score, 3),
            "opposition_score":  round(self.opposition_score, 3),
            "net_support":       self.net_support,
            "status":            self.status.value,
            "version":           self.version,
            "created_at":        self.created_at.isoformat(),
            "supporting_traces": len(self.supporting_trace_ids),
            "opposing_traces":   len(self.opposing_trace_ids),
        }


def _make_hypothesis(
    hypothesis_type:     HypothesisType,
    statement:           str,
    supporting:          List[InterpretedSignal],
    opposing:            List[InterpretedSignal],
    total:               int,
    version:             str = "1.0",
) -> Hypothesis:
    support_score  = len(supporting) / total if total else 0.0
    opposition_score = len(opposing) / total if total else 0.0
    if support_score >= BULLISH_SIGNAL_THRESHOLD:
        status = HypothesisStatus.SUPPORTED
    elif support_score < 0.20:
        status = HypothesisStatus.REJECTED
    else:
        status = HypothesisStatus.INCONCLUSIVE
    return Hypothesis(
        hypothesis_id=str(uuid.uuid4()),
        hypothesis_type=hypothesis_type,
        statement=statement,
        supporting_trace_ids=tuple(s.trace_id for s in supporting),
        opposing_trace_ids=tuple(s.trace_id for s in opposing),
        support_score=round(support_score, 4),
        opposition_score=round(opposition_score, 4),
        status=status,
        version=version,
        created_at=datetime.now(timezone.utc),
    )


class HypothesisEngine:
    """
    Proposes BULLISH, BEARISH, NEUTRAL, and ALTERNATIVE hypotheses from signals.
    Does NOT generate investment recommendations — only structural hypotheses.
    """

    def generate(
        self,
        subject_id:   str,
        subject_type: str,
        signals:      List[InterpretedSignal],
        order:        int = 4,
    ) -> Tuple[List[Hypothesis], ReasoningStep]:
        n = len(signals)
        pos = [s for s in signals if s.direction == SignalDirection.POSITIVE]
        neg = [s for s in signals if s.direction == SignalDirection.NEGATIVE]
        neu = [s for s in signals if s.direction == SignalDirection.NEUTRAL]

        hypotheses: List[Hypothesis] = []

        # Bullish hypothesis
        hypotheses.append(_make_hypothesis(
            HypothesisType.BULLISH,
            f"Positive signals dominate the evidence for {subject_type} '{subject_id}'.",
            supporting=pos, opposing=neg, total=n,
        ))
        # Bearish hypothesis
        hypotheses.append(_make_hypothesis(
            HypothesisType.BEARISH,
            f"Negative signals dominate the evidence for {subject_type} '{subject_id}'.",
            supporting=neg, opposing=pos, total=n,
        ))
        # Neutral hypothesis
        neutral_support = [s for s in signals if s.direction == SignalDirection.NEUTRAL]
        hypotheses.append(_make_hypothesis(
            HypothesisType.NEUTRAL,
            f"Evidence for {subject_type} '{subject_id}' is mixed or insufficient for directional conclusion.",
            supporting=neutral_support, opposing=[], total=n,
        ))
        # Alternative hypothesis (high-confidence contradictions present)
        if pos and neg:
            hypotheses.append(_make_hypothesis(
                HypothesisType.ALTERNATIVE,
                f"Conflicting signals detected for '{subject_id}'; alternative interpretation warranted.",
                supporting=pos + neg, opposing=[], total=n,
            ))

        primary = max(hypotheses, key=lambda h: h.support_score)
        step = make_step(
            step_type=ReasoningStepType.HYPOTHESIS_FORMATION,
            description=(
                f"Generated {len(hypotheses)} hypotheses for {subject_type} '{subject_id}'."
            ),
            intermediate_conclusion=(
                f"Primary hypothesis: {primary.hypothesis_type.value} "
                f"(support={primary.support_score:.0%}, "
                f"status={primary.status.value})."
            ),
            evidence_trace_ids=tuple(s.trace_id for s in signals),
            confidence=min(100.0, 60.0 + primary.support_score * 40.0),
            order=order,
            module_name="HypothesisEngine",
        )
        return hypotheses, step
