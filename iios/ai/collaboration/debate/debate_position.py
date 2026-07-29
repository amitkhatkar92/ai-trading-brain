"""
debate_position.py -- iios.ai.collaboration.debate
====================================================
:class:`PositionType`   — position stance classification.
:class:`DebatePosition` — immutable position submitted by one agent.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional


class PositionType(str, Enum):
    """
    Agent stance in a debate or vote.

    FOR     — in favour of the proposition
    AGAINST — opposed to the proposition
    NEUTRAL — no strong conviction either way
    ABSTAIN — explicitly refraining from the debate
    CUSTOM  — domain-specific position (use ``argument`` field for detail)
    """

    FOR     = "for"
    AGAINST = "against"
    NEUTRAL = "neutral"
    ABSTAIN = "abstain"
    CUSTOM  = "custom"

    def is_decisive(self) -> bool:
        """True for FOR, AGAINST, CUSTOM — positions that can swing consensus."""
        return self in (PositionType.FOR, PositionType.AGAINST, PositionType.CUSTOM)


@dataclass(frozen=True)
class DebatePosition:
    """
    Immutable position submitted by one agent in one debate round.

    Fields
    ------
    position_id   — UUID
    session_id    — owning collaboration session
    agent_id      — submitting agent
    round_number  — debate round this was submitted in
    position_type — stance
    argument      — free-text rationale
    evidence      — supporting references (URLs, IDs, or text)
    confidence    — 0.0–1.0 self-reported confidence
    submitted_at  — wall-clock timestamp
    responds_to   — position_id this is a counter-argument to (optional)
    """

    position_id:  str
    session_id:   str
    agent_id:     str
    round_number: int
    position_type: PositionType
    argument:     str
    evidence:     FrozenSet[str]
    confidence:   float
    submitted_at: float
    responds_to:  Optional[str]   # position_id of the position being countered

    @classmethod
    def create(
        cls,
        session_id:    str,
        agent_id:      str,
        round_number:  int,
        position_type: PositionType,
        argument:      str             = "",
        evidence:      FrozenSet[str]  = frozenset(),
        confidence:    float           = 1.0,
        responds_to:   Optional[str]   = None,
    ) -> "DebatePosition":
        return cls(
            position_id   = str(uuid.uuid4()),
            session_id    = session_id,
            agent_id      = agent_id,
            round_number  = round_number,
            position_type = position_type,
            argument      = argument,
            evidence      = frozenset(evidence),
            confidence    = max(0.0, min(1.0, confidence)),
            submitted_at  = time.time(),
            responds_to   = responds_to,
        )
