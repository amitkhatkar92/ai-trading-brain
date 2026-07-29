"""
collaboration_manager.py -- iios.ai.collaboration.manager
===========================================================
:class:`CollaborationManager` — creates and tracks :class:`CollaborationSession` objects.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..consensus.consensus_manager   import ConsensusManager
from ..core.collaboration_metadata  import CollaborationMetadata, CollaborationType
from ..debate.debate_manager        import DebateManager
from ..escalation.escalation_manager import EscalationManager
from ..events.collaboration_event_bus import CollaborationEventBus
from ..exceptions.collaboration_exceptions import (
    AICollaborationSessionAlreadyExistsError,
    AICollaborationSessionNotFoundError,
)
from ..messaging.message_bus   import MessageBus
from ..session.collaboration_session import CollaborationSession
from ..snapshot.collaboration_snapshot import (
    CollaborationFrameworkSnapshot,
    CollaborationSessionSnapshot,
)


class CollaborationManager:
    """
    Thread-safe registry of active :class:`CollaborationSession` objects.

    Shared dependencies (event_bus, debate_manager, etc.) are injected once
    and reused across all sessions.
    """

    def __init__(
        self,
        event_bus:          CollaborationEventBus,
        debate_manager:     DebateManager,
        consensus_manager:  ConsensusManager,
        escalation_manager: EscalationManager,
        message_bus:        MessageBus,
    ) -> None:
        self._event_bus          = event_bus
        self._debate_manager     = debate_manager
        self._consensus_manager  = consensus_manager
        self._escalation_manager = escalation_manager
        self._message_bus        = message_bus

        self._lock:     threading.RLock                       = threading.RLock()
        self._sessions: Dict[str, CollaborationSession]       = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(
        self,
        topic:              str,
        collaboration_type: CollaborationType = CollaborationType.DEBATE,
        created_by:         str               = "system",
        **kwargs,
    ) -> CollaborationSession:
        """Create and open a new :class:`CollaborationSession`."""
        metadata = CollaborationMetadata.create(
            topic               = topic,
            collaboration_type  = collaboration_type,
            created_by          = created_by,
            **kwargs,
        )
        with self._lock:
            if metadata.session_id in self._sessions:
                raise AICollaborationSessionAlreadyExistsError(
                    f"Session '{metadata.session_id}' already exists."
                )
            session = CollaborationSession(
                metadata           = metadata,
                event_bus          = self._event_bus,
                debate_manager     = self._debate_manager,
                consensus_manager  = self._consensus_manager,
                escalation_manager = self._escalation_manager,
                message_bus        = self._message_bus,
            )
            session.open()
            self._sessions[metadata.session_id] = session
        return session

    def get(self, session_id: str) -> CollaborationSession:
        with self._lock:
            s = self._sessions.get(session_id)
        if s is None:
            raise AICollaborationSessionNotFoundError(
                f"Collaboration session '{session_id}' not found."
            )
        return s

    def list_sessions(self) -> List[CollaborationSession]:
        with self._lock:
            return list(self._sessions.values())

    def remove(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot_session(self, session_id: str) -> CollaborationSessionSnapshot:
        s = self.get(session_id)
        return self._session_snapshot(s)

    def framework_snapshot(
        self,
        system_id: str,
        version:   str,
        is_running: bool,
    ) -> CollaborationFrameworkSnapshot:
        with self._lock:
            sessions = list(self._sessions.values())
        snaps = frozenset(self._session_snapshot(s) for s in sessions)
        return CollaborationFrameworkSnapshot.capture(
            system_id        = system_id,
            version          = version,
            is_running       = is_running,
            sessions         = snaps,
            events_published = self._event_bus.published_count,
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _session_snapshot(self, s: CollaborationSession) -> CollaborationSessionSnapshot:
        ctx = s.context()
        cns = s.consensus
        return CollaborationSessionSnapshot.capture(
            session_id           = s.session_id,
            topic                = s.metadata.topic,
            collaboration_type   = s.metadata.collaboration_type,
            status               = s.status,
            participant_count    = s.participant_count,
            current_round        = ctx.current_round,
            total_rounds         = ctx.total_rounds,
            message_count        = self._message_bus.message_count(s.session_id),
            vote_counts          = cns.vote_counts if cns else frozenset(),
            winning_position     = cns.winning_position if cns else None,
            consensus_confidence = cns.confidence if cns else 0.0,
        )
