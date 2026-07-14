"""iios/investment/decision/committee/committee_state.py
CommitteeState — mutable thread-safe state for one committee session.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.decision.committee.committee_constants import (
    CommitteePosition,
    SessionState,
    VoteType,
)
from iios.investment.decision.committee.committee_member import MemberOpinion


class CommitteeState:
    """
    Thread-safe mutable container tracking all session actions.
    Transitions: INITIALIZING → CONVENED → REVIEWING → DELIBERATING → VOTING → CONCLUDED
    """

    def __init__(self, session_id: str, decision_id: str) -> None:
        self._lock:       threading.RLock = threading.RLock()
        self._session_id  = session_id
        self._decision_id = decision_id
        self._state       = SessionState.INITIALIZING
        self._opinions:   List[MemberOpinion] = []
        self._round_count = 0
        self._challenge_count = 0
        self._resolved_challenge_count = 0
        self._convened_at:  Optional[datetime] = None
        self._concluded_at: Optional[datetime] = None
        self._version_history: List[Dict[str, Any]] = []

    # ── State transitions ──────────────────────────────────────────────────────

    def transition(self, new_state: SessionState) -> None:
        with self._lock:
            self._record_version(self._state.value, new_state.value)
            self._state = new_state
            if new_state == SessionState.CONVENED:
                self._convened_at = datetime.now(timezone.utc)
            elif new_state in {SessionState.CONCLUDED, SessionState.FAILED}:
                self._concluded_at = datetime.now(timezone.utc)

    @property
    def current_state(self) -> SessionState:
        with self._lock:
            return self._state

    @property
    def is_active(self) -> bool:
        return self.current_state.is_active

    # ── Opinion recording ─────────────────────────────────────────────────────

    def record_opinion(self, opinion: MemberOpinion) -> None:
        with self._lock:
            # Replace existing opinion for this member if already present
            self._opinions = [o for o in self._opinions if o.member_id != opinion.member_id]
            self._opinions.append(opinion)

    def get_opinions(self) -> List[MemberOpinion]:
        with self._lock:
            return list(self._opinions)

    def opinion_for(self, member_id: str) -> Optional[MemberOpinion]:
        with self._lock:
            for o in self._opinions:
                if o.member_id == member_id:
                    return o
        return None

    # ── Rounds and challenges ─────────────────────────────────────────────────

    def advance_round(self) -> int:
        with self._lock:
            self._round_count += 1
            return self._round_count

    def record_challenge(self) -> None:
        with self._lock:
            self._challenge_count += 1

    def record_resolved_challenge(self) -> None:
        with self._lock:
            self._resolved_challenge_count += 1

    @property
    def round_count(self) -> int:
        with self._lock:
            return self._round_count

    @property
    def challenge_count(self) -> int:
        with self._lock:
            return self._challenge_count

    @property
    def resolved_challenge_count(self) -> int:
        with self._lock:
            return self._resolved_challenge_count

    # ── Metadata ───────────────────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def decision_id(self) -> str:
        return self._decision_id

    @property
    def convened_at(self) -> Optional[datetime]:
        with self._lock:
            return self._convened_at

    @property
    def concluded_at(self) -> Optional[datetime]:
        with self._lock:
            return self._concluded_at

    @property
    def duration_ms(self) -> float:
        with self._lock:
            if self._convened_at and self._concluded_at:
                delta = self._concluded_at - self._convened_at
                return delta.total_seconds() * 1000.0
        return 0.0

    def version_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._version_history)

    # ── Private ────────────────────────────────────────────────────────────────

    def _record_version(self, from_state: str, to_state: str) -> None:
        self._version_history.append({
            "from": from_state,
            "to":   to_state,
            "at":   datetime.now(timezone.utc).isoformat(),
        })
