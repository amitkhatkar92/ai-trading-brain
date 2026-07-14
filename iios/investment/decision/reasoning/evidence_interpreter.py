"""iios/investment/decision/reasoning/evidence_interpreter.py
EvidenceInterpreter — catalogs all evidence items into InterpretedSignals.
Transforms raw evidence into structured, labelled signals for downstream reasoning.
No investment analysis — purely structural transformation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.evidence.evidence_constants import EvidenceCategory, EvidenceSourceType
from iios.investment.decision.evidence.evidence_item import EvidenceItem
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.reasoning.reasoning_constants import (
    ReasoningStepType,
    SignalDirection,
)
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep, make_step


@dataclass(frozen=True)
class InterpretedSignal:
    """One evidence item transformed into a labelled signal."""
    signal_id:       str
    evidence_id:     str
    trace_id:        str
    key:             str
    value:           Any
    direction:       SignalDirection
    strength:        float              # 0–1 derived from confidence × freshness
    interpretation:  str               # human-readable one-liner
    source_type:     EvidenceSourceType
    category:        EvidenceCategory
    confidence:      float              # from source (0–100)
    freshness:       float              # from source (0–1)
    is_required:     bool

    @property
    def weighted_strength(self) -> float:
        return round(self.strength * (self.confidence / 100.0), 4)


class EvidenceInterpreter:
    """
    Produces one InterpretedSignal per EvidenceItem.
    The direction is set to NEUTRAL by default — signal_interpreter.py overrides
    directions for known key patterns.
    """

    def interpret_item(self, item: EvidenceItem) -> InterpretedSignal:
        strength = round(item.freshness_score * (item.confidence / 100.0), 4)
        return InterpretedSignal(
            signal_id=str(uuid.uuid4()),
            evidence_id=item.evidence_id,
            trace_id=item.trace_id,
            key=item.key,
            value=item.value,
            direction=SignalDirection.NEUTRAL,   # overridden by SignalInterpreter
            strength=strength,
            interpretation=f"Evidence item '{item.key}' from {item.source_type.value}.",
            source_type=item.source_type,
            category=item.category,
            confidence=item.confidence,
            freshness=item.freshness_score,
            is_required=item.is_required,
        )

    def interpret_snapshot(
        self,
        snapshot: EvidenceSnapshot,
        order:    int = 0,
    ) -> Tuple[List[InterpretedSignal], ReasoningStep]:
        signals = [self.interpret_item(i) for i in snapshot.items]
        step = make_step(
            step_type=ReasoningStepType.EVIDENCE_REVIEW,
            description=(
                f"Reviewed {len(signals)} evidence items from "
                f"{len(snapshot.sources_included)} source types."
            ),
            intermediate_conclusion=(
                f"Evidence catalog complete: {len(signals)} signals available, "
                f"quality={snapshot.quality_score:.1f}."
            ),
            evidence_trace_ids=tuple(i.trace_id for i in snapshot.items),
            confidence=snapshot.overall_confidence,
            order=order,
            module_name="EvidenceInterpreter",
        )
        return signals, step
