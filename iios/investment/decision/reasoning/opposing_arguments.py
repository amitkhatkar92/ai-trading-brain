"""iios/investment/decision/reasoning/opposing_arguments.py
OpposingArgument — evidence-backed argument that opposes a hypothesis.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from iios.investment.decision.reasoning.evidence_interpreter import InterpretedSignal
from iios.investment.decision.reasoning.reasoning_constants import ArgumentType
from iios.investment.decision.reasoning.supporting_arguments import Argument, _compute_argument_strength, ArgumentStrengthLevel


class OpposingArguments:
    """Builds opposing arguments for a hypothesis from negative (contradicting) signals."""

    def build(
        self,
        hypothesis_id:        str,
        hypothesis_statement: str,
        signals:              List[InterpretedSignal],
    ) -> List[Argument]:
        if not signals:
            return []
        strength_score = _compute_argument_strength(signals)
        claim = (
            f"{len(signals)} signal(s) contradict hypothesis: {hypothesis_statement[:80]}. "
            f"Sources: {', '.join(sorted({s.source_type.value for s in signals}))}."
        )
        return [Argument(
            argument_id=str(uuid.uuid4()),
            hypothesis_id=hypothesis_id,
            argument_type=ArgumentType.OPPOSING,
            claim=claim,
            evidence_ids=tuple(s.evidence_id for s in signals),
            trace_ids=tuple(s.trace_id for s in signals),
            signal_keys=tuple(s.key for s in signals),
            strength_score=strength_score,
            strength_level=ArgumentStrengthLevel.from_score(strength_score),
            created_at=datetime.now(timezone.utc),
        )]
