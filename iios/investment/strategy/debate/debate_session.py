"""iios/investment/strategy/debate/debate_session.py
DebateSession — the central mutable object for one debate.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.debate.debate_constants import DebatePhase, DebateStatus
from iios.investment.strategy.debate.debate_state import DebateState, DebateStateError
from iios.investment.strategy.debate.debate_context import DebateContext
from iios.investment.strategy.debate.argument_manager import Argument, ArgumentManager, Rebuttal
from iios.investment.strategy.debate.evidence_registry import EvidenceRegistry
from iios.investment.strategy.debate.voting_engine import Vote
from iios.investment.strategy.debate.consensus_engine import ConsensusResult


class DebateSession:
    """
    Central mutable object for one debate session.
    All mutation is thread-safe via an RLock.
    """

    def __init__(
        self,
        context:    DebateContext,
        session_id: Optional[str] = None,
    ) -> None:
        self._lock     = threading.RLock()
        self.session_id = session_id or str(uuid.uuid4())
        self.context    = context

        self._state     = DebateState()
        self._arg_mgr   = ArgumentManager(self.session_id)
        self._evidence  = EvidenceRegistry(self.session_id)
        self._votes:    List[Vote]            = []
        self._consensus: Optional[ConsensusResult] = None
        self._participants: List[str]          = []   # participant_ids
        self._final_opinions: Dict[str, str]   = {}   # participant_id → opinion text
        self._error:    Optional[str]          = None
        self._started_at: Optional[datetime]   = None
        self._completed_at: Optional[datetime] = None

    # ── Delegate properties ───────────────────────────────────────────────────

    @property
    def phase(self) -> DebatePhase:
        return self._state.phase

    @property
    def status(self) -> DebateStatus:
        return self._state.status

    @property
    def argument_manager(self) -> ArgumentManager:
        return self._arg_mgr

    @property
    def evidence_registry(self) -> EvidenceRegistry:
        return self._evidence

    @property
    def consensus(self) -> Optional[ConsensusResult]:
        with self._lock:
            return self._consensus

    @property
    def is_running(self) -> bool:
        return self._state.is_running

    @property
    def is_terminal(self) -> bool:
        return self._state.is_terminal

    @property
    def duration_ms(self) -> Optional[float]:
        with self._lock:
            if self._started_at is None:
                return None
            end = self._completed_at or datetime.now(timezone.utc)
            return round((end - self._started_at).total_seconds() * 1000, 2)

    # ── State transitions ─────────────────────────────────────────────────────

    def start(self) -> None:
        with self._lock:
            self._state.start()
            self._started_at = datetime.now(timezone.utc)

    def advance_phase(self, target: DebatePhase) -> None:
        with self._lock:
            self._state.advance(target)
            if target == DebatePhase.CLOSED:
                self._completed_at = datetime.now(timezone.utc)

    def mark_failed(self, reason: str) -> None:
        with self._lock:
            self._state.fail(reason)
            self._error        = reason
            self._completed_at = datetime.now(timezone.utc)

    def mark_cancelled(self) -> None:
        with self._lock:
            self._state.cancel()
            self._completed_at = datetime.now(timezone.utc)

    # ── Data mutation ─────────────────────────────────────────────────────────

    def add_participant(self, participant_id: str) -> None:
        with self._lock:
            if participant_id not in self._participants:
                self._participants.append(participant_id)

    def add_argument(self, arg: Argument, round_num: int = 1) -> None:
        with self._lock:
            self._arg_mgr.add_argument(arg, round_num)

    def add_rebuttal(self, rebuttal: Rebuttal) -> None:
        with self._lock:
            self._arg_mgr.add_rebuttal(rebuttal)

    def add_vote(self, vote: Vote) -> None:
        with self._lock:
            self._votes.append(vote)

    def set_consensus(self, result: ConsensusResult) -> None:
        with self._lock:
            self._consensus = result

    def add_final_opinion(self, participant_id: str, opinion: str) -> None:
        with self._lock:
            self._final_opinions[participant_id] = opinion

    # ── Queries ───────────────────────────────────────────────────────────────

    def votes(self) -> List[Vote]:
        with self._lock:
            return list(self._votes)

    def participants(self) -> List[str]:
        with self._lock:
            return list(self._participants)

    def final_opinions(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._final_opinions)

    def phase_history(self) -> List[dict]:
        return self._state.phase_history()

    def error(self) -> Optional[str]:
        with self._lock:
            return self._error

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_id":         self.session_id,
                "context_id":         self.context.context_id,
                "symbol":             self.context.symbol,
                "strategy_name":      self.context.strategy_name,
                "phase":              self.phase.value,
                "status":             self.status.value,
                "participants":       list(self._participants),
                "argument_count":     self._arg_mgr.argument_count(),
                "rebuttal_count":     self._arg_mgr.rebuttal_count(),
                "vote_count":         len(self._votes),
                "evidence_count":     self._evidence.count(),
                "consensus_reached":  self._consensus.consensus_reached if self._consensus else None,
                "consensus_level":    self._consensus.consensus_level.value if self._consensus else None,
                "phase_history":      self._state.phase_history(),
                "duration_ms":        self.duration_ms,
                "started_at":         self._started_at.isoformat() if self._started_at else None,
                "completed_at":       self._completed_at.isoformat() if self._completed_at else None,
                "error":              self._error,
            }
