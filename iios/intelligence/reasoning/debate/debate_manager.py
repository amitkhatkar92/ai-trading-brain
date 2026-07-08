"""
iios/intelligence/reasoning/debate/debate_manager.py
====================================================
DebateManager — high-level lifecycle manager for debate sessions.
Provides the public API for starting, conducting, and retrieving debates.
"""
from __future__ import annotations

import threading
from typing import Any, Callable

from ..reasoning_constants import (
    ArgumentType, DebateRole, DebateStatus, MAX_DEBATE_ROUNDS,
    DEFAULT_DEBATE_TIMEOUT_S,
)
from ..reasoning_exceptions import (
    DebateNotFoundError, DebateDeadlockError, DebateTimeoutError,
    InsufficientParticipantsError,
)
from .argument import Argument
from .debate_engine import DebateEngine, get_debate_engine
from .debate_session import DebateSession
from .debate_summary import DebateSummary


# Callable that the manager invokes each round to collect arguments.
# Signature: (session: DebateSession, round_number: int) -> list[Argument]
ArgumentProviderFn = Callable[[DebateSession, int], list[Argument]]


class DebateManager:
    """
    Orchestrates the full debate lifecycle.

    Usage
    -----
    mgr = get_debate_manager()
    mgr.initialize()

    summary = mgr.conduct_debate(
        session_id    = "sess-1",
        topic         = "Market direction",
        proposition   = "The market will rise tomorrow",
        participants  = [("analyst1", DebateRole.PROPONENT, 1.0),
                         ("analyst2", DebateRole.OPPONENT,  1.0)],
        argument_fn   = my_argument_provider,
    )
    """

    def __init__(self, engine: DebateEngine | None = None) -> None:
        self._engine:       DebateEngine          = engine or get_debate_engine()
        self._initialized:  bool                  = False
        self._lock:         threading.RLock        = threading.RLock()

    # -- Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        with self._lock:
            self._initialized = True

    def shutdown(self) -> None:
        with self._lock:
            self._initialized = False

    # -- Session management ────────────────────────────────────────────────────

    def start_debate(
        self,
        session_id:          str,
        topic:               str,
        proposition:         str,
        participants:        list[tuple[str, DebateRole, float]] | None = None,
        consensus_threshold: float = 0.65,
        max_rounds:          int   = MAX_DEBATE_ROUNDS,
        timeout_s:           float = DEFAULT_DEBATE_TIMEOUT_S,
        debate_id:           str   = "",
    ) -> DebateSession:
        """Create a new debate session and register participants."""
        ds = self._engine.create_session(
            session_id          = session_id,
            topic               = topic,
            proposition         = proposition,
            consensus_threshold = consensus_threshold,
            max_rounds          = max_rounds,
            timeout_s           = timeout_s,
            debate_id           = debate_id,
        )
        for pid, role, weight in (participants or []):
            self._engine.add_participant(ds.debate_id, pid, role, weight)
        return ds

    def get_debate(self, debate_id: str) -> DebateSession:
        return self._engine.get_session(debate_id)

    def list_debates(self, session_id: str | None = None) -> list[DebateSession]:
        with self._engine._lock:
            sessions = list(self._engine._sessions.values())
        if session_id:
            sessions = [s for s in sessions if s.session_id == session_id]
        return sessions

    # -- Conduct ───────────────────────────────────────────────────────────────

    def conduct_debate(
        self,
        session_id:          str,
        topic:               str,
        proposition:         str,
        argument_fn:         ArgumentProviderFn,
        participants:        list[tuple[str, DebateRole, float]] | None = None,
        consensus_threshold: float = 0.65,
        max_rounds:          int   = MAX_DEBATE_ROUNDS,
        timeout_s:           float = DEFAULT_DEBATE_TIMEOUT_S,
        min_participants:    int   = 2,
        debate_id:           str   = "",
    ) -> DebateSummary:
        """
        Run a complete debate and return its summary.

        Parameters
        ----------
        session_id          : Owning reasoning session.
        topic               : General discussion topic.
        proposition         : The specific statement being debated.
        argument_fn         : Called each round to collect arguments.
                              Signature: (DebateSession, round_number) → list[Argument]
        participants        : (id, role, weight) tuples.
        consensus_threshold : Agreement score needed to end debate early.
        max_rounds          : Hard cap on rounds.
        timeout_s           : Wall-clock timeout for the entire debate.
        min_participants    : Minimum participants required.
        """
        # Validate participant count
        n_participants = len(participants or [])
        if n_participants < min_participants:
            raise InsufficientParticipantsError(min_participants, n_participants)

        ds = self.start_debate(
            session_id          = session_id,
            topic               = topic,
            proposition         = proposition,
            participants        = participants,
            consensus_threshold = consensus_threshold,
            max_rounds          = max_rounds,
            timeout_s           = timeout_s,
            debate_id           = debate_id,
        )
        debate_id_used = ds.debate_id

        import time
        t_start = time.time()

        for round_num in range(1, max_rounds + 1):
            # Timeout check
            if time.time() - t_start > timeout_s:
                ds.end(DebateStatus.FAILED)
                raise DebateTimeoutError(debate_id_used, timeout_s)

            # Open round
            self._engine.start_round(debate_id_used)

            # Collect arguments from provider
            try:
                args = argument_fn(ds, round_num)
            except Exception:
                args = []

            # Submit each argument
            for arg in args:
                arg.debate_id    = debate_id_used
                arg.session_id   = session_id
                arg.round_number = round_num
                rnd = ds.current_round()
                if rnd is not None:
                    rnd.add_argument(arg)

            # Close round
            self._engine.close_round(debate_id_used)

            # Check for consensus
            reached, score = self._engine.check_consensus(debate_id_used)
            if reached:
                ds.end(DebateStatus.CONSENSUS_REACHED)
                return self._engine.summarize(debate_id_used)

        # Exhausted rounds without consensus → deadlock
        ds.end(DebateStatus.DEADLOCKED)
        return self._engine.summarize(debate_id_used)

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "initialized": self._initialized,
            "debates":     self._engine.stats(),
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK    = threading.Lock()
_MANAGER: DebateManager | None = None


def get_debate_manager() -> DebateManager:
    global _MANAGER
    if _MANAGER is None:
        with _LOCK:
            if _MANAGER is None:
                _MANAGER = DebateManager()
    return _MANAGER


def reset_debate_manager() -> None:
    global _MANAGER
    with _LOCK:
        _MANAGER = None
