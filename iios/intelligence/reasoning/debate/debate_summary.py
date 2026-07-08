"""
iios/intelligence/reasoning/debate/debate_summary.py
====================================================
DebateSummary — immutable result of a completed debate.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import DebateStatus


@dataclass
class DebateSummary:
    """
    Immutable output produced when a debate concludes.

    Attributes
    ----------
    debate_id           : Source debate identifier.
    session_id          : Owning reasoning session.
    topic               : Debate topic.
    proposition         : The central proposition under debate.
    status              : Terminal debate status.
    consensus_reached   : Whether threshold consensus was met.
    total_rounds        : Number of rounds conducted.
    total_arguments     : Total arguments submitted across all rounds.
    supporting_count    : Arguments supporting the proposition.
    opposing_count      : Arguments opposing the proposition.
    dominant_position   : The claim text of the winning side (if any).
    dominant_confidence : Weighted average confidence of the dominant side.
    minority_opinions   : List of preserved opposing / minority views.
    consensus_score     : Final agreement score [0, 1].
    key_evidence_ids    : Deduplicated evidence IDs cited in arguments.
    participants        : Participant summaries.
    duration_ms         : Wall-clock time for the whole debate.
    created_at          : Unix timestamp.
    """

    debate_id:           str                  = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    session_id:          str                  = ""
    topic:               str                  = ""
    proposition:         str                  = ""
    status:              DebateStatus         = DebateStatus.COMPLETED
    consensus_reached:   bool                 = False
    total_rounds:        int                  = 0
    total_arguments:     int                  = 0
    supporting_count:    int                  = 0
    opposing_count:      int                  = 0
    dominant_position:   str | None           = None
    dominant_confidence: float                = 0.0
    minority_opinions:   list[dict[str, Any]] = field(default_factory=list)
    consensus_score:     float                = 0.0
    key_evidence_ids:    list[str]            = field(default_factory=list)
    participants:        list[dict[str, Any]] = field(default_factory=list)
    duration_ms:         float                = 0.0
    created_at:          float                = field(default_factory=time.time)

    # -- Properties ────────────────────────────────────────────────────────────

    @property
    def is_deadlocked(self) -> bool:
        return self.status == DebateStatus.DEADLOCKED

    @property
    def agreement_rate(self) -> float:
        total = self.supporting_count + self.opposing_count
        if total == 0:
            return 0.0
        return self.supporting_count / total

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "debate_id":           self.debate_id,
            "session_id":          self.session_id,
            "topic":               self.topic,
            "proposition":         self.proposition,
            "status":              self.status.value,
            "consensus_reached":   self.consensus_reached,
            "total_rounds":        self.total_rounds,
            "total_arguments":     self.total_arguments,
            "supporting_count":    self.supporting_count,
            "opposing_count":      self.opposing_count,
            "dominant_position":   self.dominant_position,
            "dominant_confidence": round(self.dominant_confidence, 4),
            "minority_opinions":   self.minority_opinions,
            "consensus_score":     round(self.consensus_score, 4),
            "key_evidence_ids":    self.key_evidence_ids,
            "participants":        self.participants,
            "duration_ms":         round(self.duration_ms, 2),
            "created_at":          self.created_at,
        }
