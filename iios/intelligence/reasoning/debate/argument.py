"""
iios/intelligence/reasoning/debate/argument.py
==============================================
Argument dataclass — a claim made by a debate participant.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import ArgumentType


@dataclass
class Argument:
    """
    A single structured claim submitted by a debate participant.

    Attributes
    ----------
    argument_id    : Unique identifier.
    debate_id      : Owning debate session.
    session_id     : Owning reasoning session.
    participant_id : Who submitted this argument.
    argument_type  : Semantic role (supporting, opposing, rebuttal, …).
    claim          : Human-readable statement of position.
    reasoning      : Justification for the claim.
    evidence_ids   : Evidence items that back this argument.
    confidence     : Submitter confidence [0, 1].
    weight         : Submitter-assigned importance weight.
    round_number   : Debate round this was submitted in.
    rebuttal_to    : ID of the argument being rebutted (if any).
    metadata       : Caller-supplied extras.
    created_at     : Unix timestamp.
    """

    argument_id:    str           = field(default_factory=lambda: str(uuid.uuid4()))
    debate_id:      str           = ""
    session_id:     str           = ""
    participant_id: str           = ""
    argument_type:  ArgumentType  = ArgumentType.NEUTRAL
    claim:          str           = ""
    reasoning:      str           = ""
    evidence_ids:   list[str]     = field(default_factory=list)
    confidence:     float         = 0.5
    weight:         float         = 1.0
    round_number:   int           = 1
    rebuttal_to:    str | None    = None
    metadata:       dict[str, Any] = field(default_factory=dict)
    created_at:     float         = field(default_factory=time.time)

    # -- Properties ────────────────────────────────────────────────────────────

    @property
    def is_supporting(self) -> bool:
        return self.argument_type == ArgumentType.SUPPORTING

    @property
    def is_opposing(self) -> bool:
        return self.argument_type == ArgumentType.OPPOSING

    @property
    def is_rebuttal(self) -> bool:
        return self.argument_type in (
            ArgumentType.REBUTTAL, ArgumentType.COUNTER_REBUTTAL
        )

    @property
    def weighted_confidence(self) -> float:
        return self.confidence * self.weight

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "argument_id":    self.argument_id,
            "debate_id":      self.debate_id,
            "session_id":     self.session_id,
            "participant_id": self.participant_id,
            "argument_type":  self.argument_type.value,
            "claim":          self.claim,
            "reasoning":      self.reasoning,
            "evidence_ids":   self.evidence_ids,
            "confidence":     round(self.confidence, 4),
            "weight":         round(self.weight, 4),
            "round_number":   self.round_number,
            "rebuttal_to":    self.rebuttal_to,
            "metadata":       self.metadata,
            "created_at":     self.created_at,
        }
