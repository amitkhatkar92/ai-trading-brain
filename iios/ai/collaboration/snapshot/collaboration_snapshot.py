"""
collaboration_snapshot.py -- iios.ai.collaboration.snapshot
=============================================================
:class:`CollaborationSessionSnapshot`   — point-in-time snapshot of one session.
:class:`CollaborationFrameworkSnapshot` — snapshot of the entire framework.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple

from ..core.collaboration_metadata import CollaborationStatus, CollaborationType


@dataclass(frozen=True)
class CollaborationSessionSnapshot:
    """
    Point-in-time snapshot of a single :class:`CollaborationSession`.

    ``vote_counts`` is a frozenset of ``(position_type_value, count)`` tuples,
    or empty if voting has not started.
    """

    snapshot_id:          str
    session_id:           str
    topic:                str
    collaboration_type:   CollaborationType
    status:               CollaborationStatus
    participant_count:    int
    current_round:        int
    total_rounds:         int
    message_count:        int
    vote_counts:          FrozenSet[Tuple[str, int]]
    winning_position:     Optional[str]
    consensus_confidence: float
    captured_at:          float

    @classmethod
    def capture(
        cls,
        session_id:           str,
        topic:                str,
        collaboration_type:   CollaborationType,
        status:               CollaborationStatus,
        participant_count:    int,
        current_round:        int,
        total_rounds:         int,
        message_count:        int,
        vote_counts:          FrozenSet[Tuple[str, int]] = frozenset(),
        winning_position:     Optional[str]              = None,
        consensus_confidence: float                      = 0.0,
    ) -> "CollaborationSessionSnapshot":
        return cls(
            snapshot_id          = str(uuid.uuid4()),
            session_id           = session_id,
            topic                = topic,
            collaboration_type   = collaboration_type,
            status               = status,
            participant_count    = participant_count,
            current_round        = current_round,
            total_rounds         = total_rounds,
            message_count        = message_count,
            vote_counts          = frozenset(vote_counts),
            winning_position     = winning_position,
            consensus_confidence = consensus_confidence,
            captured_at          = time.time(),
        )

    def is_active(self) -> bool:
        return self.status.is_active()

    def is_terminal(self) -> bool:
        return self.status.is_terminal()


@dataclass(frozen=True)
class CollaborationFrameworkSnapshot:
    """Point-in-time snapshot of the entire A6 framework."""

    snapshot_id:       str
    system_id:         str
    version:           str
    is_running:        bool
    total_sessions:    int
    active_sessions:   int
    closed_sessions:   int
    events_published:  int
    sessions:          FrozenSet[CollaborationSessionSnapshot]
    captured_at:       float

    @classmethod
    def capture(
        cls,
        system_id:        str,
        version:          str,
        is_running:       bool,
        sessions:         FrozenSet[CollaborationSessionSnapshot],
        events_published: int,
    ) -> "CollaborationFrameworkSnapshot":
        active  = sum(1 for s in sessions if s.is_active())
        closed_ = sum(1 for s in sessions if s.is_terminal())
        return cls(
            snapshot_id      = str(uuid.uuid4()),
            system_id        = system_id,
            version          = version,
            is_running       = is_running,
            total_sessions   = len(sessions),
            active_sessions  = active,
            closed_sessions  = closed_,
            events_published = events_published,
            sessions         = frozenset(sessions),
            captured_at      = time.time(),
        )
