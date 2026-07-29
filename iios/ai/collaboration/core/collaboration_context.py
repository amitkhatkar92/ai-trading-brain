"""
collaboration_context.py -- iios.ai.collaboration.core
========================================================
:class:`CollaborationContext` — immutable snapshot of session context
injected into policy evaluations and agent callbacks.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, FrozenSet, Tuple

from .collaboration_metadata import CollaborationMetadata, CollaborationStatus
from .participant              import Participant


@dataclass(frozen=True)
class CollaborationContext:
    """
    Immutable point-in-time context snapshot of a collaboration session.

    Passed to policy ``evaluate()`` calls and agent callbacks so they can
    inspect session state without holding a reference to the mutable
    :class:`CollaborationSession`.
    """

    context_id:    str
    session_id:    str
    topic:         str
    status:        CollaborationStatus
    participants:  FrozenSet[Participant]
    current_round: int
    total_rounds:  int
    created_at:    float
    extras:        FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        metadata:      CollaborationMetadata,
        status:        CollaborationStatus,
        participants:  FrozenSet[Participant],
        current_round: int,
        total_rounds:  int,
        **extras: Any,
    ) -> "CollaborationContext":
        return cls(
            context_id    = str(uuid.uuid4()),
            session_id    = metadata.session_id,
            topic         = metadata.topic,
            status        = status,
            participants  = participants,
            current_round = current_round,
            total_rounds  = total_rounds,
            created_at    = time.time(),
            extras        = frozenset(extras.items()),
        )

    def get_extra(self, key: str, default: Any = None) -> Any:
        for k, v in self.extras:
            if k == key:
                return v
        return default

    @property
    def participant_count(self) -> int:
        return len(self.participants)

    @property
    def active_participant_count(self) -> int:
        from .participant import ParticipantStatus
        return sum(
            1 for p in self.participants
            if p.status not in (ParticipantStatus.ABSTAINED, ParticipantStatus.REMOVED)
        )
