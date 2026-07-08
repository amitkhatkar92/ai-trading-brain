"""
iios/intelligence/reasoning/debate/counter_argument.py
======================================================
CounterArgument — a targeted rebuttal to a specific Argument.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .argument import Argument
from ..reasoning_constants import ArgumentType


@dataclass
class CounterArgument:
    """
    A rebuttal that directly targets an existing Argument.

    Attributes
    ----------
    counter_id           : Unique identifier.
    original_argument_id : The Argument being countered.
    debate_id            : Owning debate session.
    participant_id       : Who submitted this counter.
    claim                : The counter-claim.
    reasoning            : Why the original argument is flawed or incomplete.
    evidence_ids         : Evidence backing the counter.
    confidence           : Submitter confidence [0, 1].
    weight               : Importance weight.
    metadata             : Caller-supplied extras.
    created_at           : Unix timestamp.
    """

    counter_id:           str            = field(default_factory=lambda: str(uuid.uuid4()))
    original_argument_id: str            = ""
    debate_id:            str            = ""
    participant_id:       str            = ""
    claim:                str            = ""
    reasoning:            str            = ""
    evidence_ids:         list[str]      = field(default_factory=list)
    confidence:           float          = 0.5
    weight:               float          = 1.0
    metadata:             dict[str, Any] = field(default_factory=dict)
    created_at:           float          = field(default_factory=time.time)

    # -- Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_argument(
        cls,
        original: Argument,
        participant_id: str,
        claim:         str,
        reasoning:     str   = "",
        evidence_ids:  list[str] | None = None,
        confidence:    float = 0.5,
        weight:        float = 1.0,
    ) -> CounterArgument:
        return cls(
            original_argument_id = original.argument_id,
            debate_id            = original.debate_id,
            participant_id       = participant_id,
            claim                = claim,
            reasoning            = reasoning,
            evidence_ids         = evidence_ids or [],
            confidence           = confidence,
            weight               = weight,
        )

    # -- Promotion ─────────────────────────────────────────────────────────────

    def to_argument(self, session_id: str, round_number: int) -> Argument:
        """Promote this counter-argument into a full Argument for submission."""
        return Argument(
            debate_id      = self.debate_id,
            session_id     = session_id,
            participant_id = self.participant_id,
            argument_type  = ArgumentType.COUNTER_REBUTTAL,
            claim          = self.claim,
            reasoning      = self.reasoning,
            evidence_ids   = self.evidence_ids,
            confidence     = self.confidence,
            weight         = self.weight,
            round_number   = round_number,
            rebuttal_to    = self.original_argument_id,
        )

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "counter_id":           self.counter_id,
            "original_argument_id": self.original_argument_id,
            "debate_id":            self.debate_id,
            "participant_id":       self.participant_id,
            "claim":                self.claim,
            "reasoning":            self.reasoning,
            "evidence_ids":         self.evidence_ids,
            "confidence":           round(self.confidence, 4),
            "weight":               round(self.weight, 4),
            "metadata":             self.metadata,
            "created_at":           self.created_at,
        }
