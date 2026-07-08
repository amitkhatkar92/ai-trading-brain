"""
iios/intelligence/reasoning/debate/debate_engine.py
===================================================
DebateEngine — core logic for argument processing and consensus detection.
"""
from __future__ import annotations

import threading
import uuid
from collections import defaultdict
from typing import Any

from ..reasoning_constants import (
    ArgumentType, DebateRole, DebateStatus,
)
from ..reasoning_exceptions import (
    DebateDeadlockError, DebateNotFoundError, DebateTimeoutError,
    InsufficientParticipantsError,
)
from .argument import Argument
from .debate_round import DebateRound
from .debate_session import DebateParticipant, DebateSession
from .debate_summary import DebateSummary


class DebateEngine:
    """
    Manages the collection of DebateSessions and runs multi-round debate logic.

    Responsibilities
    ----------------
    - Create and store debate sessions.
    - Accept argument submissions.
    - After each round, compute consensus and decide whether to continue.
    - Summarise completed debates.
    """

    MIN_PARTICIPANTS = 2

    def __init__(self) -> None:
        self._sessions: dict[str, DebateSession] = {}
        self._lock:     threading.RLock           = threading.RLock()

    # -- Session management ────────────────────────────────────────────────────

    def create_session(
        self,
        *,
        session_id:          str   = "",
        topic:               str   = "",
        proposition:         str   = "",
        consensus_threshold: float = 0.65,
        max_rounds:          int   = 10,
        timeout_s:           float = 120.0,
        debate_id:           str   = "",
    ) -> DebateSession:
        ds = DebateSession(
            debate_id           = debate_id or str(uuid.uuid4()),
            session_id          = session_id,
            topic               = topic,
            proposition         = proposition,
            consensus_threshold = consensus_threshold,
            max_rounds          = max_rounds,
            timeout_s           = timeout_s,
        )
        with self._lock:
            self._sessions[ds.debate_id] = ds
        return ds

    def get_session(self, debate_id: str) -> DebateSession:
        with self._lock:
            ds = self._sessions.get(debate_id)
        if ds is None:
            raise DebateNotFoundError(debate_id)
        return ds

    def add_participant(
        self,
        debate_id:      str,
        participant_id: str,
        role:           DebateRole = DebateRole.PROPONENT,
        weight:         float      = 1.0,
    ) -> DebateParticipant:
        return self.get_session(debate_id).add_participant(
            participant_id, role, weight
        )

    # -- Argument submission ───────────────────────────────────────────────────

    def submit_argument(
        self,
        debate_id:      str,
        participant_id: str,
        argument_type:  ArgumentType,
        claim:          str,
        reasoning:      str      = "",
        evidence_ids:   list[str] | None = None,
        confidence:     float    = 0.5,
        weight:         float    = 1.0,
        rebuttal_to:    str | None = None,
    ) -> Argument:
        ds  = self.get_session(debate_id)
        rnd = ds.current_round()
        if rnd is None or rnd.ended_at is not None:
            raise ValueError(
                f"No active round in debate {debate_id!r}; call start_round() first"
            )
        arg = Argument(
            debate_id      = debate_id,
            session_id     = ds.session_id,
            participant_id = participant_id,
            argument_type  = argument_type,
            claim          = claim,
            reasoning      = reasoning,
            evidence_ids   = evidence_ids or [],
            confidence     = confidence,
            weight         = weight,
            rebuttal_to    = rebuttal_to,
        )
        rnd.add_argument(arg)
        return arg

    # -- Round management ──────────────────────────────────────────────────────

    def start_round(self, debate_id: str, topic: str | None = None) -> DebateRound:
        ds = self.get_session(debate_id)
        if ds.round_count >= ds.max_rounds:
            raise DebateDeadlockError(debate_id, ds.round_count)
        return ds.start_round(topic)

    def close_round(self, debate_id: str) -> DebateRound:
        ds  = self.get_session(debate_id)
        rnd = ds.close_current_round()
        if rnd is None:
            raise ValueError(f"No open round in debate {debate_id!r}")
        return rnd

    # -- Consensus & termination ───────────────────────────────────────────────

    def check_consensus(self, debate_id: str) -> tuple[bool, float]:
        """Return (reached, score) based on the last closed round."""
        ds = self.get_session(debate_id)
        closed = [r for r in ds.rounds if r.ended_at is not None]
        if not closed:
            return False, 0.0
        score = closed[-1].consensus_score
        return score >= ds.consensus_threshold, score

    def compute_dominant_position(
        self, ds: DebateSession
    ) -> tuple[str | None, float]:
        """Identify the weighted-dominant claim and its confidence."""
        all_args = ds.all_arguments()
        if not all_args:
            return None, 0.0

        tally: dict[str, float] = defaultdict(float)
        for arg in all_args:
            tally[arg.claim] += arg.weighted_confidence

        if not tally:
            return None, 0.0

        best_claim = max(tally, key=lambda c: tally[c])
        total_w    = sum(tally.values())
        confidence = tally[best_claim] / total_w if total_w > 0 else 0.0
        return best_claim, confidence

    def collect_minority_opinions(
        self, ds: DebateSession, dominant_claim: str | None
    ) -> list[dict[str, Any]]:
        """Collect unique non-dominant opposing arguments."""
        seen:    set[str]       = set()
        minority: list[dict]    = []
        for arg in ds.all_arguments():
            if arg.is_opposing and arg.claim != dominant_claim:
                if arg.claim not in seen:
                    seen.add(arg.claim)
                    minority.append({
                        "participant_id": arg.participant_id,
                        "claim":          arg.claim,
                        "reasoning":      arg.reasoning,
                        "confidence":     round(arg.confidence, 4),
                    })
        return minority

    # -- Summarise ─────────────────────────────────────────────────────────────

    def summarize(self, debate_id: str) -> DebateSummary:
        ds          = self.get_session(debate_id)
        all_args    = ds.all_arguments()
        closed      = [r for r in ds.rounds if r.ended_at is not None]
        final_score = closed[-1].consensus_score if closed else 0.0
        reached     = final_score >= ds.consensus_threshold
        dominant, dom_conf = self.compute_dominant_position(ds)
        minority    = self.collect_minority_opinions(ds, dominant)

        # Deduplicate evidence IDs
        key_eids: list[str] = []
        seen_e: set[str]    = set()
        for arg in all_args:
            for eid in arg.evidence_ids:
                if eid not in seen_e:
                    seen_e.add(eid)
                    key_eids.append(eid)

        status = DebateStatus.CONSENSUS_REACHED if reached else (
            DebateStatus.DEADLOCKED if ds.round_count >= ds.max_rounds
            else ds.status
        )

        return DebateSummary(
            debate_id           = ds.debate_id,
            session_id          = ds.session_id,
            topic               = ds.topic,
            proposition         = ds.proposition,
            status              = status,
            consensus_reached   = reached,
            total_rounds        = ds.round_count,
            total_arguments     = len(all_args),
            supporting_count    = sum(1 for a in all_args if a.is_supporting),
            opposing_count      = sum(1 for a in all_args if a.is_opposing),
            dominant_position   = dominant,
            dominant_confidence = dom_conf,
            minority_opinions   = minority,
            consensus_score     = final_score,
            key_evidence_ids    = key_eids,
            participants        = [p.to_dict() for p in ds.participants],
            duration_ms         = ds.duration_ms,
        )

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = defaultdict(int)
            for ds in self._sessions.values():
                by_status[ds.status.value] += 1
            return {
                "total":     len(self._sessions),
                "by_status": dict(by_status),
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK   = threading.Lock()
_ENGINE: DebateEngine | None = None


def get_debate_engine() -> DebateEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = DebateEngine()
    return _ENGINE


def reset_debate_engine() -> None:
    global _ENGINE
    with _LOCK:
        _ENGINE = None
