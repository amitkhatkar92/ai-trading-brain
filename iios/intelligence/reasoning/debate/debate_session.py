"""
iios/intelligence/reasoning/debate/debate_session.py
====================================================
DebateSession — full lifecycle object for one multi-round debate.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import (
    DebateRole,
    DebateStatus,
    DEFAULT_DEBATE_TIMEOUT_S,
    MAX_DEBATE_ROUNDS,
)
from .argument import Argument
from .debate_round import DebateRound


@dataclass
class DebateParticipant:
    participant_id: str
    role:           DebateRole = DebateRole.PROPONENT
    weight:         float      = 1.0
    joined_at:      float      = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "participant_id": self.participant_id,
            "role":           self.role.value,
            "weight":         round(self.weight, 4),
            "joined_at":      self.joined_at,
        }


class DebateSession:
    """
    Container for all state of one multi-round debate.
    Thread-safe.
    """

    def __init__(
        self,
        *,
        debate_id:           str   = "",
        session_id:          str   = "",
        topic:               str   = "",
        proposition:         str   = "",
        consensus_threshold: float = 0.65,
        max_rounds:          int   = MAX_DEBATE_ROUNDS,
        timeout_s:           float = DEFAULT_DEBATE_TIMEOUT_S,
    ) -> None:
        self.debate_id:          str                          = debate_id or str(uuid.uuid4())
        self.session_id:         str                          = session_id
        self.topic:              str                          = topic
        self.proposition:        str                          = proposition
        self.consensus_threshold: float                       = consensus_threshold
        self.max_rounds:         int                          = max_rounds
        self.timeout_s:          float                        = timeout_s
        self.status:             DebateStatus                 = DebateStatus.PENDING
        self._participants:      dict[str, DebateParticipant] = {}
        self._rounds:            list[DebateRound]            = []
        self._created_at:        float                        = time.time()
        self._started_at:        float | None                 = None
        self._ended_at:          float | None                 = None
        self._lock:              threading.RLock              = threading.RLock()

    # -- Participants ──────────────────────────────────────────────────────────

    def add_participant(
        self,
        participant_id: str,
        role:           DebateRole = DebateRole.PROPONENT,
        weight:         float      = 1.0,
    ) -> DebateParticipant:
        with self._lock:
            p = DebateParticipant(
                participant_id=participant_id, role=role, weight=weight
            )
            self._participants[participant_id] = p
            return p

    def get_participant(self, participant_id: str) -> DebateParticipant | None:
        with self._lock:
            return self._participants.get(participant_id)

    @property
    def participant_count(self) -> int:
        with self._lock:
            return len(self._participants)

    @property
    def participants(self) -> list[DebateParticipant]:
        with self._lock:
            return list(self._participants.values())

    # -- Rounds ────────────────────────────────────────────────────────────────

    def start_round(self, topic: str | None = None) -> DebateRound:
        with self._lock:
            if self.status == DebateStatus.PENDING:
                self.status      = DebateStatus.ACTIVE
                self._started_at = time.time()

            round_num = len(self._rounds) + 1
            rnd = DebateRound(
                debate_id    = self.debate_id,
                round_number = round_num,
                topic        = topic or self.topic,
            )
            self._rounds.append(rnd)
            return rnd

    def current_round(self) -> DebateRound | None:
        with self._lock:
            return self._rounds[-1] if self._rounds else None

    def close_current_round(self) -> DebateRound | None:
        rnd = self.current_round()
        if rnd is not None:
            rnd.close()
        return rnd

    @property
    def rounds(self) -> list[DebateRound]:
        with self._lock:
            return list(self._rounds)

    @property
    def round_count(self) -> int:
        with self._lock:
            return len(self._rounds)

    # -- Status ────────────────────────────────────────────────────────────────

    def end(self, status: DebateStatus = DebateStatus.COMPLETED) -> None:
        with self._lock:
            self.status    = status
            self._ended_at = time.time()

    @property
    def is_timed_out(self) -> bool:
        if self._started_at is None:
            return False
        return time.time() - self._started_at > self.timeout_s

    # -- Consensus detection ───────────────────────────────────────────────────

    def is_consensus_reached(self) -> bool:
        """True if the most recent closed round's consensus score meets the threshold."""
        with self._lock:
            closed = [r for r in self._rounds if r.ended_at is not None]
        if not closed:
            return False
        return closed[-1].consensus_score >= self.consensus_threshold

    def all_arguments(self) -> list[Argument]:
        with self._lock:
            args: list[Argument] = []
            for rnd in self._rounds:
                args.extend(rnd.arguments)
            return args

    # -- Properties ────────────────────────────────────────────────────────────

    @property
    def duration_ms(self) -> float:
        if self._started_at is None:
            return 0.0
        end = self._ended_at or time.time()
        return (end - self._started_at) * 1_000

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def started_at(self) -> float | None:
        return self._started_at

    @property
    def ended_at(self) -> float | None:
        return self._ended_at

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "debate_id":           self.debate_id,
                "session_id":          self.session_id,
                "topic":               self.topic,
                "proposition":         self.proposition,
                "status":              self.status.value,
                "consensus_threshold": self.consensus_threshold,
                "max_rounds":          self.max_rounds,
                "timeout_s":           self.timeout_s,
                "participant_count":   len(self._participants),
                "round_count":         len(self._rounds),
                "duration_ms":         round(self.duration_ms, 2),
                "created_at":          self._created_at,
                "started_at":          self._started_at,
                "ended_at":            self._ended_at,
            }
