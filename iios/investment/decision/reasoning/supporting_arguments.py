"""iios/investment/decision/reasoning/supporting_arguments.py
SupportingArgument — evidence-backed argument that supports a hypothesis.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from iios.investment.decision.reasoning.evidence_interpreter import InterpretedSignal
from iios.investment.decision.reasoning.reasoning_constants import (
    ArgumentStrengthLevel,
    ArgumentType,
    STRONG_ARGUMENT_EVIDENCE_COUNT,
)


@dataclass(frozen=True)
class Argument:
    """One argument (supporting or opposing) referencing specific evidence signals."""
    argument_id:     str
    hypothesis_id:   str
    argument_type:   ArgumentType
    claim:           str                 # human-readable claim statement
    evidence_ids:    Tuple[str, ...]     # evidence_id references
    trace_ids:       Tuple[str, ...]     # trace_id references (for full auditability)
    signal_keys:     Tuple[str, ...]     # the evidence keys cited
    strength_score:  float              # 0–1
    strength_level:  ArgumentStrengthLevel
    created_at:      datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "argument_id":   self.argument_id,
            "hypothesis_id": self.hypothesis_id,
            "argument_type": self.argument_type.value,
            "claim":         self.claim,
            "evidence_count": len(self.evidence_ids),
            "trace_ids":     list(self.trace_ids),
            "signal_keys":   list(self.signal_keys),
            "strength_score": round(self.strength_score, 3),
            "strength_level": self.strength_level.value,
            "created_at":    self.created_at.isoformat(),
        }


def _compute_argument_strength(signals: List[InterpretedSignal]) -> float:
    if not signals:
        return 0.0
    avg_confidence = sum(s.confidence for s in signals) / len(signals) / 100.0
    avg_freshness  = sum(s.freshness  for s in signals) / len(signals)
    count_bonus    = min(1.0, len(signals) / STRONG_ARGUMENT_EVIDENCE_COUNT)
    return round((avg_confidence * 0.5 + avg_freshness * 0.3 + count_bonus * 0.2), 4)


class SupportingArguments:
    """Builds supporting arguments for a hypothesis from positive signals."""

    def build(
        self,
        hypothesis_id: str,
        hypothesis_statement: str,
        signals:       List[InterpretedSignal],
    ) -> List[Argument]:
        if not signals:
            return []
        strength_score = _compute_argument_strength(signals)
        claim = (
            f"{len(signals)} signal(s) corroborate hypothesis: {hypothesis_statement[:80]}. "
            f"Sources: {', '.join(sorted({s.source_type.value for s in signals}))}."
        )
        return [Argument(
            argument_id=str(uuid.uuid4()),
            hypothesis_id=hypothesis_id,
            argument_type=ArgumentType.SUPPORTING,
            claim=claim,
            evidence_ids=tuple(s.evidence_id for s in signals),
            trace_ids=tuple(s.trace_id for s in signals),
            signal_keys=tuple(s.key for s in signals),
            strength_score=strength_score,
            strength_level=ArgumentStrengthLevel.from_score(strength_score),
            created_at=datetime.now(timezone.utc),
        )]
