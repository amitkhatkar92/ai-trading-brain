"""
iios/intelligence/reasoning/debate/debate_round.py
==================================================
DebateRound — one round of argument exchange within a debate session.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import ArgumentType, DebateStatus
from .argument import Argument


@dataclass
class DebateRound:
    """
    One round of argument submissions in a debate.

    A round is open while participants submit arguments.
    Calling ``close()`` seals the round and computes the consensus score.
    """

    round_id:     str              = field(default_factory=lambda: str(uuid.uuid4()))
    debate_id:    str              = ""
    round_number: int              = 1
    topic:        str              = ""
    arguments:    list[Argument]   = field(default_factory=list)
    status:       DebateStatus     = DebateStatus.ACTIVE
    started_at:   float            = field(default_factory=time.time)
    ended_at:     float | None     = None
    metadata:     dict[str, Any]   = field(default_factory=dict)

    # Computed on close()
    consensus_score: float = 0.0

    # -- Argument management ───────────────────────────────────────────────────

    def add_argument(self, argument: Argument) -> None:
        if self.status != DebateStatus.ACTIVE:
            raise ValueError(
                f"Round {self.round_id!r} is {self.status.value}; cannot add arguments"
            )
        argument.round_number = self.round_number
        self.arguments.append(argument)

    def close(self) -> None:
        """Seal the round and compute its consensus score."""
        if self.status != DebateStatus.ACTIVE:
            return
        self.consensus_score = self._compute_consensus()
        self.status          = DebateStatus.COMPLETED
        self.ended_at        = time.time()

    # -- Computed properties ───────────────────────────────────────────────────

    @property
    def supporting_count(self) -> int:
        return sum(1 for a in self.arguments if a.is_supporting)

    @property
    def opposing_count(self) -> int:
        return sum(1 for a in self.arguments if a.is_opposing)

    @property
    def total_count(self) -> int:
        return len(self.arguments)

    @property
    def duration_ms(self) -> float:
        end = self.ended_at or time.time()
        return (end - self.started_at) * 1_000

    @property
    def agreement_rate(self) -> float:
        """Fraction of arguments that are supporting (0 = all opposing, 1 = all supporting)."""
        if not self.arguments:
            return 0.0
        return self.supporting_count / len(self.arguments)

    def _compute_consensus(self) -> float:
        """
        Weighted consensus: dominant-side weighted confidence vs total.
        0 = pure opposition, 1 = pure support.
        """
        if not self.arguments:
            return 0.0
        support_w = sum(
            a.weighted_confidence for a in self.arguments if a.is_supporting
        )
        oppose_w  = sum(
            a.weighted_confidence for a in self.arguments if a.is_opposing
        )
        total_w   = support_w + oppose_w
        if total_w == 0.0:
            return 0.5
        return support_w / total_w

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_id":        self.round_id,
            "debate_id":       self.debate_id,
            "round_number":    self.round_number,
            "topic":           self.topic,
            "status":          self.status.value,
            "argument_count":  self.total_count,
            "supporting":      self.supporting_count,
            "opposing":        self.opposing_count,
            "consensus_score": round(self.consensus_score, 4),
            "agreement_rate":  round(self.agreement_rate, 4),
            "duration_ms":     round(self.duration_ms, 2),
            "started_at":      self.started_at,
            "ended_at":        self.ended_at,
        }
