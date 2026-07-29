"""
debate_result.py -- iios.ai.collaboration.debate
==================================================
:class:`DebateResult` — immutable summary of a completed debate.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from collections import Counter
from dataclasses import dataclass
from typing import FrozenSet, List, Optional, Tuple

from .debate_position import DebatePosition, PositionType
from .debate_round    import DebateRound


@dataclass(frozen=True)
class DebateResult:
    """
    Immutable summary produced when a :class:`DebateSession` closes.

    ``positions_by_type`` is a frozenset of ``(position_type_value, count)`` pairs.
    ``dominant_position`` is the :class:`PositionType` with the most submissions
    (``None`` if no positions were submitted or there was a tie).
    """

    result_id:            str
    session_id:           str
    rounds_completed:     int
    total_positions:      int
    positions_by_type:    FrozenSet[Tuple[str, int]]
    dominant_position:    Optional[PositionType]
    dominant_confidence:  float
    dissenting_positions: int
    completed_at:         float
    summary:              str

    @classmethod
    def from_rounds(
        cls,
        session_id: str,
        rounds:     List[DebateRound],
    ) -> "DebateResult":
        """Build a :class:`DebateResult` from a list of closed :class:`DebateRound` objects."""
        all_positions = [p for r in rounds for p in r.positions]
        counts: dict = Counter(p.position_type.value for p in all_positions)
        total   = len(all_positions)

        dominant_type:  Optional[PositionType] = None
        dominant_conf:  float = 0.0
        dissenting:     int   = 0

        if counts:
            top_val, top_count = max(counts.items(), key=lambda x: x[1])
            # Check for a genuine majority (> 50%) to be "dominant"
            if top_count / total > 0.5 if total else False:
                dominant_type = PositionType(top_val)
                dom_positions = [p for p in all_positions if p.position_type.value == top_val]
                dominant_conf = sum(p.confidence for p in dom_positions) / len(dom_positions)
                dissenting    = total - top_count

        return cls(
            result_id            = str(uuid.uuid4()),
            session_id           = session_id,
            rounds_completed     = len(rounds),
            total_positions      = total,
            positions_by_type    = frozenset(counts.items()),
            dominant_position    = dominant_type,
            dominant_confidence  = dominant_conf,
            dissenting_positions = dissenting,
            completed_at         = time.time(),
            summary              = _build_summary(dominant_type, total, len(rounds)),
        )


def _build_summary(
    dominant: Optional[PositionType],
    total:    int,
    rounds:   int,
) -> str:
    if dominant:
        return f"Debate completed: {total} positions across {rounds} round(s). Dominant: {dominant.value}."
    return f"Debate completed: {total} positions across {rounds} round(s). No dominant position."
