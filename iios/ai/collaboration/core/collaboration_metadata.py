"""
collaboration_metadata.py -- iios.ai.collaboration.core
=========================================================
:class:`CollaborationStatus`  — session life-cycle states.
:class:`CollaborationType`    — classification of collaboration intent.
:class:`CollaborationMetadata` — immutable session header record.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Iterable, Optional


class CollaborationStatus(str, Enum):
    """
    States of a :class:`CollaborationSession`.

    Transition diagram:
        CREATED → OPEN → DEBATING → VOTING → CONSENSUS_REACHED → CLOSED
                                          → CONSENSUS_FAILED  → ESCALATED → CLOSED
                                                                           → CLOSED
        Any state → CLOSED | FAILED
    """

    CREATED           = "created"
    OPEN              = "open"
    DEBATING          = "debating"
    VOTING            = "voting"
    CONSENSUS_REACHED = "consensus_reached"
    CONSENSUS_FAILED  = "consensus_failed"
    ESCALATED         = "escalated"
    CLOSED            = "closed"
    FAILED            = "failed"

    def is_terminal(self) -> bool:
        return self in (CollaborationStatus.CLOSED, CollaborationStatus.FAILED)

    def is_active(self) -> bool:
        return not self.is_terminal()


class CollaborationType(str, Enum):
    """Purpose classification for a collaboration session."""

    ANALYSIS     = "analysis"
    DEBATE       = "debate"
    CONSENSUS    = "consensus"
    REVIEW       = "review"
    PLANNING     = "planning"
    CUSTOM       = "custom"


@dataclass(frozen=True)
class CollaborationMetadata:
    """
    Immutable header record for one collaboration session.

    Set at creation time and never mutated.
    """

    session_id:          str
    topic:               str
    collaboration_type:  CollaborationType
    created_at:          float
    created_by:          str
    description:         str
    tags:                FrozenSet[str]
    max_participants:    int
    max_rounds:          int
    timeout_s:           Optional[float]   # wall-clock deadline in seconds; None = unlimited

    @classmethod
    def create(
        cls,
        topic:              str,
        collaboration_type: CollaborationType       = CollaborationType.DEBATE,
        created_by:         str                     = "system",
        description:        str                     = "",
        tags:               Iterable[str]           = (),
        max_participants:   int                     = 10,
        max_rounds:         int                     = 3,
        timeout_s:          Optional[float]         = None,
    ) -> "CollaborationMetadata":
        return cls(
            session_id         = str(uuid.uuid4()),
            topic              = topic,
            collaboration_type = collaboration_type,
            created_at         = time.time(),
            created_by         = created_by,
            description        = description,
            tags               = frozenset(tags),
            max_participants   = max_participants,
            max_rounds         = max_rounds,
            timeout_s          = timeout_s,
        )
