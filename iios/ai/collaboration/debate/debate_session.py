"""
debate_session.py -- iios.ai.collaboration.debate
===================================================
:class:`DebateSession` — mutable coordinator for one structured debate.

Life-cycle::

    ds = DebateSession(session_id, topic)
    ds.open()
    ds.submit_position(agent_id, PositionType.FOR, argument="...")
    round_ = ds.close_round()
    ds.next_round()          # optional — start round 2
    result = ds.close()      # DebateResult

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
from threading import RLock
from typing import FrozenSet, List, Optional

from ..exceptions.collaboration_exceptions import (
    AIDebateAlreadyClosedError,
    AIDebateRoundError,
)
from .debate_position import DebatePosition, PositionType
from .debate_result   import DebateResult
from .debate_round    import DebateRound, RoundStatus


class DebateSession:
    """
    Mutable state-machine for one structured debate inside a collaboration session.

    Thread-safe via an internal :class:`RLock`.
    """

    def __init__(self, session_id: str, topic: str) -> None:
        self._session_id:    str                     = session_id
        self._topic:         str                     = topic
        self._lock:          RLock                   = RLock()
        self._is_open:       bool                    = False
        self._is_closed:     bool                    = False
        self._round_number:  int                     = 0
        self._round_opened:  float                   = 0.0
        self._round_open:    bool                    = False
        self._current_round_positions: List[DebatePosition] = []
        self._closed_rounds: List[DebateRound]       = []
        self._result:        Optional[DebateResult]  = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def open(self) -> None:
        """Open the debate and start the first round."""
        with self._lock:
            if self._is_closed:
                raise AIDebateAlreadyClosedError(f"Debate for session {self._session_id} is already closed.")
            if self._is_open:
                return
            self._is_open     = True
            self._round_number = 1
            self._round_opened = time.time()
            self._round_open  = True

    def close_round(self) -> DebateRound:
        """
        Close the current round, freeze all its positions into a :class:`DebateRound`.

        Returns the closed round.
        """
        with self._lock:
            if not self._is_open or self._is_closed:
                raise AIDebateAlreadyClosedError(f"Debate for session {self._session_id} is not open.")
            if not self._round_open:
                raise AIDebateRoundError("No open round to close.")
            round_ = DebateRound.close(
                session_id   = self._session_id,
                round_number = self._round_number,
                topic        = self._topic,
                positions    = frozenset(self._current_round_positions),
                opened_at    = self._round_opened,
                status       = RoundStatus.CLOSED,
            )
            self._closed_rounds.append(round_)
            self._current_round_positions = []
            self._round_open = False
            return round_

    def next_round(self) -> None:
        """Close the current round (if open) and start the next one."""
        with self._lock:
            if not self._is_open or self._is_closed:
                raise AIDebateAlreadyClosedError(f"Debate for session {self._session_id} is not open.")
            if self._round_open:
                self.close_round()
            self._round_number += 1
            self._round_opened  = time.time()
            self._round_open    = True

    def close(self) -> DebateResult:
        """
        Close the debate and return the :class:`DebateResult`.

        Automatically closes the current round if still open.
        """
        with self._lock:
            if self._is_closed:
                if self._result:
                    return self._result
                raise AIDebateAlreadyClosedError(f"Debate for session {self._session_id} is already closed.")
            if not self._is_open:
                raise AIDebateRoundError("Cannot close a debate that was never opened.")
            if self._round_open:
                self.close_round()
            self._is_open   = False
            self._is_closed = True
            self._result = DebateResult.from_rounds(self._session_id, self._closed_rounds)
            return self._result

    # ── Position submission ───────────────────────────────────────────────────

    def submit_position(
        self,
        agent_id:      str,
        position_type: PositionType,
        argument:      str             = "",
        evidence:      FrozenSet[str]  = frozenset(),
        confidence:    float           = 1.0,
        responds_to:   Optional[str]   = None,
    ) -> DebatePosition:
        """Submit a position from *agent_id* in the current round."""
        with self._lock:
            if not self._is_open or self._is_closed:
                raise AIDebateAlreadyClosedError(f"Debate for session {self._session_id} is not open.")
            if not self._round_open:
                raise AIDebateRoundError("No open round to submit to. Call next_round() first.")
            position = DebatePosition.create(
                session_id    = self._session_id,
                agent_id      = agent_id,
                round_number  = self._round_number,
                position_type = position_type,
                argument      = argument,
                evidence      = evidence,
                confidence    = confidence,
                responds_to   = responds_to,
            )
            self._current_round_positions.append(position)
            return position

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_open(self) -> bool:
        return self._is_open and not self._is_closed

    @property
    def is_closed(self) -> bool:
        return self._is_closed

    @property
    def current_round_number(self) -> int:
        return self._round_number

    @property
    def all_positions(self) -> List[DebatePosition]:
        with self._lock:
            return [p for r in self._closed_rounds for p in r.positions] + list(self._current_round_positions)

    @property
    def closed_rounds(self) -> List[DebateRound]:
        with self._lock:
            return list(self._closed_rounds)

    @property
    def result(self) -> Optional[DebateResult]:
        return self._result
