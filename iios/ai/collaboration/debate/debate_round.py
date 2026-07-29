"""
debate_round.py -- iios.ai.collaboration.debate
=================================================
:class:`RoundStatus` — round life-cycle states.
:class:`DebateRound` — immutable closed round snapshot.

A :class:`DebateRound` is created only when a round is *closed*; open
rounds are tracked by :class:`DebateSession` as mutable state.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional

from .debate_position import DebatePosition


class RoundStatus(str, Enum):
    OPEN    = "open"
    CLOSED  = "closed"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class DebateRound:
    """
    Immutable snapshot of a completed debate round.

    Created by :meth:`DebateSession.close_round`.
    ``positions`` contains every :class:`DebatePosition` submitted in this round.
    """

    round_id:     str
    session_id:   str
    round_number: int
    topic:        str
    positions:    FrozenSet[DebatePosition]
    status:       RoundStatus
    opened_at:    float
    closed_at:    float

    @classmethod
    def close(
        cls,
        session_id:   str,
        round_number: int,
        topic:        str,
        positions:    FrozenSet[DebatePosition],
        opened_at:    float,
        status:       RoundStatus = RoundStatus.CLOSED,
    ) -> "DebateRound":
        return cls(
            round_id     = str(uuid.uuid4()),
            session_id   = session_id,
            round_number = round_number,
            topic        = topic,
            positions    = frozenset(positions),
            status       = status,
            opened_at    = opened_at,
            closed_at    = time.time(),
        )

    def position_count(self) -> int:
        return len(self.positions)

    def positions_by_type(self) -> dict:
        from collections import Counter
        return dict(Counter(p.position_type.value for p in self.positions))
