"""iios/investment/decision/reasoning/context_analyzer.py
ContextAnalyzer — analyzes the overall decision context from interpreted signals.
Produces a ContextProfile summarising signal distribution and evidence coverage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.reasoning.evidence_interpreter import InterpretedSignal
from iios.investment.decision.reasoning.reasoning_constants import (
    ReasoningStepType,
    SignalDirection,
)
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep, make_step


@dataclass(frozen=True)
class ContextProfile:
    """Structural summary of the decision context derived from interpreted signals."""
    subject_id:                 str
    subject_type:               str
    total_signals:              int
    positive_signals:           int
    negative_signals:           int
    neutral_signals:            int
    dominant_direction:         SignalDirection
    positive_fraction:          float          # 0–1
    negative_fraction:          float          # 0–1
    high_confidence_signals:    int            # confidence ≥ 70
    fresh_signals:              int            # freshness ≥ 0.7
    source_types_present:       Tuple[str, ...]
    source_diversity:           float          # 0–1 fraction of all source types
    risk_evidence_present:      bool
    market_evidence_present:    bool
    fundamental_evidence_present: bool

    @property
    def is_well_covered(self) -> bool:
        return self.source_diversity >= 0.30 and self.total_signals >= 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_id":         self.subject_id,
            "subject_type":       self.subject_type,
            "total_signals":      self.total_signals,
            "positive_signals":   self.positive_signals,
            "negative_signals":   self.negative_signals,
            "neutral_signals":    self.neutral_signals,
            "dominant_direction": self.dominant_direction.value,
            "positive_fraction":  round(self.positive_fraction, 3),
            "negative_fraction":  round(self.negative_fraction, 3),
            "high_conf_signals":  self.high_confidence_signals,
            "fresh_signals":      self.fresh_signals,
            "source_types_present": list(self.source_types_present),
            "source_diversity":   round(self.source_diversity, 3),
            "risk_evidence_present":        self.risk_evidence_present,
            "market_evidence_present":      self.market_evidence_present,
            "fundamental_evidence_present": self.fundamental_evidence_present,
        }


class ContextAnalyzer:
    """Derives a ContextProfile from a list of InterpretedSignals."""

    def analyze(
        self,
        subject_id:   str,
        subject_type: str,
        signals:      List[InterpretedSignal],
        order:        int = 1,
    ) -> Tuple[ContextProfile, ReasoningStep]:
        n = len(signals)
        pos = sum(1 for s in signals if s.direction == SignalDirection.POSITIVE)
        neg = sum(1 for s in signals if s.direction == SignalDirection.NEGATIVE)
        neu = sum(1 for s in signals if s.direction == SignalDirection.NEUTRAL)

        if n == 0:
            dominant = SignalDirection.NEUTRAL
        elif pos > neg and pos > neu:
            dominant = SignalDirection.POSITIVE
        elif neg > pos and neg > neu:
            dominant = SignalDirection.NEGATIVE
        else:
            dominant = SignalDirection.NEUTRAL

        pos_f = round(pos / n, 3) if n else 0.0
        neg_f = round(neg / n, 3) if n else 0.0

        srcs: Set[EvidenceSourceType] = {s.source_type for s in signals}
        diversity = len(srcs) / len(EvidenceSourceType) if signals else 0.0

        high_conf = sum(1 for s in signals if s.confidence >= 70.0)
        fresh     = sum(1 for s in signals if s.freshness >= 0.7)

        profile = ContextProfile(
            subject_id=subject_id,
            subject_type=subject_type,
            total_signals=n,
            positive_signals=pos,
            negative_signals=neg,
            neutral_signals=neu,
            dominant_direction=dominant,
            positive_fraction=pos_f,
            negative_fraction=neg_f,
            high_confidence_signals=high_conf,
            fresh_signals=fresh,
            source_types_present=tuple(sorted(s.value for s in srcs)),
            source_diversity=round(diversity, 3),
            risk_evidence_present=EvidenceSourceType.RISK in srcs,
            market_evidence_present=EvidenceSourceType.MARKET in srcs,
            fundamental_evidence_present=EvidenceSourceType.COMPANY in srcs,
        )

        step = make_step(
            step_type=ReasoningStepType.CONTEXT_ANALYSIS,
            description=(
                f"Context analysis for {subject_type} '{subject_id}': "
                f"{n} signals across {len(srcs)} source types."
            ),
            intermediate_conclusion=(
                f"Dominant signal direction: {dominant.value}. "
                f"Positive: {pos}, Negative: {neg}, Neutral: {neu}. "
                f"Source diversity: {diversity:.0%}."
            ),
            evidence_trace_ids=tuple(s.trace_id for s in signals),
            confidence=min(100.0, 50.0 + diversity * 50.0),
            order=order,
            module_name="ContextAnalyzer",
        )
        return profile, step
